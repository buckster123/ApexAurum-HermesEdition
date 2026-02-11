---
name: blender-mcp
description: Use this skill whenever the user wants to create, modify, or manipulate 3D content in Blender via the BlenderMCP integration. Covers scene creation, object manipulation, materials, lighting, asset integration (Poly Haven, Sketchfab, Hyper3D Rodin, Hunyuan3D), retopology, animation setup, rendering, procedural generation, shape keys/morph targets, glTF export, mobile 3D pipelines, and troubleshooting. Trigger on any mention of "Blender", "3D model", "3D scene", "BlenderMCP", "MCP server", or requests involving 3D content creation through natural language. Also use for Blender Python scripting (bpy) assistance, game asset creation, architectural visualization, converting reference images to 3D scenes, and mobile/WebGL 3D pipelines.
---

# BlenderMCP — The Ultimate Skill

## What is BlenderMCP?

BlenderMCP connects Blender to Claude AI through the **Model Context Protocol (MCP)**, enabling direct interaction with and control of Blender. Created by [ahujasid](https://github.com/ahujasid/blender-mcp) (16k+ GitHub stars, MIT license), it translates natural language instructions into Blender Python API calls via a socket-based bridge.

**Key insight**: BlenderMCP is a *procedural* approach to AI-assisted 3D — Claude acts as a "puppet master" using Blender's real tools (extrude, bevel, sculpt), producing clean, editable geometry. This is fundamentally different from *generative* 3D (Luma, TripoSR) which outputs single messy meshes. BlenderMCP output is production-ready, pipeline-friendly, and fully parametric.

---

## Architecture Overview

### Local Setup (Standard)
```
┌─────────────────┐    JSON/TCP     ┌──────────────────┐    MCP/stdio    ┌─────────────┐
│  Blender + Addon │◄──────────────►│  MCP Server      │◄──────────────►│ Claude AI   │
│  (addon.py)      │  localhost:9876 │  (server.py)     │                │ (Desktop/   │
│  Socket server   │                │  Python process  │                │  Cursor/    │
│  inside Blender  │                │  via uvx         │                │  VSCode)    │
└─────────────────┘                └──────────────────┘                └─────────────┘
```

### Remote/LAN Setup (Battle-Tested)
```
┌─────────────────┐    JSON/TCP     ┌──────────────────┐    MCP/stdio    ┌─────────────┐
│  Blender + Addon │◄──────────────►│  MCP Server      │◄──────────────►│ Claude Code │
│  (Windows/Mac)   │  LAN:9876      │  (blender-mcp)   │                │ (Pi/Linux/  │
│  bind: 0.0.0.0   │  192.168.x.x   │  BLENDER_HOST=   │                │  any host)  │
│  Firewall open   │                │  <blender-ip>    │                │             │
└─────────────────┘                └──────────────────┘                └─────────────┘
```

**Two components:**
1. **Blender Addon** (`addon.py`) — Creates a socket server inside Blender on port 9876 to receive and execute commands
2. **MCP Server** (`server.py`) — Implements the Model Context Protocol, connects to the Blender addon, and exposes tools to Claude

**Protocol**: Simple JSON objects over TCP sockets. Commands are `{type, params}`, responses are `{status, result/message}`.

**Critical startup behavior**: The MCP server calls `get_blender_connection()` during its lifespan startup. If Blender is unreachable, the socket times out (~30s) and the MCP handshake fails. **Blender must be running and reachable before starting Claude Code / Claude Desktop.**

---

## Remote / LAN Setup Guide

When Blender runs on a different machine (e.g., Windows laptop) than Claude Code (e.g., Raspberry Pi, Linux server):

### Step 1: Patch the Blender Addon to Bind All Interfaces

The addon defaults to `host='localhost'` which only accepts local connections. Change to `0.0.0.0`:

```python
# In blender_mcp_addon.py, find the __init__ method of the socket server class:
# BEFORE:
def __init__(self, host='localhost', port=9876):
# AFTER:
def __init__(self, host='0.0.0.0', port=9876):
```

**Addon location by platform:**
- **Windows**: `%APPDATA%/Blender Foundation/Blender/<version>/scripts/addons/blender_mcp_addon.py`
- **macOS**: `~/Library/Application Support/Blender/<version>/scripts/addons/blender_mcp_addon.py`
- **Linux**: `~/.config/blender/<version>/scripts/addons/blender_mcp_addon.py`

**CRITICAL**: After editing, delete the `__pycache__/*.pyc` file next to the addon. Blender caches compiled Python and will ignore your source changes until the stale `.pyc` is gone. Then disable/re-enable the addon in Blender Preferences.

### Step 2: Open the Firewall on the Blender Machine

**Windows (PowerShell as Admin):**
```powershell
netsh advfirewall firewall add rule name="BlenderMCP" dir=in action=allow protocol=TCP localport=9876
```

**Linux:**
```bash
sudo ufw allow 9876/tcp
```

### Step 3: Verify the Socket

From the Blender machine, confirm it's listening on all interfaces:
```
# Windows (cmd):
netstat -an | findstr 9876
# Should show: 0.0.0.0:9876    LISTENING

# Linux:
ss -tlnp | grep 9876
```

From the Claude Code machine, test connectivity:
```bash
nc -zv <blender-ip> 9876
# Should show: Connection succeeded
```

### Step 4: Configure Claude Code

In `~/.claude.json` (global) or project `.claude/settings.json`:
```json
{
  "mcpServers": {
    "blender": {
      "command": "/path/to/blender-mcp",
      "env": {
        "BLENDER_HOST": "192.168.x.x",
        "BLENDER_PORT": "9876"
      }
    }
  }
}
```

The MCP server reads `BLENDER_HOST` and `BLENDER_PORT` environment variables (defaults: `localhost`, `9876`).

### Troubleshooting Remote Setup

| Symptom | Cause | Fix |
|---------|-------|-----|
| `nc` times out | Firewall blocking | Add firewall rule (Step 2) |
| `netstat` shows `127.0.0.1:9876` | Stale `.pyc` cache | Delete `__pycache__/*.pyc`, disable/re-enable addon |
| MCP server fails on CC start | Blender unreachable at startup | Start Blender + addon first, then restart CC |
| SSH tunnel doesn't work | WSL2 localhost ≠ Windows localhost | Skip tunnel, use direct LAN IP |

---

## Blender 5.0 Compatibility

Blender 5.0 introduced significant API changes. Code that works on 4.x will break. Here are the critical differences:

### Breaking Changes Reference

| Change | Blender 4.x | Blender 5.0 | Impact |
|--------|-------------|-------------|--------|
| Compositing | `scene.node_tree` | `scene.compositing_node_group` | All compositor scripts |
| Compositing nodes | `scene.use_nodes` | `scene.use_compositing_nodes` | Compositor enable flag |
| Principled BSDF | Has `Subsurface Color` input | **REMOVED** — subsurface uses Base Color | Material scripts |
| EEVEE engine | `BLENDER_EEVEE` | `BLENDER_EEVEE_NEXT` | Render engine setting |
| Action API | `action.fcurves` | `action.slots[].channels[].fcurves` (channelbag) | All animation scripts |
| BGL module | `import bgl` | **REMOVED** — use `gpu` module | OpenGL scripts |
| Vector type | `mathutils.Vector` float64 | `mathutils.Vector` **float32** | Precision-sensitive math |
| Undo system | `bpy.ops.ed.undo()` | Changed behavior in some contexts | Undo scripting |

### Safe Patterns for Blender 5.0

**Materials — Principled BSDF:**
```python
import bpy

mat = bpy.data.materials.new(name="GoldMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")

# SAFE inputs (work in both 4.x and 5.0):
bsdf.inputs['Base Color'].default_value = (0.85, 0.65, 0.13, 1)  # Gold
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.2
bsdf.inputs['Emission Color'].default_value = (0.85, 0.65, 0.13, 1)
bsdf.inputs['Emission Strength'].default_value = 0.5

# BROKEN in 5.0 — do NOT use:
# bsdf.inputs['Subsurface Color']  # KeyError!
```

**Animation — Keyframe Insertion (channelbag-safe):**
```python
import bpy

obj = bpy.data.objects['MyObject']

# SAFE: Use keyframe_insert() on the property directly
# This works in both 4.x and 5.0 — Blender handles channelbag internally
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)

obj.location = (5, 0, 3)
obj.keyframe_insert(data_path="location", frame=60)

# For shape keys:
key_block = obj.data.shape_keys.key_blocks["smile"]
key_block.value = 0.0
key_block.keyframe_insert(data_path="value", frame=1)
key_block.value = 1.0
key_block.keyframe_insert(data_path="value", frame=30)

# BROKEN in 5.0 — do NOT use:
# action = obj.animation_data.action
# action.fcurves  # AttributeError — fcurves moved to channelbag
```

**Render Engine:**
```python
import bpy
scene = bpy.context.scene

# SAFE for Blender 5.0:
scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Not 'BLENDER_EEVEE'
scene.render.engine = 'CYCLES'               # Unchanged
```

---

## Available MCP Tools

These are the tools exposed by BlenderMCP that Claude can call:

### Core Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_scene_info` | Get detailed info about current Blender scene | `user_prompt` |
| `get_object_info` | Get info about a specific object | `object_name` |
| `execute_blender_code` | Run arbitrary Python code in Blender | `code` (string) |
| `get_viewport_screenshot` | Capture viewport screenshot | `max_size` (default: 400) |

### Asset Integration Tools
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `get_polyhaven_status` | Check PolyHaven availability | — |
| `get_polyhaven_categories` | List PolyHaven asset categories | `asset_type` (hdris/textures/models/all) |
| `search_polyhaven_assets` | Search PolyHaven with filters | `asset_type`, `categories` |
| `download_polyhaven_asset` | Download & import a PolyHaven asset | `asset_id`, `asset_type`, `resolution`, `file_format` |
| `set_texture` | Apply downloaded texture to an object | `object_name`, `texture_id` |
| `get_hyper3d_status` | Check Hyper3D Rodin availability | — |
| `generate_hyper3d_model_via_text` | Generate 3D model from text | `text_prompt`, `bbox_condition` |
| `generate_hyper3d_model_via_images` | Generate 3D from reference images | `input_image_paths` or `input_image_urls` |
| `poll_rodin_job_status` | Poll Hyper3D generation progress | `subscription_key` or `request_id` |
| `import_generated_asset` | Import Hyper3D model after generation | `name`, `task_uuid` or `request_id` |
| `get_hunyuan3d_status` | Check Tencent Hunyuan3D availability | — |
| `generate_hunyuan3d_model` | Generate via Hunyuan3D | `text_prompt`, `input_image_url` |
| `poll_hunyuan_job_status` | Poll Hunyuan3D progress | `job_id` |
| `import_generated_asset_hunyuan` | Import Hunyuan3D model | `name`, `zip_file_url` |
| `get_sketchfab_status` | Check Sketchfab availability | — |
| `search_sketchfab_models` | Search Sketchfab library | `query`, `categories`, `count` |
| `get_sketchfab_model_preview` | Preview Sketchfab model thumbnail | `uid` |
| `download_sketchfab_model` | Download & import Sketchfab model | `uid`, `target_size` |

---

## Prompting Strategy — The Golden Rules

### Rule 1: Always Start with Scene Inspection
Before doing ANY work, get the lay of the land:
```
First, get the current scene info to understand what we're working with.
```
This prevents blind operations on unknown scene states.

### Rule 2: Break Complex Tasks into Steps
BlenderMCP works best with sequential, atomic operations. Never try to do everything in one massive code block.

**Bad**: "Create a complete medieval castle with interior furniture, lighting, and materials"

**Good** (step-by-step):
1. "Create the castle base structure — walls, towers, and keep"
2. "Add crenellations and arrow slits to the walls"
3. "Create the interior rooms and floors"
4. "Add furniture pieces to each room"
5. "Set up lighting with torches and ambient fill"
6. "Apply stone and wood materials to appropriate surfaces"

### Rule 3: Be Specific with Dimensions and Positions
Vague instructions lead to unpredictable results.

**Bad**: "Make a building"
**Good**: "Create a two-story villa, 15 meters wide by 10 meters deep, with a flat roof and a black metal railing"

### Rule 4: Check Integrations Before Creating
The preferred asset creation strategy:
1. **Check integrations first** — Verify PolyHaven, Hyper3D, Sketchfab, Hunyuan3D availability
2. **Use external assets when possible** — Prefer downloading from PolyHaven/Sketchfab
3. **Generate custom assets** — Use Hyper3D/Hunyuan3D for unique 3D models
4. **Fall back to scripting** — Only use `execute_blender_code` when other methods fail

### Rule 5: Use Viewport Screenshots for Feedback
After each significant change, capture a screenshot to verify results.

**Known issue**: The MCP `get_viewport_screenshot` tool fails over remote/LAN setups ("Screenshot file was not created"). Use the **`render.opengl` workaround** below instead.

#### Viewport Screenshot — Battle-Tested Pipeline (Remote LAN)

```python
import bpy, os, http.server, threading

def take_and_serve_screenshot(filename="viewport.png", resolution=(1920, 1080), port=9877):
    """Capture viewport via render.opengl and serve via HTTP for remote download."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filepath = os.path.join(desktop, filename)

    # Configure render output
    scene = bpy.context.scene
    old_fp, old_fmt = scene.render.filepath, scene.render.image_settings.file_format
    old_rx, old_ry = scene.render.resolution_x, scene.render.resolution_y

    scene.render.filepath = filepath
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x, scene.render.resolution_y = resolution

    # Render viewport (needs VIEW_3D context)
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(window=window, area=area):
                    bpy.ops.render.opengl(write_still=True)
                break
        break

    # Restore settings
    scene.render.filepath, scene.render.image_settings.file_format = old_fp, old_fmt
    scene.render.resolution_x, scene.render.resolution_y = old_rx, old_ry

    size_kb = os.path.getsize(filepath) / 1024
    print(f"Screenshot: {filename} ({size_kb:.0f} KB)")

    # Serve via HTTP (port 9877 — adjacent to MCP port 9876, usually not firewalled)
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=desktop, **kwargs)

    server = http.server.HTTPServer(('0.0.0.0', port), Handler)
    thread = threading.Thread(target=lambda: [server.handle_request() for _ in range(3)], daemon=True)
    thread.start()
    print(f"Serving on port {port}")

take_and_serve_screenshot("viewport.png")
```

Then from the Pi/client side:
```bash
curl -s -o /tmp/viewport.png "http://<BLENDER_IP>:9877/viewport.png" --max-time 30
```

**Three screenshot methods available:**

| Method | What it captures | Use when |
|--------|-----------------|----------|
| `render.opengl(write_still=True)` | Clean viewport render (no UI) | Best for sharing & feedback |
| `screen.screenshot(filepath=...)` | Full Blender window with UI | Debugging UI/layout issues |
| `get_viewport_screenshot` (MCP tool) | Viewport via MCP | Local setups only (fails over LAN) |

**Port note:** Port 8765 may get firewall-blocked after repeated use. Port **9877** (adjacent to MCP's 9876) is reliably allowed through.

### Rule 6: Name Everything
Always name objects explicitly. Unnamed objects (`Cube.001`, `Sphere.014`) become unmanageable:
```python
obj = bpy.context.active_object
obj.name = "AgentHead"  # Not "Sphere" or "Sphere.001"
```

### Rule 7: Keep Polygon Budgets in Mind
Know your target platform and budget accordingly:
- **Mobile (SceneView/Filament)**: 1K–5K polys per object, 8 shape keys max
- **WebGL (Three.js)**: 5K–50K polys per object
- **Desktop real-time**: 50K–500K polys per object
- **Offline render**: No practical limit

---

## The `execute_blender_code` Powerhouse

This is the most powerful tool — it runs arbitrary Python in Blender.

### Object Creation
```python
import bpy

# Clear the scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create primitives
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=24, location=(3, 0, 1))
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=3, location=(-3, 0, 1.5))
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(6, 0, 1))
```

### Material Application (Blender 5.0 Safe)
```python
import bpy

obj = bpy.data.objects['MyObject']
mat = bpy.data.materials.new(name="GoldMetallic")
mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")

# Safe inputs for Blender 5.0:
bsdf.inputs['Base Color'].default_value = (0.85, 0.65, 0.13, 1)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.2
bsdf.inputs['Emission Color'].default_value = (0.85, 0.65, 0.13, 1)
bsdf.inputs['Emission Strength'].default_value = 0.3

obj.data.materials.append(mat)
```

### Emissive / Glowing Materials
```python
import bpy

mat = bpy.data.materials.new(name="GlowMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1)  # Black base
bsdf.inputs['Emission Color'].default_value = (1.0, 0.84, 0.0, 1)  # Gold glow
bsdf.inputs['Emission Strength'].default_value = 5.0

# For transparency (glass, energy effects):
mat.blend_method = 'BLEND'  # EEVEE transparency (may need 'HASHED' or 'CLIP')
bsdf.inputs['Alpha'].default_value = 0.3
```

### Camera and Lighting Setup
```python
import bpy
import math

# Camera
bpy.ops.object.camera_add(location=(10, -10, 8))
cam = bpy.context.active_object
cam.rotation_euler = (math.radians(60), 0, math.radians(45))
bpy.context.scene.camera = cam

# Three-point lighting
bpy.ops.object.light_add(type='AREA', location=(5, -3, 6))
key = bpy.context.active_object
key.name = "KeyLight"
key.data.energy = 500
key.data.size = 3
key.data.color = (1.0, 0.95, 0.8)  # Warm

bpy.ops.object.light_add(type='AREA', location=(-4, -2, 4))
fill = bpy.context.active_object
fill.name = "FillLight"
fill.data.energy = 200
fill.data.size = 2

bpy.ops.object.light_add(type='AREA', location=(0, 5, 5))
rim = bpy.context.active_object
rim.name = "RimLight"
rim.data.energy = 300
rim.data.size = 1
```

### Modifiers
```python
import bpy

obj = bpy.context.active_object

# Subdivision Surface
mod = obj.modifiers.new(name="Subdiv", type='SUBSURF')
mod.levels = 2          # Viewport
mod.render_levels = 3   # Render

# Bevel
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.02
mod.segments = 3

# Mirror
mod = obj.modifiers.new(name="Mirror", type='MIRROR')
mod.use_axis[0] = True

# Boolean
mod = obj.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = bpy.data.objects['Cutter']

# Wireframe (great for sacred geometry)
mod = obj.modifiers.new(name="Wire", type='WIREFRAME')
mod.thickness = 0.008
mod.use_replace = True  # Replace mesh with wireframe only
```

### Render Settings
```python
import bpy

scene = bpy.context.scene

# Cycles (quality)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

# EEVEE (speed) — use BLENDER_EEVEE_NEXT for Blender 5.0
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples = 64

# Output
scene.render.filepath = '/tmp/render_output.png'
scene.render.image_settings.file_format = 'PNG'
```

---

## Advanced Procedural Patterns

### BMesh — Vertex-Level Mesh Manipulation

BMesh is Blender's internal mesh editing API. Essential for procedural sculpting.

```python
import bpy
import bmesh

obj = bpy.data.objects['MyMesh']

# Enter edit mode via BMesh
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()

# Manipulate vertices
for v in bm.verts:
    # Example: push top vertices outward
    if v.co.z > 0.5:
        v.co.x *= 1.2
        v.co.y *= 1.2

# Write back and cleanup
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
```

### Distance-Based Vertex Sculpting

The most powerful procedural sculpting pattern. Uses distance from a target point with smooth falloff to create organic shapes.

```python
import bpy
import bmesh
from mathutils import Vector

obj = bpy.data.objects['AgentHead']
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()

for v in bm.verts:
    x, y, z = v.co.x, v.co.y, v.co.z

    # === Eye Sockets ===
    # Deep push inward at eye locations
    for eye_x in [-0.32, 0.32]:  # Left and right
        eye_center = Vector((eye_x, -0.7, 0.18))
        dist = ((x - eye_center.x)**2 + (z - eye_center.z)**2)**0.5
        if dist < 0.22 and y < -0.3:
            depth = (1.0 - dist / 0.22) ** 1.5  # Sharp falloff exponent
            v.co.y += depth * 0.25              # Push inward (positive Y)

    # === Nose Bridge ===
    nose_dist = abs(x)  # Distance from center line
    if nose_dist < 0.12 and y < -0.5 and -0.1 < z < 0.3:
        bridge = (1.0 - nose_dist / 0.12) ** 2
        v.co.y -= bridge * 0.2  # Pull forward (negative Y)

    # === Jaw ===
    if z < -0.2 and y < -0.2:
        jaw_factor = max(0, (-z - 0.2) / 0.5)
        taper = 1.0 - jaw_factor * 0.4  # Narrow toward chin
        v.co.x *= taper

bm.to_mesh(obj.data)
bm.free()
obj.data.update()
```

**Falloff functions** control the shape of deformations:
- `(1 - d/r) ** 1.0` — Linear falloff (cone shape)
- `(1 - d/r) ** 1.5` — Medium sharpness (good for eye sockets)
- `(1 - d/r) ** 2.0` — Smooth bell curve (good for cheeks, forehead)
- `(1 - d/r) ** 3.0` — Very sharp peak (good for nose tip)
- `max(0, 1 - (d/r)**2)` — Cosine-like (good for brow ridge)

### Shape Keys (Morph Targets)

Shape keys are Blender's morph targets — deformed copies of the mesh that can be blended. Essential for facial animation.

```python
import bpy

obj = bpy.data.objects['AgentHead']

# Step 1: Create basis (must be first)
obj.shape_key_add(name="Basis", from_mix=False)

# Step 2: Create expression shape keys
sk = obj.shape_key_add(name="jawOpen", from_mix=False)
for i, v in enumerate(obj.data.vertices):
    co = v.co.copy()
    if co.z < -0.1 and co.y < -0.15:
        jaw_factor = max(0, (-co.z - 0.1) / 0.6)
        drop = jaw_factor ** 0.8 * 0.5
        sk.data[i].co.z = co.z - drop
        sk.data[i].co.y = co.y - drop * 0.5  # Jaw moves down AND back

sk2 = obj.shape_key_add(name="smile", from_mix=False)
for i, v in enumerate(obj.data.vertices):
    co = v.co.copy()
    for side in [-1, 1]:
        corner = Vector((side * 0.25, -0.75, -0.05))
        dist = (co - corner).length
        if dist < 0.3:
            factor = (1.0 - dist / 0.3) ** 1.5
            sk2.data[i].co.z = co.z + factor * 0.15  # Lift corners
            sk2.data[i].co.x = co.x + side * factor * 0.08  # Widen

# Step 3: Verify
keys = obj.data.shape_keys.key_blocks
print(f"Shape keys: {[k.name for k in keys]}")
# ['Basis', 'jawOpen', 'smile']
```

#### The Calibration Trick

**Build shape keys at 2.5x your desired maximum deformation, then drive them at 60–75% in your application.** This gives headroom for emphasis without clipping, and the "sweet spot" at 70% looks natural.

```python
# Building at 2.5x:
drop = jaw_factor ** 0.8 * 0.5   # This is 2.5x what we'd actually show

# Driving at 70% in the app:
# sk.value = 0.7  (not 1.0)
# SceneView: renderableManager.setMorphWeights(entity, floatArrayOf(0.7f))
```

#### Standard Expression Set (16 shapes)

| Shape Key | What It Does | Priority |
|-----------|-------------|----------|
| `jawOpen` | Jaw drops down and back | High — speech |
| `smile` | Mouth corners lift, cheeks raise | High — emotion |
| `frown` | Mouth corners pull down | High — emotion |
| `browRaiseL/R` | Eyebrow lifts | High — expression |
| `browFurrow` | Brows pull together and down | Medium — anger/focus |
| `eyeSquintL/R` | Eyes narrow | Medium — emotion |
| `eyeWidenL/R` | Eyes widen | Medium — surprise |
| `mouthPucker` | Lips push forward | Medium — speech |
| `mouthStretch` | Mouth widens | Low — speech |
| `cheekPuff` | Cheeks inflate | Low — expression |
| `noseWrinkle` | Nose bridge wrinkles | Low — disgust |
| `tongueOut` | For fun / specific speech | Low — optional |

**For mobile, keep to 8 shape keys max** (GPU morph target limit on older devices).

### Sacred Geometry Patterns

Battle-tested recipes for wireframe platonic solids, energy rings, and sacred symbols.

#### Wireframe Platonic Solids
```python
import bpy

# Icosahedron with wireframe
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.4, location=(0, 0.3, 0.1))
ico = bpy.context.active_object
ico.name = "SacredIco"
wire = ico.modifiers.new(name="Wire", type='WIREFRAME')
wire.thickness = 0.008
wire.use_replace = True  # Wireframe only, no faces

# Nested octahedron (counter-rotating)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=0, radius=1.0, location=(0, 0.3, 0.1))
octa = bpy.context.active_object
octa.name = "SacredOcta"
wire2 = octa.modifiers.new(name="Wire", type='WIREFRAME')
wire2.thickness = 0.006
wire2.use_replace = True
```

#### Flower of Life (7 Interlocking Torus Rings)
```python
import bpy
import math

positions = [(0, 0)]  # Center
for i in range(6):     # 6 surrounding
    angle = math.radians(60 * i)
    positions.append((math.cos(angle) * 0.3, math.sin(angle) * 0.3))

for idx, (dx, dz) in enumerate(positions):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.3, minor_radius=0.005,
        major_segments=48, minor_segments=8,
        location=(dx, 0.5, 0.1 + dz)
    )
    ring = bpy.context.active_object
    ring.name = f"FlowerRing_{idx}"
    ring.rotation_euler.x = math.radians(90)  # Face forward
```

#### Merkaba (Star Tetrahedron) from Raw Vertices
```python
import bpy

s = 0.25  # Scale factor

# Upward-pointing tetrahedron
verts_up = [
    (0, 0, s*1.5),
    (s, s*0.577, -s*0.5),
    (-s, s*0.577, -s*0.5),
    (0, -s*1.155, -s*0.5)
]
faces_up = [(0,1,2), (0,2,3), (0,3,1), (1,3,2)]

mesh_up = bpy.data.meshes.new("MerkabaUpMesh")
mesh_up.from_pydata(verts_up, [], faces_up)
mesh_up.update()
obj_up = bpy.data.objects.new("MerkabaUp", mesh_up)
bpy.context.collection.objects.link(obj_up)
obj_up.location = (0, 0, 1.8)

# Downward-pointing tetrahedron (inverted)
verts_down = [
    (0, 0, -s*1.5),
    (s, -s*0.577, s*0.5),
    (-s, -s*0.577, s*0.5),
    (0, s*1.155, s*0.5)
]
mesh_down = bpy.data.meshes.new("MerkabaDownMesh")
mesh_down.from_pydata(verts_down, [], faces_up)  # Same face topology
mesh_down.update()
obj_down = bpy.data.objects.new("MerkabaDown", mesh_down)
bpy.context.collection.objects.link(obj_down)
obj_down.location = (0, 0, 1.8)

# Add wireframe to both
for obj in [obj_up, obj_down]:
    wire = obj.modifiers.new(name="Wire", type='WIREFRAME')
    wire.thickness = 0.008
    wire.use_replace = True
```

#### Golden Spiral (NURBS Curve)
```python
import bpy
import math

curve_data = bpy.data.curves.new(name="GoldenSpiral", type='CURVE')
curve_data.dimensions = '3D'
curve_data.bevel_depth = 0.004  # Tube thickness

spline = curve_data.splines.new('NURBS')
num_points = 60
spline.points.add(num_points - 1)

phi = (1 + math.sqrt(5)) / 2  # Golden ratio
for i in range(num_points):
    t = i / (num_points - 1) * 4 * math.pi
    r = 0.05 * math.exp(t * math.log(phi) / (2 * math.pi))  # Phi-based growth
    x = math.cos(t) * r
    z = math.sin(t) * r + 0.42  # Offset to third eye
    y = -0.8 + r * 0.3
    spline.points[i].co = (x, y, z, 1.0)

spline.use_endpoint_u = True
obj = bpy.data.objects.new("GoldenSpiral", curve_data)
bpy.context.collection.objects.link(obj)
```

### Procedural Terrain
```python
import bpy
import bmesh
from math import sin, cos

# Create subdivided plane
bpy.ops.mesh.primitive_plane_add(size=50)
obj = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=50)
bpy.ops.object.mode_set(mode='OBJECT')

# Displace vertices for terrain (multi-octave noise)
for vert in obj.data.vertices:
    x, y = vert.co.x, vert.co.y
    vert.co.z = (sin(x * 0.3) * cos(y * 0.3) * 2 +    # Large hills
                  sin(x * 0.7 + 1) * cos(y * 0.5) * 1 +  # Medium detail
                  sin(x * 1.5) * cos(y * 1.2) * 0.3)      # Fine detail
```

### Procedural Scatter
```python
import bpy
import random

base_obj = bpy.data.objects['Tree']
for i in range(50):
    new_obj = base_obj.copy()
    new_obj.data = base_obj.data.copy()
    new_obj.location = (random.uniform(-20, 20), random.uniform(-20, 20), 0)
    new_obj.scale = [random.uniform(0.8, 1.2)] * 3
    new_obj.rotation_euler.z = random.uniform(0, 6.28)
    bpy.context.collection.objects.link(new_obj)
```

---

## Animation Patterns

### Basic Keyframing (5.0 Safe)
```python
import bpy

obj = bpy.data.objects['Cube']

# Always use keyframe_insert on the property directly
obj.location = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=1)

obj.location = (5, 0, 3)
obj.keyframe_insert(data_path="location", frame=60)

obj.location = (10, 0, 0)
obj.keyframe_insert(data_path="location", frame=120)

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 120
```

### Shape Key Animation (Expression Sequences)
```python
import bpy

obj = bpy.data.objects['AgentHead']
keys = obj.data.shape_keys.key_blocks
scene = bpy.context.scene

# Define expression sequence: (frame, {shape: value})
expressions = [
    (1,   {"smile": 0.0, "jawOpen": 0.0, "browRaiseL": 0.0, "browRaiseR": 0.0}),
    (30,  {"smile": 0.7, "jawOpen": 0.0, "browRaiseL": 0.3, "browRaiseR": 0.3}),
    (60,  {"smile": 0.0, "jawOpen": 0.5, "browRaiseL": 0.6, "browRaiseR": 0.6}),
    (90,  {"smile": 0.0, "jawOpen": 0.0, "browRaiseL": 0.0, "browRaiseR": 0.0}),
    (120, {"smile": 0.7, "jawOpen": 0.2, "browRaiseL": 0.2, "browRaiseR": 0.2}),
]

all_shape_names = set()
for _, expr in expressions:
    all_shape_names.update(expr.keys())

for frame, expr in expressions:
    scene.frame_set(frame)
    for name in all_shape_names:
        if name in keys:
            keys[name].value = expr.get(name, 0.0)
            keys[name].keyframe_insert(data_path="value", frame=frame)

scene.frame_start = 1
scene.frame_end = 120
```

### Orbiting Animation
```python
import bpy
import math

obj = bpy.data.objects['EnergyOrb']
frames = 250
center = (0, 0, 0)
radius = 1.5

for frame in range(1, frames + 1):
    angle = (frame / frames) * 2 * math.pi
    obj.location.x = center[0] + math.cos(angle) * radius
    obj.location.y = center[1] + math.sin(angle) * radius
    obj.location.z = center[2] + math.sin(angle * 2) * 0.2  # Gentle bob
    obj.keyframe_insert(data_path="location", frame=frame)
```

### Emission Pulse Animation
```python
import bpy
import math

mat = bpy.data.materials['GlowMaterial']
bsdf = mat.node_tree.nodes.get("Principled BSDF")
emission = bsdf.inputs["Emission Strength"]

for frame in range(1, 251):
    pulse = 3.0 + 2.0 * math.sin(frame * 0.1)  # Oscillate 1.0–5.0
    emission.default_value = pulse
    emission.keyframe_insert(data_path="default_value", frame=frame)
```

---

## glTF Export Pipeline

glTF is the standard format for mobile/web 3D. Getting shape keys (morph targets) to export correctly requires specific settings.

### Critical Export Rules

| Setting | Value | Why |
|---------|-------|-----|
| `export_apply` | **False** | `True` applies modifiers and **DESTROYS shape keys** |
| `export_morph` | **True** | Enables morph target export |
| `export_morph_normal` | `True` | Include morph normals (smoother deformation) |
| `export_morph_tangent` | `False` | Skip tangent morphs (saves file size, rarely needed) |
| `export_draco_mesh_compression_enable` | **False** | Draco **cannot compress morph targets** |

### Export Script (Morph-Target Safe)
```python
import bpy

bpy.ops.export_scene.gltf(
    filepath="/path/to/output.glb",
    export_format='GLB',               # Single binary file
    export_apply=False,                 # CRITICAL: do NOT apply modifiers
    export_morph=True,                  # Export shape keys as morph targets
    export_morph_normal=True,           # Smooth morph normals
    export_morph_tangent=False,         # Skip tangent morphs
    export_draco_mesh_compression_enable=False,  # Draco breaks morphs
    export_animations=True,             # Include animations
    export_yup=True,                    # Y-up for most engines
)
```

### Compression: Use meshopt, NOT Draco

Draco compression **silently drops morph target data**. Use `EXT_meshopt_compression` instead:

```bash
# Install gltf-transform CLI
npm install -g @gltf-transform/cli

# Compress with meshopt (preserves morph targets)
gltf-transform optimize input.glb output.glb --compress meshopt

# Verify morph targets survived
gltf-transform inspect output.glb
```

### Pre-Export Checklist

1. **Apply scale/rotation** (`Ctrl+A` → All Transforms) — but do NOT apply modifiers
2. **Check shape key count** — 8 max for mobile, 16 for desktop
3. **Verify Basis shape** — first shape key must be "Basis"
4. **Test each shape key** — set value to 1.0, visually verify, set back to 0.0
5. **Remove unused shape keys** — each one adds to file size
6. **Check polygon count** — target 1K–5K for mobile per object

### Mobile Target Specs

| Platform | Format | Max Polys | Max Morphs | Renderer |
|----------|--------|-----------|------------|----------|
| Android (SceneView) | `.glb` | ~5K/object | 8 | Filament |
| iOS (SceneKit) | `.usdz` / `.glb` | ~10K/object | 8 | SceneKit |
| Web (Three.js) | `.glb` | ~50K/scene | 16 | WebGLRenderer |
| Web (Babylon.js) | `.glb` | ~50K/scene | 16 | Engine |

---

## Mobile 3D Pipeline (Android SceneView)

End-to-end pipeline from Blender to Android app with animated morph targets.

### Pipeline Overview
```
Blender (procedural sculpt)
    ↓ export as .glb (morph targets preserved)
glTF file
    ↓ copy to Android assets/
SceneView (Filament renderer)
    ↓ load model, drive morph weights programmatically
Android App
    ↓ expression tags from SSE stream
Live animated 3D face
```

### Driving Morph Targets in SceneView/Filament
```kotlin
// Load model
sceneView.modelLoader.loadModelInstance("models/agent_face.glb")?.let { instance ->
    val entity = instance.renderableEntities.first()
    val rm = sceneView.engine.renderableManager

    // Set morph weights (order matches glTF morph target order)
    rm.setMorphWeights(
        rm.getInstance(entity),
        floatArrayOf(
            0.7f,  // jawOpen at 70%
            0.5f,  // smile at 50%
            0.0f,  // frown
            0.3f,  // browRaiseL
            0.3f,  // browRaiseR
            // ... up to 8 weights
        ),
        0  // offset
    )
}
```

### Expression-to-Weight Mapping
```kotlin
// Map SSE expression tags to morph weight arrays
fun expressionToWeights(tag: String): FloatArray = when (tag) {
    "happy"    -> floatArrayOf(0.0f, 0.7f, 0.0f, 0.3f, 0.3f, 0.0f, 0.0f, 0.0f)
    "thinking" -> floatArrayOf(0.0f, 0.0f, 0.2f, 0.5f, 0.1f, 0.3f, 0.0f, 0.0f)
    "speaking" -> floatArrayOf(0.5f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.2f, 0.0f)
    "surprise" -> floatArrayOf(0.4f, 0.0f, 0.0f, 0.7f, 0.7f, 0.0f, 0.6f, 0.0f)
    "neutral"  -> floatArrayOf(0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f)
    else       -> floatArrayOf(0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f)
}
```

---

## Common Workflows

### Workflow 1: Reference Image → 3D Scene
1. User provides a reference image
2. Inspect the image and identify key elements
3. Plan the scene layout (objects, positions, scale)
4. Create base geometry for each element
5. Apply materials matching the reference
6. Set up camera angle to match reference perspective
7. Add lighting to match the mood
8. Screenshot and iterate

### Workflow 2: Game Asset Pipeline
1. Create base mesh via BlenderMCP primitives
2. Add detail with modifiers (subdivision, bevel)
3. Apply materials from PolyHaven textures
4. Use retopology tools to optimize for game engine
5. Set up LOD variants via `decimate`
6. Export as glTF/FBX

### Workflow 3: Animated Character Face
1. Create UV sphere with sufficient resolution (segments=32, ring_count=24)
2. Scale to head proportions (e.g., `0.82, 0.95, 1.15`)
3. Apply transforms, then use BMesh for vertex sculpting
4. Add subdivision modifier (1 level viewport, 2 render)
5. Create eyes, irises, pupils as separate objects
6. Add shape keys (Basis first, then 8–16 expressions)
7. Build at 2.5x strength, test at 70%
8. Export as `.glb` with `export_apply=False, export_morph=True`

### Workflow 4: Sacred Geometry Ensemble
1. Create platonic solids (ico, octa, tetra) at varying scales
2. Apply wireframe modifier (`use_replace=True`)
3. Add energy torus rings (Flower of Life pattern)
4. Create Merkaba from raw vertex data
5. Add golden spiral (NURBS curve with phi-based growth)
6. Apply emissive materials with gold color
7. Animate rotations and emission pulses
8. Parent to empty for easy group manipulation

### Workflow 5: Scene from Scratch with Assets
1. Check all integration statuses (PolyHaven, Sketchfab, Hyper3D)
2. Search and download HDRI from PolyHaven for environment
3. Search and download textures for ground/surfaces
4. Search Sketchfab for specific model assets
5. Generate unique assets via Hyper3D if needed
6. Arrange everything in the scene
7. Fine-tune lighting and camera

### Workflow 6: Retopology Pipeline
1. Analyze mesh with `mesh_stats`
2. Detect topology issues with `detect_topology_issues`
3. Choose remesh strategy:
   - `voxel_remesh` for uniform topology during sculpting
   - `quadriflow_remesh` for quad-dominant animation-ready mesh
4. `decimate` for LOD generation
5. `shrinkwrap_reproject` for projecting low-poly onto high-poly

---

## Asset Integration Details

### PolyHaven
- **Strengths**: HDRIs, textures, some 3D models. Best for environment lighting and surface materials.
- **Usage**: Check status → search → download → apply with `set_texture`
- **Tip**: Use HDRIs first for realistic lighting before any material work

### Sketchfab
- **Strengths**: Wider variety of models, especially specific subjects and realistic models
- **Usage**: Requires API key. `target_size` parameter scales the largest dimension.
- **Tip**: Preview thumbnails before downloading to avoid surprises

### Hyper3D Rodin
- **Strengths**: Generate unique 3D models from text or images
- **Modes**: `MAIN_SITE` (uses subscription_key) or `FAL_AI` (uses request_id)
- **Workflow**: Generate → poll status → import when "Done"
- **Tip**: Generated models have normalized size — rescale after import

### Hunyuan3D (Tencent)
- **Strengths**: Alternative 3D generation, supports text + image input, built-in materials
- **Native Blender 5.0 support**: Tencent's API has direct Blender integration
- **Workflow**: Generate → poll status (DONE/RUN) → import from zip URL
- **Tip**: Results include OBJ format in zip — `import_generated_asset_hunyuan` handles extraction

### BlenderKit (100,000+ Assets)
- **Strengths**: Largest integrated asset library — architecture, furniture, hard surface, vegetation, 5K+ brushes, complete scenes
- **MCP Integration**: Not native. Access via `execute_blender_code` (fragile) or hybrid manual+AI workflow (recommended)
- **Plans**: Free tier (~48K assets, no login), Full Plan ($14.90/mo, all 100K+)
- **Blender 5.0**: Requires BlenderKit 3.18.0+ for full compatibility
- **Full details**: See **`BLENDERKIT.md`** sub-skill for scripting patterns, cache management, version history, and troubleshooting

---

## Troubleshooting Guide

### Connection Issues
| Problem | Solution |
|---------|----------|
| "Server Disconnected" | Ensure Blender addon is running (N panel → BlenderMCP → Start MCP Server). Do NOT run `uvx blender-mcp` manually in terminal. |
| `spawn uvx ENOENT` | Claude can't find uvx. Use full path in config, e.g., `/home/user/.local/bin/blender-mcp` |
| First command fails | Known issue — the first command often fails. Just retry. |
| `ProactorEventLoop` error | Python asyncio issue on Windows. Ensure Python 3.10+ and latest blender-mcp. |
| Port 9876 conflict | Another instance may be running. Kill existing processes or restart Blender. |
| Only run ONE instance | Run MCP server in either Claude Desktop OR Cursor, never both simultaneously. |
| MCP handshake timeout | Blender must be running BEFORE starting Claude Code. MCP server connects on startup. |
| Remote connection refused | Check: addon bound to 0.0.0.0? Firewall open? pyc cache cleared? |

### Blender 5.0 Errors
| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 'Subsurface Color'` | Removed in 5.0 | Use `Base Color` for subsurface (now shared) |
| `AttributeError: 'Action' has no attribute 'fcurves'` | Channelbag API change | Use `keyframe_insert()` on properties directly |
| `KeyError: 'Fac'` | Node output names changed | Check node outputs with `node.outputs.keys()` |
| `ModuleNotFoundError: 'bgl'` | BGL removed | Use `gpu` module instead |
| `StructRNA of type Object has been removed` | Accessing deleted object | Don't iterate and delete simultaneously; collect first |
| `scene.node_tree` is None | Compositor API changed | Use `scene.compositing_node_group` |

### Screenshot Issues
| Problem | Cause | Fix |
|---------|-------|-----|
| `get_viewport_screenshot` fails: "Screenshot file was not created" | MCP screenshot tool doesn't work over remote/LAN connections | Use `bpy.ops.render.opengl(write_still=True)` with VIEW_3D context override + HTTP server on port 9877 to transfer the file |
| `screen.screenshot` error: `keyword "full" unrecognized` | Blender 5.0 removed the `full` parameter | Use `bpy.ops.screen.screenshot(filepath=path)` without `full` kwarg |
| HTTP file transfer fails on port 8765 | Windows firewall blocks the port after repeated use | Use port **9877** (adjacent to MCP's 9876, reliably allowed) |
| `render.opengl` renders black | No lights in scene | Add a Sun light before rendering, or use EEVEE with world lighting |

### Common Code Errors
| Error | Cause | Fix |
|-------|-------|-----|
| Timeout errors | Request too complex | Break into smaller steps |
| PolyHaven erratic | Wrong asset IDs | Retry with more specific search terms |
| Blender crash | Too many polygons | Save first! Reduce complexity. |
| Silent failure | Python error in Blender | Check Blender's system console for traceback |
| Shape keys not exporting | `export_apply=True` | Set `export_apply=False` — this is the #1 glTF mistake |
| Morph targets missing after compression | Draco used | Use meshopt compression instead |

---

## Platform-Specific Setup

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"]
    }
  }
}
```

### Claude Code (`~/.claude.json`) — Local
```json
{
  "mcpServers": {
    "blender": {
      "command": "/home/user/.local/bin/blender-mcp"
    }
  }
}
```

### Claude Code — Remote/LAN
```json
{
  "mcpServers": {
    "blender": {
      "command": "/home/user/.local/bin/blender-mcp",
      "env": {
        "BLENDER_HOST": "192.168.x.x",
        "BLENDER_PORT": "9876"
      }
    }
  }
}
```

### Windows (requires `cmd` wrapper)
```json
{
  "mcpServers": {
    "blender": {
      "command": "cmd",
      "args": ["/c", "uvx", "blender-mcp"]
    }
  }
}
```

### Cursor
Settings → MCP → Add Server (same JSON format)

### Disable Telemetry
```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"],
      "env": { "DISABLE_TELEMETRY": "true" }
    }
  }
}
```

---

## Advanced Techniques

### Combining MCP Servers
BlenderMCP works well alongside other MCP servers:
- **server-sequential-thinking** — Plan complex operations step-by-step before executing
- **filesystem MCP** — Read reference files, save exported assets
- **git MCP** — Version control .blend files and scripts
- **cerebro-cortex** — Store and recall 3D design decisions across sessions

### Using ThreeJS Export
BlenderMCP can inspect a scene and generate a ThreeJS sketch from it:
```
Get information about the current scene, and make a threejs sketch from it
```

### Hybrid Workflow (AI + Manual)
The best results come from combining AI generation with manual refinement:
1. Use BlenderMCP to quickly generate base geometry and layout
2. Switch to manual Blender work for hero assets and fine details
3. Use BlenderMCP again for material application, lighting, and rendering
4. Use retopology tools to optimize the final mesh

### Batch Operations
```python
import bpy

mat = bpy.data.materials['WoodMaterial']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'floor' in obj.name.lower():
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
```

### Parenting and Organization
```python
import bpy

# Create empty as parent for a group
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
parent = bpy.context.active_object
parent.name = "SacredGeometryGroup"

# Parent all sacred geometry objects
for name in ["SacredIco", "SacredOcta", "SacredTetra", "MerkabaUp", "MerkabaDown"]:
    if name in bpy.data.objects:
        bpy.data.objects[name].parent = parent

# Now you can move/rotate/scale the whole group via the empty
```

---

## Safety & Best Practices

1. **ALWAYS save your work** before using `execute_blender_code` — it runs arbitrary Python
2. **Start simple, iterate** — Build up complexity gradually
3. **Use viewport screenshots** as a feedback loop after each change
4. **Keep operations atomic** — One logical change per tool call
5. **Name your objects** — Use descriptive names for easy reference later
6. **Organize with collections** — Group related objects for scene management
7. **Check normals and scale** — Apply transforms (`Ctrl+A`) regularly
8. **Save versions** — Before major changes, save a new version of the .blend file
9. **Know your Blender version** — Check API compatibility (see Blender 5.0 section)
10. **Test shape keys individually** — Set each to 1.0, verify, reset to 0.0 before export

---

## When NOT to Use BlenderMCP

- **Final production polish** — Manual artist control is still superior for hero assets
- **Complex rigging** — Rigging requires deep manual expertise
- **Advanced sculpting** — Better done interactively in Blender's sculpt mode
- **Real-time interaction** — No live preview; results appear after execution
- **Massive scenes** — Very large scenes may cause timeouts; break into sections

---

## Quick Reference Prompts

```
"Create a beach vibe using HDRIs, textures, and models from Poly Haven"

"Create an animated character face with morph targets for mobile export"

"Build sacred geometry around a central object with wireframe platonic solids"

"Generate a 3D model of a garden gnome through Hyper3D and optimize for mobile"

"Export the scene as glTF with morph targets preserved for SceneView"

"Get information about the current scene, and make a threejs sketch from it"

"Create a low poly dungeon scene with a dragon guarding a pot of gold"

"Apply ocean materials to the water plane and add sunset HDRI lighting"

"Use the retopo_pipeline prompt to guide me through retopologizing this mesh"

"Set up the scene for Android SceneView export — 5K poly budget, 8 shape keys max"
```

---

## Version Info & Ecosystem

- **Current PyPI version**: `blender-mcp` 1.5.5+
- **Requires**: Blender 3.0+ (5.0 supported with API adjustments), Python 3.10+, `uv` package manager
- **Compatible clients**: Claude Desktop, Claude Code, Cursor, VSCode, Windsurf, Roo Code, Trae Editor
- **Also works with**: DeepSeek R1, Gemini, Qwen (via OpenRouter), Ollama (local models)
- **Notable forks**: blender-mcp-vxai (enhanced animation), CommonSenseMachines/blender-mcp (CSM.ai), poly-mcp/Blender-MCP-Server (50+ tools via HTTP), blender-open-mcp (Ollama/local models)
- **Env vars**: `BLENDER_HOST` (default: localhost), `BLENDER_PORT` (default: 9876), `DISABLE_TELEMETRY`

---

*This skill synthesizes knowledge from the official BlenderMCP repository, battle-tested sessions sculpting procedural 3D faces with morph targets via remote MCP bridge (Pi→LAN→Windows Blender 5.0), Blender 5.0 API migration research, glTF morph target export pipeline testing, and community resources. Forged in the Athanor. Last updated: February 2026.*
