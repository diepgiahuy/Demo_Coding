import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets", "police_poc")
ART_DIR = os.path.join(ROOT, "artifacts", "police_poc")
FRAME_DIR = os.path.join(ART_DIR, "frames")
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(ART_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)

BASE_MODEL = os.path.join(ASSET_DIR, "character_animated.glb")

VERIFIED_BONES = {
    "head": "Head",
    "torso": "Torso",
    "hips": "Hips",
    "upper_arm_l": "UpperArm.L",
    "upper_arm_r": "UpperArm.R",
    "lower_arm_l": "LowerArm.L",
    "lower_arm_r": "LowerArm.R",
    "thigh_l": "UpperLeg.L",
    "thigh_r": "UpperLeg.R",
    "calf_l": "LowerLeg.L",
    "calf_r": "LowerLeg.R",
    "foot_l": "Foot.L",
    "foot_r": "Foot.R",
}


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
    arms = [obj for obj in objects if obj.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature imported")
    return max(arms, key=lambda obj: len(obj.data.bones))


def find_walk(actions):
    walks = [action for action in actions if "walk" in action.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found: " + ", ".join(a.name for a in actions))
    return min(walks, key=lambda action: len(action.name))


def verify_bones(armature):
    available = {bone.name for bone in armature.pose.bones}
    missing = [name for name in VERIFIED_BONES.values() if name not in available]
    if missing:
        raise RuntimeError(f"Verified rig mismatch. Missing={missing}; available={sorted(available)}")
    return {key: armature.pose.bones[name] for key, name in VERIFIED_BONES.items()}


def make_mat(name, color, roughness=0.65, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def cube_obj(name, location, dimensions, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        modifier = obj.modifiers.new("LowPolyBevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
    obj.data.materials.append(material)
    return obj


def cylinder_obj(name, location, radius, depth, material, vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def parent_to_bone_keep_world(obj, armature, pose_bone):
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = pose_bone.name
    obj.matrix_world = world


def evaluated_bounds(meshes):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        temp_mesh = evaluated.to_mesh()
        try:
            world = evaluated.matrix_world
            for vertex in temp_mesh.vertices:
                points.append(world @ vertex.co)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise RuntimeError("No rendered geometry")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def bone_head_world(armature, bone):
    return armature.matrix_world @ bone.head


def bone_tail_world(armature, bone):
    return armature.matrix_world @ bone.tail


def box_along_bone(name, armature, bone, width, depth, material, length_scale=0.9):
    head = bone_head_world(armature, bone)
    tail = bone_tail_world(armature, bone)
    direction = tail - head
    center = (head + tail) * 0.5
    length = max(0.025, direction.length * length_scale)
    obj = cube_obj(name, center, (width, depth, length), material, bevel=width * 0.045)
    if direction.length > 1e-6:
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    parent_to_bone_keep_world(obj, armature, bone)
    return obj


def assign_walk_60fps(armature, action):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)

    action_start = float(action.frame_range[0])
    action_end = float(action.frame_range[1])
    source_span = max(1.0, action_end - action_start)

    track = ad.nla_tracks.new()
    track.name = "Walk_60fps"
    strip = track.strips.new("Walk", 0, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_end
    strip.scale = 2.0
    strip.repeat = 1.0
    strip.blend_type = "REPLACE"

    return int(round(source_span * 2.0))


def build_police(armature, bones, height):
    navy = make_mat("MAT_Police_Navy", (0.025, 0.075, 0.17))
    blue = make_mat("MAT_Police_Shirt", (0.055, 0.16, 0.31))
    vest_black = make_mat("MAT_Police_Vest", (0.025, 0.028, 0.032))
    gear_dark = make_mat("MAT_Police_Gear", (0.055, 0.06, 0.07))
    gold = make_mat("MAT_Police_Badge", (0.86, 0.58, 0.09), roughness=0.42, metallic=0.22)

    gear = []
    torso = bones["torso"]
    hips = bones["hips"]
    head = bones["head"]

    torso_head = bone_head_world(armature, torso)
    torso_tail = bone_tail_world(armature, torso)
    torso_center = (torso_head + torso_tail) * 0.5

    shirt = cube_obj(
        "Police_Shirt_Torso",
        torso_center,
        (height * 0.275, height * 0.15, height * 0.31),
        blue,
        bevel=height * 0.006,
    )
    parent_to_bone_keep_world(shirt, armature, torso)
    gear.append(shirt)

    vest_center = torso_center + Vector((0.0, -height * 0.012, height * 0.005))
    vest = cube_obj(
        "Police_Tactical_Vest",
        vest_center,
        (height * 0.295, height * 0.17, height * 0.24),
        vest_black,
        bevel=height * 0.007,
    )
    parent_to_bone_keep_world(vest, armature, torso)
    gear.append(vest)

    badge = cube_obj(
        "Police_Chest_Badge",
        vest_center + Vector((-height * 0.073, -height * 0.09, height * 0.035)),
        (height * 0.030, height * 0.010, height * 0.042),
        gold,
        bevel=height * 0.0025,
    )
    parent_to_bone_keep_world(badge, armature, torso)
    gear.append(badge)

    radio = cube_obj(
        "Police_Radio",
        vest_center + Vector((height * 0.09, -height * 0.09, height * 0.055)),
        (height * 0.042, height * 0.025, height * 0.082),
        gear_dark,
        bevel=height * 0.003,
    )
    parent_to_bone_keep_world(radio, armature, torso)
    gear.append(radio)

    hips_pos = bone_head_world(armature, hips) + Vector((0, 0, height * 0.018))
    belt = cube_obj(
        "Police_Utility_Belt",
        hips_pos,
        (height * 0.285, height * 0.16, height * 0.052),
        vest_black,
        bevel=height * 0.0035,
    )
    parent_to_bone_keep_world(belt, armature, hips)
    gear.append(belt)

    buckle = cube_obj(
        "Police_Belt_Buckle",
        hips_pos + Vector((0, -height * 0.085, 0)),
        (height * 0.050, height * 0.011, height * 0.036),
        gold,
        bevel=height * 0.002,
    )
    parent_to_bone_keep_world(buckle, armature, hips)
    gear.append(buckle)

    holster = cube_obj(
        "Police_Holster",
        hips_pos + Vector((height * 0.13, 0.0, -height * 0.06)),
        (height * 0.055, height * 0.075, height * 0.11),
        gear_dark,
        bevel=height * 0.004,
    )
    parent_to_bone_keep_world(holster, armature, hips)
    gear.append(holster)

    for key, suffix in (("upper_arm_l", "L"), ("upper_arm_r", "R")):
        gear.append(
            box_along_bone(
                f"Police_Sleeve_{suffix}",
                armature,
                bones[key],
                height * 0.092,
                height * 0.098,
                blue,
                length_scale=0.62,
            )
        )

    for key, suffix in (("thigh_l", "L"), ("thigh_r", "R")):
        gear.append(
            box_along_bone(
                f"Police_Pants_Thigh_{suffix}",
                armature,
                bones[key],
                height * 0.105,
                height * 0.105,
                navy,
                length_scale=0.93,
            )
        )

    for key, suffix in (("calf_l", "L"), ("calf_r", "R")):
        gear.append(
            box_along_bone(
                f"Police_Pants_Calf_{suffix}",
                armature,
                bones[key],
                height * 0.095,
                height * 0.095,
                navy,
                length_scale=0.92,
            )
        )

    head_a = bone_head_world(armature, head)
    head_b = bone_tail_world(armature, head)
    cap_z = max(head_a.z, head_b.z) + height * 0.04
    cap_center = Vector(((head_a.x + head_b.x) * 0.5, (head_a.y + head_b.y) * 0.5, cap_z))

    cap = cylinder_obj(
        "Police_Cap_Crown",
        cap_center,
        height * 0.112,
        height * 0.065,
        navy,
        vertices=10,
    )
    parent_to_bone_keep_world(cap, armature, head)
    gear.append(cap)

    brim = cube_obj(
        "Police_Cap_Brim",
        cap_center + Vector((0, -height * 0.078, -height * 0.028)),
        (height * 0.19, height * 0.115, height * 0.018),
        navy,
        bevel=height * 0.004,
    )
    parent_to_bone_keep_world(brim, armature, head)
    gear.append(brim)

    cap_badge = cube_obj(
        "Police_Cap_Badge",
        cap_center + Vector((0, -height * 0.116, -height * 0.002)),
        (height * 0.036, height * 0.010, height * 0.043),
        gold,
        bevel=height * 0.002,
    )
    parent_to_bone_keep_world(cap_badge, armature, head)
    gear.append(cap_badge)

    return gear


def make_floor(z):
    bpy.ops.mesh.primitive_plane_add(size=5.5, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "Floor"
    floor.data.materials.append(make_mat("MAT_Floor", (0.10, 0.11, 0.13)))


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)
    data = bpy.data.cameras.new("Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.32
    camera = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = center + Vector((height * 0.85, -height * 3.2, height * 0.04))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()


def pose_qc(armature, bones, start, end):
    scene = bpy.context.scene
    test_keys = [
        "upper_arm_l", "upper_arm_r", "lower_arm_l", "lower_arm_r",
        "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r",
    ]
    frames = [start, start + (end-start)//4, start + (end-start)//2, start + 3*(end-start)//4, end]
    motion = {}
    for key in test_keys:
        bone = bones[key]
        positions = []
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            positions.append((armature.matrix_world @ bone.matrix).translation.copy())
        motion[bone.name] = round(max((a-b).length for a in positions for b in positions), 6)

    if sum(1 for value in motion.values() if value > 0.004) < 6:
        raise RuntimeError("Walk limb motion insufficient: " + repr(motion))
    return motion


def main():
    reset_scene()
    objects, actions = import_glb(BASE_MODEL)
    armature = find_armature(objects)
    bones = verify_bones(armature)
    base_meshes = [obj for obj in objects if obj.type == "MESH"]
    walk = find_walk(actions)

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.render.fps = 60
    scene.frame_set(0)
    bpy.context.view_layer.update()

    lo0, hi0 = evaluated_bounds(base_meshes)
    height = hi0.z - lo0.z
    if not 0.5 < height < 4.0:
        raise RuntimeError(f"Unexpected character height: {height}")

    scene_end = assign_walk_60fps(armature, walk)
    scene.frame_end = scene_end
    scene.frame_set(0)
    bpy.context.view_layer.update()

    gear = build_police(armature, bones, height)
    all_meshes = base_meshes + [obj for obj in gear if obj.type == "MESH"]
    lo, hi = evaluated_bounds(all_meshes)

    make_floor(lo.z - 0.01)
    make_camera(lo, hi)

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 30
    scene.render.filepath = os.path.join(FRAME_DIR, "frame_")

    motion = pose_qc(armature, bones, 0, scene_end)
    scene.frame_set(0)
    bpy.context.view_layer.update()

    report = {
        "blender_version": bpy.app.version_string,
        "base_asset": "Quaternius character_animated.glb",
        "license": "CC0 1.0",
        "walk_action": walk.name,
        "source_action_range": [float(walk.frame_range[0]), float(walk.frame_range[1])],
        "fps": 60,
        "frame_start": 0,
        "frame_end": scene_end,
        "character_height": round(height, 4),
        "verified_bones": VERIFIED_BONES,
        "base_meshes": len(base_meshes),
        "gear_objects": [obj.name for obj in gear],
        "limb_motion_amplitude": motion,
        "reference_design": "user-provided low-poly police concept",
        "animation_strategy": "original Walk action; 60 fps scene; NLA scale 2.0; no bone orientation edits",
    }
    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Police_Officer.blend"))
    bpy.ops.render.render(animation=True)

    print("POLICE_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
