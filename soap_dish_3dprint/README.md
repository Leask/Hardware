# Wall-mounted draining soap dish

This folder contains a first-pass 3D-printable soap dish for a bathroom wall.

## Files

- `wall_mounted_draining_soap_dish.blend`: editable Blender source.
- `wall_mounted_draining_soap_dish.stl`: slicer-ready model.
- `wall_mounted_draining_soap_dish.obj`: interchange/export copy.
- `wall_mounted_draining_soap_dish_preview.png`: preview render.
- `make_wall_soap_dish.py`: parametric Blender generation script.

## Model

- Overall size: 120 mm wide, 84 mm deep, 82 mm high.
- 4 mm base and walls.
- Raised ribs keep soap above standing water.
- Round drain holes under the soap area.
- Low front lip with a finger notch.
- Tall flat back plate for bathroom wall mounting.
- Four M4 clearance holes with shallow front counterbores.

## Printing

- Material: PETG is preferred for bathroom humidity; PLA is acceptable for a
  quick prototype.
- Orientation: print upright with the base on the print bed.
- Supports: likely only needed around the screw counterbores/finger notch,
  depending on slicer bridging settings.
- Layer height: 0.2 mm is a reasonable first print.
- Walls/perimeters: 3 or more.
- Infill: 20% grid/gyroid is enough for a soap holder.

## Editing

Open `wall_mounted_draining_soap_dish.blend` in Blender to modify the mesh
directly, or edit the dimensions near the top of `make_wall_soap_dish.py` and
rerun:

```sh
/opt/homebrew/bin/blender --background --factory-startup \
  --python /Volumes/Betty/soap_dish_3dprint/make_wall_soap_dish.py
```

