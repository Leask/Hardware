#!/usr/bin/env python3
"""Generate a wall-mounted 3D-printable bathroom soap dish.

Run with:
    blender -b --python generate_soap_box.py

Dimensions are in millimeters.  The exported STL/OBJ coordinates are also
millimeters, which is what most slicers expect.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


OUT_DIR = Path(__file__).resolve().parent

W = 120.0
D = 85.0
BASE_T = 3.2
WALL_T = 3.4
SIDE_H = 25.5
FRONT_H = 15.5
BACK_H = 70.0
BACK_T = 4.2
OVERLAP = 0.25


def clear_scene() -> None:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def set_units() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = 'MILLIMETERS'


def cube(name: str, loc: tuple[float, float, float],
         dims: tuple[float, float, float]) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def cylinder_y(name: str, loc: tuple[float, float, float],
               radius: float, depth: float, vertices: int = 64) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=loc,
        rotation=(math.pi / 2.0, 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def cylinder_z(name: str, loc: tuple[float, float, float],
               radius: float, depth: float, vertices: int = 48) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    return obj


def capsule_prism_z(name: str, x: float, y: float, z: float, length: float,
                    width: float, height: float,
                    segments: int = 18) -> bpy.types.Object:
    """Create a vertical rounded-slot prism used as a boolean cutter."""
    radius = width / 2.0
    straight = max(0.0, length - width)
    y0 = y - straight / 2.0
    y1 = y + straight / 2.0
    pts: list[tuple[float, float]] = []

    for i in range(segments + 1):
        a = math.pi - i * math.pi / segments
        pts.append((x + radius * math.cos(a), y1 + radius * math.sin(a)))
    for i in range(segments + 1):
        a = -i * math.pi / segments
        pts.append((x + radius * math.cos(a), y0 + radius * math.sin(a)))

    verts: list[tuple[float, float, float]] = []
    for px, py in pts:
        verts.append((px, py, z - height / 2.0))
    for px, py in pts:
        verts.append((px, py, z + height / 2.0))

    n = len(pts)
    faces: list[tuple[int, ...]] = [tuple(range(n - 1, -1, -1)),
                                   tuple(range(n, 2 * n))]
    for i in range(n):
        faces.append((i, (i + 1) % n, n + (i + 1) % n, n + i))

    mesh = bpy.data.meshes.new(name + 'Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def triangular_web(name: str, x: float, width: float) -> bpy.types.Object:
    """Right-triangle gusset between tray base and wall plate."""
    x0 = x - width / 2.0
    x1 = x + width / 2.0
    pts_yz = [
        (0.0, BASE_T - OVERLAP),
        (0.0, 36.0),
        (28.0, BASE_T - OVERLAP),
    ]
    verts = [(x0, y, z) for y, z in pts_yz] + [(x1, y, z) for y, z in pts_yz]
    faces = [
        (0, 2, 1),
        (3, 4, 5),
        (0, 3, 5, 2),
        (2, 5, 4, 1),
        (1, 4, 3, 0),
    ]
    mesh = bpy.data.meshes.new(name + 'Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def apply_boolean(target: bpy.types.Object, cutter: bpy.types.Object,
                  operation: str) -> None:
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(cutter.name, 'BOOLEAN')
    mod.operation = operation
    mod.operand_type = 'OBJECT'
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)


def union_into(target: bpy.types.Object, obj: bpy.types.Object) -> None:
    apply_boolean(target, obj, 'UNION')
    bpy.data.objects.remove(obj, do_unlink=True)


def difference_from(target: bpy.types.Object, cutter: bpy.types.Object) -> None:
    apply_boolean(target, cutter, 'DIFFERENCE')
    bpy.data.objects.remove(cutter, do_unlink=True)


def add_bevel(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    bevel = obj.modifiers.new('print_soft_edges', 'BEVEL')
    bevel.width = 1.1
    bevel.segments = 4
    bevel.affect = 'EDGES'
    bevel.harden_normals = True
    bevel.profile = 0.45
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    weighted = obj.modifiers.new('weighted_normals', 'WEIGHTED_NORMAL')
    weighted.keep_sharp = True
    bpy.ops.object.modifier_apply(modifier=weighted.name)


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = color
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.64
    return mat


def build_model() -> bpy.types.Object:
    printable = material('slightly_warm_white_petg', (0.92, 0.94, 0.91, 1.0))

    base = cube(
        'printable_soap_box',
        (0.0, D / 2.0 - OVERLAP / 2.0, BASE_T / 2.0),
        (W, D + OVERLAP, BASE_T),
    )

    drain_z = BASE_T / 2.0
    drain_depth = BASE_T + 3.0
    for x in (-48.0, -24.0, 0.0, 24.0, 48.0):
        difference_from(
            base,
            cube('drain_slot_rect', (x, 45.0, drain_z), (6.0, 46.0, drain_depth)),
        )
        difference_from(
            base,
            cylinder_z('drain_slot_round_end', (x, 22.0, drain_z), 3.0, drain_depth),
        )
        difference_from(
            base,
            cylinder_z('drain_slot_round_end', (x, 68.0, drain_z), 3.0, drain_depth),
        )

    back = cube(
        'wall_back_plate',
        (0.0, -BACK_T / 2.0 + OVERLAP, BACK_H / 2.0),
        (W, BACK_T, BACK_H),
    )

    for x in (-35.0, 35.0):
        difference_from(back, cylinder_y('keyhole_head', (x, -BACK_T / 2.0, 42.0),
                                         radius=5.2, depth=BACK_T + 5.0))
        difference_from(back, cube('keyhole_slot', (x, -BACK_T / 2.0, 52.0),
                                   (4.4, BACK_T + 5.0, 22.0)))
        difference_from(back, cylinder_y('keyhole_top', (x, -BACK_T / 2.0, 63.0),
                                         radius=2.2, depth=BACK_T + 5.0))

    left = cube(
        'left_side_wall',
        (-W / 2.0 + WALL_T / 2.0, D / 2.0, BASE_T + SIDE_H / 2.0 - OVERLAP),
        (WALL_T, D, SIDE_H + OVERLAP),
    )
    right = cube(
        'right_side_wall',
        (W / 2.0 - WALL_T / 2.0, D / 2.0, BASE_T + SIDE_H / 2.0 - OVERLAP),
        (WALL_T, D, SIDE_H + OVERLAP),
    )
    front = cube(
        'low_front_lip',
        (0.0, D - WALL_T / 2.0, BASE_T + FRONT_H / 2.0 - OVERLAP),
        (W, WALL_T, FRONT_H + OVERLAP),
    )

    parts = [back, left, right, front]

    for x in (-36.0, -12.0, 12.0, 36.0):
        parts.append(
            cube(
                'raised_soap_rib',
                (x, 45.0, BASE_T + 1.7),
                (6.0, 61.0, 3.4),
            )
        )

    parts.append(triangular_web('left_gusset', -47.0, 5.4))
    parts.append(triangular_web('right_gusset', 47.0, 5.4))

    for part in parts:
        union_into(base, part)

    add_bevel(base)
    base.data.materials.append(printable)
    base.name = 'bathroom_wall_mounted_soap_box_printable'
    return base


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def add_preview_context(model: bpy.types.Object) -> None:
    wall_mat = material('preview_matte_tile_wall', (0.80, 0.83, 0.82, 1.0))
    floor_mat = material('preview_soft_shadow_floor', (0.72, 0.73, 0.71, 1.0))

    wall = cube('preview_wall_not_for_printing', (0.0, -7.5, 50.0), (160.0, 2.0, 115.0))
    wall.data.materials.append(wall_mat)
    wall.hide_select = True
    wall.hide_render = True

    floor = cube('preview_floor_not_for_printing', (0.0, 45.0, -1.1), (170.0, 125.0, 1.0))
    floor.data.materials.append(floor_mat)
    floor.hide_select = True
    floor.hide_render = True

    bpy.ops.object.light_add(type='AREA', location=(0.0, 125.0, 180.0))
    light = bpy.context.object
    light.name = 'large_softbox'
    light.data.energy = 450.0
    light.data.size = 90.0

    bpy.ops.object.camera_add(location=(145.0, 175.0, 162.0))
    camera = bpy.context.object
    camera.name = 'preview_camera'
    look_at(camera, Vector((0.0, 42.0, 25.0)))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 135.0
    bpy.context.scene.camera = camera

    model.select_set(True)
    bpy.context.view_layer.objects.active = model


def export_model(model: bpy.types.Object) -> None:
    blend = OUT_DIR / 'Bathroom Soap Box.blend'
    stl = OUT_DIR / 'Bathroom Soap Box - print mm.stl'
    obj = OUT_DIR / 'Bathroom Soap Box - blender.obj'
    bpy.context.preferences.filepaths.save_version = 0

    model.select_set(True)
    bpy.context.view_layer.objects.active = model
    for other in bpy.context.scene.objects:
        if other is not model:
            other.select_set(False)

    if hasattr(bpy.ops.wm, 'stl_export'):
        bpy.ops.wm.stl_export(filepath=str(stl), export_selected_objects=True)
    else:
        bpy.ops.export_mesh.stl(filepath=str(stl), use_selection=True)

    bpy.ops.wm.obj_export(filepath=str(obj), export_selected_objects=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))


def render_preview() -> None:
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.background_type = 'VIEWPORT'
    scene.display.shading.background_color = (1.0, 1.0, 1.0)
    for obj in scene.objects:
        if obj.name.startswith('bathroom_wall_mounted_soap_box'):
            obj.color = (0.90, 0.94, 0.93, 1.0)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.film_transparent = False
    scene.render.filepath = str(OUT_DIR / 'Bathroom Soap Box preview.png')
    bpy.ops.render.render(write_still=True)

    camera = scene.camera
    camera.location = (0.0, 42.0, 220.0)
    look_at(camera, Vector((0.0, 42.0, 0.0)))
    camera.data.ortho_scale = 130.0
    scene.render.filepath = str(OUT_DIR / 'Bathroom Soap Box top preview.png')
    bpy.ops.render.render(write_still=True)


def main() -> None:
    clear_scene()
    set_units()
    model = build_model()
    add_preview_context(model)
    export_model(model)
    render_preview()


if __name__ == '__main__':
    main()
