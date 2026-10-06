import bpy
import json
import math
import os
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
scene.frame_end = 48
scene.render.fps = 24
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = str(VIDEO)

# World.
scene.world.color = (0.04, 0.06, 0.1)

# Helpers.
def add_cube(name, location, scale):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

# Ground and roads.
add_cube("Ground", (0, 0, -0.3), (14, 20, 0.3))
add_cube("Road_Main", (0, 0, 0.02), (3.0, 20, 0.03))
add_cube("Road_Cross", (0, 0, 0.03), (14, 2.4, 0.03))

# Buildings.
for ix, x in enumerate((-10, -6, 6, 10)):
    for iy, y in enumerate((-14, -7, 7, 14)):
        h = 2.5 + ((ix + iy) % 4) * 1.8
        add_cube(f"Building_{ix}_{iy}", (x, y, h), (2.2, 2.6, h))

# Cars move along the main road.
car_count = 6
for i in range(car_count):
    lane_x = -1.15 if i % 2 == 0 else 1.15
    start_y = -18 + i * 5.5
    car = add_cube(f"Car_{i:02d}", (lane_x, start_y, 0.55), (0.65, 1.2, 0.45))
    car.keyframe_insert(data_path="location", frame=1)
    car.location.y = start_y + (28 if i % 2 == 0 else -28)
    car.keyframe_insert(data_path="location", frame=48)

# NPCs move on sidewalks.
npc_count = 12
for i in range(npc_count):
    side = -1 if i % 2 == 0 else 1
    x = side * (3.8 + (i % 3) * 0.6)
    start_y = -16 + (i % 6) * 6
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.45, location=(x, start_y, 1.45))
    npc = bpy.context.object
    npc.name = f"NPC_{i:02d}"
    body = add_cube(f"NPC_Body_{i:02d}", (x, start_y, 0.75), (0.35, 0.25, 0.7))
    for obj in (npc, body):
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.y = start_y + (10 if i % 3 else -10)
        obj.keyframe_insert(data_path="location", frame=48)

# Camera.
bpy.ops.object.camera_add(location=(18, -24, 18))
cam = bpy.context.object
cam.name = "Camera_Main"
scene.camera = cam

def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

point_camera(cam, (0, 2, 3))
cam.keyframe_insert(data_path="location", frame=1)
cam.location = (12, -14, 13)
point_camera(cam, (0, 5, 2.5))
cam.keyframe_insert(data_path="location", frame=48)
cam.keyframe_insert(data_path="rotation_euler", frame=48)
scene.frame_set(1)
point_camera(cam, (0, 2, 3))
cam.keyframe_insert(data_path="rotation_euler", frame=1)

# Sun and area light.
bpy.ops.object.light_add(type="SUN", location=(0, 0, 15))
sun = bpy.context.object
sun.name = "Sun"
sun.rotation_euler = (math.radians(28), math.radians(-20), math.radians(25))
sun.data.energy = 2.0

bpy.ops.object.light_add(type="AREA", location=(0, -4, 14))
area = bpy.context.object
area.data.energy = 1200
area.data.shape = "DISK"
area.data.size = 12
point_camera(area, (0, 0, 0))

# Save source scene before rendering.
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

# Render the real animation.
bpy.ops.render.render(animation=True)

report = {
    "blender_version": bpy.app.version_string,
    "engine": scene.render.engine,
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

assert report["blend_exists"], "preview.blend was not created"
assert report["video_exists"], "preview.mp4 was not created"
assert report["video_size_bytes"] > 1000, "preview.mp4 is unexpectedly small"
assert report["car_count"] == car_count, "car count mismatch"
assert report["npc_count"] == npc_count, "NPC count mismatch"
assert report["camera"] == "Camera_Main", "camera mismatch"

print("BLENDER_PROOF_PASS")
print(json.dumps(report, indent=2))
