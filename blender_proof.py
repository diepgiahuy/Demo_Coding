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

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 8
scene.render.fps = 8
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 180
scene.render.resolution_y = 320
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = str(VIDEO)


def add_cube(name, location, scale):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


add_cube("Ground", (0, 0, -0.3), (14, 20, 0.3))
add_cube("Road_Main", (0, 0, 0.02), (3.0, 20, 0.03))
add_cube("Road_Cross", (0, 0, 0.03), (14, 2.4, 0.03))

for ix, x in enumerate((-10, -6, 6, 10)):
    for iy, y in enumerate((-14, -7, 7, 14)):
        h = 2.5 + ((ix + iy) % 4) * 1.8
        add_cube(f"Building_{ix}_{iy}", (x, y, h), (2.2, 2.6, h))

car_count = 6
for i in range(car_count):
    lane_x = -1.15 if i % 2 == 0 else 1.15
    start_y = -18 + i * 5.5
    car = add_cube(f"Car_{i:02d}", (lane_x, start_y, 0.55), (0.65, 1.2, 0.45))
    car.keyframe_insert(data_path="location", frame=1)
    car.location.y = start_y + (28 if i % 2 == 0 else -28)
    car.keyframe_insert(data_path="location", frame=8)

npc_count = 12
for i in range(npc_count):
    side = -1 if i % 2 == 0 else 1
    x = side * (3.8 + (i % 3) * 0.6)
    start_y = -16 + (i % 6) * 6
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.45, location=(x, start_y, 1.45))
    npc = bpy.context.object
    npc.name = f"NPC_{i:02d}"
    body = add_cube(f"NPC_Body_{i:02d}", (x, start_y, 0.75), (0.35, 0.25, 0.7))
    for obj in (npc, body):
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.y = start_y + (10 if i % 3 else -10)
        obj.keyframe_insert(data_path="location", frame=8)

bpy.ops.object.camera_add(location=(18, -24, 18))
cam = bpy.context.object
cam.name = "Camera_Main"
scene.camera = cam


def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


point_camera(cam, (0, 2, 3))
cam.keyframe_insert(data_path="location", frame=1)
cam.keyframe_insert(data_path="rotation_euler", frame=1)
cam.location = (12, -14, 13)
point_camera(cam, (0, 5, 2.5))
cam.keyframe_insert(data_path="location", frame=8)
cam.keyframe_insert(data_path="rotation_euler", frame=8)

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
assert report["video_size_bytes"] > 1000
assert report["car_count"] == car_count
assert report["npc_count"] == npc_count
assert report["camera"] == "Camera_Main"

print("BLENDER_PROOF_PASS")
print(json.dumps(report, indent=2))
