import bpy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
ANIMATIC = OUT / "THE_NEXT_WAVE_animatic.mp4"
PROOF = OUT / "THE_NEXT_WAVE_proof.mp4"
BLEND = OUT / "THE_NEXT_WAVE_v01.blend"
REPORT = OUT / "test_report.json"
DIALOGUE = OUT / "dialogue_en.txt"
README = OUT / "README_vi.md"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 1200
scene.render.fps = 30
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = "VIDEO"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "WORLD"

COLORS = {
    "steel": (0.10, 0.13, 0.16, 1.0),
    "frame": (0.035, 0.045, 0.055, 1.0),
    "console": (0.07, 0.09, 0.11, 1.0),
    "screen": (0.05, 0.55, 0.62, 1.0),
    "deck": (0.17, 0.20, 0.22, 1.0),
    "ocean": (0.035, 0.11, 0.16, 1.0),
    "wave": (0.025, 0.18, 0.25, 1.0),
    "foam": (0.72, 0.84, 0.86, 1.0),
    "water": (0.03, 0.25, 0.33, 1.0),
    "container_a": (0.70, 0.16, 0.08, 1.0),
    "container_b": (0.10, 0.32, 0.56, 1.0),
    "container_c": (0.65, 0.50, 0.08, 1.0),
    "red": (0.85, 0.05, 0.03, 1.0),
    "glass": (0.16, 0.30, 0.34, 1.0),
    "crack": (0.88, 0.94, 0.98, 1.0),
}


def set_linear(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def cube(name, loc, scale, color, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.color = color
    if parent:
        o.parent = parent
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    o = bpy.context.object
    o.name = name
    if parent:
        o.parent = parent
    return o


def key_transform(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert(data_path="location", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)


def key_visible(obj, frame, visible):
    obj.hide_render = not visible
    obj.hide_viewport = not visible
    obj.keyframe_insert(data_path="hide_render", frame=frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)


def deg(x):
    return math.radians(x)


# Controllers and ship root.
ship = empty("SHIP_MOTION")
wave_timing = empty("WAVE_TIMING")
damage_state = empty("DAMAGE_STATE")
camera_inertia = empty("CAMERA_INERTIA", parent=ship)

# Ocean stays in world space. The ship and bridge move against it.
cube("Ocean_Base", (0, 45, -4.0), (70, 110, 2.5), COLORS["ocean"])
for y in (8, 22, 38, 54, 70):
    strip = cube(f"Sea_Ridge_{y}", (0, y, -0.8), (65, 3.0, 0.7), COLORS["wave"])
    strip.rotation_euler.x = deg(2)

# Deck, bow and cargo.
cube("Deck", (0, 18, -0.7), (9.0, 30.0, 0.6), COLORS["deck"], ship)
cube("Bow", (0, 48, -0.2), (7.0, 8.0, 1.6), COLORS["steel"], ship)
for side in (-1, 1):
    x = side * 4.2
    for row, y in enumerate((16, 25, 34)):
        col = [COLORS["container_a"], COLORS["container_b"], COLORS["container_c"]][row % 3]
        cube(f"Container_{side}_{row}", (x, y, 1.1), (2.0, 3.8, 1.7), col, ship)

hero = cube("Container_Hero", (-4.2, 11.5, 1.1), (2.0, 3.8, 1.7), COLORS["container_a"], ship)

# Bridge interior, window frame and console.
cube("Console", (0, -2.6, 0.4), (6.2, 1.7, 1.2), COLORS["console"], ship)
cube("Console_Radar", (-2.4, -1.0, 1.35), (1.2, 0.08, 0.55), COLORS["screen"], ship)
cube("Console_Main", (1.2, -1.0, 1.35), (1.8, 0.08, 0.55), COLORS["screen"], ship)

# Front window frames. Camera stays inside this cage.
for x in (-6.7, -3.4, 0, 3.4, 6.7):
    cube(f"Window_Post_{x}", (x, 1.0, 4.2), (0.16, 0.20, 4.2), COLORS["frame"], ship)
cube("Window_Top", (0, 1.0, 8.1), (7.0, 0.2, 0.25), COLORS["frame"], ship)
cube("Window_Bottom", (0, 1.0, 0.35), (7.0, 0.2, 0.25), COLORS["frame"], ship)
for x in (-5.0, -1.7, 1.7, 5.0):
    cube(f"Glass_{x}", (x, 1.15, 4.2), (1.45, 0.035, 3.55), COLORS["glass"], ship)

# Wiper and cup.
wiper = cube("Wiper", (1.6, 0.78, 3.9), (0.09, 0.08, 2.7), COLORS["frame"], ship)
wiper.rotation_euler.y = deg(-16)
cup = cube("Metal_Cup", (-2.5, -2.0, 1.95), (0.32, 0.32, 0.45), (0.55, 0.58, 0.60, 1.0), ship)

# Emergency lamp.
lamp = cube("Emergency_Lamp", (5.8, -1.0, 7.1), (0.35, 0.35, 0.25), COLORS["red"], ship)
key_visible(lamp, 1, False)
key_visible(lamp, 659, False)
key_visible(lamp, 660, True)

# Camera rig.
bpy.ops.object.camera_add(location=(0, -8.2, 4.6))
cam = bpy.context.object
cam.name = "Camera_Main"
cam.data.lens = 27
cam.data.clip_start = 0.1
cam.data.clip_end = 500
cam.parent = camera_inertia
cam.rotation_euler = (deg(78), 0, 0)
scene.camera = cam

# Keep the head inside the bridge. Use small delayed inertia only.
for f, x, z, rx, rz in [
    (1, 0.0, 0.0, 0.0, 0.0),
    (180, 0.0, -0.12, deg(0.8), 0.0),
    (225, 0.0, 0.16, deg(-1.2), 0.0),
    (410, 0.18, -0.08, deg(0.5), deg(-0.7)),
    (650, -0.16, 0.12, deg(-1.0), deg(0.6)),
    (990, 0.18, -0.10, deg(0.7), deg(-0.8)),
    (1055, 0.35, -0.25, deg(2.2), deg(-2.0)),
    (1200, 0.25, -0.35, deg(1.2), deg(-3.0)),
]:
    key_transform(camera_inertia, f, (x, 0, z), (rx, 0, rz))

# Ship motion: contact first, response second. Damage never resets.
ship_keys = [
    (1, 0.0, 0.0, 0.0),
    (90, 0.15, deg(-0.6), deg(0.3)),
    (125, 0.2, deg(-0.8), deg(0.2)),
    (165, 1.0, deg(3.0), deg(0.4)),
    (205, 0.6, deg(1.0), deg(0.2)),
    (225, -0.7, deg(-3.8), deg(-0.5)),
    (270, -0.25, deg(-1.2), deg(-0.2)),
    (320, 0.0, deg(-0.5), deg(-1.0)),
    (380, 0.8, deg(2.2), deg(4.0)),
    (430, -0.45, deg(-2.8), deg(6.0)),
    (480, -0.2, deg(-1.0), deg(4.5)),
    (540, -1.2, deg(-3.0), deg(5.0)),
    (610, -1.5, deg(-4.0), deg(4.0)),
    (650, 0.5, deg(4.5), deg(7.0)),
    (705, -0.9, deg(-4.5), deg(8.0)),
    (780, -0.45, deg(-2.0), deg(7.0)),
    (840, -0.4, deg(-1.2), deg(7.5)),
    (900, -1.1, deg(-3.0), deg(9.0)),
    (980, 0.2, deg(3.8), deg(12.0)),
    (1045, -1.0, deg(-4.0), deg(14.0)),
    (1120, -0.8, deg(-2.0), deg(16.0)),
    (1200, -1.0, deg(-2.5), deg(18.0)),
]
for f, z, pitch, roll in ship_keys:
    key_transform(ship, f, (0, 0, z), (pitch, 0, roll))

# Cup slide and bounce.
key_transform(cup, 1, (-2.5, -2.0, 1.95))
key_transform(cup, 80, (-1.2, -2.0, 1.95))
key_transform(cup, 215, (-0.4, -2.0, 1.95))
key_transform(cup, 222, (-0.4, -2.0, 2.25))
key_transform(cup, 230, (-0.2, -2.0, 1.95))
key_transform(cup, 430, (1.3, -2.0, 1.95))
key_transform(cup, 705, (2.2, -2.0, 1.95))
key_transform(cup, 1050, (4.6, -1.2, 1.35))

# Wiper runs, then stops in the middle after wave three.
for f, ang in [(1, -16), (45, 24), (90, -16), (135, 24), (180, -16), (270, 24), (360, -16), (480, 24), (570, -16), (650, 8), (1200, 8)]:
    key_transform(wiper, f, rot=(0, deg(ang), 0))

# Hero waves. They move toward the bow. Each later wave is larger.
def make_wave(name, start, impact, height, width, offset_x=0):
    w = cube(name, (offset_x, 70, height * 0.35), (width, 4.0, height), COLORS["wave"])
    foam = cube(name + "_Foam", (offset_x, 70, height * 1.35), (width, 2.0, 0.55), COLORS["foam"])
    for obj in (w, foam):
        key_transform(obj, start, loc=(offset_x, 70, obj.location.z))
        key_transform(obj, impact - 20, loc=(offset_x, 18, obj.location.z))
        key_transform(obj, impact + 20, loc=(offset_x, 3, obj.location.z))
        key_visible(obj, start - 1, False)
        key_visible(obj, start, True)
        key_visible(obj, impact + 35, True)
        key_visible(obj, impact + 36, False)
    return w

make_wave("Wave_One", 70, 205, 2.3, 26)
make_wave("Wave_Two", 285, 405, 3.5, 28, 5)
make_wave("Wave_Three", 500, 625, 5.7, 32)
make_wave("Wave_Four", 855, 1000, 7.3, 35, -3)

# Deck-water slabs persist after impact and move aft.
def deck_water(name, start, end, x, z=0.15):
    w = cube(name, (x, 48, z), (5.8, 6.0, 0.22), COLORS["water"], ship)
    key_visible(w, 1, False)
    key_visible(w, start - 1, False)
    key_visible(w, start, True)
    key_transform(w, start, loc=(x, 48, z), scale=(1.0, 0.8, 1.0))
    key_transform(w, end, loc=(x, 7, z), scale=(1.0, 2.2, 1.0))
    key_visible(w, end + 20, True)
    key_visible(w, end + 21, False)
    return w

deck_water("Deck_Water_1", 205, 260, 0)
deck_water("Deck_Water_2", 405, 470, 3)
deck_water("Deck_Water_3", 625, 705, 0)
deck_water("Deck_Water_4", 1000, 1080, -2)

# Wet glass overlay after wave three. It remains visible during false relief.
wet = cube("Wet_Glass", (0, 0.62, 4.15), (6.4, 0.03, 3.45), COLORS["water"], ship)
key_visible(wet, 1, False)
key_visible(wet, 625, False)
key_visible(wet, 626, True)
key_transform(wet, 626, scale=(1.0, 1.0, 1.0))
key_transform(wet, 760, scale=(1.0, 1.0, 0.18))
key_visible(wet, 830, True)
key_visible(wet, 831, False)

# Cracks appear after the impact. They persist.
cracks = []
for i, (x, z, rz) in enumerate([(5.3, 2.2, 30), (5.0, 2.7, -18), (5.6, 3.0, 62), (4.8, 3.3, -48)]):
    c = cube(f"Crack_{i}", (x, 0.55, z), (0.04, 0.02, 0.75), COLORS["crack"], ship)
    c.rotation_euler.y = deg(rz)
    key_visible(c, 1, False)
    key_visible(c, 649, False)
    key_visible(c, 650, True)
    cracks.append(c)

# Damage continuity: one deck light disappears after wave two.
deck_light = cube("Deck_Light", (6.5, 32, 3.2), (0.25, 0.25, 0.5), (0.95, 0.9, 0.5, 1.0), ship)
key_visible(deck_light, 1, True)
key_visible(deck_light, 420, True)
key_visible(deck_light, 421, False)

# Hero container warns early, then breaks free during the surprise.
key_transform(hero, 1, (-4.2, 11.5, 1.1), (0, 0, 0))
key_transform(hero, 430, (-3.7, 11.0, 1.1), (0, 0, deg(2)))
key_transform(hero, 840, (-3.7, 11.0, 1.1), (0, 0, deg(2)))
key_transform(hero, 900, (-2.7, 8.0, 1.1), (0, 0, deg(5)))
key_transform(hero, 950, (-1.2, 4.5, 1.1), (0, 0, deg(16)))
key_transform(hero, 990, (3.8, 1.6, 1.6), (deg(4), deg(-10), deg(28)))
key_transform(hero, 1020, (4.6, 1.2, 2.0), (deg(8), deg(-18), deg(34)))

# Local breach geometry appears only after the frame impact.
broken_glass = cube("Broken_Glass_Patch", (5.0, 0.35, 3.8), (1.45, 0.08, 3.1), COLORS["frame"], ship)
key_visible(broken_glass, 1, False)
key_visible(broken_glass, 1035, False)
key_visible(broken_glass, 1036, True)

breach = cube("Water_Breach", (5.0, 0.2, 3.8), (1.1, 0.5, 1.2), COLORS["water"], ship)
key_visible(breach, 1, False)
key_visible(breach, 1045, False)
key_visible(breach, 1046, True)
key_transform(breach, 1046, loc=(5.0, 0.2, 3.8), scale=(0.2, 0.3, 0.2))
key_transform(breach, 1080, loc=(3.5, -2.0, 2.0), scale=(2.0, 3.0, 1.3))
key_transform(breach, 1140, loc=(1.5, -3.0, 0.9), scale=(3.8, 4.5, 0.6))

# Make critical timing linear.
for obj in bpy.data.objects:
    set_linear(obj)

DIALOGUE.write_text(
    "00:00 Bridge, secure for heavy seas.\n"
    "00:12 Cargo is shifting!\n"
    "00:19 Hold on.\n"
    "00:26 Why aren't we coming back?\n"
    "00:36 Mayday—\n",
    encoding="utf-8",
)

README.write_text(
    "# THE NEXT WAVE v01\n\n"
    "Đây là blocking, animatic và proof cơ học ở chất lượng thấp.\n\n"
    "- Camera luôn ở trong buồng lái.\n"
    "- Tàu dùng keyframe heave, pitch và roll.\n"
    "- Sóng chính dùng mesh điều khiển.\n"
    "- Nước boong và breach dùng geometry cục bộ.\n"
    "- Proof lấy đoạn wave three, wet glass và crack.\n"
    "- Chưa có fluid cache nặng hoặc voice render.\n"
    "- dialogue_en.txt chứa câu thoại và timestamp.\n",
    encoding="utf-8",
)

# Save the complete 40-second scene before renders.
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

# 40-second animatic.
scene.frame_start = 1
scene.frame_end = 1200
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.filepath = str(ANIMATIC)
bpy.ops.render.render(animation=True)

# 9-second proof: wave three, delayed recovery, wet glass and crack.
scene.frame_start = 481
scene.frame_end = 750
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.filepath = str(PROOF)
bpy.ops.render.render(animation=True)

report = {
    "blender_version": bpy.app.version_string,
    "ffmpeg_supported": bool(bpy.app.ffmpeg.supported),
    "engine": scene.render.engine,
    "fps": scene.render.fps,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "camera": scene.camera.name if scene.camera else None,
    "animatic_frames": 1200,
    "proof_frames": 270,
    "animatic_exists": ANIMATIC.exists(),
    "proof_exists": PROOF.exists(),
    "blend_exists": BLEND.exists(),
    "dialogue_exists": DIALOGUE.exists(),
    "readme_exists": README.exists(),
    "animatic_size_bytes": ANIMATIC.stat().st_size if ANIMATIC.exists() else 0,
    "proof_size_bytes": PROOF.stat().st_size if PROOF.exists() else 0,
}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

assert report["ffmpeg_supported"]
assert report["camera"] == "Camera_Main"
assert report["animatic_exists"] and report["animatic_size_bytes"] > 10000
assert report["proof_exists"] and report["proof_size_bytes"] > 10000
assert report["blend_exists"]
print("BLENDER_PROOF_PASS")
print(json.dumps(report, indent=2))
