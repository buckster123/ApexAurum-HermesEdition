---
name: blenderkit-assets
description: Sub-skill for the BlenderMCP skill covering BlenderKit integration — the largest asset library integrated into Blender (100,000+ assets). Use when the user wants to search, download, or use BlenderKit assets (models, materials, HDRIs, scenes, brushes, node groups, printables, add-ons) within a BlenderMCP workflow. Also covers Full Plan vs Free Plan differences, scripting BlenderKit via bpy, Blender 5.0 compatibility, cache management, troubleshooting, and workarounds for programmatic access. Trigger on any mention of "BlenderKit", "Full Plan", "asset library", or requests for large collections of production-ready 3D assets.
---

# BlenderKit Assets — Sub-Skill for BlenderMCP

> **Parent skill**: `blender-mcp/Blender-SKILL.md`
> **Relationship**: BlenderKit is a *separate* asset ecosystem from PolyHaven/Sketchfab/Hyper3D. It is **not** natively integrated into BlenderMCP's MCP tools, but can be accessed through `execute_blender_code` when the BlenderKit addon is installed in Blender.

---

## What is BlenderKit?

BlenderKit is the **largest asset library integrated directly into Blender** — a community-driven marketplace founded in 2017 with 100,000+ assets from 2,266+ creators. Unlike PolyHaven (which is a static open library), BlenderKit is a living ecosystem with validation, ratings, revenue sharing, and AI-powered search.

### Key Stats (September 2025 — 100K Milestone)

| Category | Free Count | Full Plan Count |
|----------|-----------|-----------------|
| **3D Models** | 17,000+ | 27,000+ |
| **Materials/Textures** | 26,000+ | ~40,000+ |
| **HDRIs** | 2,000+ | 1,500+ |
| **Scenes** | 250+ | 750+ |
| **Brushes** | 300+ | 5,000+ |
| **Node Groups** | — | Available (new in 3.15) |
| **Printables** | — | Available (new in 3.16) |
| **Add-ons** | Free + Paid | Separate purchase (new in 3.18) |
| **Total** | **~48,000** | **100,000+** |
| **Contributing Artists** | — | **2,266+** |

**Strengths**: Architecture, furniture, hard surface models, 3D plants/vegetation, FibreGuard fabric digital twins (1,000+).

---

## Plans & Pricing

| Plan | Price | Access | Storage | Notes |
|------|-------|--------|---------|-------|
| **Free (no account)** | $0 | ~48,000 free assets | — | No login required for downloads |
| **Free (registered)** | $0 | Same + bookmarks, ratings | — | Faster workflow with account |
| **Full Plan** | **$14.90/mo** or **$108/yr** | All 100,000+ assets | 2 GiB private | Revenue under $100K/yr. 75% goes to creators + Blender dev fund |
| **Business Plan** | **$40/mo** or **$300/yr** | All assets | 100 GiB private | Revenue over $100K/yr or teams/studios |

- **Add-ons** are sold separately (not included in Full Plan subscription)
- **Student discount**: 50% off Full Plan with verified student email
- All assets are **Royalty-Free (RF)** or **CC0** — commercial use in projects allowed
- You can't resell raw assets, but can use them in commercial projects
- Pricing was increased in 2025 from earlier rates

---

## Asset Types in Detail

### 1. 3D Models
**Strengths**: Architectural assets, household objects, props, vehicles, weapons, hard surface, 3D plants
**Categories**: Architecture, Animals, Characters, Electronics, Food, Furniture, Interior, Nature, Sports, Transport, Weapons, and many more
**Filters**: Style (realistic/painted/polygonal), poly count, texture resolution, file size, age/year, free only

### 2. Materials
**Strengths**: Rock, wood, metal, plastics, glass, bricks, ground, organic, fabrics (1,000+ FibreGuard/Fabric Library digital twins)
**Note**: All materials are free on BlenderKit
**Compatibility**: All materials are Cycles-compatible. Some procedural materials may have issues with EEVEE due to node complexity.

### 3. HDRIs
Interior environments, exterior environments, studio lighting setups.
**Includes**: Manually created studio lighting rigs (not just photographed HDRIs).

### 4. Scenes
Ready-made setups: product visualization, motion graphics, complete environments.
**Range**: From simple object displays to full room interiors.

### 5. Brushes
5,000+ sculpting brushes for Blender's sculpt mode. Full Blender 4.4/4.5/5.0 brush support since v3.15.

### 6. Node Groups (NEW — v3.15, March 2025)
Procedural workflows as reusable geometry node groups. Previously experimental, now official.

### 7. Printables (NEW — v3.16, May 2025)
3D printing-ready assets with dedicated category and thumbnails.

### 8. Add-ons (NEW — v3.18, November 2025)
Search, download, and install Blender add-ons directly from within BlenderKit — all inside Blender. Free and paid add-ons available, purchased individually (not part of Full Plan).

---

## Addon Version History (2025)

| Version | Date | Key Changes | Blender Compat |
|---------|------|-------------|----------------|
| **3.15.0** | March 2025 | Node groups official, multi-tab search, smart type detection, experimental printables | 3.0 — 5.0 |
| **3.16.0/3.16.1** | May/June 2025 | Printables official, drag-and-drop fixes, Blender 3.0-3.1 fixes | 3.0 — 5.0 |
| **3.17.0** | October 2025 | Asset Bar overhaul (fwd/back nav), drag-and-drop to collections, **Blender 5.0 support** | 3.0 — 5.0 |
| **3.18.0** | November 2025 | Add-on asset type, **Blender 5.1 Alpha support**, darker thumbnail fix for 5.0/5.1, **aarch64/ARM64 fix**, multi-window perf | 3.0 — 5.1 |

### Blender 5.0 Compatibility Details

BlenderKit **v3.17.0+** is required for Blender 5.0. Specific fixes:

| Issue | Fixed In | Details |
|-------|----------|---------|
| `scene.world.use_nodes` errors | 3.17.0 | Disabled calls that Blender 5.0 removed |
| Darker thumbnails in search bar | 3.18.0 | Thumbnail rendering adapted for 5.0/5.1 |
| Drag-and-drop failures in 5.1 | 3.18.0 | Drag targets updated for new API |
| "X" close button on asset popups | 3.18.0 | UI layout changes in 5.0/5.1 |
| Linux ARM64 binary detection | 3.18.0 | Fixed aarch64 binary name in client |

**Recommendation**: Use **BlenderKit 3.18.0+** with Blender 5.0. Update via Blender's Extensions interface (Blender 4.2+) or from [blenderkit.com/get-blenderkit](https://www.blenderkit.com/get-blenderkit/).

---

## BlenderKit + BlenderMCP Integration

### Current Status: Not Natively Integrated (Yet)

BlenderMCP's creator (ahujasid) has filed a feature request with BlenderKit:
> *"A popular user request is to integrate with BlenderKit. Think of the user writing a prompt and the right asset being imported. Could an API be made available?"*

**Source**: [GitHub Issue #1514](https://github.com/BlenderKit/BlenderKit/issues/1514) — Status: "NEEDS TRIAGE"

Community fork with BlenderKit support: [breakerh/blender-mcp-blenderkit](https://github.com/breakerh/blender-mcp-blenderkit)

**Blender Foundation 2026 plans**: The Blender team is exploring an official MCP server for Blender, communicating via the Python API. This could eventually provide a first-party pathway for BlenderKit integration.

### Programmatic Access via `execute_blender_code` (Battle-Tested)

The full search → download → import pipeline has been proven working via BlenderMCP's `execute_blender_code`. This is the **real** integration path until an official MCP tool exists.

**Important**: BlenderKit's `bpy.ops` operators are designed for UI interaction and are fragile from scripts ([GitHub Issue #1643](https://github.com/BlenderKit/blenderkit/issues/1643)). **Use the REST API for searching and `client_lib` for authenticated downloads.**

#### Step 1: Check BlenderKit Availability

```python
import bpy

# Blender 5.0 uses extensions namespace — NOT just 'blenderkit'
BK_ADDON_NAME = 'bl_ext.user_default.blenderkit'  # Blender 5.0+
# BK_ADDON_NAME = 'blenderkit'                     # Blender 4.x and earlier

blenderkit_available = BK_ADDON_NAME in bpy.context.preferences.addons
if blenderkit_available:
    print("BlenderKit addon is installed and enabled")
    import importlib
    bk = importlib.import_module(BK_ADDON_NAME)
    print(f"Module path: {bk.__path__[0]}")

    # Check WM properties are loaded
    wm = bpy.context.window_manager
    ui_attrs = [a for a in dir(wm) if 'blenderkit' in a.lower()]
    print(f"BlenderKit properties: {ui_attrs}")
    # Expected: ['blenderkitUI', 'blenderkit_HDR', 'blenderkit_addon',
    #            'blenderkit_brush', 'blenderkit_mat', 'blenderkit_models',
    #            'blenderkit_nodegroup', 'blenderkit_scene']
else:
    print("BlenderKit addon not found — install from blenderkit.com/get-blenderkit")
```

#### Step 2: Search via REST API (Most Reliable)

BlenderKit's REST API at `www.blenderkit.com/api/v1/search/` works without any UI context. No auth needed for search.

```python
import requests

params = {
    "query": "asset_type:model+order:_score+crystal+gem",
    "addon_version": "3.18.0",
    "page": 1
}
response = requests.get("https://www.blenderkit.com/api/v1/search/", params=params, timeout=10)
data = response.json()

print(f"Found {data.get('count', 0)} results")
for r in data.get('results', [])[:5]:
    print(f"  {r.get('name')}")
    print(f"    Author: {r.get('author', {}).get('fullName')}")
    print(f"    Free: {r.get('isFree', False)} | Faces: {r.get('dictParameters', {}).get('faceCount', '?')}")
    print(f"    assetBaseId: {r.get('assetBaseId')}")
```

**Query syntax:**
- `asset_type:model` / `material` / `brush` / `hdr` / `scene` / `nodegroup` / `printable`
- `is_free:True` — free assets only
- `order:_score` — sort by relevance
- `asset_base_id:<uuid>` — find specific asset by ID
- `category_subtree:sculpture` — filter by category
- Combine with `+`: `asset_type:model+is_free:True+wooden+chair`

#### Step 3: Get Authenticated Download URL (Requires Pro/Login)

**V2 Pipeline (Direct API — Battle-Tested February 2026):**

The search results include a `files` array with `downloadUrl` for each file type. Call this URL with Bearer auth + `scene_uuid` to get a signed URL.

```python
import bpy, requests, uuid

BK = 'bl_ext.user_default.blenderkit'
api_key = bpy.context.preferences.addons[BK].preferences.api_key

asset = data['results'][0]  # From REST API search above

# Get the blend file download endpoint from the files array
blend_files = [f for f in asset.get('files', []) if f['fileType'] == 'blend']
download_url = blend_files[0]['downloadUrl']

# Call with Bearer auth + scene_uuid → returns JSON with signed filePath
r = requests.get(download_url,
    headers={"Authorization": f"Bearer {api_key}"},
    params={"scene_uuid": str(uuid.uuid4())},
    timeout=15)

signed_data = r.json()
signed_url = signed_data['filePath']  # → https://assets.blenderkit.com/...?verify=...
print(f"Signed URL: {signed_url[:80]}...")
```

**Why V2?** The older `client_lib.get_download_url()` approach relies on a local wrapper server (`localhost:1234`) whose API changes between BlenderKit versions. The V2 pipeline talks directly to `blenderkit.com` — no wrapper dependency.

<details>
<summary>Legacy V1 Pipeline (client_lib — may not work with all BlenderKit versions)</summary>

```python
import bpy, importlib, uuid

BK = 'bl_ext.user_default.blenderkit'
SAFE_AUTHOR_KEYS = {'aboutMe','aboutMeUrl','avatar128','firstName',
                     'fullName','gravatarHash','id','lastName'}

asset = data['results'][0]
# CRITICAL: Strip unknown author fields (avatar512 bug)
asset['author'] = {k: v for k, v in asset.get('author', {}).items() if k in SAFE_AUTHOR_KEYS}
parsed = importlib.import_module(f'{BK}.search').parse_result(asset)

api_key = bpy.context.preferences.addons[BK].preferences.api_key
client_lib = importlib.import_module(f'{BK}.client_lib')
can_download, download_url, filename = client_lib.get_download_url(
    parsed, str(uuid.uuid4()), api_key)
```

**Known issue:** If the local wrapper server (`localhost:1234`) rejects GET requests to `/wrappers/get_download_url`, you'll get `KeyError: 'can_download'`. This happens when the wrapper binary version doesn't match the addon code. Use V2 instead.
</details>

#### Step 4: Download and Import

```python
import bpy, requests, tempfile, os

# Download the .blend file from the signed URL (from Step 3)
r = requests.get(signed_url, timeout=120, stream=True)
temp_path = os.path.join(tempfile.gettempdir(), "bk_asset.blend")

with open(temp_path, 'wb') as f:
    for chunk in r.iter_content(chunk_size=8192):
        f.write(chunk)
print(f"Downloaded: {os.path.getsize(temp_path) / (1024*1024):.1f} MB")

# Append all objects from the .blend into the current scene
with bpy.data.libraries.load(temp_path, link=False) as (src, dst):
    dst.objects = src.objects

for obj in dst.objects:
    if obj is not None:
        bpy.context.collection.objects.link(obj)
        obj.location = (3.0, 0.0, 0.0)  # Offset from origin
        print(f"Imported: {obj.name} ({obj.type})")
```

#### Complete One-Shot Pipeline (V2 — Direct API)

The full search → auth → download → import flow in a single `execute_blender_code` call.
Successfully used to batch-import 8 assets (crystals, temples, characters, props) in one session.

```python
import bpy, requests, uuid, tempfile, os

BK = 'bl_ext.user_default.blenderkit'
SEARCH_QUERY = "asset_type:model+order:_score+crystal+gem"
PLACE_AT = (3.0, 0.0, 0.0)
API_KEY = bpy.context.preferences.addons[BK].preferences.api_key

# 1. Search via REST API (no auth needed)
resp = requests.get("https://www.blenderkit.com/api/v1/search/",
    params={"query": SEARCH_QUERY, "addon_version": "3.18.0", "page": 1}, timeout=10)
asset = resp.json()['results'][0]

# 2. Get the blend file download endpoint from files array
blend_files = [f for f in asset.get('files', []) if f['fileType'] == 'blend']
download_url = blend_files[0]['downloadUrl']

# 3. Authenticate → get signed URL (Bearer + scene_uuid)
r = requests.get(download_url,
    headers={"Authorization": f"Bearer {API_KEY}"},
    params={"scene_uuid": str(uuid.uuid4())},
    timeout=15)
signed_url = r.json()['filePath']  # → https://assets.blenderkit.com/...?verify=...

# 4. Download the .blend file
r2 = requests.get(signed_url, timeout=120, stream=True)
path = os.path.join(tempfile.gettempdir(), "bk_asset.blend")
with open(path, 'wb') as f:
    for chunk in r2.iter_content(8192): f.write(chunk)

# 5. Import objects into scene
with bpy.data.libraries.load(path, link=False) as (src, dst):
    dst.objects = src.objects
for obj in dst.objects:
    if obj:
        bpy.context.collection.objects.link(obj)
        obj.location = PLACE_AT
        print(f"Imported: {obj.name} ({obj.type})")
```

#### Reusable Download Function (for batch imports)

```python
import bpy, requests, uuid, tempfile, os

BK = 'bl_ext.user_default.blenderkit'
API_KEY = bpy.context.preferences.addons[BK].preferences.api_key

def bk_grab(search_query, place_at=(0,0,0), label="asset"):
    """Search, download, and import a BlenderKit asset in one call."""
    resp = requests.get("https://www.blenderkit.com/api/v1/search/",
        params={"query": search_query, "addon_version": "3.18.0", "page": 1}, timeout=10)
    results = resp.json().get('results', [])
    if not results:
        print(f"[{label}] No results"); return None
    asset = results[0]
    print(f"[{label}] Found: {asset['name']}")
    blend_files = [f for f in asset.get('files', []) if f['fileType'] == 'blend']
    if not blend_files:
        print(f"[{label}] No blend file"); return None
    r = requests.get(blend_files[0]['downloadUrl'],
        headers={"Authorization": f"Bearer {API_KEY}"},
        params={"scene_uuid": str(uuid.uuid4())}, timeout=15)
    if r.status_code != 200:
        print(f"[{label}] Auth failed: {r.status_code}"); return None
    signed_url = r.json().get('filePath', '')
    r2 = requests.get(signed_url, timeout=120, stream=True)
    safe = label.replace(' ', '_').lower()
    path = os.path.join(tempfile.gettempdir(), f"bk_{safe}.blend")
    with open(path, 'wb') as f:
        for chunk in r2.iter_content(8192): f.write(chunk)
    size_mb = os.path.getsize(path) / (1024*1024)
    print(f"[{label}] Downloaded: {size_mb:.1f} MB")
    imported = []
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = src.objects
    for obj in dst.objects:
        if obj:
            bpy.context.collection.objects.link(obj)
            obj.location = place_at
            imported.append(obj.name)
    print(f"[{label}] Imported {len(imported)} objects")
    return imported

# Example: batch import multiple assets
bk_grab("asset_type:model+amethyst+crystal", (0, 0, 0), "Crystal")
bk_grab("asset_type:model+ancient+temple",   (10, 0, 0), "Temple")
bk_grab("asset_type:model+fantasy+tree",     (20, 0, 0), "Tree")
```

#### Alternative: Trigger Search via bpy.ops (Fragile)

If you need to use the addon's built-in search UI (e.g., to browse results interactively):

```python
import bpy

# Requires 3D Viewport context override in Blender 5.0
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(window=window, area=area):
                bpy.ops.view3d.blenderkit_search(keywords="wooden chair")
            break
    break

# Results populate asynchronously — check with:
import importlib
search_mod = importlib.import_module('bl_ext.user_default.blenderkit.search')
results = search_mod.get_search_results()  # Returns list[dict] when ready
```

**Smart type detection (v3.15+):** Typing "model", "material", or "HDR" in the search field auto-switches category.

#### Pattern: Check Cache Size

```python
import os

global_dir = os.path.expanduser("~/blenderkit_data")
assets_dir = os.path.join(global_dir, "assets")
if os.path.exists(assets_dir):
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, files in os.walk(assets_dir) for f in files)
    blends = sum(1 for r, _, files in os.walk(assets_dir) for f in files if f.endswith('.blend'))
    print(f"BlenderKit cache: {blends} .blend files, {total / (1024**3):.2f} GB")
```

---

## Cache Management

**BlenderKit's asset cache can silently consume significant disk space.** This is the #1 community complaint.

### How It Works
1. Assets download to `$HOME/blenderkit_data/assets/`
2. On import, copies go to your project's directory
3. If "Pack resources" is enabled, data also gets embedded in the `.blend` file
4. **Result**: One asset can exist in 3 places simultaneously

### Paths by Platform
| OS | Default Cache Path |
|----|-------------------|
| Windows | `%USERPROFILE%\blenderkit_data\` |
| macOS | `~/blenderkit_data/` |
| Linux | `~/blenderkit_data/` |

### Management Tips
- **Monitor regularly**: Check cache size with the script above or `du -sh ~/blenderkit_data`
- **Custom path**: Move the data directory if your home drive is space-constrained (set in addon preferences)
- **Unpack resources**: Uncheck "Pack resources" in Blender to keep `.blend` files smaller — assets reference external files instead
- **Periodic cleanup**: Delete old/unused assets from the cache directory
- **Client binary**: BlenderKit uses a `blenderkit-client` binary in `blenderkit_data/client/bin/` for background operations — don't delete this

---

## Best Practices for BlenderKit + BlenderMCP Workflows

### Strategy 1: Hybrid Manual + AI (Recommended)
1. **User browses BlenderKit manually** in Blender's sidebar (search, preview, drag-and-drop)
2. **User tells Claude what they imported**: "I've added a wooden table from BlenderKit"
3. **Claude takes over via BlenderMCP**: positioning, duplicating, materials, lighting, building the scene around BlenderKit assets

This is the most reliable approach since BlenderKit's search/download works best through its native UI.

### Strategy 2: Scene Inspection + Enhancement
1. User builds a scene using BlenderKit assets manually
2. User asks Claude: "Inspect my scene and enhance it"
3. Claude uses `get_scene_info` to understand what's there
4. Claude adds lighting, adjusts materials, positions camera, adds procedural elements

### Strategy 3: Full Programmatic Pipeline (V2 — Battle-Tested February 2026)
1. Search via REST API (`requests.get` to `blenderkit.com/api/v1/search/`)
2. Extract `downloadUrl` from the asset's `files` array (fileType: `blend`)
3. Call `downloadUrl` with `Authorization: Bearer <api_key>` + `scene_uuid=<uuid>` query param
4. Response JSON contains `filePath` → signed URL on `assets.blenderkit.com`
5. Download `.blend` from signed URL, import via `bpy.data.libraries.load()`
6. Claude positions, materials, lighting via BlenderMCP

**This is the proven path.** No dependency on the local wrapper server. Successfully batch-imported 8 assets (190MB character with armature, 99MB photoscan, temples, trees, props) in one session. See "Complete One-Shot Pipeline (V2)" above.

### Strategy 4: Community Fork
For MCP-native BlenderKit tools, [breakerh/blender-mcp-blenderkit](https://github.com/breakerh/blender-mcp-blenderkit) adds BlenderKit capabilities directly to the MCP server.

---

## BlenderKit Assets + glTF Export

BlenderKit assets are delivered as `.blend` files. When exporting to glTF (for mobile/web):

### Known Issues
- **Procedural materials**: Complex BlenderKit node setups may not translate to glTF PBR. **Bake procedural materials to textures** before export.
- **Simple PBR preferred**: For glTF targets, prefer BlenderKit assets with texture-based materials (diffuse/roughness/metallic/normal maps) over procedural nodes.
- **Morph targets**: BlenderKit models don't typically have shape keys, so this isn't an issue — but if you add shape keys post-import, remember `export_apply=False`.
- **Image formats**: glTF requires PNG or JPEG. Blender auto-converts, but this slows export.

### Recommended Export After BlenderKit Import
```python
import bpy

# Select the BlenderKit asset(s) to export
bpy.ops.export_scene.gltf(
    filepath="/path/to/output.glb",
    export_format='GLB',
    use_selection=True,        # Only selected objects
    export_apply=False,        # Preserve shape keys if added
    export_materials='EXPORT',
    export_yup=True,
)
```

---

## BlenderKit vs Other Asset Sources

| Feature | BlenderKit | PolyHaven | Sketchfab | Hyper3D Rodin | Hunyuan3D |
|---------|-----------|-----------|-----------|---------------|-----------|
| **MCP Integration** | Via `execute_blender_code` | Native tool | Native tool | Native tool | Native tool |
| **Asset Count** | 100,000+ | ~2,500 | Millions | On demand | On demand |
| **Cost** | Free tier + paid | Fully free (CC0) | Free + paid | Free trial + paid | API key |
| **Strengths** | Massive variety, arch-viz | HDRIs, textures | Widest model variety | Unique custom models | Text+image to 3D |
| **Materials** | 40,000+ (many procedural) | Textures & HDRIs | Limited | Built-in | Built-in |
| **Scenes** | 750+ complete | None | None | None | None |
| **Brushes** | 5,000+ | None | None | None | None |
| **Node Groups** | Yes | None | None | None | None |
| **Licensing** | RF + CC0 | CC0 | Varies | Varies | Varies |

### When to Use BlenderKit
- **Complete scenes** (PolyHaven has none)
- **Furniture, architecture, vehicles** (BlenderKit's sweet spot)
- **Sculpting brushes** (5,000+, not available elsewhere)
- **Fabric/textile materials** (1,000+ FibreGuard digital twins)
- **Geometry node setups** (PolyHaven/Sketchfab don't offer these)
- **Printable assets** for 3D printing
- **Quick scene prototyping** with drag-and-drop

### When PolyHaven is Better
- **HDRIs for environment lighting** (gold standard, CC0)
- **Everything free with no account** (CC0, no login)
- **Seamless MCP integration** (native BlenderMCP tools)

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Addon not showing in Blender | Directory must be named exactly `blenderkit` |
| "Invalid token (401)" | Log out and log back in to refresh API token |
| "Cannot connect to host" | Check internet, flush DNS, check firewall |
| Client binary blocked (Windows) | Start `blenderkit-client` manually from `blenderkit_data/client/bin/` |
| `RuntimeError: can't modify blend data` | Race condition with drawing/rendering — retry |
| `bpy.ops.blenderkit` fails from script | BlenderKit operators expect UI context — use REST API + `client_lib` pipeline instead |
| EEVEE material issues | Some procedural materials too complex for EEVEE — use Cycles |
| Assets show as linked (not editable) | Switch to "Append" mode instead of "Link" in BlenderKit panel |
| Darker thumbnails in Blender 5.0 | Update to BlenderKit 3.18.0+ |
| Drag-and-drop fails in 5.1 | Update to BlenderKit 3.18.0+ |
| Linux ARM64 client not found | Update to BlenderKit 3.18.0+ (fixed aarch64 binary detection) |

### Programmatic Pipeline Bugs (Battle-Tested)

| Bug | Cause | Workaround |
|-----|-------|------------|
| `'blenderkit' not in addons` returns True despite addon being active | Blender 5.0 extensions namespace | Check for `'bl_ext.user_default.blenderkit'` instead of `'blenderkit'` |
| `TypeError: UserProfile.__init__() got unexpected keyword argument 'avatar512'` | REST API returns author fields the addon's dataclass doesn't expect | Strip unknown author keys before calling `search.parse_result()` — see SAFE_AUTHOR_KEYS pattern |
| `scene.blenderkit_download` operator fails with avatar512 | Same root cause as above — operator calls `parse_result` internally | Bypass the operator entirely — use `client_lib.get_download_url()` + `requests.get()` + `bpy.data.libraries.load()` |
| `get_search_results()` returns stale results | BlenderKit search is async — results from previous query may linger | Use REST API search for immediate results, or wait + re-call `get_search_results()` |
| Download URL returns 403 `"Parameter scene_uuid not set"` | Tried downloading via REST API file URL without auth | Add `Authorization: Bearer <api_key>` header + `scene_uuid=<uuid>` query param to the `downloadUrl` from files array |
| `KeyError: 'can_download'` in `client_lib.get_download_url()` | Local wrapper server (`localhost:1234`) version mismatch — rejects GET requests to `/wrappers/get_download_url` | **Use V2 pipeline instead** — call `downloadUrl` directly with Bearer auth + scene_uuid, no wrapper dependency |
| Large asset download fails with `IncompleteRead` | Connection timeout on assets >100MB over slow/unstable networks | Increase timeout to 300s, use larger chunk size (16384), or retry |

### Addon Paths

**Addon location (Blender 5.0 extensions system):**

| OS | Extensions Path |
|----|----------------|
| Windows | `%APPDATA%\Blender Foundation\Blender\5.0\extensions\user_default\blenderkit\` |
| macOS | `~/Library/Application Support/Blender/5.0/extensions/user_default/blenderkit/` |
| Linux | `~/.config/blender/5.0/extensions/user_default/blenderkit/` |

**Addon location (Blender 4.x legacy):**

| OS | Addons Path |
|----|-------------|
| Windows | `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\blenderkit` |
| macOS | `~/Library/Application Support/Blender/<version>/scripts/addons/blenderkit` |
| Linux | `~/.config/blender/<version>/scripts/addons/blenderkit` |

---

## Advanced: REST API & Future

BlenderKit uses a REST API at `www.blenderkit.com` for search and asset metadata. While there's no officially documented public API for third-party integrations:

- **Authentication**: OAuth tokens
- **Asset download**: Authenticated file URLs
- **Background ops**: Separate `blenderkit-client` binary handles downloads
- **JS client**: [BlenderKit/bkclientjs](https://github.com/BlenderKit/bkclientjs) (TypeScript) exists for browser-to-client communication

### Future Outlook

1. **Official BlenderKit API** — [Issue #1514](https://github.com/BlenderKit/BlenderKit/issues/1514) feature request is open
2. **Blender Foundation MCP** — Official Blender MCP server being explored for 2026 roadmap, using Python API
3. **Community forks** — [breakerh/blender-mcp-blenderkit](https://github.com/breakerh/blender-mcp-blenderkit) is pioneering MCP integration
4. **Blender Asset Manager** — Blender Foundation developing official asset manager that BlenderKit will integrate with

---

## Example Prompts

```
"I've imported some BlenderKit furniture into my scene. Can you inspect it
and arrange the furniture in a cozy living room layout?"

"Set up three-point lighting for the BlenderKit product I imported, and
configure a studio render setup."

"I have BlenderKit installed. Check if it's available and search for
realistic office chair models."

"The BlenderKit materials on my walls look flat. Enhance them with better
roughness and normal values."

"I built this arch-viz scene with BlenderKit assets. Add an HDRI from
PolyHaven to light it, position the camera for a magazine shot, and set
up Cycles rendering at 2K."

"Take a viewport screenshot of my BlenderKit scene and suggest improvements."

"Check the BlenderKit cache size — I think it's getting big."
```

---

*Sub-skill of the BlenderMCP skill suite. Enhanced with battle-tested session learnings (V1 pipeline: Feb 11 2026 session 1, V2 direct API pipeline: Feb 11 2026 session 2) and research from BlenderKit release notes, GitHub issues, community forums, and CG Channel coverage. Last updated: February 11, 2026.*
