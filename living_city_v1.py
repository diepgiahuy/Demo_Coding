import bpy
import math
import random
import json
from pathlib import Path
from mathutils import Vector

SEED = 27
random.seed(SEED)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)
VIDEO = OUT / 'LivingCity_v1.mp4'
BLEND = OUT / 'LivingCity_v1.blend'
REPORT = OUT / 'report.json'

W, H = 480, 854
FPS = 24
END = 120  # 5 seconds

# ---------- scene ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = END
scene.render.fps = FPS
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.image_settings.media_type = 'VIDEO'
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.filepath = str(VIDEO)
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'WORLD'
scene.world.color = (0.58, 0.70, 0.83)
if hasattr(scene.display.shading, 'background_type'):
    scene.display.shading.background_type = 'WORLD'

# ---------- helpers ----------
def add_cube(name, loc, scale, color, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.color = color
    if parent:
        o.parent = parent
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def add_cyl(name, loc, radius, depth, color, vertices=10, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.color = color
    if parent:
        o.parent = parent
    return o


def add_ico(name, loc, radius, color, parent=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    o.color = color
    if parent:
        o.parent = parent
    return o


def boxes_mesh(name, boxes, color):
    # boxes: (cx,cy,cz,sx,sy,sz), where s is full size
    verts, faces = [], []
    for cx, cy, cz, sx, sy, sz in boxes:
        hx, hy, hz = sx/2, sy/2, sz/2
        base = len(verts)
        verts.extend([
            (cx-hx, cy-hy, cz-hz), (cx+hx, cy-hy, cz-hz),
            (cx+hx, cy+hy, cz-hz), (cx-hx, cy+hy, cz-hz),
            (cx-hx, cy-hy, cz+hz), (cx+hx, cy-hy, cz+hz),
            (cx+hx, cy+hy, cz+hz), (cx-hx, cy+hy, cz+hz),
        ])
        faces.extend([
            (base+0,base+1,base+2,base+3), (base+4,base+7,base+6,base+5),
            (base+0,base+4,base+5,base+1), (base+1,base+5,base+6,base+2),
            (base+2,base+6,base+7,base+3), (base+4,base+0,base+3,base+7),
        ])
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.color = color
    return obj


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()


def linear_keys(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

# ---------- palette ----------
ROAD = (0.10,0.11,0.13,1)
SIDEWALK = (0.46,0.46,0.43,1)
LAND = (0.25,0.34,0.24,1)
WATER = (0.24,0.50,0.66,1)
WINDOW_DARK = (0.10,0.15,0.20,1)
WINDOW_LIT = (0.96,0.73,0.33,1)
ROOF = (0.20,0.20,0.20,1)
TREE_TRUNK = (0.23,0.12,0.06,1)
TREE = (0.14,0.40,0.16,1)
WHITE = (0.88,0.88,0.83,1)
BUILDING_COLORS = [
    (0.43,0.24,0.20,1), (0.55,0.31,0.24,1), (0.34,0.38,0.40,1),
    (0.44,0.46,0.42,1), (0.50,0.45,0.34,1), (0.30,0.35,0.39,1),
    (0.58,0.55,0.47,1), (0.36,0.28,0.25,1),
]
CAR_COLORS = [(0.76,0.10,0.08,1),(0.12,0.30,0.68,1),(0.90,0.64,0.10,1),(0.16,0.53,0.29,1),(0.72,0.72,0.69,1)]

# ---------- terrain / waterfront ----------
add_cube('Land', (-12, 5, -0.55), (58, 74, 0.55), LAND)
add_cube('Water', (62, 9, -0.40), (18, 74, 0.45), WATER)
# waterfront promenade / boulevard
add_cube('WaterfrontRoad', (32, 6, 0.01), (5.2, 72, 0.06), ROAD)
add_cube('Promenade', (39.0, 6, 0.10), (1.7, 72, 0.10), SIDEWALK)
# internal avenues
for x in (-42,-28,-14,0,14):
    add_cube(f'RoadV_{x}', (x, 4, 0.0), (2.1, 70, 0.05), ROAD)
for y in (-46,-32,-18,-4,10,24,38,52):
    add_cube(f'RoadH_{y}', (-5, y, 0.02), (39, 2.0, 0.05), ROAD)
# lane markings waterfront
mark_boxes=[]
for y in range(-58,67,8):
    mark_boxes.append((32,y,0.09,0.16,3.4,0.03))
boxes_mesh('WaterfrontLaneMarks', mark_boxes, (0.90,0.82,0.24,1))

# ---------- buildings ----------
building_count = 0
window_count = 0

def add_building(name, x, y, w, d, floors, color, detail=True, storefront=False, crown=False):
    global building_count, window_count
    h = floors * 2.4
    add_cube(name, (x,y,h/2), (w/2,d/2,h/2), color)
    building_count += 1

    # roof lip + equipment
    add_cube(name+'_Roof', (x,y,h+0.20), (w*0.48,d*0.48,0.20), ROOF)
    if detail and w > 6:
        add_cube(name+'_HVAC', (x-w*0.18,y,h+0.55), (0.7,0.8,0.35), (0.35,0.35,0.34,1))

    # Visible facades from southwest camera: south and west.
    if detail:
        boxes_dark=[]; boxes_lit=[]
        floor_start = 1 if storefront else 0
        cols_s = max(2, int(w // 2.3))
        cols_w = max(2, int(d // 2.4))
        for f in range(floor_start, floors):
            z = 1.2 + f*2.4
            for c in range(cols_s):
                wx = x - w*0.40 + c*(w*0.80/max(1,cols_s-1))
                b=(wx, y-d/2-0.035, z, min(1.1,w/cols_s*0.55), 0.07, 1.0)
                (boxes_lit if random.random()<0.30 else boxes_dark).append(b)
            for c in range(cols_w):
                wy = y - d*0.40 + c*(d*0.80/max(1,cols_w-1))
                b=(x-w/2-0.035, wy, z, 0.07, min(1.1,d/cols_w*0.55), 1.0)
                (boxes_lit if random.random()<0.26 else boxes_dark).append(b)
        if boxes_dark:
            boxes_mesh(name+'_WindowsDark', boxes_dark, WINDOW_DARK); window_count += len(boxes_dark)
        if boxes_lit:
            boxes_mesh(name+'_WindowsLit', boxes_lit, WINDOW_LIT); window_count += len(boxes_lit)

        # Door/storefront on south face.
        add_cube(name+'_Door', (x, y-d/2-0.07, 1.0), (0.65,0.08,1.0), (0.18,0.15,0.12,1))
        if storefront:
            boxes=[]
            for sx in (-w*0.25, w*0.25):
                boxes.append((x+sx,y-d/2-0.09,1.4,w*0.34,0.07,1.8))
            boxes_mesh(name+'_ShopGlass', boxes, (0.15,0.26,0.32,1))
            add_cube(name+'_Awning',(x,y-d/2-0.42,2.55),(w*0.42,0.38,0.12),(0.66,0.18,0.12,1))

    if crown:
        add_cube(name+'_Crown',(x,y,h+1.5),(w*0.34,d*0.34,1.5),(0.28,0.30,0.31,1))
        add_cyl(name+'_Spire',(x,y,h+5.2),0.10,5.0,(0.22,0.22,0.22,1),8)

# dense low-rise foreground & mid city
xs = [-48,-40,-34,-26,-20,-12,-6,2,8,16,24]
ys = [-52,-42,-34,-24,-16,-6,4,14,24,34]
for yi,y in enumerate(ys):
    for xi,x in enumerate(xs):
        # Preserve major roads and waterfront edge
        if abs(x-(-42))<3 or abs(x-(-28))<3 or abs(x-(-14))<3 or abs(x)<3 or abs(x-14)<3:
            continue
        if any(abs(y-r)<3 for r in (-46,-32,-18,-4,10,24,38,52)):
            continue
        if x > 27:
            continue
        w=random.uniform(6.0,9.5); d=random.uniform(6.0,10.0)
        floors=random.randint(2,5) if y<12 else random.randint(3,7)
        detail = y < 30
        storefront = detail and random.random()<0.22
        add_building(f'B_{xi}_{yi}',x+random.uniform(-1,1),y+random.uniform(-1,1),w,d,floors,random.choice(BUILDING_COLORS),detail,storefront)

# simple far-city massing behind the detailed blocks; keeps skyline dense without heavy facade geometry
for row,y in enumerate((46,56,66)):
    for col,x in enumerate((-50,-40,-30,-20,-10,0,10,20)):
        # leave room for the hero skyline cluster but fill gaps around it
        if row == 0 and x in (-30,-20,-10,0,10,20):
            continue
        floors = random.randint(5,11)
        add_building(
            f'Far_{row}_{col}', x+random.uniform(-1.0,1.0), y+random.uniform(-0.8,0.8),
            random.uniform(6.5,9.5), random.uniform(6.5,9.5), floors,
            random.choice(BUILDING_COLORS), False, False
        )

# skyline cluster toward rear-left/middle
skyline_specs = [
    (-30,43,11,11,17,False),(-20,46,10,12,25,True),(-9,45,12,12,20,False),
    (2,48,10,10,28,True),(12,44,12,12,22,False),(22,48,10,10,18,True),
    (-15,57,9,9,19,False),(-2,58,11,10,23,False),(10,58,9,9,20,True),
]
for i,(x,y,w,d,f,crown) in enumerate(skyline_specs):
    add_building(f'Tower_{i}',x,y,w,d,f,random.choice([(0.42,0.46,0.48,1),(0.53,0.55,0.53,1),(0.38,0.43,0.48,1)]),True,False,crown)

# ---------- street furniture / trees ----------
# waterfront tree rows, key visual from reference
for y in range(-56,65,6):
    for x in (26.0,38.5):
        add_cyl(f'Trunk_{x}_{y}',(x,y,0.75),0.16,1.5,TREE_TRUNK,8)
        add_ico(f'Tree_{x}_{y}',(x,y,2.05),0.78,TREE)
# selected internal street trees
for y in range(-45,39,9):
    for x in (-32,-18,-4,10):
        add_cyl(f'IT_{x}_{y}',(x+2.8,y+2.7,0.65),0.13,1.3,TREE_TRUNK,8)
        add_ico(f'IC_{x}_{y}',(x+2.8,y+2.7,1.75),0.65,TREE)

# lamp posts along waterfront
for y in range(-54,63,9):
    add_cyl(f'LampPost_{y}',(40.0,y,1.8),0.07,3.6,(0.18,0.18,0.18,1),8)
    add_ico(f'LampHead_{y}',(40.0,y,3.65),0.16,(0.95,0.78,0.35,1))

# piers and distant bridge
for y in (-30,-12,8,28):
    add_cube(f'Pier_{y}',(48,y,0.02),(8.0,0.7,0.08),(0.34,0.27,0.20,1))
add_cube('FarBridgeDeck',(55,62,2.2),(24,1.0,0.22),(0.38,0.38,0.38,1))
for x in (38,52,66):
    add_cyl(f'BridgePillar_{x}',(x,62,1.1),0.30,2.2,(0.36,0.36,0.36,1),10)

# ---------- vehicles ----------
car_count = 0

def make_car(name, x, y, color, scale=1.0):
    global car_count
    boxes = [
        (0,0,0.42,1.65*scale,3.3*scale,0.62*scale),
        (0,0.20*scale,0.86*scale,1.30*scale,1.75*scale,0.55*scale),
        (-0.83*scale,-0.85*scale,0.25*scale,0.18*scale,0.62*scale,0.40*scale),
        (0.83*scale,-0.85*scale,0.25*scale,0.18*scale,0.62*scale,0.40*scale),
        (-0.83*scale,0.85*scale,0.25*scale,0.18*scale,0.62*scale,0.40*scale),
        (0.83*scale,0.85*scale,0.25*scale,0.18*scale,0.62*scale,0.40*scale),
    ]
    obj = boxes_mesh(name, boxes, color)
    obj.location=(x,y,0.10)
    car_count += 1
    return obj

# moving cars on waterfront boulevard
for i in range(26):
    lane_x = 29.6 if i%2==0 else 34.4
    start_y = -58 + (i%13)*9.5
    direction = 1 if i%2==0 else -1
    c=make_car(f'MovingCar_{i}',lane_x,start_y,random.choice(CAR_COLORS),0.78)
    c.keyframe_insert(data_path='location',frame=1)
    c.location.y = start_y + direction*48
    c.keyframe_insert(data_path='location',frame=END)
    linear_keys(c)

# moving cars on one internal avenue
for i in range(12):
    lane_x = -1.0 if i%2==0 else 1.0
    start_y=-48+(i%6)*15
    direction=1 if i%2==0 else -1
    c=make_car(f'CityCar_{i}',lane_x,start_y,random.choice(CAR_COLORS),0.72)
    c.keyframe_insert(data_path='location',frame=1)
    c.location.y=start_y+direction*36
    c.keyframe_insert(data_path='location',frame=END)
    linear_keys(c)

# parked cars along foreground roads
for i in range(34):
    y=-50+(i%17)*5.4
    x=-46 if i<17 else -24
    make_car(f'ParkedCar_{i}',x,y,random.choice(CAR_COLORS),0.68)

# boats
for i in range(5):
    boat=boxes_mesh(f'Boat_{i}',[(0,0,0,2.0+0.5*i,5.5+0.8*i,0.6),(0,0.3,0.65,1.3+0.3*i,2.4,0.7)],(0.72,0.72,0.68,1))
    boat.location=(49+random.uniform(2,20),-42+i*20,0.45)
    boat.keyframe_insert(data_path='location',frame=1)
    boat.location.y += random.uniform(7,14)
    boat.keyframe_insert(data_path='location',frame=END)
    linear_keys(boat)

# ---------- people ----------
npc_count=0

def make_person(name,x,y,shirt,walk_dir=1):
    global npc_count
    bpy.ops.object.empty_add(type='PLAIN_AXES',location=(x,y,0))
    root=bpy.context.object; root.name=name+'_Root'
    # local-part constructor
    def cube_part(n,loc,scale,color):
        o=add_cube(n,(0,0,0),scale,color,parent=root); o.location=loc; return o
    def cyl_part(n,loc,r,d,color):
        o=add_cyl(n,(0,0,0),r,d,color,8,parent=root); o.location=loc; return o
    torso=cube_part(name+'_Torso',(0,0,1.35),(0.24,0.16,0.40),shirt)
    head=add_ico(name+'_Head',(0,0,0),0.20,(0.78,0.57,0.39,1),parent=root); head.location=(0,0,1.95)
    armL=cyl_part(name+'_ArmL',(-0.34,0,1.38),0.07,0.72,shirt)
    armR=cyl_part(name+'_ArmR',(0.34,0,1.38),0.07,0.72,shirt)
    legL=cyl_part(name+'_LegL',(-0.13,0,0.60),0.085,0.95,(0.12,0.14,0.18,1))
    legR=cyl_part(name+'_LegR',(0.13,0,0.60),0.085,0.95,(0.12,0.14,0.18,1))
    cube_part(name+'_FootL',(-0.13,-0.09,0.10),(0.10,0.19,0.07),(0.08,0.08,0.08,1))
    cube_part(name+'_FootR',(0.13,-0.09,0.10),(0.10,0.19,0.07),(0.08,0.08,0.08,1))
    # walking root translation
    root.keyframe_insert(data_path='location',frame=1)
    root.location.y += walk_dir*12
    root.keyframe_insert(data_path='location',frame=END)
    linear_keys(root)
    # looping walk cycle on visible limbs
    for part,phase in ((armL,1),(armR,-1),(legL,-1),(legR,1)):
        for fr,val in ((1,0.48*phase),(7,0),(13,-0.48*phase),(19,0),(25,0.48*phase)):
            part.rotation_euler.x=val
            part.keyframe_insert(data_path='rotation_euler',frame=fr)
        if part.animation_data and part.animation_data.action:
            for fc in part.animation_data.action.fcurves:
                fc.modifiers.new('CYCLES')
                for kp in fc.keyframe_points: kp.interpolation='BEZIER'
    npc_count += 1
    return root

shirts=[(0.64,0.12,0.12,1),(0.10,0.26,0.65,1),(0.16,0.48,0.24,1),(0.75,0.50,0.11,1),(0.48,0.20,0.55,1)]
# detailed pedestrians near foreground and waterfront promenade
for i in range(28):
    if i<14:
        x=38.8+random.uniform(-0.5,0.5); y=-52+(i%14)*7.2
    else:
        x=-8+random.choice([-1,1])*3.1; y=-48+(i%14)*7.2
    make_person(f'NPC_{i}',x,y,random.choice(shirts),1 if i%2==0 else -1)
# static distant crowd dots/silhouettes
for i in range(70):
    x=random.uniform(-45,38); y=random.uniform(-25,55)
    if random.random()<0.55: x=38.8+random.uniform(-0.7,0.7)
    add_cyl(f'Crowd_{i}',(x,y,0.75),0.07,1.5,(0.18,0.18,0.20,1),6)

# ---------- camera ----------
bpy.ops.object.camera_add(location=(-58,-84,61))
cam=bpy.context.object; cam.name='Camera_Main'; scene.camera=cam
cam.data.lens=52
cam.data.clip_start=0.1; cam.data.clip_end=500
point_at(cam,(-4,10,12))
cam.keyframe_insert(data_path='location',frame=1)
cam.keyframe_insert(data_path='rotation_euler',frame=1)
# slow forward/right rooftop drift, reference-style
cam.location=(-52,-76,57)
point_at(cam,(-1,14,11))
cam.keyframe_insert(data_path='location',frame=END)
cam.keyframe_insert(data_path='rotation_euler',frame=END)
linear_keys(cam)

# ---------- QA / save / render ----------
# save scene before render
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.render.render(animation=True)

report={
    'blender_version': bpy.app.version_string,
    'engine': scene.render.engine,
    'resolution':[W,H],
    'fps':FPS,
    'frames':END,
    'duration_seconds':END/FPS,
    'building_count':building_count,
    'window_count':window_count,
    'car_count':car_count,
    'npc_detailed_count':npc_count,
    'video_exists':VIDEO.exists(),
    'video_size_bytes':VIDEO.stat().st_size if VIDEO.exists() else 0,
    'blend_exists':BLEND.exists(),
}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
assert building_count >= 55, report
assert window_count >= 400, report
assert car_count >= 60, report
assert npc_count >= 25, report
assert VIDEO.exists() and VIDEO.stat().st_size > 10000, report
assert BLEND.exists(), report
print('LIVING_CITY_V1_PASS')
print(json.dumps(report,indent=2))
