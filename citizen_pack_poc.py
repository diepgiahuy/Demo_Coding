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
    ("Citizen_A_Hoodie", "hoodie_character.glb", -4.4),
    ("Citizen_B_Punk", "punk.glb", -2.2),
    ("Citizen_C_Casual_Woman", "animated_woman.glb", 0.0),
    ("Citizen_D_Suit_Woman", "suit_woman.glb", 2.2),
    ("Citizen_E_Worker_Woman", "worker_woman.glb", 4.4),
]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    objects_before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new_objects = [o for o in bpy.data.objects if o not in objects_before]
    new_actions = [a for a in bpy.data.actions if a not in actions_before]
    return new_objects, new_actions


def find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature found: " + repr([(o.name, o.type) for o in objects]))
    return max(arms, key=lambda o: len(o.data.bones))


def find_walk_action(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found: " + ", ".join(a.name for a in actions))
    walks.sort(key=lambda a: ("walk" not in a.name.lower().split("|")[-1], len(a.name)))
    return walks[0]


def activate_walk(armature, action, scene_start, scene_end, phase):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)

    action_start = float(action.frame_range[0])
    action_end = float(action.frame_range[1])
    action_span = max(1.0, action_end - action_start)

    track = ad.nla_tracks.new()
    track.name = "Walk"
    strip_start = scene_start - phase
    strip = track.strips.new("Walk", strip_start, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_end
    strip.repeat = max(2.0, math.ceil((scene_end - strip_start) / action_span) + 1.0)
    return action_span


def parent_import_to_root(objects, root):
    imported_set = set(objects)
    top_level = [o for o in objects if o.parent not in imported_set]
    for obj in top_level:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world


def pose_motion(armature, start, end):
    scene = bpy.context.scene
    candidate_names = [
        "FootL", "FootR", "WristL", "WristR",
        "LowerLegL", "LowerLegR", "LowerArmL", "LowerArmR",
    ]
    names = [n for n in candidate_names if armature.pose.bones.get(n)]
    frames = sorted(set([start, start + (end-start)//4, start + (end-start)//2, start + 3*(end-start)//4, end]))
    amplitudes = {}

    for name in names:
        positions = []
        for frame in frames:
            scene.frame_set(frame)
            pb = armature.pose.bones[name]
            matrix = armature.matrix_world @ pb.matrix
            p = matrix.translation
            if not all(math.isfinite(v) for v in p):
                raise RuntimeError(f"Invalid pose: {armature.name} {name} frame={frame}")
            positions.append(p.copy())
        amp = max((a-b).length for a in positions for b in positions) if len(positions) > 1 else 0.0
        amplitudes[name] = round(amp, 6)

    feet = [amplitudes[n] for n in ("FootL", "FootR") if n in amplitudes]
    if feet and max(feet) < 0.005:
        raise RuntimeError(f"Feet did not move for {armature.name}: {amplitudes}")
    return amplitudes


def create_floor():
    bpy.ops.mesh.primitive_plane_add(size=22, location=(0, 0, -0.01))
    floor = bpy.context.object
    floor.name = "Floor"
    mat = bpy.data.materials.new("Floor_Mat")
    mat.diffuse_color = (0.12, 0.13, 0.15, 1.0)
    floor.data.materials.append(mat)


def create_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (0.0, -15.0, 3.2)
    target = Vector((0.0, 0.0, 1.05))
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 55


def main():
    reset_scene()
    scene = bpy.context.scene
    scene_start = 0
    scene_end = 32
    scene.frame_start = scene_start
    scene.frame_end = scene_end
    scene.render.fps = 30

    report = {"citizens": []}
    phase_offsets = [0, 6, 12, 18, 24]

    for idx, (citizen_name, filename, x) in enumerate(CITIZENS):
        path = os.path.join(ASSET_DIR, filename)
        objects, actions = import_glb(path)
        armature = find_armature(objects)
        walk = find_walk_action(actions)

        root = bpy.data.objects.new(citizen_name, None)
        bpy.context.collection.objects.link(root)
        root.location.x = x
        parent_import_to_root(objects, root)

        armature.name = citizen_name + "_Rig"
        mesh_objects = [o for o in objects if o.type == "MESH"]
        for mesh_index, obj in enumerate(mesh_objects, start=1):
            obj.name = f"{citizen_name}_Mesh_{mesh_index:02d}"

        action_span = activate_walk(
            armature,
            walk,
            scene_start,
            scene_end,
            phase_offsets[idx],
        )

        scene.frame_set(scene_start)
        amplitudes = pose_motion(armature, scene_start, scene_end)

        report["citizens"].append({
            "name": citizen_name,
            "source": filename,
            "walk_action": walk.name,
            "bones": len(armature.data.bones),
            "meshes": len(mesh_objects),
            "walk_action_span": action_span,
            "phase_offset": phase_offsets[idx],
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
    scene.frame_set(scene_start)

    report.update({
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "preview_engine": scene.render.engine,
    })

    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Citizen_Pack_5.blend"))
    bpy.ops.render.render(animation=True)

    print("CITIZEN_PACK_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
