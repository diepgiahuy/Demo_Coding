import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(ROOT, "artifacts", "citizen_a")
ASSET = os.path.join(ROOT, "assets", "citizen_a")
os.makedirs(ART, exist_ok=True)
os.makedirs(ASSET, exist_ok=True)

HOODIE = os.path.join(ASSET, "m_hoodie.glb")
ANIMS = os.path.join(ASSET, "anims.glb")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature was imported")
    return max(arms, key=lambda o: len(o.data.bones))


def walk_action_from(actions):
    exact = [a for a in actions if a.name.lower() == "walk"]
    if exact:
        return exact[0]
    partial = [a for a in actions if "walk" in a.name.lower()]
    if partial:
        return partial[0]
    raise RuntimeError("Walk action was not found: " + ", ".join(a.name for a in actions))


def configure_walk(armature, walk_action, repeats=4):
    armature.animation_data_create()
    ad = armature.animation_data
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)
    start = int(round(walk_action.frame_range[0]))
    action_end = float(walk_action.frame_range[1])
    action_len = max(1.0, action_end - float(start))
    track = ad.nla_tracks.new()
    track.name = "Walk"
    strip = track.strips.new("Walk", start, walk_action)
    strip.repeat = float(repeats)
    end = int(math.ceil(start + action_len * repeats))
    return start, end


def rebind_meshes(mesh_objects, old_armature, new_armature):
    rebound = 0
    for obj in mesh_objects:
        for mod in obj.modifiers:
            if mod.type == "ARMATURE" and mod.object == old_armature:
                mod.object = new_armature
                rebound += 1
        if obj.parent == old_armature:
            world = obj.matrix_world.copy()
            obj.parent = new_armature
            obj.matrix_world = world
    return rebound


def add_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_plane():
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "Floor"
    plane.data.materials.append(add_material("FloorMat", (0.12, 0.13, 0.15), 0.72))
    return plane


def add_camera(frame_start, frame_end):
    target = bpy.data.objects.new("CameraTarget", None)
    target.location = (0, 0, 1.15)
    bpy.context.collection.objects.link(target)

    orbit = bpy.data.objects.new("CameraOrbit", None)
    bpy.context.collection.objects.link(orbit)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.parent = orbit
    cam.location = (0.0, -4.6, 1.85)
    cam_data.lens = 56

    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    orbit.rotation_euler = (0, 0, math.radians(-30))
    orbit.keyframe_insert(data_path="rotation_euler", index=2, frame=frame_start)
    orbit.rotation_euler = (0, 0, math.radians(95))
    orbit.keyframe_insert(data_path="rotation_euler", index=2, frame=frame_end)

    if orbit.animation_data and orbit.animation_data.action:
        for fc in orbit.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return cam


def add_lights():
    world = bpy.context.scene.world
    world.color = (0.025, 0.03, 0.045)
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.025, 0.03, 0.045, 1.0)
        bg.inputs["Strength"].default_value = 0.5

    key_data = bpy.data.lights.new("Key", type="AREA")
    key_data.energy = 900
    key_data.shape = "DISK"
    key_data.size = 4.0
    key = bpy.data.objects.new("Key", key_data)
    key.location = (-3.0, -3.0, 5.0)
    bpy.context.collection.objects.link(key)

    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill_data.energy = 520
    fill_data.size = 3.0
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.location = (3.2, -1.5, 3.5)
    bpy.context.collection.objects.link(fill)

    rim_data = bpy.data.lights.new("Rim", type="AREA")
    rim_data.energy = 700
    rim_data.size = 2.5
    rim = bpy.data.objects.new("Rim", rim_data)
    rim.location = (0.0, 3.0, 4.0)
    bpy.context.collection.objects.link(rim)


def validate_pose(armature, start, end):
    scene = bpy.context.scene
    bad = []
    samples = sorted(set([start, start + (end-start)//4, start + (end-start)//2, start + 3*(end-start)//4, end]))
    for frame in samples:
        scene.frame_set(frame)
        for pb in armature.pose.bones:
            values = [v for row in pb.matrix for v in row]
            if not all(math.isfinite(v) for v in values):
                bad.append({"frame": frame, "bone": pb.name})
    if bad:
        raise RuntimeError("Non-finite pose matrices: " + json.dumps(bad[:10]))
    return samples


def main():
    reset_scene()

    actions_before = set(bpy.data.actions)
    anim_objects = import_glb(ANIMS)
    anim_arm = find_armature(anim_objects)
    imported_actions = [a for a in bpy.data.actions if a not in actions_before]
    walk = walk_action_from(imported_actions)
    frame_start, frame_end = configure_walk(anim_arm, walk, repeats=4)

    hoodie_objects = import_glb(HOODIE)
    hoodie_arm = find_armature(hoodie_objects)
    meshes = [o for o in hoodie_objects if o.type == "MESH"]
    rebound = rebind_meshes(meshes, hoodie_arm, anim_arm)
    if rebound == 0:
        raise RuntimeError("No hoodie mesh used the expected armature")

    bpy.data.objects.remove(hoodie_arm, do_unlink=True)
    anim_arm.name = "Citizen_A_Rig"
    for i, obj in enumerate(meshes):
        if i == 0:
            obj.name = "Citizen_A_Mesh"
        else:
            obj.name = f"Citizen_A_Mesh_{i+1:02d}"

    root = bpy.data.objects.new("Citizen_A", None)
    bpy.context.collection.objects.link(root)
    world = anim_arm.matrix_world.copy()
    anim_arm.parent = root
    anim_arm.matrix_world = world

    add_plane()
    add_camera(frame_start, frame_end)
    add_lights()

    scene = bpy.context.scene
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.filepath = os.path.join(ART, "Citizen_A_walk.mp4")

    samples = validate_pose(anim_arm, frame_start, frame_end)
    scene.frame_set(frame_start)

    blend_path = os.path.join(ART, "Citizen_A.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.render.render(animation=True)

    report = {
        "blender_version": bpy.app.version_string,
        "asset": "Quaternius Hoodie Character",
        "license": "CC0 1.0",
        "walk_action": walk.name,
        "fps": scene.render.fps,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "mesh_objects": len(meshes),
        "bones": len(anim_arm.data.bones),
        "rebound_armature_modifiers": rebound,
        "pose_sample_frames": samples,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }
    with open(os.path.join(ART, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("CITIZEN_A_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
