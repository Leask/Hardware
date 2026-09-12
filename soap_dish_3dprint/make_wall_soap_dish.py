import math
from pathlib import Path

import bpy


OUT_DIR = Path('/Volumes/Betty/soap_dish_3dprint')


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def apply_transform(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def cube(name, dims, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    apply_transform(obj)
    return obj


def cyl(name, radius, depth, loc, axis='Z', vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    if axis == 'X':
        obj.rotation_euler[1] = math.radians(90)
    elif axis == 'Y':
        obj.rotation_euler[0] = math.radians(90)
    apply_transform(obj)
    return obj


def add_bevel(obj, amount=1.2, segments=5):
    bevel = obj.modifiers.new(name='small_print_fillet', type='BEVEL')
    bevel.width = amount
    bevel.segments = segments
    bevel.affect = 'EDGES'
    bevel.profile = 0.5

    normal = obj.modifiers.new(name='weighted_normals', type='WEIGHTED_NORMAL')
    normal.keep_sharp = True
    return obj


def apply_all_modifiers(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def boolean_apply(target, cutter, operation='DIFFERENCE'):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(name=f'{operation.lower()}_{cutter.name}', type='BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)


def union_into(target, parts):
    for part in parts:
        boolean_apply(target, part, 'UNION')
        bpy.data.objects.remove(part, do_unlink=True)


def make_label(text, loc, size=5.0, rot=(math.radians(90), 0, 0)):
    font_curve = bpy.data.curves.new(text, type='FONT')
    font_curve.body = text
    font_curve.align_x = 'CENTER'
    font_curve.align_y = 'CENTER'
    font_curve.size = size
    font_curve.extrude = 0.35
    obj = bpy.data.objects.new(f'label_{text}', font_curve)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    obj.select_set(False)
    return obj


def build_model():
    clear_scene()
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 0.001

    width = 120.0
    depth = 84.0
    wall = 4.0
    base = 4.0
    side_height = 34.0
    front_height = 23.0
    back_plate_height = 82.0

    body = cube('body_base', (width, depth, base), (0, 0, base / 2))
    parts = [
        cube(
            'left_wall',
            (wall, depth, side_height),
            (-width / 2 + wall / 2, 0, side_height / 2),
        ),
        cube(
            'right_wall',
            (wall, depth, side_height),
            (width / 2 - wall / 2, 0, side_height / 2),
        ),
        cube(
            'front_lip',
            (width, wall, front_height),
            (0, -depth / 2 + wall / 2, front_height / 2),
        ),
        cube(
            'wall_mount_back',
            (width, wall, back_plate_height),
            (0, depth / 2 - wall / 2, back_plate_height / 2),
        ),
    ]
    union_into(body, parts)

    # Drainage grid: round holes are easier to print cleanly than narrow slots.
    cutters = []
    for x in [-42, -24, -6, 12, 30, 48]:
        for y in [-22, -5, 12]:
            cutters.append(cyl('drain_hole', 3.2, base + 5, (x, y, base / 2), 'Z', 36))

    # A shallow finger notch on the front lip helps lift wet soap.
    cutters.append(cyl('front_finger_notch', 13.0, wall + 8, (0, -depth / 2, 19), 'Y', 64))

    # Two M4 clearance holes with shallow front counterbores.
    for x in [-34, 34]:
        cutters.append(cyl('screw_clearance', 2.4, wall + 10, (x, depth / 2, 62), 'Y', 48))
        cutters.append(cyl('screw_head_counterbore', 5.8, 2.4, (x, depth / 2 - wall + 1.2, 62), 'Y', 64))
        cutters.append(cyl('screw_clearance', 2.4, wall + 10, (x, depth / 2, 39), 'Y', 48))
        cutters.append(cyl('screw_head_counterbore', 5.8, 2.4, (x, depth / 2 - wall + 1.2, 39), 'Y', 64))

    for cutter in cutters:
        boolean_apply(body, cutter, 'DIFFERENCE')
        bpy.data.objects.remove(cutter, do_unlink=True)

    body.name = 'wall_mounted_draining_soap_dish'

    # Raised ribs keep soap above standing water.
    ribs = []
    for x in [-36, -18, 0, 18, 36]:
        rib = cube('raised_soap_rib', (5.0, 54.0, 3.0), (x, -4, base + 1.5))
        add_bevel(rib, 1.2, 5)
        apply_all_modifiers(rib)
        ribs.append(rib)
    union_into(body, ribs)

    label = make_label('SOAP', (0, depth / 2 - wall - 0.35, 74), size=8.0)
    boolean_apply(body, label, 'DIFFERENCE')
    bpy.data.objects.remove(label, do_unlink=True)

    add_bevel(body, 0.4, 2)
    mat = bpy.data.materials.new('matte warm white PLA')
    mat.diffuse_color = (0.85, 0.82, 0.72, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.86, 0.82, 0.70, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.68
    body.data.materials.append(mat)

    return body


def add_scene_helpers(body):
    # Add a translucent wall plane for the preview render only.
    wall = cube('preview_bathroom_wall', (150, 3, 100), (0, 48, 50))
    mat = bpy.data.materials.new('preview pale tile')
    mat.diffuse_color = (0.70, 0.82, 0.86, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.70, 0.82, 0.86, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.85
    wall.data.materials.append(mat)
    wall.display_type = 'TEXTURED'

    bpy.ops.object.light_add(type='AREA', location=(0, -120, 120))
    light = bpy.context.object
    light.name = 'large_softbox'
    light.data.energy = 650000
    light.data.size = 80

    bpy.ops.object.light_add(type='POINT', location=(-80, -80, 70))
    fill = bpy.context.object
    fill.name = 'front_fill'
    fill.data.energy = 90000

    bpy.ops.object.camera_add(location=(128, -150, 92), rotation=(math.radians(60), 0, math.radians(38)))
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    cam.data.lens = 42

    empty = bpy.data.objects.new('camera_target', None)
    bpy.context.collection.objects.link(empty)
    empty.location = (0, -1, 36)
    constraint = cam.constraints.new(type='TRACK_TO')
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    constraint.target = empty

    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(bpy.context.scene, 'eevee'):
        bpy.context.scene.eevee.taa_render_samples = 64
    bpy.context.scene.render.resolution_x = 1600
    bpy.context.scene.render.resolution_y = 1200
    bpy.context.scene.world.color = (0.92, 0.95, 0.97)
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.view_settings.look = 'Medium High Contrast'
    bpy.context.scene.view_settings.exposure = 0

    return wall


def export_files(body):
    blend_path = OUT_DIR / 'wall_mounted_draining_soap_dish.blend'
    stl_path = OUT_DIR / 'wall_mounted_draining_soap_dish.stl'
    obj_path = OUT_DIR / 'wall_mounted_draining_soap_dish.obj'
    preview_path = OUT_DIR / 'wall_mounted_draining_soap_dish_preview.png'

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.wm.stl_export(filepath=str(stl_path), export_selected_objects=True)
    bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)

    add_scene_helpers(body)
    bpy.context.scene.render.filepath = str(preview_path)
    bpy.ops.render.render(write_still=True)

    return blend_path, stl_path, obj_path, preview_path


if __name__ == '__main__':
    model = build_model()
    paths = export_files(model)
    print('Generated:')
    for path in paths:
        print(path)
