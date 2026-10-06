import bpy
import math
import os
import json
import random
from pathlib import Path
from mathutils import Vector

SEED = 2706
rng = random.Random(SEED)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 360
scene.render.fps = 30

OUT = Path(os.environ.get('OUT_DIR', 'outbreak_proof_output'))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'frames').mkdir(exist_ok=True)
(OUT / 'qa').mkdir(exist_ok=True)

# ---------- cleanup / collection ----------
COLL_NAME = 'OUTBREAK_PROOF_12S'
if COLL_NAME in bpy.data.collections:
    old = bpy.data.collections[COLL_NAME]
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
coll = bpy.data.collections.new(COLL_NAME)
scene.collection.children.link(coll)

def move_to_coll(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)

# ---------- materials ----------
def make_mat(name, color, rough=0.75, metallic=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = color
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metallic
    return m

M_SKIN = make_mat('P12_Skin', (0.63,0.44,0.31,1), 0.9)
M_DARK = make_mat('P12_Dark', (0.05,0.06,0.08,1), 0.8)
M_MUSTARD = make_mat('P12_Mustard', (0.62,0.38,0.06,1), 0.78)
M_GREY = make_mat('P12_Grey', (0.32,0.35,0.38,1), 0.8)
M_BLUE = make_mat('P12_Blue', (0.05,0.18,0.48,1), 0.72)
M_GREEN = make_mat('P12_Green', (0.07,0.35,0.16,1), 0.8)
M_RED = make_mat('P12_Red', (0.55,0.04,0.03,1), 0.72)
M_POLICE = make_mat('P12_Police', (0.02,0.07,0.16,1), 0.68)
M_MASK = make_mat('P12_Mask', (0.42,0.72,0.78,1), 0.55)
M_BARRIER = make_mat('P12_Barrier', (0.92,0.28,0.03,1), 0.5)
M_WHITE = make_mat('P12_White', (0.72,0.74,0.75,1), 0.52)
M_GLASS = make_mat('P12_Glass', (0.03,0.08,0.10,1), 0.25, 0.05)
M_SHOP = make_mat('P12_Shop', (0.18,0.20,0.23,1), 0.7)
M_SIGN = make_mat('P12_Sign', (0.48,0.10,0.05,1), 0.65)
M_AMB = make_mat('P12_Amb', (0.82,0.82,0.78,1), 0.46)
M_EMT = make_mat('P12_EMT', (0.09,0.34,0.48,1), 0.72)
M_GURNEY = make_mat('P12_Gurney', (0.36,0.38,0.42,1), 0.5, 0.2)

# ---------- primitives ----------
def cube(name, loc, dims, mat=None, bevel=0.03, coll_target=True):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
        o.color = mat.diffuse_color
    if bevel:
        md = o.modifiers.new('Bevel', 'BEVEL')
        md.width = bevel
        md.segments = 2
        md.limit_method = 'ANGLE'
    if coll_target:
        move_to_coll(o)
    return o

def sphere(name, loc, radius, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    o.color = mat.diffuse_color
    move_to_coll(o)
    return o

def point_camera(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z','Y').to_euler()

def key_loc(obj, frame, xyz):
    obj.location = xyz
    obj.keyframe_insert(data_path='location', frame=frame)

def key_rot(obj, frame, xyz):
    obj.rotation_euler = xyz
    obj.keyframe_insert(data_path='rotation_euler', frame=frame)

def key_scale(obj, frame, value):
    obj.scale = value
    obj.keyframe_insert(data_path='scale', frame=frame)

def appear(obj, frame):
    key_scale(obj, max(1, frame-1), (0.001,0.001,0.001))
    key_scale(obj, frame, (1,1,1))

def disappear(obj, frame):
    key_scale(obj, frame-1, (1,1,1))
    key_scale(obj, frame, (0.001,0.001,0.001))

# ---------- fix road surface seams ----------
# Existing proof built roads as overlapping slabs. Use asphalt CityBase below block slabs,
# and hide the overlapping RoadV_/RoadH_ surfaces. Blocks remain as sidewalks.
city_base = bpy.data.objects.get('CityBase')
asphalt = bpy.data.materials.get('Asphalt')
if city_base and asphalt:
    city_base.data.materials.clear()
    city_base.data.materials.append(asphalt)
    city_base.color = getattr(asphalt, 'diffuse_color', (0.04,0.04,0.04,1))
for o in list(bpy.data.objects):
    if o.name.startswith('RoadV_') or o.name.startswith('RoadH_'):
        o.hide_render = True
        o.hide_viewport = True

# ---------- hero storefront facing avenue ----------
# East face of the left-side block, directly beside the central avenue.
shop_y = -28.0
shop_x = -8.72
shop_door = cube('P12_ShopDoor', (shop_x, shop_y, 1.35), (0.16, 1.45, 2.45), M_GLASS, 0.03)
shop_win1 = cube('P12_ShopWindowA', (shop_x, shop_y-2.15, 1.55), (0.15, 2.2, 2.2), M_GLASS, 0.025)
shop_win2 = cube('P12_ShopWindowB', (shop_x, shop_y+2.15, 1.55), (0.15, 2.2, 2.2), M_GLASS, 0.025)
shop_sign = cube('P12_ShopSign', (shop_x-0.04, shop_y, 3.35), (0.18, 5.9, 0.65), M_SIGN, 0.04)
shop_awning = cube('P12_ShopAwning', (shop_x+0.55, shop_y, 2.95), (1.15, 5.6, 0.18), M_SIGN, 0.04)

# ---------- person rig proxy ----------
def make_person(name, x, y, z=0.13, body_mat=M_GREY, masked=False, police=False, scale=1.0):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x,y,z))
    root = bpy.context.object
    root.name = name
    move_to_coll(root)
    h = 1.72 * scale
    torso_h = h*0.34
    leg_h = h*0.45
    arm_len = h*0.28
    head_r = h*0.095
    torso_mat = M_POLICE if police else body_mat
    torso = cube(name+'_Torso', (x,y,z+leg_h+torso_h*0.53), (h*0.22,h*0.11,torso_h), torso_mat, 0.02)
    head = sphere(name+'_Head', (x,y,z+leg_h+torso_h+head_r*1.22), head_r, M_SKIN)
    arm_z = z+leg_h+torso_h*0.70
    arm_x = h*0.145
    armL = cube(name+'_ArmL', (x-arm_x,y,arm_z), (h*0.055,h*0.055,arm_len), torso_mat, 0.015)
    armR = cube(name+'_ArmR', (x+arm_x,y,arm_z), (h*0.055,h*0.055,arm_len), torso_mat, 0.015)
    leg_z = z+leg_h*0.50
    leg_x = h*0.055
    legL = cube(name+'_LegL', (x-leg_x,y,leg_z), (h*0.07,h*0.07,leg_h), M_DARK, 0.015)
    legR = cube(name+'_LegR', (x+leg_x,y,leg_z), (h*0.07,h*0.07,leg_h), M_DARK, 0.015)
    parts = [torso, head, armL, armR, legL, legR]
    mask = None
    if masked:
        mask = cube(name+'_Mask', (x, y-0.105, z+leg_h+torso_h+head_r*1.22), (head_r*1.35,0.045,head_r*0.72), M_MASK, 0.01)
        parts.append(mask)
    for p in parts:
        p.parent = root
        p.matrix_parent_inverse = root.matrix_world.inverted()
    return {'root':root,'armL':armL,'armR':armR,'legL':legL,'legR':legR,'parts':parts}

def pose_walk(p, frame, forward=True, amount=18):
    a = math.radians(amount if forward else -amount)
    p['armL'].rotation_euler.x = a
    p['armR'].rotation_euler.x = -a
    p['legL'].rotation_euler.x = -a
    p['legR'].rotation_euler.x = a
    for part in (p['armL'],p['armR'],p['legL'],p['legR']):
        part.keyframe_insert(data_path='rotation_euler', frame=frame)

def animate_walk(p, f0, f1, start, end, steps=8):
    key_loc(p['root'], f0, start)
    key_loc(p['root'], f1, end)
    for i in range(steps+1):
        f = int(f0 + (f1-f0)*i/steps)
        pose_walk(p, f, forward=(i%2==0), amount=20)

# ---------- phase timings ----------
F1 = 1
F_COERCE_END = 120
F_PUSH_START = 121
F_PUSH_END = 240
F_STALL_START = 241
F_END = 360

# ---------- coercion beat ----------
hero = make_person('P12_Hero', -8.55, -23.4, body_mat=M_MUSTARD, masked=True)
hero['root'].rotation_euler.z = math.radians(180)
police1 = make_person('P12_Police_Force', -6.9, -22.2, body_mat=M_POLICE, masked=True, police=True)
police1['root'].rotation_euler.z = math.radians(180)
filmer = make_person('P12_Filmer', -8.65, -26.2, body_mat=M_GREEN, masked=True)
filmer['armR'].rotation_euler.x = math.radians(-70)
filmer['armR'].keyframe_insert(data_path='rotation_euler', frame=1)

# approach, contact, forced step-back along sidewalk (not through building)
key_loc(police1['root'], 1, (-6.9,-22.2,0.13))
key_loc(police1['root'], 52, (-7.65,-22.7,0.13))
key_loc(police1['root'], 92, (-7.95,-23.0,0.13))
key_loc(hero['root'], 1, (-8.55,-23.4,0.13))
key_loc(hero['root'], 52, (-8.55,-23.4,0.13))
key_loc(hero['root'], 92, (-8.55,-25.0,0.13))
key_loc(hero['root'], 120, (-8.55,-25.8,0.13))
# readable arm contact gesture
police1['armL'].rotation_euler.x = math.radians(-5)
police1['armL'].keyframe_insert(data_path='rotation_euler', frame=35)
police1['armL'].rotation_euler.x = math.radians(-72)
police1['armL'].keyframe_insert(data_path='rotation_euler', frame=68)
police1['armL'].rotation_euler.x = math.radians(-35)
police1['armL'].keyframe_insert(data_path='rotation_euler', frame=105)
pose_walk(hero, 72, True, 24)
pose_walk(hero, 90, False, 24)
pose_walk(hero, 108, True, 24)

# ---------- barrier / police line ----------
barriers = []
for i,x in enumerate((-4.2,4.2)):
    b = cube(f'P12_Barrier_{i}', (x,-17.8,0.58), (7.5,0.38,1.0), M_BARRIER, 0.05)
    barriers.append(b)
    appear(b, 105)
police_line = []
for i,x in enumerate((-5.4,-1.8,1.8,5.4)):
    p = make_person(f'P12_PoliceLine_{i}', x, -15.2, body_mat=M_POLICE, masked=True, police=True)
    p['root'].rotation_euler.z = math.radians(180)
    appear(p['root'], 105)
    police_line.append(p)

# ---------- crowd push beat ----------
crowd = []
coords = [
    (-5.8,-31.0),(-3.8,-31.8),(-1.8,-31.0),(0.8,-31.5),(3.0,-31.0),(5.5,-31.8),
    (-6.2,-34.2),(-4.0,-34.8),(-2.0,-34.0),(0.0,-34.8),(2.2,-34.2),(4.5,-34.9),(6.2,-34.1),
    (-5.0,-37.2),(-2.8,-37.8),(-0.5,-37.0),(1.8,-37.8),(4.0,-37.1),(6.0,-37.8)
]
body_mats = [M_GREY,M_GREEN,M_BLUE,M_RED]
for i,(x,y) in enumerate(coords):
    p = make_person(f'P12_Crowd_{i:02d}', x, y, body_mat=body_mats[i%len(body_mats)], masked=(i%3!=0), scale=0.96 if i>10 else 1.0)
    p['root'].rotation_euler.z = 0.0
    appear(p['root'], F_PUSH_START)
    # staggered advance, front row pushes more
    dy = 7.0 if y > -33 else 5.0 if y > -36 else 3.5
    fstart = F_PUSH_START + (i%5)*4
    fend = 210 + (i%4)*5
    animate_walk(p, fstart, fend, (x,y,0.13), (x,y+dy,0.13), steps=6)
    crowd.append(p)

# barrier buckles slightly at peak
for i,b in enumerate(barriers):
    key_loc(b, 121, (b.location.x,-17.8,0.58))
    key_loc(b, 205, (b.location.x,-17.0,0.58))
    key_loc(b, 235, (b.location.x,-16.5,0.58))
    b.rotation_euler.z = 0.0
    b.keyframe_insert(data_path='rotation_euler', frame=121)
    b.rotation_euler.z = math.radians(7 if i==0 else -7)
    b.keyframe_insert(data_path='rotation_euler', frame=235)
for i,p in enumerate(police_line):
    key_loc(p['root'], 121, (p['root'].location.x,-15.2,0.13))
    key_loc(p['root'], 235, (p['root'].location.x,-14.4-(i%2)*0.25,0.13))

# ---------- moving base traffic until stall ----------
base_cars = []
for o in list(bpy.data.objects):
    if o.name.startswith('Car_') and not o.name.startswith('CarCab_'):
        base_cars.append(o)
base_cars.sort(key=lambda o:o.name)
scene.frame_set(1)
for i,o in enumerate(base_cars):
    start = o.location.copy()
    o.animation_data_clear()
    direction = 1.0 if start.x < 0 else -1.0
    # 30-35 km/h visual target, continuous through first 8 s
    key_loc(o, 1, (start.x,start.y,start.z))
    key_loc(o, 120, (start.x,start.y + direction*34.0,start.z))
    key_loc(o, 240, (start.x,start.y + direction*68.0,start.z))
    if i % 5 != 0:
        disappear(o, F_STALL_START)
    else:
        key_loc(o, 241, (o.location.x,o.location.y,o.location.z))
        key_loc(o, 360, (o.location.x,o.location.y,o.location.z))

# ---------- ambulance + medical pressure cue ----------
amb_root = cube('P12_Ambulance', (4.8,-46,0.75), (2.1,5.1,1.5), M_AMB, 0.16)
amb_cab = cube('P12_AmbulanceCab', (4.8,-44.6,1.55), (1.8,2.0,0.9), M_GLASS, 0.10)
amb_cab.parent = amb_root
amb_cab.matrix_parent_inverse = amb_root.matrix_world.inverted()
amb_red = cube('P12_AmbLightR', (4.4,-44.3,2.10), (0.24,0.34,0.16), M_RED, 0.03)
amb_blue = cube('P12_AmbLightB', (5.2,-44.3,2.10), (0.24,0.34,0.16), M_BLUE, 0.03)
for light in (amb_red,amb_blue):
    light.parent = amb_root
    light.matrix_parent_inverse = amb_root.matrix_world.inverted()
appear(amb_root, 130)
key_loc(amb_root, 130, (4.8,-46,0.75))
key_loc(amb_root, 230, (4.8,18,0.75))
key_loc(amb_root, 241, (4.8,34,0.75))
key_loc(amb_root, 360, (4.8,34,0.75))

# ---------- stalled street phase ----------
# remove active confrontation, leave one displaced barrier and sparse survivors
for p in [hero, police1, filmer] + crowd + police_line:
    disappear(p['root'], F_STALL_START)
disappear(barriers[1], F_STALL_START)
# keep one barrier skewed as aftermath
key_scale(barriers[0], F_STALL_START, (1,1,1))

# abandoned van / delivery cue
delivery = cube('P12_StoppedDelivery', (-4.8,8.0,0.75), (2.0,5.2,1.45), M_WHITE, 0.14)
appear(delivery, F_STALL_START)
delivery.rotation_euler.z = math.radians(5)

# two survivors still moving slowly
surv1 = make_person('P12_SurvivorA', -8.65, 6.0, body_mat=M_BLUE, masked=True)
surv2 = make_person('P12_SurvivorB', 8.65, 20.0, body_mat=M_GREY, masked=True)
appear(surv1['root'], F_STALL_START)
appear(surv2['root'], F_STALL_START)
animate_walk(surv1, 245, 355, (-8.65,6.0,0.13), (-8.65,18.0,0.13), steps=8)
animate_walk(surv2, 250, 355, (8.65,20.0,0.13), (8.65,8.0,0.13), steps=8)

# EMTs + gurney at right sidewalk, visible only in stalled phase
emt1 = make_person('P12_EMT_A', 9.2, 33.0, body_mat=M_EMT, masked=True)
emt2 = make_person('P12_EMT_B', 10.2, 35.0, body_mat=M_EMT, masked=True)
appear(emt1['root'], F_STALL_START)
appear(emt2['root'], F_STALL_START)
gurney = cube('P12_Gurney', (9.7,34.1,0.72), (0.78,2.0,0.18), M_GURNEY, 0.04)
appear(gurney, F_STALL_START)
for wx,wy in ((9.38,33.35),(10.02,33.35),(9.38,34.85),(10.02,34.85)):
    w = sphere('P12_GurneyWheel', (wx,wy,0.38), 0.13, M_DARK)
    appear(w, F_STALL_START)

# ---------- proof cameras ----------
def new_camera(name, loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_end = 800
    point_camera(cam, target)
    move_to_coll(cam)
    return cam

cam_coerce = new_camera('P12_CAM_COERCION', (5.6,-48.0,10.8), (-6.3,-22.8,1.7), 58)
cam_push = new_camera('P12_CAM_PUSH', (4.5,-58.0,13.5), (0.0,-20.0,1.8), 52)
cam_stall = new_camera('P12_CAM_STALL', (5.5,-82.0,27.5), (0.0,18.0,4.0), 48)

# camera markers for blend playback
for name, frame, cam in [('COERCION',1,cam_coerce),('PUSH',121,cam_push),('STALL',241,cam_stall)]:
    m = scene.timeline_markers.get(name) or scene.timeline_markers.new(name, frame=frame)
    m.frame = frame
    m.camera = cam
scene.camera = cam_coerce

# ---------- preview render settings ----------
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'WORLD'

# Ensure material viewport colors are reflected in Workbench
for o in bpy.data.objects:
    if o.type == 'MESH' and o.data and len(o.data.materials):
        m = o.data.materials[0]
        if m:
            try:
                o.color = m.diffuse_color
            except Exception:
                pass

# Save proof blend before rendering
blend_out = OUT / 'OUTBREAK_PROOF_12S.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))

# QA stills from each beat
for frame, cam, label in [(70,cam_coerce,'coercion'),(205,cam_push,'barrier_push'),(310,cam_stall,'stalled_street')]:
    scene.frame_set(frame)
    scene.camera = cam
    scene.render.filepath = str(OUT / 'qa' / f'{label}.png')
    bpy.ops.render.render(write_still=True)

# Motion preview: sample every 3rd timeline frame => 10 fps / 12 s.
# Workbench is intentional for fast animation QA; saved blend retains all geometry/animation.
idx = 0
for frame in range(1, 361, 3):
    scene.frame_set(frame)
    if frame < 121:
        scene.camera = cam_coerce
    elif frame < 241:
        scene.camera = cam_push
    else:
        scene.camera = cam_stall
    scene.render.filepath = str(OUT / 'frames' / f'frame_{idx:04d}.png')
    bpy.ops.render.render(write_still=True)
    idx += 1

report = {
    'proof_seconds': 12,
    'timeline_fps': 30,
    'preview_sample_fps': 10,
    'timeline_frames': 360,
    'preview_frames': idx,
    'crowd_count': len(crowd),
    'police_count': 1 + len(police_line),
    'base_car_count': len(base_cars),
    'beats': ['coercion','barrier_push','stalled_street'],
    'road_surface_fix': 'CityBase asphalt + overlapping road slabs hidden',
    'render_engine_preview': scene.render.engine,
}
(OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('OUTBREAK_PROOF_12S_READY')
print(json.dumps(report, indent=2))
