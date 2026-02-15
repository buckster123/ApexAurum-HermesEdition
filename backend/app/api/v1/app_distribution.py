"""
ApexAurum Cloud - APK Distribution Endpoints

Public: version info + APK download
Admin: upload APK, update release metadata, list releases
Storage: Railway persistent volume at /data/apk/
"""

import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, status
from fastapi.responses import FileResponse, JSONResponse

from app.config import get_settings
from app.api.v1.admin import require_admin

router = APIRouter(prefix="/app", tags=["App Distribution"])

# ─── Storage paths ───────────────────────────────────────────────────

settings = get_settings()
APK_DIR = Path(settings.vault_path) / "apk"
RELEASE_JSON = APK_DIR / "release.json"

# Default release info (used when no release.json exists yet)
DEFAULT_RELEASE = {
    "version_name": "1.0.0",
    "version_code": 1,
    "min_sdk": 26,
    "min_android": "8.0 (Oreo)",
    "target_sdk": 35,
    "release_date": "2026-02-15",
    "changelog": [
        "Initial release of ApexPocket",
        "Four AI agents: AZOTH, ELYSIAN, VAJRA, KETHER",
        "Animated soul face with mood expressions",
        "Full chat with streaming responses",
        "Council deliberation viewer",
        "Village pulse with live WebSocket events",
        "SensorHead dashboard (cameras, thermal, environment)",
        "Sentinel motion detection with push alerts",
        "CerebroCortex memory browser and graph",
        "Morning briefings and smart nudges",
        "Music library with ExoPlayer streaming",
        "Agora social feed",
        "Home screen widget with soul state",
    ],
    "file_size_mb": 43,
    "apk_filename": None,
    "download_url": "https://backend-production-507c.up.railway.app/api/v1/app/download",
    "permissions": [
        "Internet access",
        "Camera (for Pocket Guardian mode)",
        "Notifications",
        "Foreground service (background sync)",
    ],
}


def _load_release() -> dict:
    """Load release metadata from disk, or return defaults."""
    if RELEASE_JSON.exists():
        try:
            return json.loads(RELEASE_JSON.read_text())
        except Exception:
            pass
    return DEFAULT_RELEASE.copy()


def _save_release(data: dict):
    """Persist release metadata to disk."""
    APK_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_JSON.write_text(json.dumps(data, indent=2))


def _find_apk() -> Path | None:
    """Find the current APK file on disk."""
    release = _load_release()
    filename = release.get("apk_filename")
    if filename:
        path = APK_DIR / filename
        if path.exists():
            return path
    # Fallback: find any .apk file
    if APK_DIR.exists():
        apks = sorted(APK_DIR.glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
        if apks:
            return apks[0]
    return None


# ─── Public Endpoints ────────────────────────────────────────────────

@router.get("/latest")
async def get_latest_version():
    """Return current APK version info for update checks and the download page."""
    release = _load_release()
    # Include whether an APK is actually available
    release["apk_available"] = _find_apk() is not None
    return JSONResponse(content=release)


@router.get("/download")
async def download_apk():
    """Serve the APK file for download."""
    apk_path = _find_apk()
    if apk_path is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_available",
                "message": "No APK has been uploaded yet. Check back soon!",
            },
        )
    return FileResponse(
        path=str(apk_path),
        filename=apk_path.name,
        media_type="application/vnd.android.package-archive",
    )


# ─── Admin Endpoints ─────────────────────────────────────────────────

@router.post("/upload")
async def upload_apk(
    file: UploadFile = FastAPIFile(...),
    admin=Depends(require_admin),
):
    """Upload a new APK release. Admin only."""
    if not file.filename or not file.filename.endswith(".apk"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an .apk file",
        )

    APK_DIR.mkdir(parents=True, exist_ok=True)

    # Read content
    content = await file.read()
    file_size_mb = round(len(content) / (1024 * 1024), 1)

    # Save with timestamp-prefixed name for versioning
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    filename = f"{timestamp}_{safe_name}"
    apk_path = APK_DIR / filename
    apk_path.write_bytes(content)

    # Update release metadata
    release = _load_release()
    release["apk_filename"] = filename
    release["file_size_mb"] = file_size_mb
    release["upload_date"] = datetime.utcnow().isoformat()
    _save_release(release)

    return {
        "status": "uploaded",
        "filename": filename,
        "size_mb": file_size_mb,
        "download_url": release["download_url"],
    }


@router.put("/release")
async def update_release_info(
    data: dict,
    admin=Depends(require_admin),
):
    """Update release metadata (version, changelog, etc). Admin only."""
    release = _load_release()

    # Allow updating specific fields
    allowed = {
        "version_name", "version_code", "min_sdk", "min_android",
        "target_sdk", "release_date", "changelog", "permissions",
    }
    updated = {}
    for key, value in data.items():
        if key in allowed:
            release[key] = value
            updated[key] = value

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No valid fields to update. Allowed: {sorted(allowed)}",
        )

    _save_release(release)
    return {"status": "updated", "fields": list(updated.keys())}


@router.get("/releases")
async def list_releases(admin=Depends(require_admin)):
    """List all uploaded APK files. Admin only."""
    if not APK_DIR.exists():
        return {"releases": [], "current": None}

    apks = []
    for f in sorted(APK_DIR.glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True):
        apks.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            "uploaded": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })

    release = _load_release()
    return {
        "releases": apks,
        "current": release.get("apk_filename"),
        "release_info": release,
    }


@router.delete("/releases/{filename}")
async def delete_release(filename: str, admin=Depends(require_admin)):
    """Delete an uploaded APK file. Admin only."""
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    apk_path = APK_DIR / filename
    if not apk_path.exists():
        raise HTTPException(status_code=404, detail="APK not found")

    # If deleting the current release, clear the filename
    release = _load_release()
    if release.get("apk_filename") == filename:
        release["apk_filename"] = None
        _save_release(release)

    apk_path.unlink()
    return {"status": "deleted", "filename": filename}
