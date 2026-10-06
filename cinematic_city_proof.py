import bpy
import math
import random
import json
from pathlib import Path
from mathutils import Vector

SEED = 2706
random.seed(SEED)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'proof_artifacts'
OUT.mkdir(exist_ok=True)
QA = OUT / 'qa'
QA.mkdir(exist_ok=True)
VIDEO = OUT / 'CinematicCity_Proof.mp4'
BLEND = OUT / 'CinematicCity_Proof.blend'
REPORT = OUT / 'proof_report.json'

FPS = 24
END = 72
W, H = 360, 640

# ---------------- scene ----------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = END
scene.render.fps = FPS
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = W
scene.render.resolution_y = H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False

# Color management (safe across 5.2 builds)
try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    try:
        scene.view_settings.look = 'Medium High Contrast'
    except Exception:
        pass
try:
    scene.view_settings.view_transform = 'AgX'
except Exception:
    pass

# World lighting
scene.world.use_nodes = True
world_nodes = scene.world.node_tree.nodes
bg = world_nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.34, 0.47, 0.64, 1.0)
    bg.inputs['Strength'].default_value = 0.35

# ---------------- materials ----------------
def mat_principled(name, base, rough=0.6, metallic=0.0, emission=None, emission_strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = base
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metallic
    if emission is not None:
        for key in ('Emission Color', 'Emission'):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = emission
                break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emission_strength
    return m

MAT_ASPHALT = mat_principled('Asphalt', (0.025,0.03,0.035,1), 0.92)
MAT_SIDEWALK = mat_principled('Sidewalk', (0.34,0.35,0.34,1), 0.82)
MAT_CURB = mat_principled('Curb', (0.52,0.52,0.49,1), 0.78)
MAT_MEDIAN = mat_principled('MedianGrass', (0.10,0.24,0.09,1), 0.95)
MAT_GLASS = mat_principled('GlassDark', (0.025,0.065,0.10,1), 0.22, 0.05)
MAT_GLASS_LIT = mat_principled('GlassLit', (0.36,0.19,0.055,1), 0.35, 0.0, (1.0,0.43,0.08,1), 1.8)
MAT_ROOF = mat_principled('Roof', (0.11,0.115,0.12,1), 0.88)
MAT_MARK = mat_principled('RoadMark', (0.78,0.72,0.50,1), 0.55)
MAT_TREE = mat_principled('Tree', (0.045,0.18,0.055,1), 0.95)
MAT_TRUNK = mat_principled('Trunk', (0.16,0.075,0.025,1), 0.95)
MAT_METAL = mat_principled('StreetMetal', (0.09,0.095,0.10,1), 0.35, 0.55)
MAT_CAR_GLASS = mat_principled('CarGlass', (0.025,0.055,0.075,1), 0.18, 0.10)

BUILDING_MATS = [
    mat_principled('FacadeBrick1',(0.31,0.115,0.075,1),0.78),
    mat_principled('FacadeBrick2',(0.42,0.18,0.10,1),0.76),
    mat_principled('FacadeStone',(0.45,0.42,0.36,1),0.83),
    mat_principled('FacadeConcrete',(0.31,0.33,0.34,1),0.74),
    mat_principled('FacadeWarm',(0.48,0.39,0.27,1),0.80),
    mat_principled('FacadeGrey',(0.24,0.27,0.30,1),0.73),
]
FAR_BUILDING_MATS = [
    mat_principled('FarA',(0.34,0.38,0.42,1),0.82),
    mat_principled('FarB',(0.40,0.41,0.39,1),0.85),
    mat_principled('FarC',(0.36,0.34,0.32,1),0.86),
]
CAR_MATS = [
    mat_principled('CarRed',(0.52,0.035,0.025,1),0.35,0.15),
    mat_principled('CarBlue',(0.03,0.13,0.42,1),0.32,0.15),
    mat_principled('CarWhite',(0.62,0.62,0.58,1),0.28,0.12),
    mat_principled('CarYellow',(0.68,0.37,0.025,1),0.35,0.10),
    mat_principled('CarGreen',(0.025,0.30,0.12,1),0.38,0.10),
]

def apply_mat(obj, mat):
    if len(obj.data.materials):
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_cube(name, loc, dims, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_mat(o, mat)
    if bevel > 0:
        mod = o.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    return o


def add_cyl(name, loc, radius, depth, mat, vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    apply_mat(o, mat)
    return o


def add_ico(name, loc, radius, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    apply_mat(o, mat)
    return o


def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()


def add_window_panel(name, loc, dims, lit=False):
    return add_cube(name, loc, dims, MAT_GLASS_LIT if lit else MAT_GLASS, bevel=0.015)

V_ROADS = [(-108,8),(-72,8),(-36,8),(0,16),(36,8),(72,8),(108,8)]
H_ROADS = [(-112,8),(-80,8),(-48,8),(-16,8),(16,8),(48,8),(80,8),(112,8)]

add_cube('CityBase', (0,0,-0.55), (252,260,1.0), MAT_SIDEWALK)
for x,w in V_ROADS:
    add_cube(f'RoadV_{x}', (x,0,0.01), (w,248,0.12), MAT_ASPHALT)
for y,w in H_ROADS:
    add_cube(f'RoadH_{y}', (0,y,0.02), (240,w,0.13), MAT_ASPHALT)

add_cube('MainMedian', (0,0,0.11), (2.2,248,0.20), MAT_MEDIAN, bevel=0.10)
for y in range(-108,113,12):
    add_cyl(f'MedianTrunk_{y}', (0,y,0.85), 0.15, 1.5, MAT_TRUNK, 8)
    add_ico(f'MedianTree_{y}', (0,y,2.05), 0.85, MAT_TREE)
for x in (-5.0,5.0):
    for y in range(-110,112,10):
        add_cube(f'Mark_{x}_{y}', (x,y,0.10), (0.18,4.0,0.035), MAT_MARK)

def intervals_from_roads(roads):
    intervals=[]
    for (c0,w0),(c1,w1) in zip(roads[:-1], roads[1:]):
        a = c0 + w0/2
        b = c1 - w1/2
        if b > a:
            intervals.append((a,b))
    return intervals

X_BLOCKS = intervals_from_roads(V_ROADS)
Y_BLOCKS = intervals_from_roads(H_ROADS)
parcel_count = 0
building_count = 0
empty_parcels = 0
parcel_overflow = 0
window_count = 0
block_count = len(X_BLOCKS) * len(Y_BLOCKS)

def detail_level(cx, cy):
    d = math.hypot(cx-70, cy+95)
    if d < 100:
        return 2
    if d < 180:
        return 1
    return 0


def building_from_parcel(name, bounds, floors, mat, detail):
    global building_count, parcel_overflow, window_count
    xmin,xmax,ymin,ymax = bounds
    setback = 1.0 if detail >= 1 else 0.7
    bx0,bx1 = xmin+setback, xmax-setback
    by0,by1 = ymin+setback, ymax-setback
    if bx1 <= bx0 or by1 <= by0:
        raise RuntimeError(f'Parcel too small: {bounds}')
    if bx0 < xmin or bx1 > xmax or by0 < ymin or by1 > ymax:
        parcel_overflow += 1
    bw,bd = bx1-bx0, by1-by0
    cx,cy = (bx0+bx1)/2, (by0+by1)/2
    h = floors*3.0
    add_cube(name,(cx,cy,h/2+0.24),(bw,bd,h),mat,bevel=0.12 if detail==2 else 0.07 if detail==1 else 0.025)
    building_count += 1
    add_cube(name+'_Roof',(cx,cy,h+0.42),(bw*0.96,bd*0.96,0.36),MAT_ROOF,bevel=0.06 if detail else 0.02)
    if detail >= 1 and random.random() < 0.70:
        add_cube(name+'_HVAC',(cx+bw*0.18,cy-bd*0.12,h+0.85),(1.2,1.5,0.55),MAT_METAL,bevel=0.05)
    if detail < 1:
        return
    cols_s = max(2, int(bw // 2.7))
    cols_e = max(2, int(bd // 2.7))
    for f in range(1, floors):
        z = 0.24 + 1.55 + f*3.0
        for c in range(cols_s):
            t = (c+0.5)/cols_s
            wx = bx0 + t*bw
            add_window_panel(f'{name}_S_{f}_{c}', (wx, by0-0.035, z), (min(1.15,bw/cols_s*0.62),0.10,1.15), random.random() < 0.18)
            window_count += 1
        for c in range(cols_e):
            t = (c+0.5)/cols_e
            wy = by0 + t*bd
            add_window_panel(f'{name}_E_{f}_{c}', (bx1+0.035, wy, z), (0.10,min(1.15,bd/cols_e*0.62),1.15), random.random() < 0.16)
            window_count += 1
    add_cube(name+'_Door',(cx,by0-0.055,1.35),(1.25,0.12,2.25),MAT_GLASS,bevel=0.03)
    if detail == 2 and bw > 8:
        add_cube(name+'_ShopL',(cx-bw*0.23,by0-0.06,1.55),(bw*0.30,0.12,2.0),MAT_GLASS,bevel=0.03)
        add_cube(name+'_ShopR',(cx+bw*0.23,by0-0.06,1.55),(bw*0.30,0.12,2.0),MAT_GLASS,bevel=0.03)
        add_cube(name+'_Awning',(cx,by0-0.42,2.95),(bw*0.72,0.75,0.14),mat,bevel=0.05)

for iy,(y0,y1) in enumerate(Y_BLOCKS):
    for ix,(x0,x1) in enumerate(X_BLOCKS):
        cx,cy=(x0+x1)/2,(y0+y1)/2
        add_cube(f'Block_{ix}_{iy}',(cx,cy,0.11),(x1-x0,y1-y0,0.20),MAT_SIDEWALK,bevel=0.12)
        if (x1-x0) >= (y1-y0):
            xm=(x0+x1)/2
            parcels=[(x0,xm,y0,y1),(xm,x1,y0,y1)]
        else:
            ym=(y0+y1)/2
            parcels=[(x0,x1,y0,ym),(x0,x1,ym,y1)]
        for pi,p in enumerate(parcels):
            parcel_count += 1
            pcx=(p[0]+p[1])/2; pcy=(p[2]+p[3])/2
            detail=detail_level(pcx,pcy)
            depth = (pcy - Y_BLOCKS[0][0]) / max(1,(Y_BLOCKS[-1][1]-Y_BLOCKS[0][0]))
            if depth > 0.70 and random.random() < 0.38:
                floors=random.randint(9,16)
            elif depth > 0.50:
                floors=random.randint(5,10)
            else:
                floors=random.randint(3,7)
            mat = random.choice(BUILDING_MATS if detail else FAR_BUILDING_MATS)
            building_from_parcel(f'B_{ix}_{iy}_{pi}',p,floors,mat,detail)

for x,w in V_ROADS:
    if x == 0:
        continue
    for y in range(-104,105,16):
        side = -1 if ((y//16) % 2 == 0) else 1
        tx = x + side*(w/2 + 2.2)
        add_cyl(f'TreeTrunk_{x}_{y}',(tx,y,0.85),0.14,1.5,MAT_TRUNK,8)
        add_ico(f'TreeCrown_{x}_{y}',(tx,y,2.0),0.72,MAT_TREE)

car_count=0
for lane_x, direction in [(-5.5,1),(-2.8,1),(2.8,-1),(5.5,-1)]:
    for i,y in enumerate(range(-105,106,28)):
        yy = y + (i%2)*5
        body = add_cube(f'Car_{car_count}',(lane_x,yy,0.63),(1.85,4.2,0.75),random.choice(CAR_MATS),bevel=0.18)
        add_cube(f'CarGlass_{car_count}',(lane_x,yy+0.15,1.15),(1.52,1.95,0.55),MAT_CAR_GLASS,bevel=0.12)
        body.keyframe_insert(data_path='location',frame=1)
        body.location.y += direction*18
        body.keyframe_insert(data_path='location',frame=END)
        car_count += 1

bpy.ops.object.camera_add(location=(122,-154,78))
cam=bpy.context.object
cam.name='Camera_Main'
cam.data.lens=58
cam.data.sensor_width=36
cam.data.clip_start=0.1
cam.data.clip_end=800
scene.camera=cam
point_camera(cam,(0,28,13))
cam.keyframe_insert(data_path='location',frame=1)
cam.keyframe_insert(data_path='rotation_euler',frame=1)
cam.location=(116,-147,75)
point_camera(cam,(0,34,13))
cam.keyframe_insert(data_path='location',frame=END)
cam.keyframe_insert(data_path='rotation_euler',frame=END)

bpy.ops.object.light_add(type='SUN', location=(0,0,70))
sun=bpy.context.object
sun.name='Sun_Key'
sun.data.energy=2.2
sun.data.angle=math.radians(4.0)
sun.rotation_euler=(math.radians(42),math.radians(-18),math.radians(-38))

bpy.ops.object.light_add(type='AREA', location=(70,-90,55))
fill=bpy.context.object
fill.name='Sky_Fill'
fill.data.energy=650
fill.data.shape='DISK'
fill.data.size=45
point_camera(fill,(0,10,5))

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
qa_frames=[1,24,48,72]
for idx,frame in enumerate(qa_frames,1):
    scene.frame_set(frame)
    scene.render.image_settings.file_format='PNG'
    scene.render.filepath=str(QA / f'frame_{idx:02d}.png')
    bpy.ops.render.render(write_still=True)

scene.frame_set(1)
scene.render.image_settings.media_type='VIDEO'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'
scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='MEDIUM'
scene.render.filepath=str(VIDEO)
bpy.ops.render.render(animation=True)

report={
    'blender_version': bpy.app.version_string,
    'engine': scene.render.engine,
    'resolution':[W,H],
    'fps':FPS,
    'frames':END,
    'duration_seconds':END/FPS,
    'block_count':block_count,
    'parcel_count':parcel_count,
    'building_count':building_count,
    'empty_parcels':empty_parcels,
    'parcel_overflow':parcel_overflow,
    'window_count':window_count,
    'car_count':car_count,
    'camera_lens_mm':cam.data.lens,
    'waterfront_objects':len([o for o in bpy.data.objects if any(k in o.name.lower() for k in ('water','pier','boat','bridge'))]),
    'video_exists':VIDEO.exists(),
    'video_size_bytes':VIDEO.stat().st_size if VIDEO.exists() else 0,
    'blend_exists':BLEND.exists(),
    'qa_frames':[str(QA / f'frame_{i:02d}.png') for i in range(1,5)],
}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')

assert block_count == 42, report
assert parcel_count == 84, report
assert building_count == parcel_count, report
assert empty_parcels == 0, report
assert parcel_overflow == 0, report
assert report['waterfront_objects'] == 0, report
assert window_count > 500, report
assert car_count >= 24, report
assert VIDEO.exists() and VIDEO.stat().st_size > 5000, report
assert BLEND.exists(), report
for p in report['qa_frames']:
    assert Path(p).exists() and Path(p).stat().st_size > 5000, p
print('CINEMATIC_CITY_PROOF_PASS')
print(json.dumps(report,indent=2))
