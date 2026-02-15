"""
schema_crystal.glb — Multifaceted amber/gold crystal for schema memory nodes.

Target: <200KB, <3K polys
Material: translucent amber/gold with emission glow
Size: ~1 unit tall

Run this script in Blender 5.0's scripting editor, then the GLB
will be exported to your Desktop.

"Chrysopoeia — the schema crystallizes from raw memory."
"""

import bpy
import bmesh
import os
import math
import random

# ============================================================
# 1. Clear the scene
# ============================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Remove orphan data
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ============================================================
# 2. Create crystal geometry
# ============================================================
# Start with an icosphere (subdivisions=2 gives a nice faceted look)
bpy.ops.mesh.primitive_ico_sphere_add(
    subdivisions=2,
    radius=0.45,
    location=(0, 0, 0),
)
crystal = bpy.context.active_object
crystal.name = "SchemaCrystal"

# Elongate slightly to be taller than wide (crystal-like)
crystal.scale = (0.8, 0.8, 1.2)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Use BMesh to displace vertices for a more crystalline look
bm = bmesh.new()
bm.from_mesh(crystal.data)
bm.verts.ensure_lookup_table()

random.seed(42)  # Deterministic for reproducibility

for v in bm.verts:
    x, y, z = v.co.x, v.co.y, v.co.z

    # Distance from center axis
    radial_dist = math.sqrt(x * x + y * y)

    # Vertical stretch for top and bottom points (crystal terminations)
    if abs(z) > 0.35:
        # Pull top/bottom vertices outward to form crystal points
        stretch = 1.0 + (abs(z) - 0.35) * 0.8
        v.co.z *= stretch

    # Add faceted displacement — push some vertices in/out based on angle
    angle = math.atan2(y, x)
    # Create 6-fold symmetry (hexagonal crystal structure)
    hex_factor = math.cos(angle * 6) * 0.04
    v.co.x += v.co.x * hex_factor
    v.co.y += v.co.y * hex_factor

    # Small random displacement for natural variation
    noise = (random.random() - 0.5) * 0.03
    v.co.x += noise
    v.co.y += noise
    v.co.z += noise * 0.5

bm.to_mesh(crystal.data)
bm.free()
crystal.data.update()

# Smooth shading on the crystal
bpy.ops.object.shade_smooth()

# ============================================================
# 3. Apply PBR material (Blender 5.0 safe)
# ============================================================
mat = bpy.data.materials.new(name="AmberCrystalMat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
bsdf = nodes.get("Principled BSDF")

# Amber/gold translucent crystal
bsdf.inputs['Base Color'].default_value = (0.85, 0.55, 0.08, 1)  # Deep amber
bsdf.inputs['Metallic'].default_value = 0.0  # Non-metallic (crystal)
bsdf.inputs['Roughness'].default_value = 0.15  # Very smooth/glassy
bsdf.inputs['IOR'].default_value = 1.55  # Crystal-like refraction
bsdf.inputs['Alpha'].default_value = 0.75  # Semi-transparent

# Emission glow — warm gold
bsdf.inputs['Emission Color'].default_value = (1.0, 0.75, 0.1, 1)
bsdf.inputs['Emission Strength'].default_value = 1.5

# Transmission for glass-like appearance
bsdf.inputs['Transmission Weight'].default_value = 0.4

# Enable transparency for glTF export
mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None
mat.surface_render_method = 'DITHERED' if hasattr(mat, 'surface_render_method') else None

crystal.data.materials.append(mat)

# ============================================================
# 4. Add inner glow core (small emissive sphere inside)
# ============================================================
bpy.ops.mesh.primitive_ico_sphere_add(
    subdivisions=1,
    radius=0.15,
    location=(0, 0, 0),
)
core = bpy.context.active_object
core.name = "CrystalCore"

core_mat = bpy.data.materials.new(name="CrystalCoreMat")
core_mat.use_nodes = True
core_bsdf = core_mat.node_tree.nodes.get("Principled BSDF")
core_bsdf.inputs['Base Color'].default_value = (1.0, 0.85, 0.2, 1)
core_bsdf.inputs['Emission Color'].default_value = (1.0, 0.85, 0.2, 1)
core_bsdf.inputs['Emission Strength'].default_value = 5.0
core_bsdf.inputs['Roughness'].default_value = 0.0

core.data.materials.append(core_mat)
bpy.ops.object.shade_smooth()

# ============================================================
# 5. Apply transforms
# ============================================================
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ============================================================
# 6. Export as GLB
# ============================================================
export_path = os.path.join(os.path.expanduser("~"), "Desktop", "schema_crystal.glb")

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
print(f"=== EXPORTED: schema_crystal.glb ===")
print(f"  Path: {export_path}")
print(f"  Size: {file_size / 1024:.1f} KB")
print(f"  Polys: {total_polys}")
print(f"  Objects: {len([o for o in bpy.data.objects if o.type == 'MESH'])}")
