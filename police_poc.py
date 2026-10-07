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

BASE_MODEL = os.path.join(ASSET_DIR, "hoodie_character.glb")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return (
        [o for o in bpy.data.objects if o not in before_objects],
        [a for a in bpy.data.actions if a not in before_actions],
    )


def find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature imported")
    return max(arms, key=lambda o: len(o.data.bones))


def find_walk(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found")
    return min(walks, key=lambda a: len(a.name))


def find_bone(armature, candidates, contains=()):
    by_name = {b.name: b for b in armature.pose.bones}
    for name in candidates:
        if name in by_name:
            return by_name[name]
    for token in contains:
        token = token.lower()
        matches = [b for b in armature.pose.bones if token in b.name.lower()]
        if len(matches) == 1:
            return matches[0]
    raise RuntimeError(
        f"Required bone not found. candidates={candidates}, contains={contains}, "
        f"available={[b.name for b in armature.pose.bones]}"
    )


def make_mat(name, color, roughness=0.62, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def cube(name, location, dimensions, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new("LowPolyBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
    obj.data.materials.append(material)
    return obj


def cylinder(name, location, radius, depth, material, vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def bone_parent_keep_world(obj, armature, bone):
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone.name
    obj.matrix_world = world


def bone_point(armature, bone, tail=False):
    return armature.matrix_world @ (bone.tail if tail else bone.head)


def evaluated_bounds(meshes):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in meshes:
        e = obj.evaluated_get(dg)
        m = e.to_mesh()
        try:
            for v in m.vertices:
                pts.append(e.matrix_world @ v.co)
        finally:
            e.to_mesh_clear()
    if not pts:
        raise RuntimeError("No evaluated mesh geometry")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def assign_walk_60fps(armature, action):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)

    a0 = float(action.frame_range[0])
    a1 = float(action.frame_range[1])
    span = max(1.0, a1 - a0)
    track = ad.nla_tracks.new()
    track.name = "Walk_60fps"
    strip = track.strips.new("Walk", 0, action)
    strip.action_frame_start = a0
    strip.action_frame_end = a1
    strip.scale = 2.0
    strip.repeat = 1.0
    strip.blend_type = "REPLACE"
    return int(round(span * 2.0))


def build_police_gear(armature, height):
    head = find_bone(armature, ["Head"], ("head",))
    torso = find_bone(
        armature,
        ["Chest", "Torso", "Spine2", "Spine.002", "Spine1", "Spine"],
        ("chest", "torso"),
    )
    hips = find_bone(armature, ["Hips", "Pelvis"], ("hips", "pelvis"))

    navy = make_mat("MAT_Police_Navy", (0.025, 0.075, 0.17))
    black = make_mat("MAT_Police_Vest", (0.022, 0.026, 0.032))
    gear_dark = make_mat("MAT_Police_Gear", (0.05, 0.055, 0.065))
    gold = make_mat("MAT_Police_Badge", (0.88, 0.62, 0.12), 0.42, 0.22)

    gear = []

    a = bone_point(armature, torso)
    b = bone_point(armature, torso, True)
    torso_center = (a + b) * 0.5

    vest = cube(
        "Police_Tactical_Vest",
        torso_center + Vector((0, -height * 0.010, 0)),
        (height * 0.265, height * 0.145, height * 0.205),
        black,
        height * 0.006,
    )
    bone_parent_keep_world(vest, armature, torso)
    gear.append(vest)

    chest_badge = cube(
        "Police_Chest_Badge",
        torso_center + Vector((-height * 0.070, -height * 0.080, height * 0.025)),
        (height * 0.026, height * 0.009, height * 0.038),
        gold,
        height * 0.002,
    )
    bone_parent_keep_world(chest_badge, armature, torso)
    gear.append(chest_badge)

    radio = cube(
        "Police_Radio",
        torso_center + Vector((height * 0.075, -height * 0.080, height * 0.045)),
        (height * 0.038, height * 0.023, height * 0.070),
        gear_dark,
        height * 0.003,
    )
    bone_parent_keep_world(radio, armature, torso)
    gear.append(radio)

    hips_pos = bone_point(armature, hips) + Vector((0, 0, height * 0.018))
    belt = cube(
        "Police_Utility_Belt",
        hips_pos,
        (height * 0.27, height * 0.14, height * 0.045),
        black,
        height * 0.003,
    )
    bone_parent_keep_world(belt, armature, hips)
    gear.append(belt)

    buckle = cube(
        "Police_Belt_Buckle",
        hips_pos + Vector((0, -height * 0.075, 0)),
        (height * 0.042, height * 0.010, height * 0.032),
        gold,
        height * 0.002,
    )
    bone_parent_keep_world(buckle, armature, hips)
    gear.append(buckle)

    holster = cube(
        "Police_Holster",
        hips_pos + Vector((height * 0.12, 0, -height * 0.052)),
        (height * 0.050, height * 0.060, height * 0.095),
        gear_dark,
        height * 0.003,
    )
    bone_parent_keep_world(holster, armature, hips)
    gear.append(holster)

    ha = bone_point(armature, head)
    hb = bone_point(armature, head, True)
    head_mid = (ha + hb) * 0.5
    top_z = max(ha.z, hb.z)
    cap_center = Vector((head_mid.x, head_mid.y, top_z + height * 0.035))

    cap_crown = cylinder(
        "Police_Cap_Crown",
        cap_center,
        height * 0.105,
        height * 0.060,
        navy,
        10,
    )
    bone_parent_keep_world(cap_crown, armature, head)
    gear.append(cap_crown)

    brim = cube(
        "Police_Cap_Brim",
        cap_center + Vector((0, -height * 0.065, -height * 0.026)),
        (height * 0.175, height * 0.095, height * 0.016),
        navy,
        height * 0.003,
    )
    bone_parent_keep_world(brim, armature, head)
    gear.append(brim)

    cap_badge = cube(
        "Police_Cap_Badge",
        cap_center + Vector((0, -height * 0.102, -height * 0.002)),
        (height * 0.032, height * 0.009, height * 0.038),
        gold,
        height * 0.002,
    )
    bone_parent_keep_world(cap_badge, armature, head)
    gear.append(cap_badge)

    return gear, {"head": head.name, "torso": torso.name, "hips": hips.name}


def limb_motion_qc(armature, start, end):
    candidates = [
        ["Wrist.L", "Hand.L", "Fist.L"],
        ["Wrist.R", "Hand.R", "Fist.R"],
        ["Foot.L"],
        ["Foot.R"],
    ]
    bones = []
    for names in candidates:
        bones.append(find_bone(armature, names, (names[0].lower(),)))

    scene = bpy.context.scene
    frames = [start, start + (end-start)//4, start + (end-start)//2, start + 3*(end-start)//4, end]
    motion = {}
    for bone in bones:
        pts = []
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            pts.append((armature.matrix_world @ bone.matrix).translation.copy())
        motion[bone.name] = round(max((a-b).length for a in pts for b in pts), 6)
    if min(motion.values()) < 0.004:
        raise RuntimeError("Limb motion QC failed: " + repr(motion))
    return motion


def make_floor(z):
    bpy.ops.mesh.primitive_plane_add(size=5.5, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "Floor"
    floor.data.materials.append(make_mat("MAT_Floor", (0.09, 0.10, 0.12)))


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)
    data = bpy.data.cameras.new("Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.28
    camera = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = center + Vector((height * 0.72, -height * 3.1, height * 0.025))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()


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

    scene_end = assign_walk_60fps(armature, walk)
    scene.frame_end = scene_end
    scene.frame_set(0)
    bpy.context.view_layer.update()

    gear, bone_map = build_police_gear(armature, height)
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

    motion = limb_motion_qc(armature, 0, scene_end)
    scene.frame_set(0)
    bpy.context.view_layer.update()

    report = {
        "blender_version": bpy.app.version_string,
        "base_asset": "Quaternius hoodie_character.glb",
        "license": "CC0 1.0",
        "walk_action": walk.name,
        "fps": 60,
        "frame_start": 0,
        "frame_end": scene_end,
        "character_height": round(height, 4),
        "base_meshes": len(base_meshes),
        "gear_objects": [o.name for o in gear],
        "bone_map": bone_map,
        "limb_motion_amplitude": motion,
        "animation_strategy": "original embedded Walk; 60 fps with NLA scale 2; no retargeting; no bone orientation edits",
        "visual_strategy": "accepted Hoodie citizen base + rigid police vest/cap/belt/badge accessories",
    }
    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Police_Officer.blend"))
    bpy.ops.render.render(animation=True)
    print("POLICE_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
