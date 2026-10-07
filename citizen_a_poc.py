import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(ROOT, "artifacts", "citizen_a")
ASSET = os.path.join(ROOT, "assets", "citizen_a")
FRAMES = os.path.join(ART, "frames")
os.makedirs(ART, exist_ok=True)
os.makedirs(ASSET, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)

MODEL = os.path.join(ASSET, "hoodie_character.glb")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        detail = [(o.name, o.type) for o in objects]
        raise RuntimeError("No armature was imported: " + repr(detail))
    return max(arms, key=lambda o: len(o.data.bones))


def all_actions_for_armature(armature):
    found = []
    seen = set()

    def add(action):
        if action and action.name not in seen:
            seen.add(action.name)
            found.append(action)

    ad = armature.animation_data
    if ad:
        add(ad.action)
        for track in ad.nla_tracks:
            for strip in track.strips:
                add(strip.action)

    for action in bpy.data.actions:
        add(action)
    return found


def find_walk_action(actions):
    exact = [a for a in actions if a.name.lower() == "walk"]
    if exact:
        return exact[0]
    partial = [a for a in actions if "walk" in a.name.lower()]
    if partial:
        return partial[0]
    raise RuntimeError("Walk action was not found. Actions: " + ", ".join(a.name for a in actions))


def activate_walk(armature, walk_action, repeats=3):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)

    start = int(math.floor(float(walk_action.frame_range[0])))
    end_src = float(walk_action.frame_range[1])
    span = max(1.0, end_src - start)

    track = ad.nla_tracks.new()
    track.name = "Citizen_A_Walk"
    strip = track.strips.new("Walk", start, walk_action)
    strip.repeat = float(repeats)
    end = int(math.ceil(start + span * repeats))
    return start, end


def world_bounds(objects):
    pts = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    if not pts:
        raise RuntimeError("No mesh bounds were found")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def make_material(name, color, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_floor(z, size):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    obj = bpy.context.object
    obj.name = "Floor"
    obj.data.materials.append(make_material("FloorMat", (0.10, 0.11, 0.13), 0.78))


def point_camera(camera, target):
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)
    cam_data = bpy.data.cameras.new("Camera_Main")
    cam = bpy.data.objects.new("Camera_Main", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = center + Vector((height * 1.15, -height * 2.5, height * 0.35))
    cam.data.lens = 58
    point_camera(cam, center + Vector((0, 0, height * 0.02)))
    return cam


def add_lights(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)

    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Citizen_A_World")
    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.018, 0.022, 0.03, 1.0)
        bg.inputs["Strength"].default_value = 0.55

    specs = [
        ("Key", center + Vector((-height * 1.6, -height * 1.8, height * 2.0)), 900, height * 2.2),
        ("Fill", center + Vector((height * 1.8, -height * 0.7, height * 1.2)), 500, height * 1.8),
        ("Rim", center + Vector((0, height * 1.8, height * 1.8)), 700, height * 1.5),
    ]
    for name, loc, energy, size in specs:
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = loc
        bpy.context.collection.objects.link(light)
        direction = center - light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def remove_optional_face_objects(objects):
    removed = []
    tokens = ("eye", "brow", "mouth", "teeth", "tongue")
    for obj in list(objects):
        low = obj.name.lower()
        if obj.type == "MESH" and any(t in low for t in tokens):
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def bone_samples(armature, start, end):
    scene = bpy.context.scene
    names = ["FootL", "FootR", "WristL", "WristR", "LowerLegL", "LowerLegR", "LowerArmL", "LowerArmR"]
    available = [n for n in names if armature.pose.bones.get(n)]
    frames = sorted(set([start, start + (end - start) // 6, start + (end - start) // 3, start + (end - start) // 2]))
    data = {n: [] for n in available}

    for frame in frames:
        scene.frame_set(frame)
        for name in available:
            pb = armature.pose.bones[name]
            matrix = armature.matrix_world @ pb.matrix
            p = matrix.translation
            q = matrix.to_quaternion()
            values = [*p, q.w, q.x, q.y, q.z]
            if not all(math.isfinite(v) for v in values):
                raise RuntimeError(f"Invalid pose at frame {frame}, bone {name}")
            data[name].append([round(v, 6) for v in values])

    moving = {}
    for name, samples in data.items():
        positions = [Vector(s[:3]) for s in samples]
        amplitude = max((a - b).length for a in positions for b in positions) if len(positions) > 1 else 0.0
        moving[name] = round(amplitude, 6)

    for name in ("FootL", "FootR", "WristL", "WristR"):
        if name in moving and moving[name] < 0.005:
            raise RuntimeError(f"Expected animated limb did not move: {name} amplitude={moving[name]}")

    return frames, moving, data


def main():
    reset_scene()
    imported = import_glb(MODEL)
    armature = find_armature(imported)
    actions = all_actions_for_armature(armature)
    walk = find_walk_action(actions)
    start, end = activate_walk(armature, walk, repeats=3)

    removed_face = remove_optional_face_objects(imported)
    meshes = [o for o in imported if o.type == "MESH" and o.name in bpy.data.objects]
    lo, hi = world_bounds(meshes)

    root = bpy.data.objects.new("Citizen_A", None)
    bpy.context.collection.objects.link(root)
    root_world = armature.matrix_world.copy()
    armature.parent = root
    armature.matrix_world = root_world
    armature.name = "Citizen_A_Rig"

    for index, obj in enumerate(meshes, start=1):
        obj.name = "Citizen_A_Mesh" if index == 1 else f"Citizen_A_Mesh_{index:02d}"

    add_floor(lo.z - 0.006, max(6.0, (hi.z - lo.z) * 4.5))
    add_camera(lo, hi)
    add_lights(lo, hi)

    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    scene.frame_set(start)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 30
    scene.render.filepath = os.path.join(FRAMES, "frame_")

    sample_frames, amplitudes, samples = bone_samples(armature, start, end)
    scene.frame_set(start)

    report = {
        "blender_version": bpy.app.version_string,
        "asset": "Quaternius Hoodie Character",
        "license": "CC0 1.0",
        "walk_action": walk.name,
        "available_actions": [a.name for a in actions],
        "fps": scene.render.fps,
        "frame_start": start,
        "frame_end": end,
        "mesh_objects": len(meshes),
        "bones": len(armature.data.bones),
        "removed_optional_face_objects": removed_face,
        "pose_sample_frames": sample_frames,
        "limb_motion_amplitude": amplitudes,
        "pose_samples": samples,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    }

    with open(os.path.join(ART, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "Citizen_A.blend"))
    bpy.ops.render.render(animation=True)

    print("CITIZEN_A_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
