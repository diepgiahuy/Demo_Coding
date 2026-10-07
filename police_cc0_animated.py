import bpy
import json
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, "assets", "police_cc0_anim")
ART_DIR = os.path.join(ROOT, "artifacts", "police_cc0_anim")
FRAME_DIR = os.path.join(ART_DIR, "frames")
os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(ART_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)

RIGGED_HOODIE = os.path.join(ASSET_DIR, "hoodie_character.glb")
TPOSE = os.path.join(ASSET_DIR, "police_tpose_base.glb")


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
        raise RuntimeError("No armature found")
    return max(arms, key=lambda o: len(o.data.bones))


def find_walk(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found")
    return min(walks, key=lambda a: len(a.name))


def evaluated_bounds(meshes):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in meshes:
        e = obj.evaluated_get(dg)
        tmp = e.to_mesh()
        try:
            for v in tmp.vertices:
                pts.append(e.matrix_world @ v.co)
        finally:
            e.to_mesh_clear()
    if not pts:
        raise RuntimeError("No evaluated mesh vertices")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def join_meshes(meshes, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.hide_viewport = False
        o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    out = bpy.context.object
    out.name = name
    return out


def make_material(name, color, roughness=0.67, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return m


def cube_obj(name, location, dimensions, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.object
    o.name = name
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = o.modifiers.new("LowPolyBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
    o.data.materials.append(material)
    return o


def cylinder_obj(name, location, radius, depth, material, vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return o


def bone_parent_keep_world(obj, armature, bone):
    world = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone.name
    obj.matrix_world = world


def find_bone(armature, exact=(), tokens=()):
    by_lower = {b.name.lower(): b for b in armature.pose.bones}
    for n in exact:
        if n.lower() in by_lower:
            return by_lower[n.lower()]
    for token in tokens:
        token = token.lower()
        hits = [b for b in armature.pose.bones if token in b.name.lower()]
        if len(hits) == 1:
            return hits[0]
    raise RuntimeError(f"Bone not found exact={exact} tokens={tokens}; available={[b.name for b in armature.pose.bones]}")


def bone_world(armature, bone, tail=False):
    return armature.matrix_world @ (bone.tail if tail else bone.head)


def align_target_to_source(target, source_meshes):
    source_lo, source_hi = evaluated_bounds(source_meshes)
    target_lo, target_hi = evaluated_bounds([target])

    source_height = source_hi.z - source_lo.z
    target_height = target_hi.z - target_lo.z
    if target_height <= 0:
        raise RuntimeError("Invalid target height")

    scale = source_height / target_height
    target.scale *= scale
    bpy.context.view_layer.update()

    target_lo, target_hi = evaluated_bounds([target])
    source_center_xy = Vector(((source_lo.x + source_hi.x) * 0.5, (source_lo.y + source_hi.y) * 0.5, 0))
    target_center_xy = Vector(((target_lo.x + target_hi.x) * 0.5, (target_lo.y + target_hi.y) * 0.5, 0))
    offset = source_center_xy - target_center_xy
    offset.z = source_lo.z - target_lo.z
    target.location += offset
    bpy.context.view_layer.update()

    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    target.select_set(False)

    final_lo, final_hi = evaluated_bounds([target])
    return {
        "scale": round(scale, 6),
        "source_bounds": [[round(v,5) for v in source_lo], [round(v,5) for v in source_hi]],
        "target_bounds": [[round(v,5) for v in final_lo], [round(v,5) for v in final_hi]],
    }


def auto_weight_to_armature(target, armature):
    for vg in list(target.vertex_groups):
        target.vertex_groups.remove(vg)
    for mod in list(target.modifiers):
        if mod.type == "ARMATURE":
            target.modifiers.remove(mod)

    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.parent_set(type="ARMATURE_AUTO", keep_transform=True)
    bpy.context.view_layer.update()

    arm_mods = [m for m in target.modifiers if m.type == "ARMATURE" and m.object == armature]
    if not arm_mods:
        raise RuntimeError("Automatic weights did not create Armature modifier")
    weighted_groups = [g.name for g in target.vertex_groups if g.name in armature.data.bones]
    if len(weighted_groups) < 8:
        raise RuntimeError(f"Too few weighted bone groups: {len(weighted_groups)}")
    return weighted_groups


def color_police_body(target):
    skin = make_material("MAT_Skin", (0.72, 0.47, 0.29))
    navy = make_material("MAT_Police_Shirt", (0.045, 0.12, 0.25))
    vest = make_material("MAT_Police_Vest", (0.025, 0.03, 0.04))
    pants = make_material("MAT_Police_Pants", (0.025, 0.07, 0.16))
    shoes = make_material("MAT_Shoes", (0.035, 0.035, 0.04))

    target.data.materials.clear()
    mats = [skin, navy, vest, pants, shoes]
    for m in mats:
        target.data.materials.append(m)

    # Work in local coordinates after transforms were applied.
    zs = [v.co.z for v in target.data.vertices]
    xs = [v.co.x for v in target.data.vertices]
    zmin, zmax = min(zs), max(zs)
    xmin, xmax = min(xs), max(xs)
    h = zmax - zmin
    half_span = max(abs(xmin), abs(xmax))

    for poly in target.data.polygons:
        c = poly.center
        zn = (c.z - zmin) / h
        xn = abs(c.x) / max(half_span, 1e-6)

        # Head/neck and far hands stay skin.
        if zn > 0.83 or (xn > 0.79 and 0.60 < zn < 0.80):
            poly.material_index = 0
        elif zn < 0.075:
            poly.material_index = 4
        elif zn < 0.52:
            poly.material_index = 3
        else:
            # Central torso is vest; arms/shoulders stay police blue.
            if xn < 0.28 and 0.55 < zn < 0.79:
                poly.material_index = 2
            else:
                poly.material_index = 1

    return {
        "zmin": round(zmin, 5),
        "zmax": round(zmax, 5),
        "half_span": round(half_span, 5),
    }


def add_accessories(armature, target_height):
    head = find_bone(armature, exact=("Head",), tokens=("head",))
    hips = find_bone(armature, exact=("Hips", "Pelvis"), tokens=("hips", "pelvis"))
    chest = find_bone(armature, exact=("Chest", "Torso", "Spine2", "Spine1", "Spine"), tokens=("chest", "torso"))

    cap_mat = make_material("MAT_Cap", (0.02, 0.055, 0.13))
    black = make_material("MAT_Belt", (0.02, 0.022, 0.025))
    gold = make_material("MAT_Badge", (0.90, 0.63, 0.10), roughness=0.4, metallic=0.2)

    accessories = []

    hp0 = bone_world(armature, head)
    hp1 = bone_world(armature, head, True)
    topz = max(hp0.z, hp1.z)
    hcenter = (hp0 + hp1) * 0.5
    cap_center = Vector((hcenter.x, hcenter.y, topz + target_height * 0.035))

    crown = cylinder_obj("Police_Cap_Crown", cap_center, target_height * 0.105, target_height * 0.058, cap_mat, vertices=10)
    bone_parent_keep_world(crown, armature, head)
    accessories.append(crown)

    brim = cube_obj("Police_Cap_Brim", cap_center + Vector((0, -target_height * 0.070, -target_height * 0.025)), (target_height * 0.17, target_height * 0.10, target_height * 0.015), cap_mat, target_height * 0.003)
    bone_parent_keep_world(brim, armature, head)
    accessories.append(brim)

    cap_badge = cube_obj("Police_Cap_Badge", cap_center + Vector((0, -target_height * 0.108, -target_height * 0.002)), (target_height * 0.032, target_height * 0.009, target_height * 0.040), gold, target_height * 0.002)
    bone_parent_keep_world(cap_badge, armature, head)
    accessories.append(cap_badge)

    hips_pos = bone_world(armature, hips)
    belt = cube_obj("Police_Belt", hips_pos + Vector((0, 0, target_height * 0.015)), (target_height * 0.27, target_height * 0.13, target_height * 0.042), black, target_height * 0.003)
    bone_parent_keep_world(belt, armature, hips)
    accessories.append(belt)

    buckle = cube_obj("Police_Buckle", hips_pos + Vector((0, -target_height * 0.070, target_height * 0.015)), (target_height * 0.042, target_height * 0.010, target_height * 0.030), gold, target_height * 0.002)
    bone_parent_keep_world(buckle, armature, hips)
    accessories.append(buckle)

    chest_pos = (bone_world(armature, chest) + bone_world(armature, chest, True)) * 0.5
    badge = cube_obj("Police_Chest_Badge", chest_pos + Vector((-target_height * 0.055, -target_height * 0.070, target_height * 0.020)), (target_height * 0.026, target_height * 0.008, target_height * 0.036), gold, target_height * 0.002)
    bone_parent_keep_world(badge, armature, chest)
    accessories.append(badge)

    return accessories, {"head": head.name, "hips": hips.name, "chest": chest.name}


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


def qc_deformation(target, frames):
    scene = bpy.context.scene
    sizes = []
    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        lo, hi = evaluated_bounds([target])
        size = hi - lo
        if not all(math.isfinite(v) for v in size):
            raise RuntimeError(f"Non-finite deformation at frame {f}")
        sizes.append([round(v,5) for v in size])
    # Exploded geometry guard.
    max_h = max(s[2] for s in sizes)
    min_h = min(s[2] for s in sizes)
    if min_h <= 0 or max_h / min_h > 1.45:
        raise RuntimeError(f"Unstable animated bounds: {sizes}")
    return sizes


def make_floor(z, height):
    bpy.ops.mesh.primitive_plane_add(size=height * 3.2, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "Floor"
    floor.data.materials.append(make_material("MAT_Floor", (0.085, 0.09, 0.105)))


def make_camera(meshes):
    lo, hi = evaluated_bounds(meshes)
    center = (lo + hi) * 0.5
    h = max(0.5, hi.z - lo.z)
    data = bpy.data.cameras.new("Camera")
    data.type = "ORTHO"
    data.ortho_scale = h * 1.28
    cam = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = center + Vector((h * 0.68, -h * 3.0, h * 0.035))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    return lo, hi


def main():
    reset_scene()

    source_objects, source_actions = import_glb(RIGGED_HOODIE)
    armature = find_armature(source_objects)
    walk = find_walk(source_actions)
    source_meshes = [o for o in source_objects if o.type == "MESH"]

    # Work strictly in source rest pose while fitting/skinning.
    armature.data.pose_position = "REST"
    if armature.animation_data:
        armature.animation_data_clear()
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()

    target_objects, _ = import_glb(TPOSE)
    target_meshes = [o for o in target_objects if o.type == "MESH"]
    target = join_meshes(target_meshes, "Police_Body")

    alignment = align_target_to_source(target, source_meshes)
    weighted_groups = auto_weight_to_armature(target, armature)
    material_regions = color_police_body(target)

    # Hide source Hoodie geometry only after it served as a verified rig/proportion source.
    for o in source_meshes:
        o.hide_render = True
        o.hide_viewport = True

    target_lo, target_hi = evaluated_bounds([target])
    target_height = target_hi.z - target_lo.z
    accessories, bone_map = add_accessories(armature, target_height)

    armature.data.pose_position = "POSE"
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.render.fps = 60
    scene_end = assign_walk_60fps(armature, walk)
    scene.frame_end = scene_end

    sample_frames = sorted(set([0, scene_end // 4, scene_end // 2, 3 * scene_end // 4, scene_end]))
    deform_sizes = qc_deformation(target, sample_frames)
    scene.frame_set(0)
    bpy.context.view_layer.update()

    visible_meshes = [target] + [o for o in accessories if o.type == "MESH"]
    lo, hi = make_camera(visible_meshes)
    make_floor(lo.z - 0.01, hi.z - lo.z)

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

    report = {
        "blender_version": bpy.app.version_string,
        "body_asset": "3DAssets.dev T-pose reference 36385, CC0",
        "rig_animation_asset": "Quaternius Hoodie Character, CC0",
        "walk_action": walk.name,
        "fps": 60,
        "frame_end": scene_end,
        "alignment": alignment,
        "weighted_bone_group_count": len(weighted_groups),
        "weighted_groups": weighted_groups,
        "material_regions": material_regions,
        "bone_map": bone_map,
        "accessories": [o.name for o in accessories],
        "deformation_sample_frames": sample_frames,
        "deformation_sizes": deform_sizes,
        "strategy": "CC0 T-pose low-poly body, official Blender automatic armature weights to already-proven Quaternius rig; original Walk action; 60fps sampling; no retarget and no bone-orientation changes",
    }
    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Police_Officer_CC0.blend"))
    bpy.ops.render.render(animation=True)

    print("POLICE_CC0_ANIM_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
