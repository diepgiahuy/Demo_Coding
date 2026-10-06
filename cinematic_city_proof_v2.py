import bpy
import math
import random
import json
from pathlib import Path
from mathutils import Vector
from city_plan import build_plan, validate_plan, V_ROADS, H_ROADS

SEED=2706
rng=random.Random(SEED)
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'proof_v2_artifacts'
QA=OUT/'qa'
OUT.mkdir(exist_ok=True); QA.mkdir(exist_ok=True)
BLEND=OUT/'CinematicCity_Proof_v2.blend'
REPORT=OUT/'proof_report.json'
W,H=360,640
FPS=24
END=48

print('PHASE:PLAN', flush=True)
plan=build_plan(SEED)
validation=validate_plan(plan)
assert validation['ok'], validation
assert validation['block_count']==42
assert validation['parcel_count']==84
assert validation['building_count']==84

print('PHASE:SCENE_INIT', flush=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=END; scene.render.fps=FPS
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=W; scene.render.resolution_y=H; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
try: scene.view_settings.view_transform='AgX'
except Exception: pass
try: scene.view_settings.look='Medium High Contrast'
except Exception: pass
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value=(0.24,0.36,0.52,1)
    bg.inputs['Strength'].default_value=0.32

def mat(name, color, rough=0.7, metallic=0.0, emission=None, estr=0.0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=color
    bsdf.inputs['Roughness'].default_value=rough
    bsdf.inputs['Metallic'].default_value=metallic
    if emission:
        for k in ('Emission Color','Emission'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value=emission; break
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value=estr
    return m

ASPHALT=mat('Asphalt',(0.025,0.028,0.033,1),0.92)
SIDEWALK=mat('Sidewalk',(0.34,0.35,0.34,1),0.86)
MEDIAN=mat('Median',(0.07,0.21,0.075,1),0.95)
MARK=mat('Mark',(0.82,0.74,0.45,1),0.55)
ROOF=mat('Roof',(0.09,0.10,0.11,1),0.88)
GLASS=mat('Glass',(0.02,0.055,0.085,1),0.22,0.05)
GLASS_LIT=mat('GlassLit',(0.22,0.095,0.025,1),0.35,0.0,(1.0,0.35,0.05,1),1.4)
METAL=mat('Metal',(0.08,0.085,0.09,1),0.36,0.45)
TREE=mat('Tree',(0.04,0.17,0.055,1),0.95)
TRUNK=mat('Trunk',(0.15,0.065,0.02,1),0.95)
FACADES=[mat('Brick1',(0.30,0.105,0.065,1),0.78),mat('Brick2',(0.40,0.17,0.09,1),0.78),mat('Stone',(0.45,0.41,0.34,1),0.84),mat('Concrete',(0.30,0.32,0.33,1),0.78),mat('Warm',(0.46,0.37,0.25,1),0.82),mat('Grey',(0.23,0.26,0.29,1),0.77)]
FAR=[mat('Far1',(0.34,0.37,0.40,1),0.88),mat('Far2',(0.40,0.40,0.38,1),0.88),mat('Far3',(0.35,0.33,0.31,1),0.90)]
CAR_MATS=[mat('CarRed',(0.5,0.03,0.02,1),0.35,0.15),mat('CarBlue',(0.025,0.12,0.38,1),0.34,0.15),mat('CarWhite',(0.62,0.62,0.58,1),0.30,0.1),mat('CarYellow',(0.63,0.31,0.02,1),0.36,0.1)]
CAR_GLASS=mat('CarGlass',(0.02,0.045,0.065,1),0.18,0.08)

def apply_mat(o,m): o.data.materials.append(m)

def cube(name,loc,dims,m,bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    apply_mat(o,m)
    if bevel:
        md=o.modifiers.new('Bevel','BEVEL'); md.width=bevel; md.segments=2; md.limit_method='ANGLE'
    return o

def boxes_mesh(name, boxes, m):
    verts=[]; faces=[]
    for cx,cy,cz,sx,sy,sz in boxes:
        hx,hy,hz=sx/2,sy/2,sz/2; b=len(verts)
        verts.extend([(cx-hx,cy-hy,cz-hz),(cx+hx,cy-hy,cz-hz),(cx+hx,cy+hy,cz-hz),(cx-hx,cy+hy,cz-hz),(cx-hx,cy-hy,cz+hz),(cx+hx,cy-hy,cz+hz),(cx+hx,cy+hy,cz+hz),(cx-hx,cy+hy,cz+hz)])
        faces.extend([(b,b+1,b+2,b+3),(b+4,b+7,b+6,b+5),(b,b+4,b+5,b+1),(b+1,b+5,b+6,b+2),(b+2,b+6,b+7,b+3),(b+4,b,b+3,b+7)])
    mesh=bpy.data.meshes.new(name+'_Mesh'); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); apply_mat(o,m); return o

def point_at(o,target): o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def create_tree_sources():
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=0.14,depth=1.5,location=(0,0,-50))
    t=bpy.context.object; t.name='TreeTrunk_Source'; apply_mat(t,TRUNK); t.hide_render=True
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=0.72,location=(0,0,-50))
    c=bpy.context.object; c.name='TreeCrown_Source'; apply_mat(c,TREE); c.hide_render=True
    return t,c

def linked_clone(src,name,loc):
    o=src.copy(); o.data=src.data; o.name=name; o.location=loc; o.hide_render=False; bpy.context.collection.objects.link(o); return o

print('PHASE:ROADS_BLOCKS', flush=True)
cube('CityBase',(0,0,-0.55),(252,260,1.0),SIDEWALK)
for x,w in V_ROADS: cube(f'RoadV_{x}',(x,0,0.01),(w,248,0.12),ASPHALT)
for y,w in H_ROADS: cube(f'RoadH_{y}',(0,y,0.02),(240,w,0.13),ASPHALT)
cube('MainMedian',(0,0,0.11),(2.2,248,0.20),MEDIAN,0.08)
mark_boxes=[]
for x in (-5.0,5.0):
    for y in range(-110,112,10): mark_boxes.append((x,y,0.10,0.18,4.0,0.035))
boxes_mesh('RoadMarks',mark_boxes,MARK)
for blk in plan['blocks']:
    x0,x1,y0,y1=blk['bounds']; cube(blk['id'],((x0+x1)/2,(y0+y1)/2,0.11),(x1-x0,y1-y0,0.20),SIDEWALK,0.08)

print('PHASE:BUILDINGS_BATCH_WINDOWS', flush=True)
dark_windows=[]; lit_windows=[]; roof_count=0; hvac_count=0; window_count=0
for b in plan['buildings']:
    x0,x1,y0,y1=b['footprint']; bw=x1-x0; bd=y1-y0; cx=(x0+x1)/2; cy=(y0+y1)/2
    floors=b['floors']; detail=b['detail']; h=floors*3.0
    material=(FACADES[b['material_index']] if detail else FAR[b['material_index']])
    cube(b['id'],(cx,cy,h/2+0.24),(bw,bd,h),material,0.12 if detail==2 else 0.06 if detail==1 else 0.02)
    cube(b['id']+'_Roof',(cx,cy,h+0.40),(bw*0.96,bd*0.96,0.34),ROOF,0.04 if detail else 0.015); roof_count+=1
    if detail>=1 and rng.random()<0.60:
        cube(b['id']+'_HVAC',(cx+bw*0.18,cy-bd*0.10,h+0.78),(1.15,1.35,0.50),METAL,0.04); hvac_count+=1
    if detail<1: continue
    cols_s=max(2,int(bw//2.7)); cols_e=max(2,int(bd//2.7))
    for f in range(1,floors):
        z=0.24+1.55+f*3.0
        for c in range(cols_s):
            wx=x0+(c+0.5)/cols_s*bw; box=(wx,y0-0.035,z,min(1.15,bw/cols_s*0.62),0.10,1.15)
            (lit_windows if rng.random()<0.18 else dark_windows).append(box); window_count+=1
        for c in range(cols_e):
            wy=y0+(c+0.5)/cols_e*bd; box=(x1+0.035,wy,z,0.10,min(1.15,bd/cols_e*0.62),1.15)
            (lit_windows if rng.random()<0.16 else dark_windows).append(box); window_count+=1
    cube(b['id']+'_Door',(cx,y0-0.055,1.35),(1.25,0.12,2.25),GLASS,0.02)
    if detail==2 and bw>8:
        cube(b['id']+'_ShopL',(cx-bw*0.23,y0-0.06,1.55),(bw*0.30,0.12,2.0),GLASS,0.02)
        cube(b['id']+'_ShopR',(cx+bw*0.23,y0-0.06,1.55),(bw*0.30,0.12,2.0),GLASS,0.02)
        cube(b['id']+'_Awning',(cx,y0-0.40,2.95),(bw*0.72,0.70,0.14),material,0.04)
if dark_windows: boxes_mesh('Windows_Dark_BATCH',dark_windows,GLASS)
if lit_windows: boxes_mesh('Windows_Lit_BATCH',lit_windows,GLASS_LIT)

print('PHASE:PROPS_TRAFFIC', flush=True)
trunk_src,crown_src=create_tree_sources(); tree_count=0
for y in range(-108,113,12):
    linked_clone(trunk_src,f'MedianTrunk_{y}',(0,y,0.85)); linked_clone(crown_src,f'MedianTree_{y}',(0,y,2.05)); tree_count+=1
for x,w in V_ROADS:
    if x==0: continue
    for y in range(-104,105,20):
        side=-1 if ((y//20)%2==0) else 1; tx=x+side*(w/2+2.2)
        linked_clone(trunk_src,f'Trunk_{x}_{y}',(tx,y,0.85)); linked_clone(crown_src,f'Crown_{x}_{y}',(tx,y,2.0)); tree_count+=1

car_count=0
for lane_x,direction in [(-5.5,1),(-2.8,1),(2.8,-1),(5.5,-1)]:
    for i,y in enumerate(range(-102,103,34)):
        yy=y+(i%2)*5
        body=cube(f'Car_{car_count}',(lane_x,yy,0.62),(1.85,4.15,0.72),CAR_MATS[car_count%len(CAR_MATS)],0.16)
        cab=cube(f'CarCab_{car_count}',(lane_x,yy+0.10,1.12),(1.5,1.9,0.52),CAR_GLASS,0.10); cab.parent=body; cab.matrix_parent_inverse=body.matrix_world.inverted()
        body.keyframe_insert(data_path='location',frame=1); body.location.y += direction*12; body.keyframe_insert(data_path='location',frame=END)
        car_count+=1

print('PHASE:CAMERA_LIGHT', flush=True)
bpy.ops.object.camera_add(location=(124,-158,76))
cam=bpy.context.object; cam.name='Camera_Main'; cam.data.lens=55; cam.data.sensor_width=36; cam.data.clip_end=800; scene.camera=cam
point_at(cam,(0,25,12)); cam.keyframe_insert(data_path='location',frame=1); cam.keyframe_insert(data_path='rotation_euler',frame=1)
cam.location=(116,-149,72); point_at(cam,(0,34,12)); cam.keyframe_insert(data_path='location',frame=END); cam.keyframe_insert(data_path='rotation_euler',frame=END)

bpy.ops.object.light_add(type='SUN',location=(0,0,70)); sun=bpy.context.object; sun.name='Sun_Key'; sun.data.energy=2.0; sun.data.angle=math.radians(4.0); sun.rotation_euler=(math.radians(43),math.radians(-20),math.radians(-36))
bpy.ops.object.light_add(type='AREA',location=(70,-100,58)); fill=bpy.context.object; fill.name='Fill'; fill.data.energy=500; fill.data.shape='DISK'; fill.data.size=50; point_at(fill,(0,15,5))

report={**validation,'blender_version':bpy.app.version_string,'engine':scene.render.engine,'resolution':[W,H],'frames':END,'fps':FPS,'camera_lens_mm':cam.data.lens,'window_count':window_count,'window_batch_objects':int(bool(dark_windows))+int(bool(lit_windows)),'tree_count':tree_count,'car_count':car_count,'roof_count':roof_count,'hvac_count':hvac_count,'waterfront_objects':len([o for o in bpy.data.objects if any(k in o.name.lower() for k in ('water','pier','boat','bridge'))]),'object_count':len(bpy.data.objects),'qa_frames':[]}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PHASE:SAVE_BLEND objects=',report['object_count'],'windows=',window_count, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

for idx,frame in enumerate((1,24,48),1):
    scene.frame_set(frame); scene.render.filepath=str(QA/f'frame_{idx:02d}.png')
    print(f'PHASE:RENDER_QA_{idx} frame={frame}', flush=True)
    bpy.ops.render.render(write_still=True)
    report['qa_frames'].append(str(QA/f'frame_{idx:02d}.png')); REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')

assert validation['ok']
assert validation['empty_parcels']==0
assert validation['overflow_count']==0
assert report['waterfront_objects']==0
assert report['window_batch_objects']<=2
assert report['object_count']<650, report['object_count']
assert BLEND.exists() and BLEND.stat().st_size>10000
for p in report['qa_frames']: assert Path(p).exists() and Path(p).stat().st_size>5000, p
print('CINEMATIC_CITY_V2_TECHNICAL_PASS', flush=True)
print(json.dumps(report,indent=2), flush=True)
