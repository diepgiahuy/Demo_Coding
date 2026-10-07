import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets", "citizen_pack")
ART_DIR = os.path.join(ROOT, "artifacts", "citizen_pack")
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(ART_DIR, exist_ok=True)

CITIZENS = [
    ("Citizen_A_Hoodie", "hoodie_character.glb"),
    ("Citizen_B_Punk", "punk.glb"),
    ("Citizen_C_Casual_Woman", "animated_woman.glb"),
    ("Citizen_D_Suit_Woman", "suit_woman.glb"),
    ("Citizen_E_Worker_Woman", "worker_woman.glb"),
]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return (
        [obj for obj in bpy.data.objects if obj not in before_objects],
        [action for action in bpy.data.actions if action not in before_actions],
    )


def find_armature(objects):
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if not armatures:
        raise RuntimeError("No armature found")
    return max(armatures, key=lambda obj: len(obj.data.bones))


def find_walk_action(actions):
    walks = [action for action in actions if "walk" in action.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found")
    return min(walks, key=lambda action: len(action.name))


def assign_walk(armature, action):
    animation_data = armature.animation_data_create()
    for track in list(animation_data.nla_tracks):
        animation_data.nla_tracks.remove(track)
    animation_data.action = action


def pose_motion(armature, start, end):
    scene = bpy.context.scene
    bone_names = [bone.name for bone in armature.pose.bones]
    limb_names = [
        name for name in bone_names
        if any(token in name.lower() for token in ("foot", "wrist", "hand", "ankle"))
    ]
    if len(limb_names) < 4:
        limb_names = [
            name for name in bone_names
            if any(token in name.lower() for token in ("leg", "arm"))
        ][:12]
    if len(limb_names) < 4:
        raise RuntimeError(f"Could not identify limb bones for {armature.name}")

    frames = sorted(set([
        start,
        start + (end - start) // 4,
        start + (end - start) // 2,
        start + 3 * (end - start) // 4,
        end,
    ]))

    amplitudes = {}
    for name in limb_names:
        positions = []
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            position = (armature.matrix_world @ armature.pose.bones[name].matrix).translation
            positions.append(position.copy())
        amplitudes[name] = round(
            max((a - b).length for a in positions for b in positions),
            6,
        )

    if sum(1 for value in amplitudes.values() if value > 0.005) < 2:
        raise RuntimeError(f"Limb motion check failed for {armature.name}: {amplitudes}")
    return amplitudes


def world_bounds(meshes):
    points = []
    for obj in meshes:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("No mesh bounds found")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def make_floor(z):
    bpy.ops.mesh.primitive_plane_add(size=5.0, location=(0.0, 0.0, z))
    floor = bpy.context.object
    floor.name = "Floor"
    material = bpy.data.materials.new("Floor_Mat")
    material.diffuse_color = (0.12, 0.13, 0.15, 1.0)
    floor.data.materials.append(material)


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(1.0, hi.z - lo.z)

    data = bpy.data.cameras.new("Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.35
    camera = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = (0.0, -6.0, center.z + height * 0.04)
    target = Vector((center.x, center.y, center.z))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def configure_render(frame_dir):
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
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 35
    scene.render.filepath = os.path.join(frame_dir, "frame_")


def render_citizen(citizen_name, filename):
    reset_scene()
    citizen_dir = os.path.join(ART_DIR, citizen_name)
    frame_dir = os.path.join(citizen_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)

    objects, actions = import_glb(os.path.join(ASSET_DIR, filename))
    armature = find_armature(objects)
    walk = find_walk_action(actions)
    meshes = [obj for obj in objects if obj.type == "MESH"]

    armature.name = citizen_name + "_Rig"
    for index, mesh in enumerate(meshes, start=1):
        mesh.name = f"{citizen_name}_Mesh_{index:02d}"

    assign_walk(armature, walk)

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = 32
    scene.render.fps = 30
    scene.frame_set(0)
    bpy.context.view_layer.update()

    amplitudes = pose_motion(armature, 0, 32)
    scene.frame_set(0)
    bpy.context.view_layer.update()

    lo, hi = world_bounds(meshes)
    make_floor(lo.z - 0.01)
    make_camera(lo, hi)
    configure_render(frame_dir)

    blend_path = os.path.join(citizen_dir, citizen_name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.render.render(animation=True)

    return {
        "name": citizen_name,
        "source": filename,
        "blend": os.path.relpath(blend_path, ART_DIR),
        "walk_action": walk.name,
        "bones": len(armature.data.bones),
        "meshes": len(meshes),
        "limb_motion_amplitude": amplitudes,
        "frame_count": 33,
        "resolution": [300, 450],
    }


def main():
    report = {
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "fps": 30,
        "preview_strategy": "Five independent Blender scenes rendered separately",
        "citizens": [],
    }

    for citizen_name, filename in CITIZENS:
        report["citizens"].append(render_citizen(citizen_name, filename))

    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("CITIZEN_PACK_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

# Real Blender proof rerun: 2026-10-08
