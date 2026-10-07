import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "source_exact_packs"
ART_ROOT = ROOT / "artifacts" / "animated_men_women"
ART_ROOT.mkdir(parents=True, exist_ok=True)

PACKS = [
    ("Men", SOURCE_ROOT / "men"),
    ("Women", SOURCE_ROOT / "women"),
]


def all_blends(folder):
    return [p for p in folder.rglob("*.blend") if not p.name.endswith(".blend1")]


def blend_score(path):
    s = str(path).lower()
    score = path.stat().st_size / 1_000_000.0
    if "lowpoly" in s or "low_poly" in s or "low poly" in s:
        score += 100
    if "smooth" in s:
        score -= 50
    if "source" in s:
        score += 10
    return score


def choose_source_blend(folder):
    blends = all_blends(folder)
    if not blends:
        raise RuntimeError(f"No .blend source found under {folder}")
    blends.sort(key=blend_score, reverse=True)
    return blends[0], blends


def walk_action():
    actions = list(bpy.data.actions)
    if not actions:
        raise RuntimeError("No actions found in source .blend")
    preferred = [a for a in actions if "walk" in a.name.lower()]
    if not preferred:
        preferred = [a for a in actions if "run" in a.name.lower()]
    if not preferred:
        preferred = actions
    return sorted(preferred, key=lambda a: (len(a.name), a.name.lower()))[0]


def armature_meshes(arm):
    result = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        linked = obj.parent == arm
        if not linked:
            for mod in obj.modifiers:
                if mod.type == "ARMATURE" and mod.object == arm:
                    linked = True
                    break
        if linked:
            result.append(obj)
    return result


def get_character_armatures():
    arms = []
    for obj in bpy.data.objects:
        if obj.type != "ARMATURE":
            continue
        meshes = armature_meshes(obj)
        if meshes:
            arms.append((obj, meshes))
    arms.sort(key=lambda pair: pair[0].name.lower())
    return arms


def isolate_character(target_arm, target_meshes):
    keep = {target_arm, *target_meshes}
    for obj in bpy.data.objects:
        if obj.type in {"CAMERA", "LIGHT"}:
            obj.hide_render = True
            continue
        if obj not in keep:
            obj.hide_render = True
            obj.hide_viewport = True
        else:
            obj.hide_render = False
            obj.hide_viewport = False


def assign_action(arm, action):
    anim = arm.animation_data_create()
    for track in list(anim.nla_tracks):
        anim.nla_tracks.remove(track)
    anim.action = action


def bounds(meshes, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pts = []
    for obj in meshes:
        if obj.hide_render:
            continue
        eval_obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for c in eval_obj.bound_box:
            pts.append(eval_obj.matrix_world @ Vector(c))
    if not pts:
        raise RuntimeError("No visible mesh bounds")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def make_floor(z, center):
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(center.x, center.y, z - 0.015))
    floor = bpy.context.object
    floor.name = "Proof_Floor"
    mat = bpy.data.materials.new("Proof_Floor_Mat")
    mat.diffuse_color = (0.10, 0.11, 0.13, 1.0)
    floor.data.materials.append(mat)
    return floor


def make_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)
    data = bpy.data.cameras.new("Proof_Camera")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.35
    cam = bpy.data.objects.new("Proof_Camera", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (center.x, center.y - height * 3.2, center.z + height * 0.02)
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def configure_render(out_dir, start):
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
    scene.render.filepath = str(out_dir / "frames" / "frame_")


def motion_probe(arm, start):
    names = [b.name for b in arm.pose.bones]
    limbs = [n for n in names if any(k in n.lower() for k in ("hand", "wrist", "foot", "ankle"))]
    if len(limbs) < 4:
        limbs = [n for n in names if any(k in n.lower() for k in ("arm", "leg"))][:12]
    frames = [start, start + 8, start + 16, start + 24, start + 32]
    result = {}
    for name in limbs[:12]:
        pts = []
        for f in frames:
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            pts.append((arm.matrix_world @ arm.pose.bones[name].matrix).translation.copy())
        result[name] = round(max((a - b).length for a in pts for b in pts), 6)
    return result


def render_character(pack_name, source_blend, arm_index, output_name):
    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    chars = get_character_armatures()
    if arm_index >= len(chars):
        raise RuntimeError(f"{source_blend}: expected armature index {arm_index}, found {len(chars)}")
    arm, meshes = chars[arm_index]
    action = walk_action()
    assign_action(arm, action)
    isolate_character(arm, meshes)

    start = int(math.floor(action.frame_range[0]))
    out_dir = ART_ROOT / output_name
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)
    configure_render(out_dir, start)

    lo, hi = bounds(meshes, start)
    center = (lo + hi) * 0.5
    floor = make_floor(lo.z, center)
    floor.hide_render = False
    make_camera(lo, hi)

    motion = motion_probe(arm, start)
    moving_limbs = sum(1 for v in motion.values() if v > 0.005)
    if moving_limbs < 2:
        raise RuntimeError(f"Motion probe failed for {output_name}: {motion}")

    arm.name = output_name + "_Rig"
    for i, mesh in enumerate(meshes, 1):
        mesh.name = f"{output_name}_Mesh_{i:02d}"

    blend_out = out_dir / f"{output_name}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
    bpy.ops.render.render(animation=True)

    return {
        "name": output_name,
        "pack": pack_name,
        "source_blend": str(source_blend.relative_to(ROOT)),
        "source_armature": chars[arm_index][0].name,
        "action": action.name,
        "bones": len(arm.data.bones),
        "meshes": len(meshes),
        "moving_limbs": moving_limbs,
        "motion": motion,
        "frame_start": start,
        "frame_end": start + 32,
        "resolution": [300, 450],
    }


def main():
    report = {
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "source": "Official Quaternius Animated Men Pack + Animated Women Pack Google Drive folders",
        "packs": {},
        "characters": [],
    }

    for pack_name, folder in PACKS:
        source_blend, candidates = choose_source_blend(folder)
        bpy.ops.wm.open_mainfile(filepath=str(source_blend))
        chars = get_character_armatures()
        report["packs"][pack_name] = {
            "selected_blend": str(source_blend.relative_to(ROOT)),
            "blend_candidates": [str(p.relative_to(ROOT)) for p in candidates],
            "armatures_with_mesh": len(chars),
            "actions": [a.name for a in bpy.data.actions],
        }
        if len(chars) < 4:
            raise RuntimeError(f"{pack_name}: selected source has only {len(chars)} character armatures")

        for i in range(4):
            report["characters"].append(
                render_character(pack_name, source_blend, i, f"{pack_name}_{i+1:02d}")
            )

    with open(ART_ROOT / "qc_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("ANIMATED_MEN_WOMEN_PROOF_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
