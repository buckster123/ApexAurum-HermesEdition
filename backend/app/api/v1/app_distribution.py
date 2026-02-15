"""
ApexAurum Cloud - APK Distribution Endpoints

Public endpoints for mobile app version info and download.
No authentication required — anyone can check for updates or download.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter(prefix="/app", tags=["App Distribution"])

# ─── Current release info ────────────────────────────────────────────
# Update these values when publishing a new APK release.
CURRENT_RELEASE = {
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
    "download_url": "https://backend-production-507c.up.railway.app/api/v1/app/download",
    "permissions": [
        "Internet access",
        "Camera (for Pocket Guardian mode)",
        "Notifications",
        "Foreground service (background sync)",
    ],
}


@router.get("/latest")
async def get_latest_version():
    """Return current APK version info for update checks and the download page."""
    return JSONResponse(content=CURRENT_RELEASE)


@router.get("/download")
async def download_apk():
    """
    Redirect to the APK download.

    In production, this would serve from S3/MinIO or redirect to a CDN.
    For now, serves a placeholder response until the APK is uploaded.
    """
    # TODO: When APK is uploaded to S3/MinIO, redirect:
    # return RedirectResponse(url=s3_presigned_url, status_code=302)

    return JSONResponse(
        status_code=200,
        content={
            "status": "pending",
            "message": "APK distribution is being set up. Check back soon!",
            "version": CURRENT_RELEASE["version_name"],
            "instructions": [
                "For now, build from source or request a debug APK from the developer.",
                "The install script at scripts/install.sh handles full Pi setup.",
                "See /devices/build-guide for hardware assembly instructions.",
            ],
        },
    )
