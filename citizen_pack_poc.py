import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets", "citizen_pack")
ART_DIR = os.path.join(ROOT, "artifacts", "citizen_pack")
FRAME_DIR = os.path.join(ART_DIR, "frames")
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(ART_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)

CITIZENS = [
    ("Citizen_A_Hoodie", "hoodie_character.glb", -3.0),
    ("Citizen_B_Punk", "punk.glb", -1.5),
    ("Citizen_C_Casual_Woman", "animated_woman.glb", 0.0),
    ("Citizen_D_Suit_Woman", "suit_woman.glb", 1.5),
    ("Citizen_E_Worker_Woman", "worker_woman.glb", 3.0),
]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    objects_before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return (
        [obj for obj in bpy.data.objects if obj not in objects_before],
        [action for action in bpy.data.actions if action not in actions_before],
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


def activate_walk(armature, action, start, end):
    data = armature.animation_data_create()
    data.action = None
    for track in list(data.nla_tracks):
        data.nla_tracks.remove(track)

    action_start = float(action.frame_range[0])
    action_end = float(action.frame_range[1])
    action_span = max(1.0, action_end - action_start)

    track = data.nla_tracks.new()
    track.name = "Walk"
    strip = track.strips.new("Walk", start, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_end
    strip.repeat = max(1.0, math.ceil((end - start + 1) / action_span))
    return action_span


def pose_motion(armature, start, end):
    scene = bpy.context.scene
    names = [bone.name for bone in armature.pose.bones]
    limb_names = [
        name for name in names
        if any(token in name.lower() for token in ("foot", "wrist", "hand", "ankle"))
    ]
    if len(limb_names) < 4:
        limb_names = [
            name for name in names
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
        raise RuntimeError(f"Limb motion check failed for {armature.name}")
    return amplitudes


def move_to_source_collection(name, objects):
    source = bpy.data.collections.new(name + "_Source")
    for obj in objects:
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        source.objects.link(obj)
    return source


def create_collection_instance(name, source_collection, x):
    instance = bpy.data.objects.new(name + "_Instance", None)
    instance.instance_type = "COLLECTION"
    instance.instance_collection = source_collection
    instance.location = (x, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(instance)
    return instance


def create_floor():
    bpy.ops.mesh.primitive_plane_add(size=18, location=(0, 0, -0.01))
    floor = bpy.context.object
    floor.name = "Floor"
    material = bpy.data.materials.new("Floor_Mat")
    material.diffuse_color = (0.12, 0.13, 0.15, 1.0)
    floor.data.materials.append(material)


def create_camera():
    camera_data = bpy.data.cameras.new("Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 4.3
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = (0.0, -10.0, 2.3)
    target = Vector((0.0, 0.0, 1.05))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main():
    reset_scene()
    scene = bpy.context.scene
    start = 0
    end = 32
    scene.frame_start = start
    scene.frame_end = end
    scene.render.fps = 30

    report = {"citizens": []}

    for citizen_name, filename, x in CITIZENS:
        objects, actions = import_glb(os.path.join(ASSET_DIR, filename))
        armature = find_armature(objects)
        walk = find_walk_action(actions)
        meshes = [obj for obj in objects if obj.type == "MESH"]

        armature.name = citizen_name + "_Rig"
        for index, mesh in enumerate(meshes, start=1):
            mesh.name = f"{citizen_name}_Mesh_{index:02d}"

        action_span = activate_walk(armature, walk, start, end)
        amplitudes = pose_motion(armature, start, end)

        scene.frame_set(start)
        bpy.context.view_layer.update()

        source_collection = move_to_source_collection(citizen_name, objects)
        instance = create_collection_instance(citizen_name, source_collection, x)

        report["citizens"].append({
            "name": citizen_name,
            "source": filename,
            "instance": instance.name,
            "instance_x": x,
            "source_collection": source_collection.name,
            "walk_action": walk.name,
            "bones": len(armature.data.bones),
            "meshes": len(meshes),
            "walk_action_span": action_span,
            "phase_offset": 0,
            "limb_motion_amplitude": amplitudes,
        })

    create_floor()
    create_camera()

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 30
    scene.render.filepath = os.path.join(FRAME_DIR, "frame_")

    scene.frame_set(start)
    bpy.context.view_layer.update()

    report.update({
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "fps": scene.render.fps,
        "frame_start": start,
        "frame_end": end,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "preview_engine": scene.render.engine,
        "placement_strategy": "Collection Instance",
    })

    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Citizen_Pack_5.blend"))
    bpy.ops.render.render(animation=True)

    print("CITIZEN_PACK_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
