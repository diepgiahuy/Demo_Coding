import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
VIDEO = OUT / "preview.mp4"
BLEND = OUT / "preview.blend"
REPORT = OUT / "test_report.json"

# Reset scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 72
scene.render.fps = 24
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = str(VIDEO)

# Workbench display settings.
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "WORLD"


def add_cube(name, location, scale, color):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.color = color
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_cylinder(name, location, radius, depth, color):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.color = color
    return obj


def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


# Base city block.
add_cube("Ground", (0, 0, -0.35), (15, 22, 0.35), (0.20, 0.42, 0.18, 1.0))
add_cube("Road_Main", (0, 0, 0.01), (3.2, 22, 0.04), (0.08, 0.08, 0.10, 1.0))
add_cube("Road_Cross", (0, 0, 0.02), (15, 2.8, 0.04), (0.08, 0.08, 0.10, 1.0))

# Sidewalks.
for x in (-4.2, 4.2):
    add_cube(f"Sidewalk_{x}", (x, 0, 0.08), (0.8, 22, 0.08), (0.55, 0.55, 0.55, 1.0))

# Lane markers.
for y in range(-18, 19, 4):
    add_cube(f"Lane_{y}", (0, y, 0.09), (0.10, 1.2, 0.03), (0.95, 0.85, 0.15, 1.0))

# Crosswalk.
for x in (-2.4, -1.6, -0.8, 0.8, 1.6, 2.4):
    add_cube(f"Crosswalk_{x}", (x, 0, 0.10), (0.25, 2.2, 0.03), (0.95, 0.95, 0.95, 1.0))

# Buildings, kept away from the camera path.
building_colors = [
    (0.26, 0.47, 0.78, 1.0),
    (0.78, 0.34, 0.28, 1.0),
    (0.72, 0.62, 0.28, 1.0),
    (0.34, 0.62, 0.50, 1.0),
]
for ix, x in enumerate((-11, -7, 7, 11)):
    for iy, y in enumerate((-16, -8, 8, 16)):
        h = 3.5 + ((ix + iy) % 4) * 1.8
        add_cube(
            f"Building_{ix}_{iy}",
            (x, y, h),
            (2.2, 2.8, h),
            building_colors[(ix + iy) % len(building_colors)],
        )

# Cars.
car_count = 8
car_colors = [
    (0.90, 0.12, 0.10, 1.0),
    (0.12, 0.36, 0.90, 1.0),
    (0.95, 0.70, 0.08, 1.0),
    (0.10, 0.70, 0.35, 1.0),
]
for i in range(car_count):
    lane_x = -1.25 if i % 2 == 0 else 1.25
    start_y = -18 + (i % 4) * 10
    direction = 1 if i % 2 == 0 else -1
    car = add_cube(
        f"Car_{i:02d}",
        (lane_x, start_y, 0.55),
        (0.65, 1.25, 0.45),
        car_colors[i % len(car_colors)],
    )
    car.keyframe_insert(data_path="location", frame=1)
    car.location.y = start_y + direction * 30
    car.keyframe_insert(data_path="location", frame=72)

# NPCs with separate head/body objects.
npc_count = 20
for i in range(npc_count):
    side = -1 if i % 2 == 0 else 1
    x = side * (4.0 + (i % 3) * 0.35)
    start_y = -18 + (i % 10) * 4
    direction = 1 if (i // 2) % 2 == 0 else -1

    body = add_cylinder(
        f"NPC_Body_{i:02d}",
        (x, start_y, 0.9),
        0.28,
        1.2,
        (0.18, 0.38 + 0.02 * (i % 5), 0.75, 1.0),
    )
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.28, location=(x, start_y, 1.72))
    head = bpy.context.object
    head.name = f"NPC_{i:02d}"
    head.color = (0.90, 0.68, 0.44, 1.0)

    for obj in (body, head):
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.y = start_y + direction * 12
        obj.keyframe_insert(data_path="location", frame=72)

# Trees for clear depth cues.
for x in (-5.6, 5.6):
    for y in (-15, -9, -3, 3, 9, 15):
        add_cylinder(f"TreeTrunk_{x}_{y}", (x, y, 0.65), 0.18, 1.3, (0.25, 0.12, 0.05, 1.0))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.8, location=(x, y, 1.8))
        crown = bpy.context.object
        crown.name = f"TreeCrown_{x}_{y}"
        crown.color = (0.12, 0.55, 0.16, 1.0)

# Camera stays outside all geometry and performs a small dolly.
bpy.ops.object.camera_add(location=(30, -40, 30))
cam = bpy.context.object
cam.name = "Camera_Main"
cam.data.lens = 38
cam.data.clip_start = 0.1
cam.data.clip_end = 500
scene.camera = cam

point_camera(cam, (0, 1, 2.0))
cam.keyframe_insert(data_path="location", frame=1)
cam.keyframe_insert(data_path="rotation_euler", frame=1)

cam.location = (26, -34, 26)
point_camera(cam, (0, 3, 2.0))
cam.keyframe_insert(data_path="location", frame=72)
cam.keyframe_insert(data_path="rotation_euler", frame=72)

# Save and render.
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.render.render(animation=True)

report = {
    "blender_version": bpy.app.version_string,
    "ffmpeg_supported": bool(bpy.app.ffmpeg.supported),
    "engine": scene.render.engine,
    "media_type": scene.render.image_settings.media_type,
    "file_format": scene.render.image_settings.file_format,
    "frame_start": scene.frame_start,
    "frame_end": scene.frame_end,
    "fps": scene.render.fps,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "car_count": len([o for o in bpy.data.objects if o.name.startswith("Car_")]),
    "npc_count": len([o for o in bpy.data.objects if o.name.startswith("NPC_") and not o.name.startswith("NPC_Body_")]),
    "camera": scene.camera.name if scene.camera else None,
    "blend_exists": BLEND.exists(),
    "video_exists": VIDEO.exists(),
    "video_size_bytes": VIDEO.stat().st_size if VIDEO.exists() else 0,
}

REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

assert report["ffmpeg_supported"]
assert report["blend_exists"]
assert report["video_exists"]
assert report["video_size_bytes"] > 5000
assert report["car_count"] == car_count
assert report["npc_count"] == npc_count
assert report["camera"] == "Camera_Main"

print("BLENDER_PROOF_PASS")
print(json.dumps(report, indent=2))
