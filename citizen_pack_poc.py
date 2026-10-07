import bpy
import json
import math
import os
from mathutils import Matrix, Vector

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
        [o for o in bpy.data.objects if o not in objects_before],
        [a for a in bpy.data.actions if a not in actions_before],
    )


def find_armature(objects):
    armatures = [o for o in objects if o.type == "ARMATURE"]
    if not armatures:
        raise RuntimeError("No armature found")
    return max(armatures, key=lambda o: len(o.data.bones))


def find_walk_action(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError("No Walk action found: " + ", ".join(a.name for a in actions))
    return min(walks, key=lambda a: len(a.name))


def activate_walk(armature, action, scene_start, scene_end):
    ad = armature.animation_data_create()
    ad.action = None
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)

    action_start = float(action.frame_range[0])
    action_end = float(action.frame_range[1])
    action_span = max(1.0, action_end - action_start)

    track = ad.nla_tracks.new()
    track.name = "Walk"
    strip = track.strips.new("Walk", scene_start, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_end
    strip.repeat = max(1.0, math.ceil((scene_end - scene_start + 1) / action_span))
    return action_span


def top_level_objects(objects):
    imported = set(objects)
    result = [o for o in objects if o.parent not in imported]
    if not result:
        raise RuntimeError("No top-level objects found")
    return result


def make_placement_root(name, top_objects):
    root = bpy.data.objects.new(name + "_Placement", None)
    bpy.context.collection.objects.link(root)
    root.matrix_world = Matrix.Identity(4)

    for obj in top_objects:
        local_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = local_matrix

    bpy.context.view_layer.update()
    return root


def evaluated_mesh_bounds(meshes):
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
        raise RuntimeError("No evaluated mesh vertices found")

    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (lo + hi) * 0.5
    return {
        "min": [round(v, 4) for v in lo],
        "max": [round(v, 4) for v in hi],
        "center": [round(v, 4) for v in center],
    }


def place_root_from_rendered_geometry(root, meshes, desired_x):
    before = evaluated_mesh_bounds(meshes)
    root.location.x += desired_x - before["center"][0]
    bpy.context.view_layer.update()
    after = evaluated_mesh_bounds(meshes)

    if abs(after["center"][0] - desired_x) > 0.05:
        raise RuntimeError(f"Placement failed: desired={desired_x}, bounds={after}")

    return before, after


def pose_motion(armature, start, end):
    scene = bpy.context.scene
    all_names = [b.name for b in armature.pose.bones]
    limb_names = [
        name for name in all_names
        if any(token in name.lower() for token in ("foot", "hand", "wrist", "ankle"))
    ]

    if len(limb_names) < 4:
        limb_names = [
            name for name in all_names
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
            if not all(math.isfinite(value) for value in position):
                raise RuntimeError(f"Invalid pose: {armature.name} {name} frame={frame}")
            positions.append(position.copy())

        amplitudes[name] = round(
            max((a - b).length for a in positions for b in positions),
            6,
        )

    if sum(1 for value in amplitudes.values() if value > 0.005) < 2:
        raise RuntimeError(f"Limb motion check failed for {armature.name}: {amplitudes}")

    return all_names, amplitudes


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
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = (0.0, -10.0, 2.3)
    target = Vector((0.0, 0.0, 1.05))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main():
    reset_scene()
    scene = bpy.context.scene
    scene_start = 0
    scene_end = 32
    scene.frame_start = scene_start
    scene.frame_end = scene_end
    scene.render.fps = 30

    report = {"citizens": []}

    for citizen_name, filename, desired_x in CITIZENS:
        objects, actions = import_glb(os.path.join(ASSET_DIR, filename))
        armature = find_armature(objects)
        walk = find_walk_action(actions)
        meshes = [o for o in objects if o.type == "MESH"]
        tops = top_level_objects(objects)

        armature.name = citizen_name + "_Rig"
        for mesh_index, mesh in enumerate(meshes, start=1):
            mesh.name = f"{citizen_name}_Mesh_{mesh_index:02d}"

        placement_root = make_placement_root(citizen_name, tops)
        action_span = activate_walk(armature, walk, scene_start, scene_end)

        scene.frame_set(scene_start)
        bpy.context.view_layer.update()
        bounds_before, bounds_after = place_root_from_rendered_geometry(
            placement_root,
            meshes,
            desired_x,
        )

        bone_names, amplitudes = pose_motion(armature, scene_start, scene_end)

        scene.frame_set(scene_start)
        bpy.context.view_layer.update()
        final_bounds = evaluated_mesh_bounds(meshes)

        if abs(final_bounds["center"][0] - desired_x) > 0.05:
            raise RuntimeError(
                f"Placement did not survive animation evaluation for {citizen_name}: {final_bounds}"
            )

        report["citizens"].append({
            "name": citizen_name,
            "source": filename,
            "desired_x": desired_x,
            "placement_root": placement_root.name,
            "placement_root_x": round(placement_root.location.x, 4),
            "rendered_bounds_before": bounds_before,
            "rendered_bounds_after": bounds_after,
            "rendered_bounds_final_frame0": final_bounds,
            "top_level_objects": [o.name for o in tops],
            "walk_action": walk.name,
            "bones": len(armature.data.bones),
            "meshes": len(meshes),
            "walk_action_span": action_span,
            "phase_offset": 0,
            "bone_names": bone_names,
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
    bpy.context.view_layer.update()

    report.update({
        "blender_version": bpy.app.version_string,
        "license": "CC0 1.0",
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "preview_engine": scene.render.engine,
        "placement_strategy": "unanimated parent Empty",
    })

    with open(os.path.join(ART_DIR, "qc_report.json"), "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART_DIR, "Citizen_Pack_5.blend"))
    bpy.ops.render.render(animation=True)

    print("CITIZEN_PACK_POC_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
