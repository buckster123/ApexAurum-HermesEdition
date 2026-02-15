"""
scythe.glb — Tiny sickle/scythe for the pruning phase particles.

Target: <50KB, <500 polys
Material: dark iron/steel with slight gold edge highlight
Size: ~0.5 units

Run this script in Blender 5.0's scripting editor, then the GLB
will be exported to your Desktop.

"Nigredo — the pruning blade cuts away what no longer serves."
"""

import bpy
import bmesh
import os
import math

# ============================================================
# 1. Clear the scene
# ============================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ============================================================
# 2. Create scythe blade using a curve + bevel
# ============================================================

# --- Blade as a mesh from vertices ---
# The blade is a curved crescent shape
verts = []
faces = []

# Create blade profile: a curved arc with tapering width
num_segments = 16
blade_radius = 0.2       # Arc radius of the blade curve
blade_width_base = 0.035  # Width at the base of the blade
blade_width_tip = 0.005   # Width at the tip (sharp point)
blade_thickness = 0.008   # How thick the blade is

for i in range(num_segments + 1):
    t = i / num_segments
    # Arc from ~45 degrees to ~225 degrees (crescent shape)
    angle = math.radians(30 + t * 180)

    # Position along the arc
    cx = math.cos(angle) * blade_radius
    cz = math.sin(angle) * blade_radius + 0.1  # Offset up

    # Blade width tapers from base to tip
    width = blade_width_base * (1.0 - t) + blade_width_tip * t

    # Inner and outer edge vertices (top and bottom for thickness)
    # Top face
    verts.append((cx - width, blade_thickness / 2, cz))   # Outer top
    verts.append((cx + width, blade_thickness / 2, cz))   # Inner top
    # Bottom face
    verts.append((cx - width, -blade_thickness / 2, cz))  # Outer bottom
    verts.append((cx + width, -blade_thickness / 2, cz))  # Inner bottom

# Build faces connecting the segments
for i in range(num_segments):
    base = i * 4
    nxt = (i + 1) * 4
    # Top face
    faces.append((base + 0, base + 1, nxt + 1, nxt + 0))
    # Bottom face
    faces.append((base + 2, nxt + 2, nxt + 3, base + 3))
    # Outer edge
    faces.append((base + 0, nxt + 0, nxt + 2, base + 2))
    # Inner edge
    faces.append((base + 1, base + 3, nxt + 3, nxt + 1))

# Cap start
faces.append((0, 2, 3, 1))
# Cap end
last = num_segments * 4
faces.append((last + 0, last + 1, last + 3, last + 2))

mesh = bpy.data.meshes.new("ScytheBladeMesh")
mesh.from_pydata(verts, [], faces)
mesh.update()

blade = bpy.data.objects.new("ScytheBlade", mesh)
bpy.context.collection.objects.link(blade)
bpy.context.view_layer.objects.active = blade
blade.select_set(True)

# ============================================================
# 3. Create handle (simple cylinder)
# ============================================================
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.012,
    depth=0.25,
    vertices=8,
    location=(blade_radius * math.cos(math.radians(30)),
              0,
              blade_radius * math.sin(math.radians(30)) + 0.1 - 0.125),
)
handle = bpy.context.active_object
handle.name = "ScytheHandle"

# ============================================================
# 4. Apply materials (Blender 5.0 safe)
# ============================================================

# --- Blade material: dark iron with gold edge emission ---
blade_mat = bpy.data.materials.new(name="IronBladeMat")
blade_mat.use_nodes = True
bsdf = blade_mat.node_tree.nodes.get("Principled BSDF")

bsdf.inputs['Base Color'].default_value = (0.12, 0.11, 0.10, 1)  # Dark iron
bsdf.inputs['Metallic'].default_value = 0.95
bsdf.inputs['Roughness'].default_value = 0.35
# Subtle gold edge emission
bsdf.inputs['Emission Color'].default_value = (0.85, 0.65, 0.13, 1)
bsdf.inputs['Emission Strength'].default_value = 0.3

blade.data.materials.append(blade_mat)

# --- Handle material: dark wood/wrapped leather ---
handle_mat = bpy.data.materials.new(name="HandleMat")
handle_mat.use_nodes = True
h_bsdf = handle_mat.node_tree.nodes.get("Principled BSDF")

h_bsdf.inputs['Base Color'].default_value = (0.15, 0.08, 0.04, 1)  # Dark wood
h_bsdf.inputs['Metallic'].default_value = 0.0
h_bsdf.inputs['Roughness'].default_value = 0.7

handle.data.materials.append(handle_mat)

# ============================================================
# 5. Join, center, and scale to target size
# ============================================================
bpy.ops.object.select_all(action='SELECT')

# Set origin to geometry center
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# Select all and join
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = blade
bpy.ops.object.join()

# Move to origin
scythe = bpy.context.active_object
scythe.name = "Scythe"
scythe.location = (0, 0, 0)

# Scale so it fits within ~0.5 units
# Measure current bounding box
bbox = [scythe.matrix_world @ bpy.types.Object.bound_box.fget(scythe)[i]
        if hasattr(bpy.types.Object.bound_box, 'fget') else (0, 0, 0)
        for i in range(8)]

# Simple approach: scale to 0.5 units max dimension
dims = scythe.dimensions
max_dim = max(dims)
if max_dim > 0:
    target_size = 0.5
    scale_factor = target_size / max_dim
    scythe.scale = (scale_factor, scale_factor, scale_factor)

# Apply all transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Shade smooth
bpy.ops.object.shade_smooth()

# ============================================================
# 6. Export as GLB
# ============================================================
export_path = os.path.join(os.path.expanduser("~"), "Desktop", "scythe.glb")

bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    export_apply=True,
    export_yup=True,
    use_selection=False,
)

# Report
file_size = os.path.getsize(export_path)
total_polys = sum(len(obj.data.polygons) for obj in bpy.data.objects if obj.type == 'MESH')
print(f"=== EXPORTED: scythe.glb ===")
print(f"  Path: {export_path}")
print(f"  Size: {file_size / 1024:.1f} KB")
print(f"  Polys: {total_polys}")
