import bpy
import os
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "styleframe_assets"
OUT = Path(os.environ.get("OUT_DIR", ROOT / "styleframe_output"))
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Clean scene
# -----------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.resolution_percentage = 100
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.fps = 30

try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
scene.view_settings.exposure = 0.25

# World
scene.world.use_nodes = True
wn = scene.world.node_tree.nodes
bg = wn.get('Background')
bg.inputs['Color'].default_value = (0.55, 0.70, 0.86, 1.0)
bg.inputs['Strength'].default_value = 0.42

# -----------------------------------------------------------------------------
# Materials
# -----------------------------------------------------------------------------
def mat(name, color, rough=0.65, metallic=0.0, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = rough
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metallic
        if emission is not None:
            if 'Emission Color' in bsdf.inputs:
                bsdf.inputs['Emission Color'].default_value = emission
                if 'Emission Strength' in bsdf.inputs:
                    bsdf.inputs['Emission Strength'].default_value = 1.4
            elif 'Emission' in bsdf.inputs:
                bsdf.inputs['Emission'].default_value = emission
    return m

MAT = {
    'asphalt': mat('M_Asphalt', (0.055,0.065,0.075,1), 0.92),
    'sidewalk': mat('M_Sidewalk', (0.53,0.51,0.47,1), 0.88),
    'curb': mat('M_Curb', (0.72,0.70,0.64,1), 0.78),
    'terracotta': mat('M_Terracotta', (0.50,0.16,0.075,1), 0.72),
    'cream': mat('M_Cream', (0.78,0.68,0.51,1), 0.72),
    'green': mat('M_AwningGreen', (0.06,0.27,0.19,1), 0.58),
    'glass': mat('M_GlassDark', (0.025,0.10,0.14,1), 0.16),
    'black': mat('M_BlackMetal', (0.025,0.032,0.04,1), 0.28, 0.35),
    'white': mat('M_WarmWhite', (0.88,0.84,0.74,1), 0.62),
    'wood': mat('M_Wood', (0.33,0.13,0.055,1), 0.72),
    'shelf': mat('M_Shelf', (0.16,0.18,0.19,1), 0.55, 0.15),
    'box_red': mat('M_BoxRed', (0.72,0.18,0.10,1), 0.72),
    'box_yellow': mat('M_BoxYellow', (0.82,0.57,0.10,1), 0.72),
    'box_blue': mat('M_BoxBlue', (0.10,0.32,0.62,1), 0.72),
    'skin': mat('M_Skin', (0.59,0.38,0.25,1), 0.78),
    'skin_light': mat('M_SkinLight', (0.77,0.56,0.39,1), 0.78),
    'hair': mat('M_Hair', (0.055,0.035,0.025,1), 0.80),
    'civilian': mat('M_CivilianJacket', (0.76,0.44,0.055,1), 0.83),
    'civilian_shirt': mat('M_CivilianShirt', (0.16,0.34,0.25,1), 0.84),
    'civilian_pants': mat('M_CivilianPants', (0.12,0.14,0.16,1), 0.88),
    'navy': mat('M_PoliceNavy', (0.025,0.085,0.16,1), 0.78),
    'vest': mat('M_PoliceVest', (0.018,0.035,0.055,1), 0.54),
    'badge': mat('M_Badge', (0.88,0.67,0.18,1), 0.36, 0.6),
    'shoe': mat('M_Shoe', (0.025,0.025,0.028,1), 0.60),
    'tree_trunk': mat('M_TreeTrunk', (0.22,0.095,0.038,1), 0.88),
    'leaf1': mat('M_Leaf1', (0.19,0.42,0.12,1), 0.86),
    'leaf2': mat('M_Leaf2', (0.32,0.55,0.16,1), 0.84),
    'marking': mat('M_RoadMarking', (0.87,0.84,0.68,1), 0.72),
}

# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------
def assign(obj, material):
    if obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(material)


def bevel(obj, width=0.04, segments=2):
    if obj.type != 'MESH':
        return obj
    mod = obj.modifiers.new('Soft bevel', 'BEVEL')
    mod.width = width
    mod.segments = segments
    return obj


def cube(name, loc, dims, material, bevel_w=0.0, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(o, material)
    if bevel_w:
        bevel(o, bevel_w)
    return o


def ico(name, loc, radius, material, scale=(1,1,1), subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    assign(o, material)
    return o


def cyl_between(name, a, b, radius, material, vertices=8):
    a, b = Vector(a), Vector(b)
    vec = b-a
    length = vec.length
    mid = (a+b)/2
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = vec.to_track_quat('Z','Y')
    o.rotation_mode = 'XYZ'
    assign(o, material)
    bevel(o, radius*0.12, 1)
    return o


def box_between(name, a, b, width, depth, material, bevel_w=0.04):
    a, b = Vector(a), Vector(b)
    vec = b-a
    mid = (a+b)/2
    o = cube(name, mid, (width, depth, vec.length), material, bevel_w)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = vec.to_track_quat('Z','Y')
    o.rotation_mode = 'XYZ'
    return o


def text_obj(name, body, loc, size, material, extrude=0.018):
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(90),0,math.radians(90)))
    t = bpy.context.object
    t.name = name
    t.data.body = body
    t.data.align_x = 'CENTER'
    t.data.align_y = 'CENTER'
    t.data.size = size
    t.data.extrude = extrude
    t.data.bevel_depth = 0.006
    t.data.materials.append(material)
    return t


def point_camera(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()

# -----------------------------------------------------------------------------
# Base street: deliberate foreground + depth
# -----------------------------------------------------------------------------
# asphalt street
cube('Street_Asphalt', (2.25, 9.0, -0.07), (7.2, 27.0, 0.14), MAT['asphalt'], 0.02)
# sidewalk and curb
cube('Sidewalk', (-3.0, 9.0, 0.05), (3.2, 27.0, 0.18), MAT['sidewalk'], 0.025)
cube('Curb', (-1.35, 9.0, 0.09), (0.20, 27.0, 0.25), MAT['curb'], 0.025)
# paving seams
for y in [i*1.55-3 for i in range(16)]:
    cube('PaveSeam', (-3.0, y, 0.148), (3.05, 0.022, 0.008), MAT['curb'])
# lane dashes farther from hero action
for y in range(1, 26, 4):
    cube('LaneDash', (2.1, y, 0.015), (0.09, 1.55, 0.018), MAT['marking'])
# crosswalk in depth
for x in [-0.5,0.2,0.9,1.6,2.3,3.0,3.7,4.4]:
    cube('Crosswalk', (x, 17.7, 0.018), (0.38, 3.2, 0.02), MAT['marking'])

# -----------------------------------------------------------------------------
# Hero storefront — modeled only where camera sees it
# -----------------------------------------------------------------------------
# upper building mass
cube('MarketUpper', (-5.55, 4.0, 5.7), (1.6, 8.0, 5.3), MAT['terracotta'], 0.055)
# lower interior backing and side columns
cube('MarketInteriorBack', (-5.55, 4.0, 1.55), (0.32, 7.8, 3.1), MAT['wood'], 0.025)
cube('MarketColumnA', (-4.73, 0.15, 1.65), (0.25, 0.38, 3.3), MAT['cream'], 0.025)
cube('MarketColumnB', (-4.73, 7.85, 1.65), (0.25, 0.38, 3.3), MAT['cream'], 0.025)
# storefront windows left/right + central recessed doorway
for y,w in [(1.0,1.35),(5.85,2.25)]:
    cube('ShopGlass', (-4.69, y, 1.35), (0.065, w, 2.30), MAT['glass'], 0.018)
    # sill / header
    cube('ShopFrameTop', (-4.62, y, 2.53), (0.14, w+0.10, 0.10), MAT['black'], 0.015)
    cube('ShopFrameBottom', (-4.62, y, 0.18), (0.14, w+0.10, 0.10), MAT['black'], 0.015)
# doorway frame
cube('DoorRecess', (-5.05, 3.05, 1.20), (0.62, 1.38, 2.40), MAT['glass'], 0.03)
cube('DoorLeftFrame', (-4.65, 2.34, 1.25), (0.14, 0.12, 2.50), MAT['black'], 0.02)
cube('DoorRightFrame', (-4.65, 3.76, 1.25), (0.14, 0.12, 2.50), MAT['black'], 0.02)
cube('DoorHeader', (-4.65, 3.05, 2.49), (0.14, 1.52, 0.13), MAT['black'], 0.02)
# door threshold
cube('Threshold', (-4.42, 3.05, 0.10), (0.62, 1.55, 0.12), MAT['curb'], 0.02)
# visible interior shelves through/around doorway
for yy in [0.9, 5.8]:
    for zz in [0.55,1.10,1.65]:
        cube('InteriorShelf', (-5.16, yy, zz), (0.28, 1.10, 0.10), MAT['shelf'], 0.015)
    for k,zz in enumerate([0.73,1.27,1.82]):
        cube('Product', (-5.00, yy-0.25, zz), (0.16,0.24,0.22), [MAT['box_red'],MAT['box_yellow'],MAT['box_blue']][k%3], 0.02)
        cube('Product', (-5.00, yy+0.25, zz), (0.16,0.24,0.22), [MAT['box_blue'],MAT['box_red'],MAT['box_yellow']][k%3], 0.02)
# awning with thickness and striped underside
cube('Awning', (-4.15, 3.55, 3.05), (1.25, 6.75, 0.18), MAT['green'], 0.055, rot=(0,math.radians(-9),0))
for yy in [0.55,1.70,2.85,4.00,5.15,6.30]:
    cube('AwningStripe', (-4.02, yy, 2.99), (1.05,0.24,0.045), MAT['cream'], 0.01, rot=(0,math.radians(-9),0))
# signboard + actual readable English sign
cube('ShopSignBoard', (-4.55, 3.6, 3.70), (0.18, 4.7, 0.72), MAT['green'], 0.04)
text_obj('MarketText','CORNER MARKET',(-4.43,3.6,3.70),0.38,MAT['white'],0.014)
# upper recessed-looking windows via dark panes + thick frames
for z in [4.65,6.25,7.85]:
    for y in [0.65,2.35,4.05,5.75,7.15]:
        cube('UpperWindow', (-4.70,y,z), (0.055,0.83,0.78), MAT['glass'], 0.012)
        cube('UpperWindowTop',(-4.64,y,z+0.43),(0.11,0.91,0.075),MAT['cream'],0.01)
        cube('UpperWindowBottom',(-4.64,y,z-0.43),(0.11,0.91,0.075),MAT['cream'],0.01)
        cube('UpperWindowL',(-4.64,y-0.455,z),(0.11,0.075,0.85),MAT['cream'],0.01)
        cube('UpperWindowR',(-4.64,y+0.455,z),(0.11,0.075,0.85),MAT['cream'],0.01)

# -----------------------------------------------------------------------------
# Imported CC0 assets for background city / vehicles / background people
# -----------------------------------------------------------------------------
def group_bbox(objs):
    pts=[]
    for o in objs:
        if o.type == 'MESH':
            for c in o.bound_box:
                pts.append(o.matrix_world @ Vector(c))
    if not pts:
        return Vector((0,0,0)), Vector((1,1,1))
    mins=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    maxs=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return mins,maxs


def import_glb(filename, name, loc, target_height=None, target_length=None, rot_z=0.0):
    path=ASSETS/filename
    if not path.exists():
        print('ASSET_MISSING',path)
        return None
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new=[o for o in bpy.data.objects if o not in before]
    if not new:
        return None
    mins,maxs=group_bbox(new)
    center=Vector(((mins.x+maxs.x)/2,(mins.y+maxs.y)/2,mins.z))
    root=bpy.data.objects.new(name,None)
    scene.collection.objects.link(root)
    root.location=center
    for o in new:
        mw=o.matrix_world.copy()
        o.parent=root
        o.matrix_world=mw
    dims=maxs-mins
    s=1.0
    if target_height and dims.z>1e-5:
        s=target_height/dims.z
    elif target_length:
        longest=max(dims.x,dims.y)
        if longest>1e-5:
            s=target_length/longest
    root.scale=(s,s,s)
    root.rotation_euler.z=rot_z
    root.location=loc
    return root

# background buildings: only enough to create depth
import_glb('building-a.glb','BG_Building_A',(-5.1,12.4,0),target_height=9.5,rot_z=math.radians(90))
import_glb('building-e.glb','BG_Building_E',(-5.2,20.0,0),target_height=12.5,rot_z=math.radians(90))
import_glb('building-j.glb','BG_Building_J',(6.5,17.5,0),target_height=13.5,rot_z=math.radians(-90))
# quality vehicles
import_glb('sedan.glb','Car_Sedan',(2.6,7.0,0.02),target_length=4.3,rot_z=math.radians(90))
import_glb('police.glb','PoliceCar_BG',(3.5,13.2,0.02),target_length=4.4,rot_z=math.radians(90))
import_glb('taxi.glb','Taxi_BG',(1.4,21.0,0.02),target_length=4.3,rot_z=math.radians(90))
# street furniture
import_glb('traffic-light.glb','TrafficLight',(4.9,17.2,0),target_height=4.2,rot_z=math.radians(180))
import_glb('light-curved.glb','StreetLamp',(-1.55,10.2,0),target_height=5.2,rot_z=math.radians(180))
# background citizens, deliberately not hero focus
for idx,(fn,loc,rz) in enumerate([
    ('character-a.glb',(-2.8,9.0,0),math.radians(15)),
    ('character-b.glb',(-2.4,12.0,0),math.radians(-10)),
    ('character-c.glb',(-3.1,15.3,0),math.radians(8)),
    ('character-d.glb',(-2.5,18.5,0),math.radians(-12)),
]):
    import_glb(fn,f'BG_Person_{idx}',loc,target_height=1.75,rot_z=rz)

# -----------------------------------------------------------------------------
# Hero characters: segmented, readable joints, precise contact pose
# -----------------------------------------------------------------------------
def shoe(name, pos, material, yaw=0.0):
    return cube(name,pos,(0.34,0.18,0.13),material,0.045,rot=(0,0,yaw))


def hero_civilian():
    # Key joints. Facing police (+X) while being forced back toward storefront (-X).
    hip=Vector((-3.72,3.00,0.94))
    chest=Vector((-3.93,3.00,1.42))
    neck=Vector((-4.01,3.00,1.61))
    head=Vector((-4.06,3.00,1.80))
    # torso/jacket
    box_between('Civ_Torso',hip,chest,0.38,0.54,MAT['civilian'],0.055)
    box_between('Civ_Shirt',hip+Vector((0.08,0,0.08)),chest+Vector((0.08,0,0.01)),0.22,0.36,MAT['civilian_shirt'],0.035)
    cyl_between('Civ_Neck',neck-Vector((0,0,0.09)),neck+Vector((0,0,0.06)),0.075,MAT['skin_light'])
    ico('Civ_Head',head,0.175,MAT['skin_light'],scale=(0.88,0.95,1.05),subdivisions=2)
    ico('Civ_Hair',head+Vector((-0.012,0,0.075)),0.18,MAT['hair'],scale=(0.93,0.98,0.60),subdivisions=1)
    # legs: back leg bent near threshold, front leg braced forward
    Lhip=hip+Vector((0,-0.12,-0.02)); Rhip=hip+Vector((0,0.12,-0.02))
    Lk=Vector((-3.88,2.88,0.52)); Rk=Vector((-3.50,3.12,0.51))
    La=Vector((-4.04,2.86,0.15)); Ra=Vector((-3.28,3.12,0.15))
    cyl_between('Civ_LThigh',Lhip,Lk,0.105,MAT['civilian_pants'])
    cyl_between('Civ_LShin',Lk,La,0.088,MAT['civilian_pants'])
    cyl_between('Civ_RThigh',Rhip,Rk,0.105,MAT['civilian_pants'])
    cyl_between('Civ_RShin',Rk,Ra,0.088,MAT['civilian_pants'])
    shoe('Civ_LShoe',La+Vector((-0.06,0,0)),MAT['shoe'],math.radians(3))
    shoe('Civ_RShoe',Ra+Vector((0.09,0,0)),MAT['shoe'],math.radians(-4))
    # shoulders and arms: one arm raised in refusal, other pulled back for balance
    Ls=chest+Vector((0,-0.29,0.05)); Rs=chest+Vector((0,0.29,0.05))
    Le=Vector((-3.58,2.70,1.35)); Lh=Vector((-3.30,2.66,1.58))
    Re=Vector((-3.71,3.29,1.18)); Rh=Vector((-3.44,3.30,1.08))
    cyl_between('Civ_LUpperArm',Ls,Le,0.085,MAT['civilian'])
    cyl_between('Civ_LForearm',Le,Lh,0.073,MAT['skin_light'])
    ico('Civ_LHand',Lh,0.09,MAT['skin_light'],scale=(1.15,0.75,0.85),subdivisions=1)
    cyl_between('Civ_RUpperArm',Rs,Re,0.085,MAT['civilian'])
    cyl_between('Civ_RForearm',Re,Rh,0.073,MAT['skin_light'])
    ico('Civ_RHand',Rh,0.09,MAT['skin_light'],scale=(1.15,0.75,0.85),subdivisions=1)
    return {'shoulder_contact':Ls,'head':head}


def hero_police(contact_target):
    hip=Vector((-2.66,2.98,0.97))
    chest=Vector((-2.78,2.98,1.47))
    neck=Vector((-2.82,2.98,1.66))
    head=Vector((-2.84,2.98,1.84))
    # uniform body and visible vest
    box_between('Police_Torso',hip,chest,0.40,0.56,MAT['navy'],0.055)
    box_between('Police_Vest',hip+Vector((-0.06,0,0.10)),chest+Vector((-0.06,0,0.01)),0.30,0.50,MAT['vest'],0.035)
    cube('Police_Badge',(-2.54,2.80,1.49),(0.055,0.10,0.13),MAT['badge'],0.015)
    cyl_between('Police_Neck',neck-Vector((0,0,0.08)),neck+Vector((0,0,0.05)),0.078,MAT['skin'])
    ico('Police_Head',head,0.18,MAT['skin'],scale=(0.90,0.96,1.04),subdivisions=2)
    ico('Police_Hair',head+Vector((0,0,0.075)),0.18,MAT['hair'],scale=(0.94,0.98,0.55),subdivisions=1)
    # cap reads silhouette as police
    cube('Police_CapTop',(-2.84,2.98,2.02),(0.24,0.38,0.09),MAT['navy'],0.035)
    cube('Police_CapBrim',(-2.66,2.98,1.99),(0.22,0.34,0.045),MAT['navy'],0.018)
    # legs show planted force: rear leg extended, front leg loaded
    Lhip=hip+Vector((0,-0.13,-0.02)); Rhip=hip+Vector((0,0.13,-0.02))
    Lk=Vector((-2.42,2.82,0.55)); Rk=Vector((-2.79,3.12,0.54))
    La=Vector((-2.20,2.77,0.15)); Ra=Vector((-2.93,3.12,0.15))
    cyl_between('Police_LThigh',Lhip,Lk,0.11,MAT['navy'])
    cyl_between('Police_LShin',Lk,La,0.092,MAT['navy'])
    cyl_between('Police_RThigh',Rhip,Rk,0.11,MAT['navy'])
    cyl_between('Police_RShin',Rk,Ra,0.092,MAT['navy'])
    shoe('Police_LBoot',La+Vector((0.10,0,0)),MAT['shoe'],math.radians(-2))
    shoe('Police_RBoot',Ra+Vector((-0.04,0,0)),MAT['shoe'],math.radians(3))
    # arms: contact hand is exactly on civilian upper shoulder
    Ls=chest+Vector((-0.02,-0.30,0.04)); Rs=chest+Vector((-0.02,0.30,0.04))
    Le=Vector((-3.15,2.71,1.39)); Lh=Vector(contact_target)
    Re=Vector((-3.05,3.24,1.31)); Rh=Vector((-3.45,3.23,1.25))
    cyl_between('Police_LUpperArm',Ls,Le,0.090,MAT['navy'])
    cyl_between('Police_LForearm',Le,Lh,0.076,MAT['skin'])
    ico('Police_ContactHand',Lh,0.095,MAT['skin'],scale=(1.15,0.78,0.88),subdivisions=1)
    cyl_between('Police_RUpperArm',Rs,Re,0.090,MAT['navy'])
    cyl_between('Police_RForearm',Re,Rh,0.076,MAT['skin'])
    ico('Police_RHand',Rh,0.095,MAT['skin'],scale=(1.12,0.78,0.88),subdivisions=1)
    # belt + radio as small identity details
    cube('Police_Belt',(-2.67,2.98,1.02),(0.10,0.59,0.09),MAT['black'],0.02)
    cube('Police_Radio',(-2.70,3.28,1.34),(0.12,0.09,0.22),MAT['black'],0.02)

civ=hero_civilian()
hero_police(civ['shoulder_contact'])

# reacting bystander, smaller and behind action
# more polished than old sticks but intentionally secondary
hip=Vector((-3.25,5.15,0.92)); chest=Vector((-3.25,5.15,1.38)); head=Vector((-3.25,5.15,1.75))
box_between('Witness_Torso',hip,chest,0.36,0.50,MAT['box_blue'],0.05)
ico('Witness_Head',head,0.165,MAT['skin_light'],subdivisions=1)
ico('Witness_Hair',head+Vector((0,0,0.07)),0.17,MAT['hair'],scale=(0.95,1,0.56),subdivisions=1)
# hands raised slightly in reaction
for side in (-1,1):
    s=chest+Vector((0,0.27*side,0.03)); e=Vector((-3.10,5.15+0.35*side,1.30)); h=Vector((-3.00,5.15+0.42*side,1.42))
    cyl_between('WitnessArm',s,e,0.075,MAT['box_blue']); cyl_between('WitnessForearm',e,h,0.065,MAT['skin_light']); ico('WitnessHand',h,0.075,MAT['skin_light'],subdivisions=1)
for side in (-1,1):
    h=hip+Vector((0,0.10*side,-0.03)); k=Vector((-3.25,5.15+0.11*side,0.52)); a=Vector((-3.25,5.15+0.11*side,0.15))
    cyl_between('WitnessThigh',h,k,0.10,MAT['civilian_pants']); cyl_between('WitnessShin',k,a,0.085,MAT['civilian_pants']); shoe('WitnessShoe',a+Vector((0.06,0,0)),MAT['shoe'])

# -----------------------------------------------------------------------------
# Trees with deliberate placement away from hero contact
# -----------------------------------------------------------------------------
def tree(name,x,y,scale=1.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=0.14*scale,depth=2.2*scale,location=(x,y,1.1*scale))
    tr=bpy.context.object; tr.name=name+'_Trunk'; assign(tr,MAT['tree_trunk'])
    ico(name+'_Crown1',(x,y,2.55*scale),0.72*scale,MAT['leaf1'],scale=(0.95,0.90,1.05),subdivisions=1)
    ico(name+'_Crown2',(x+0.18*scale,y-0.08*scale,2.75*scale),0.54*scale,MAT['leaf2'],scale=(0.95,0.95,0.95),subdivisions=1)

tree('TreeNear',-1.55,6.2,0.95)
tree('TreeFar',-1.55,14.7,0.82)

# -----------------------------------------------------------------------------
# Lighting
# -----------------------------------------------------------------------------
bpy.ops.object.light_add(type='SUN', location=(4,-6,11))
sun=bpy.context.object
sun.name='Sun_Key'
sun.data.energy=2.7
sun.data.angle=math.radians(6.0)
sun.rotation_euler=(math.radians(42),math.radians(-12),math.radians(-38))

bpy.ops.object.light_add(type='AREA', location=(1.2,-0.8,5.1))
fill=bpy.context.object
fill.name='Area_Fill'
fill.data.energy=520
fill.data.shape='DISK'
fill.data.size=4.5
point_camera(fill,(-3.4,3.0,1.4))

# warm storefront interior light
bpy.ops.object.light_add(type='AREA', location=(-5.0,3.0,2.0))
inside=bpy.context.object
inside.name='Store_Interior_Light'
inside.data.energy=280
inside.data.color=(1.0,0.68,0.38)
inside.data.size=2.5
point_camera(inside,(-4.4,3.0,1.3))

# -----------------------------------------------------------------------------
# Camera: human-height 3/4, no top-down model view
# -----------------------------------------------------------------------------
bpy.ops.object.camera_add(location=(1.15,-2.55,1.92))
cam=bpy.context.object
cam.name='Camera_STYLEFRAME'
cam.data.lens=66
cam.data.sensor_width=36
scene.camera=cam
point_camera(cam,(-3.35,3.05,1.24))

# -----------------------------------------------------------------------------
# Render + save
# -----------------------------------------------------------------------------
blend_path=OUT/'OUTBREAK_STYLEFRAME_V1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

# Full requested render
scene.render.resolution_x=1080
scene.render.resolution_y=1920
scene.render.resolution_percentage=100
scene.render.filepath=str(OUT/'STYLEFRAME_1080x1920.png')
bpy.ops.render.render(write_still=True)

# Phone-size gate, rendered from same camera
scene.render.resolution_x=360
scene.render.resolution_y=640
scene.render.filepath=str(OUT/'STYLEFRAME_360x640.png')
bpy.ops.render.render(write_still=True)

report={
    'technical_status':'PASS',
    'visual_status':'UNVERIFIED_UNTIL_IMAGE_INSPECTION',
    'render_engine':'BLENDER_EEVEE',
    'hero_action':'police hand contacts civilian shoulder; civilian braced backward at storefront threshold',
    'camera':'human-height 3/4, 66mm',
    'outputs':['STYLEFRAME_1080x1920.png','STYLEFRAME_360x640.png','OUTBREAK_STYLEFRAME_V1.blend'],
    'asset_source':'Kenney CC0 models via Hidencod/tge-assets mirror',
    'imported_assets':['building-a','building-e','building-j','sedan','police car','taxi','traffic-light','light-curved','blocky characters a-d'],
    'notes':'Hero storefront and two foreground characters are purpose-built for exact staging/contact; background environment uses actual CC0 GLB assets.'
}
(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STYLEFRAME_V1_READY')
print(json.dumps(report,indent=2))
