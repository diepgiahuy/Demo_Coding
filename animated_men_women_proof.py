import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "source_exact_packs"
ART_ROOT = ROOT / "artifacts" / "animated_men_women"
ART_ROOT.mkdir(parents=True, exist_ok=True)

CHARACTERS = [
    ("Men", "Men_Casual", SOURCE_ROOT / "men" / "FBX" / "Male_Casual.fbx"),
    ("Men", "Men_LongSleeve", SOURCE_ROOT / "men" / "FBX" / "Male_LongSleeve.fbx"),
    ("Men", "Men_Shirt", SOURCE_ROOT / "men" / "FBX" / "Male_Shirt.fbx"),
    ("Men", "Men_Suit", SOURCE_ROOT / "men" / "FBX" / "Male_Suit.fbx"),
    ("Women", "Women_Alternative", SOURCE_ROOT / "women" / "FBX" / "Female_Alternative.fbx"),
    ("Women", "Women_Casual", SOURCE_ROOT / "women" / "FBX" / "Female_Casual.fbx"),
    ("Women", "Women_Dress", SOURCE_ROOT / "women" / "FBX" / "Female_Dress.fbx"),
    ("Women", "Women_TankTop", SOURCE_ROOT / "women" / "FBX" / "Female_TankTop.fbx"),
]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_fbx(path):
    if not path.is_file():
        raise RuntimeError(f"Missing FBX: {path}")
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)

    # Blender 5.x exposes the native importer as wm.fbx_import.
    # Older builds expose import_scene.fbx. Support both.
    try:
        bpy.ops.wm.fbx_import(filepath=str(path))
    except Exception as first_error:
        try:
            bpy.ops.import_scene.fbx(filepath=str(path))
        except Exception as second_error:
            raise RuntimeError(
                f"FBX import failed. wm.fbx_import={first_error}; import_scene.fbx={second_error}"
            )

    objects = [obj for obj in bpy.data.objects if obj not in before_objects]
    actions = [action for action in bpy.data.actions if action not in before_actions]
    return objects, actions


def find_armature(objects):
    arms = [obj for obj in objects if obj.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature found")
    return max(arms, key=lambda obj: len(obj.data.bones))


def find_meshes(objects, armature):
    meshes = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        linked = obj.parent == armature
        if not linked:
            linked = any(
                mod.type == "ARMATURE" and mod.object == armature
                for mod in obj.modifiers
            )
        if linked:
            meshes.append(obj)
    if not meshes:
        meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("No character mesh found")
    return meshes


def find_walk_action(actions):
    walk = [a for a in actions if "walk" in a.name.lower()]
    if not walk:
        walk = [a for a in bpy.data.actions if "walk" in a.name.lower()]
    if not walk:
        raise RuntimeError(f"No Walk action found. Imported actions: {[a.name for a in actions]}")
    return sorted(walk, key=lambda a: (len(a.name), a.name.lower()))[0]


def assign_action(armature, action):
    data = armature.animation_data_create()
    for track in list(data.nla_tracks):
        data.nla_tracks.remove(track)
    data.action = action


def world_bounds(meshes, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        for corner in evaluated.bound_box:
            points.append(evaluated.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("No evaluated mesh bounds")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def make_floor(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.1, hi.z - lo.z)
    bpy.ops.mesh.primitive_plane_add(
        size=height * 3.0,
        location=(center.x, center.y, lo.z - height * 0.005),
    )
    floor = bpy.context.object
    floor.name = "Proof_Floor"
    mat = bpy.data.materials.new("Proof_Floor_Mat")
    mat.diffuse_color = (0.10, 0.11, 0.13, 1.0)
    floor.data.materials.append(mat)


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.1, hi.z - lo.z)
    data = bpy.data.cameras.new("Proof_Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.35
    camera = bpy.data.objects.new("Proof_Camera", data)
    bpy.context.collection.objects.link(camera)
    camera.location = (center.x, center.y - height * 3.0, center.z + height * 0.03)
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera


def configure_render(frame_dir, start):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 300
    scene.render.resolution_y = 450
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.frame_start = start
    scene.frame_end = start + 32
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 35
    scene.render.filepath = str(frame_dir / "frame_")


def motion_probe(armature, start):
    names = [bone.name for bone in armature.pose.bones]
    limb_names = [
        name for name in names
        if any(token in name.lower() for token in ("hand", "wrist", "foot", "ankle"))
    ]
    if len(limb_names) < 4:
        limb_names = [
            name for name in names
            if any(token in name.lower() for token in ("arm", "leg"))
        ][:12]
    frames = [start, start + 8, start + 16, start + 24, start + 32]
    amplitudes = {}
    for name in limb_names[:12]:
        positions = []
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            positions.append(
                (armature.matrix_world @ armature.pose.bones[name].matrix).translation.copy()
            )
        amplitudes[name] = round(
            max((a - b).length for a in positions for b in positions),
            6,
        )
    moving = sum(1 for value in amplitudes.values() if value > 0.005)
    if moving < 2:
        raise RuntimeError(f"Limb motion check failed: {amplitudes}")
    return moving, amplitudes


def render_character(pack_name, output_name, source_path):
    reset_scene()
    objects, actions = import_fbx(source_path)
    armature = find_armature(objects)
    meshes = find_meshes(objects, armature)
    walk = find_walk_action(actions)
    assign_action(armature, walk)

    start = int(math.floor(walk.frame_range[0]))
    out_dir = ART_ROOT / output_name
    frame_dir = out_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    configure_render(frame_dir, start)

    moving_limbs, amplitudes = motion_probe(armature, start)
    lo, hi = world_bounds(meshes, start)
    make_floor(lo, hi)
    make_camera(lo, hi)

    source_armature_name = armature.name
    armature.name = output_name + "_Rig"
    for index, mesh in enumerate(meshes, 1):
        mesh.name = f"{output_name}_Mesh_{index:02d}"

    blend_path = out_dir / f"{output_name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.render.render(animation=True)

    return {
        "name": output_name,
        "pack": pack_name,
        "source_fbx": str(source_path.relative_to(ROOT)),
        "source_armature": source_armature_name,
        "walk_action": walk.name,
        "all_imported_actions": [a.name for a in actions],
        "bones": len(armature.data.bones),
        "meshes": len(meshes),
        "moving_limbs": moving_limbs,
        "motion": amplitudes,
        "frame_start": start,
        "frame_end": start + 32,
        "resolution": [300, 450],
    }


def main():
    report = {
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "source": "Quaternius Animated Men/Women pack files mirrored by MRPT/mvsim-models and cross-checked against official Quaternius Drive filenames",
        "characters": [],
    }

    for pack_name, output_name, source_path in CHARACTERS:
        report["characters"].append(
            render_character(pack_name, output_name, source_path)
        )

    with open(ART_ROOT / "qc_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("ANIMATED_MEN_WOMEN_PROOF_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
