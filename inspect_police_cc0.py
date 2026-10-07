import bpy
import json
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(ROOT, "assets", "police_cc0", "police_static.glb")
ART = os.path.join(ROOT, "artifacts", "police_cc0")
os.makedirs(ART, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ASSET)
    return [o for o in bpy.data.objects if o not in before]


def world_bounds(objects):
    pts = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        for c in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(c))
    if not pts:
        raise RuntimeError("No mesh geometry")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def mesh_stats(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) * 0.5
    return {
        "name": obj.name,
        "parent": obj.parent.name if obj.parent else None,
        "verts": len(obj.data.vertices),
        "polys": len(obj.data.polygons),
        "materials": [m.name if m else None for m in obj.data.materials],
        "center": [round(v, 5) for v in center],
        "min": [round(v, 5) for v in lo],
        "max": [round(v, 5) for v in hi],
    }


def separate_loose_parts(mesh_objects):
    for obj in list(mesh_objects):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.separate(type="LOOSE")
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def add_floor(z, size):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    floor = bpy.context.object
    floor.name = "QC_Floor"
    mat = bpy.data.materials.new("QC_Floor_Mat")
    mat.diffuse_color = (0.08, 0.09, 0.11, 1)
    floor.data.materials.append(mat)
    return floor


def add_camera(lo, hi):
    center = (lo + hi) * 0.5
    height = max(0.5, hi.z - lo.z)
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = height * 1.28
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = center + Vector((height * 0.82, -height * 3.2, height * 0.05))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


def main():
    reset()
    imported = import_model()
    original_meshes = [o for o in imported if o.type == "MESH"]
    lo, hi = world_bounds(original_meshes)

    report = {
        "blender_version": bpy.app.version_string,
        "source": "3DAssets.dev asset 36370",
        "license": "CC0 1.0 Universal",
        "original_objects": [
            {
                "name": o.name,
                "type": o.type,
                "parent": o.parent.name if o.parent else None,
            }
            for o in imported
        ],
        "original_meshes": [mesh_stats(o) for o in original_meshes],
        "model_bounds": {
            "min": [round(v, 5) for v in lo],
            "max": [round(v, 5) for v in hi],
            "size": [round(v, 5) for v in (hi - lo)],
        },
    }

    separated = separate_loose_parts(original_meshes)
    # Exclude any QC geometry if this function is reused later.
    separated = [o for o in separated if not o.name.startswith("QC_")]
    report["loose_part_count"] = len(separated)
    report["loose_parts"] = sorted(
        [mesh_stats(o) for o in separated],
        key=lambda row: (row["center"][2], row["center"][0], row["center"][1]),
        reverse=True,
    )

    with open(os.path.join(ART, "inspection.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Keep separated geometry in the diagnostic .blend so it can be inspected directly.
    add_floor(lo.z - 0.01, max(5.0, (hi.z - lo.z) * 3.0))
    add_camera(lo, hi)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(ART, "police_static_preview.png")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, "Police_Static_Separated.blend"))
    bpy.ops.render.render(write_still=True)

    print("POLICE_CC0_INSPECT_PASS")
    print("LOOSE_PART_COUNT", len(separated))
    for row in report["loose_parts"]:
        print("PART", row["name"], "center", row["center"], "size", [round(row["max"][i]-row["min"][i], 5) for i in range(3)], "verts", row["verts"], "mats", row["materials"])


if __name__ == "__main__":
    main()
