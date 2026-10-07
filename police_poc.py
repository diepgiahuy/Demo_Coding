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
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature imported")
    return max(arms, key=lambda o: len(o.data.bones))


def find_walk(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found: " + ", ".join(a.name for a in actions))
    return min(walks, key=lambda a: len(a.name))


def find_pose_bone(armature, exact_names=(), contains=()):
    bones = list(armature.pose.bones)
    by_lower = {b.name.lower(): b for b in bones}
    for name in exact_names:
        hit = by_lower.get(name.lower())
        if hit:
            return hit
    for token in contains:
        token = token.lower()
        for bone in bones:
            if token in bone.name.lower():
                return bone
    raise RuntimeError(f"Bone not found exact={exact_names} contains={contains}; available={[b.name for b in bones]}")


def make_mat(name, color, roughness=0.68, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def parent_to_bone_keep_world(obj, armature, pose_bone):
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = pose_bone.name
    obj.matrix_world = world


def cube_obj(name, location, scale_xyz, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale_xyz
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new("SoftEdges", "BEVEL")
        mod.width = bevel
        mod.segments = 1
    obj.data.materials.append(material)
    return obj


def cylinder_obj(name, location, radius, depth, material, vertices=8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def evaluated_bounds(meshes):
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(deps)
        tmp = evaluated.to_mesh()
        try:
            world = evaluated.matrix_world
            for v in tmp.vertices:
                points.append(world @ v.co)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise RuntimeError("No rendered geometry")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def bone_world_point(armature, pose_bone, which="head"):
    local = pose_bone.head if which == "head" else pose_bone.tail
    return armature.matrix_world @ local


def add_box_along_bone(name, armature, pose_bone, width, depth, material, length_scale=0.88):
    head = bone_world_point(armature, pose_bone, "head")
    tail = bone_world_point(armature, pose_bone, "tail")
    direction = tail - head
    length = max(0.03, direction.length * length_scale)
    center = (head + tail) * 0.5
    obj = cube_obj(name, center, (width, depth, length), material, bevel=width * 0.05)
    if direction.length > 1e-6:
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    parent_to_bone_keep_world(obj, armature, pose_bone)
    return obj


def assign_smooth_walk_60fps(armature, action):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)
    start = float(action.frame_range[0])
    end = float(action.frame_range[1])
    span = max(1.0, end - start)
    track = ad.nla_tracks.new()
    track.name = "Walk_60fps"
    strip = track.strips.new("Walk", 0, action)
    strip.action_frame_start = start
    strip.action_frame_end = end
    strip.scale = 2.0
    strip.repeat = 1.0
    strip.blend_type = "REPLACE"
    return int(round(span * 2.0))


def build_police_gear(armature, base_meshes, height):
    navy = make_mat("Police_Navy", (0.035, 0.09, 0.19))
    navy2 = make_mat("Police_Navy_Light", (0.06, 0.15, 0.29))
    black = make_mat("Police_Vest_Black", (0.025, 0.028, 0.032))
    charcoal = make_mat("Police_Gear", (0.055, 0.06, 0.065))
    gold = make_mat("Police_Badge", (0.86, 0.60, 0.10), roughness=0.42, metallic=0.25)

    head = find_pose_bone(armature, exact_names=("Head",), contains=("head",))
    chest = find_pose_bone(armature, exact_names=("Spine2", "Chest", "UpperChest"), contains=("chest", "spine2", "spine_02", "spine.002"))
    hips = find_pose_bone(armature, exact_names=("Hips", "Pelvis"), contains=("hips", "pelvis"))
    upper_l = find_pose_bone(armature, exact_names=("UpperArmL", "LeftArm"), contains=("upperarml", "upper_arm.l", "leftarm", "arm_l"))
    upper_r = find_pose_bone(armature, exact_names=("UpperArmR", "RightArm"), contains=("upperarmr", "upper_arm.r", "rightarm", "arm_r"))
    thigh_l = find_pose_bone(armature, exact_names=("UpperLegL", "LeftUpLeg"), contains=("upperlegl", "thigh.l", "leftupleg", "leg_l"))
    thigh_r = find_pose_bone(armature, exact_names=("UpperLegR", "RightUpLeg"), contains=("upperlegr", "thigh.r", "rightupleg", "leg_r"))
    calf_l = find_pose_bone(armature, exact_names=("LowerLegL", "LeftLeg"), contains=("lowerlegl", "shin.l", "leftleg"))
    calf_r = find_pose_bone(armature, exact_names=("LowerLegR", "RightLeg"), contains=("lowerlegr", "shin.r", "rightleg"))

    gear = []

    chest_pos = bone_world_point(armature, chest, "head")
    chest_tail = bone_world_point(armature, chest, "tail")
    torso_center = (chest_pos + chest_tail) * 0.5

    shirt = cube_obj("Police_Shirt_Torso", torso_center, (height * 0.27, height * 0.145, height * 0.30), navy2, bevel=height * 0.006)
    parent_to_bone_keep_world(shirt, armature, chest)
    gear.append(shirt)

    vest_center = torso_center + Vector((0.0, -height * 0.010, height * 0.012))
    vest = cube_obj("Police_Tactical_Vest", vest_center, (height * 0.29, height * 0.165, height * 0.245), black, bevel=height * 0.007)
    parent_to_bone_keep_world(vest, armature, chest)
    gear.append(vest)

    badge = cube_obj("Police_Chest_Badge", vest_center + Vector((-height * 0.075, -height * 0.087, height * 0.035)), (height * 0.028, height * 0.010, height * 0.042), gold, bevel=height * 0.003)
    parent_to_bone_keep_world(badge, armature, chest)
    gear.append(badge)

    belt_pos = bone_world_point(armature, hips, "head") + Vector((0, 0, height * 0.015))
    belt = cube_obj("Police_Utility_Belt", belt_pos, (height * 0.285, height * 0.155, height * 0.055), black, bevel=height * 0.004)
    parent_to_bone_keep_world(belt, armature, hips)
    gear.append(belt)

    buckle = cube_obj("Police_Belt_Buckle", belt_pos + Vector((0, -height * 0.083, 0)), (height * 0.048, height * 0.012, height * 0.038), gold, bevel=height * 0.002)
    parent_to_bone_keep_world(buckle, armature, hips)
    gear.append(buckle)

    for name, bone in (("Sleeve_L", upper_l), ("Sleeve_R", upper_r)):
        gear.append(add_box_along_bone(name, armature, bone, height * 0.095, height * 0.10, navy2, length_scale=0.58))

    for name, bone in (("Pants_Thigh_L", thigh_l), ("Pants_Thigh_R", thigh_r)):
        gear.append(add_box_along_bone(name, armature, bone, height * 0.105, height * 0.105, navy, length_scale=0.94))
    for name, bone in (("Pants_Calf_L", calf_l), ("Pants_Calf_R", calf_r)):
        gear.append(add_box_along_bone(name, armature, bone, height * 0.095, height * 0.095, navy, length_scale=0.94))

    head_center = bone_world_point(armature, head, "head")
    head_top = bone_world_point(armature, head, "tail")
    if head_top.z < head_center.z:
        head_center, head_top = head_top, head_center
    cap_center = head_top + Vector((0, 0, height * 0.045))
    cap = cylinder_obj("Police_Cap_Crown", cap_center, height * 0.112, height * 0.070, navy, vertices=10)
    parent_to_bone_keep_world(cap, armature, head)
    gear.append(cap)

    brim = cube_obj("Police_Cap_Brim", cap_center + Vector((0, -height * 0.075, -height * 0.030)), (height * 0.19, height * 0.115, height * 0.018), navy, bevel=height * 0.004)
    parent_to_bone_keep_world(brim, armature, head)
    gear.append(brim)

    cap_badge = cube_obj("Police_Cap_Badge", cap_center + Vector((0, -height * 0.113, 0)), (height * 0.036, height * 0.010, height * 0.045), gold, bevel=height * 0.003)
    parent_to_bone_keep_world(cap_badge, armature, head)
    gear.append(cap_badge)

    holster = cube_obj("Police_Holster", belt_pos + Vector((height * 0.13, 0, -height * 0.055)), (height * 0.055, height * 0.075, height * 0.105), charcoal, bevel=height * 0.004)
    parent_to_bone_keep_world(holster, armature, hips)
    gear.append(holster)

    radio = cube_obj("Police_Radio", vest_center + Vector((height * 0.095, -height * 0.090, height * 0.055)), (height * 0.045, height * 0.026, height * 0.085), charcoal, bevel=height * 0.003)
    parent_to_bone_keep_world(radio, armature, chest)
    gear.append(radio)

    return gear, {
        "head_bone": head.name,
        "chest_bone": chest.name,
        "hips_bone": hips.name,
        "upper_arm_l": upper_l.name,
        "upper_arm_r": upper_r.name,
        "thigh_l": thigh_l.name,
        "thigh_r": thigh_r.name,
        "calf_l": calf_l.name,
        "calf_r": calf_r.name,
    }


def make_floor(z):
    bpy.ops.mesh.primitive_plane_add(size=5.5, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "Floor"
    floor.data.materials.append(make_mat("Floor", (0.10, 0.11, 0.13)))


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = hi.z - lo.z
    data = bpy.data.cameras.new("Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.34
    cam = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (height * 0.95, -height * 3.2, center.z + height * 0.03)
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


def pose_qc(armature, start, end):
    scene = bpy.context.scene
    names = [b.name for b in armature.pose.bones if any(t in b.name.lower() for t in ("hand", "wrist", "foot", "ankle", "leg", "arm"))]
    frames = [start, start + (end-start)//4, start + (end-start)//2, start + 3*(end-start)//4, end]
    motion = {}
    for name in names[:24]:
        pts = []
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            pts.append((armature.matrix_world @ armature.pose.bones[name].matrix).translation.copy())
        motion[name] = round(max((a-b).length for a in pts for b in pts), 6)
    if sum(1 for v in motion.values() if v > 0.004) < 4:
        raise RuntimeError("Walk limb motion insufficient: " + repr(motion))
    return motion


def main():
    reset_scene()
    objects, actions = import_glb(BASE_MODEL)
    armature = find_armature(objects)
    base_meshes = [o for o in objects if o.type == "MESH"]
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

    scene_end = assign_smooth_walk_60fps(armature, walk)
    scene.frame_end = scene_end
    scene.frame_set(0)
    bpy.context.view_layer.update()

    gear, bone_map = build_police_gear(armature, base_meshes, height)
    all_meshes = base_meshes + [o for o in gear if o.type == "MESH"]
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

    motion = pose_qc(armature, 0, scene_end)
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
        "base_meshes": len(base_meshes),
        "gear_objects": [o.name for o in gear],
        "bone_map": bone_map,
        "limb_motion_amplitude": motion,
        "reference_design": "user-provided low-poly civilian/police concept",
        "animation_strategy": "original Walk action sampled at 60 fps with NLA time scale 2.0; skeleton and bone orientation unchanged",
    }
    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Police_Officer.blend"))
    bpy.ops.render.render(animation=True)
    print("POLICE_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
