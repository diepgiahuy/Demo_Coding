import bpy, os, json, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(ROOT, 'artifacts', 'police_reference')
VIEWS = os.path.join(ART, 'views')
os.makedirs(VIEWS, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.studio_light = 'paint.sl'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'WORLD'
scene.display.shading.curvature_ridge_factor = 1.6
scene.display.shading.curvature_valley_factor = 1.2
scene.display.shading.show_specular_highlight = True
scene.display.shading.background_type = 'VIEWPORT'
scene.display.shading.background_color = (0.035, 0.042, 0.055)
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.fps = 60

def mat(name, color, rough=0.72, metal=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.roughness = rough
    m.metallic = metal
    return m

SKIN = mat('Skin_Warm_Beige', (0.78, 0.50, 0.30), 0.82)
NAVY = mat('Police_Navy', (0.028, 0.060, 0.145), 0.78)
NAVY2 = mat('Police_Navy_Trim', (0.018, 0.040, 0.095), 0.80)
VEST = mat('Vest_Black_Navy', (0.020, 0.023, 0.032), 0.88)
BLACK = mat('Boot_Belt_Charcoal', (0.028, 0.029, 0.034), 0.86)
BLACK2 = mat('Accessory_Charcoal', (0.040, 0.043, 0.050), 0.80)
HAIR = mat('Hair_Dark_Brown', (0.060, 0.030, 0.020), 0.90)
GOLD = mat('Badge_Gold', (0.90, 0.58, 0.10), 0.38, 0.12)
GRAY = mat('Radio_Grille', (0.16, 0.17, 0.19), 0.72)

created = []
def register(o): created.append(o); return o

def apply_bevel(o, width=0.012, segments=2):
    if width <= 0: return
    mod = o.modifiers.new('Edge_Soften', 'BEVEL')
    mod.width = width; mod.segments = segments; mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(20)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    try: bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception: pass
    o.select_set(False)

def mesh_obj(name, verts, faces, material, bevel=0.0):
    me = bpy.data.meshes.new(name + '_Mesh'); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.data.materials.append(material)
    apply_bevel(o, bevel, 2); return register(o)

def frustum_box(name, z0, z1, w0, w1, d0, d1, material, cx=0, cy=0, bevel=0.01):
    v=[(cx-w0/2,cy-d0/2,z0),(cx+w0/2,cy-d0/2,z0),(cx+w0/2,cy+d0/2,z0),(cx-w0/2,cy+d0/2,z0),
       (cx-w1/2,cy-d1/2,z1),(cx+w1/2,cy-d1/2,z1),(cx+w1/2,cy+d1/2,z1),(cx-w1/2,cy+d1/2,z1)]
    f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return mesh_obj(name,v,f,material,bevel)

def box(name, loc, dims, material, bevel=0.01, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material); apply_bevel(o,bevel,2); return register(o)

def cyl(name, loc, radius, depth, material, vertices=10, rot=(0,0,0), scale=(1,1,1)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.scale=scale; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material); return register(o)

def cylinder_between(name,a,b,r,material,vertices=8,scale_xy=(1.0,1.0)):
    a,b=Vector(a),Vector(b); mid=(a+b)/2; vec=b-a
    o=cyl(name,mid,r,vec.length,material,vertices); o.rotation_euler=vec.to_track_quat('Z','Y').to_euler(); o.scale.x=scale_xy[0]; o.scale.y=scale_xy[1]
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.select_set(False); return o

def extruded_poly_y(name, points_xz, y_center, depth, material, bevel=0.004):
    n=len(points_xz); yf=y_center-depth/2; yb=y_center+depth/2
    verts=[(x,yf,z) for x,z in points_xz]+[(x,yb,z) for x,z in points_xz]
    faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
    for i in range(n):
        j=(i+1)%n; faces.append((i,j,n+j,n+i))
    return mesh_obj(name,verts,faces,material,bevel)

def elliptical_frustum(name,z0,z1,rx0,ry0,rx1,ry1,material,n=12,cx=0,cy=0):
    verts=[]
    for z,rx,ry in [(z0,rx0,ry0),(z1,rx1,ry1)]:
        for i in range(n):
            a=2*math.pi*i/n; verts.append((cx+rx*math.cos(a),cy+ry*math.sin(a),z))
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    for i in range(n):
        j=(i+1)%n; faces.append((i,j,n+j,n+i))
    return mesh_obj(name,verts,faces,material,0.004)

def foot_wedge(name,cx,z0,material):
    x=.105; y_back=.13; y_toe=-.23; z1=z0+.16
    v=[(-x,y_toe,z0),(x,y_toe,z0),(x,y_back,z0),(-x,y_back,z0),(-x*.88,y_toe+.025,z1),(x*.88,y_toe+.025,z1),(x*.82,y_back-.015,z1*.92),(-x*.82,y_back-.015,z1*.92)]
    v=[(px+cx,py,pz) for px,py,pz in v]; f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return mesh_obj(name,v,f,material,.012)

foot_wedge('Boot_L',-.13,.02,BLACK); foot_wedge('Boot_R',.13,.02,BLACK)
box('Boot_Cuff_L',(-.13,.015,.215),(.18,.20,.14),BLACK,.012); box('Boot_Cuff_R',(.13,.015,.215),(.18,.20,.14),BLACK,.012)
frustum_box('Pant_Shin_L',.25,.56,.18,.195,.20,.21,NAVY,cx=-.13,bevel=.012); frustum_box('Pant_Shin_R',.25,.56,.18,.195,.20,.21,NAVY,cx=.13,bevel=.012)
frustum_box('Pant_Thigh_L',.55,.90,.195,.22,.21,.235,NAVY,cx=-.13,bevel=.014); frustum_box('Pant_Thigh_R',.55,.90,.195,.22,.21,.235,NAVY,cx=.13,bevel=.014)
frustum_box('Police_Pelvis',.86,1.00,.40,.45,.25,.27,NAVY,bevel=.014)
box('Cargo_L',(-.235,-.108,.69),(.105,.035,.16),NAVY2,.009); box('Cargo_R',(.235,-.108,.69),(.105,.035,.16),NAVY2,.009)
box('Knee_L',(-.13,-.102,.54),(.155,.025,.07),NAVY2,.007); box('Knee_R',(.13,-.102,.54),(.155,.025,.07),NAVY2,.007)
frustum_box('Police_Shirt_Torso',.98,1.39,.44,.56,.27,.31,NAVY,bevel=.018)
cyl('Neck',(0,0,1.435),.09,.11,SKIN,vertices=10,scale=(1,.92,1))
extruded_poly_y('Collar_L',[(-.13,1.405),(-.015,1.405),(-.04,1.31),(-.17,1.36)],-.157,.018,NAVY2,.003)
extruded_poly_y('Collar_R',[(.015,1.405),(.13,1.405),(.17,1.36),(.04,1.31)],-.157,.018,NAVY2,.003)
extruded_poly_y('Collar_Skin_V',[(-.035,1.405),(.035,1.405),(0,1.34)],-.168,.012,SKIN,.002)
for side,s in [('L',-1),('R',1)]:
    shoulder=(s*.305,0,1.31); elbow=(s*.35,0,1.115); wrist=(s*.36,-.002,.93)
    cylinder_between('Sleeve_'+side,shoulder,elbow,.086,NAVY,8,(1,.92)); cylinder_between('Sleeve_Cuff_'+side,(s*.329,0,1.15),(s*.339,0,1.105),.088,NAVY2,8,(1,.92)); cylinder_between('Forearm_'+side,elbow,wrist,.078,SKIN,8,(.96,.90)); box('Hand_'+side,(s*.355,-.006,.865),(.13,.12,.16),SKIN,.028)

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(0,-.006,1.595))
head=bpy.context.object; head.name='Head_Faceless'; head.scale=(.215,.190,.220); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for v in head.data.vertices:
    if v.co.y<-.135: v.co.y=-.135+(v.co.y+.135)*.45
head.data.materials.append(SKIN); register(head)
cyl('Ear_L',(-.214,0,1.595),.040,.050,SKIN,vertices=8,rot=(0,math.radians(90),0),scale=(1,1,1.18)); cyl('Ear_R',(.214,0,1.595),.040,.050,SKIN,vertices=8,rot=(0,math.radians(90),0),scale=(1,1,1.18))
box('Hair_Back',(0,.115,1.655),(.34,.13,.18),HAIR,.035); box('Hair_Left',(-.165,.020,1.65),(.08,.14,.17),HAIR,.025,rot=(0,0,math.radians(-8))); box('Hair_Right',(.165,.020,1.65),(.08,.14,.17),HAIR,.025,rot=(0,0,math.radians(8)))
extruded_poly_y('Hair_Front',[(-.16,1.74),(-.08,1.765),(-.015,1.72),(.05,1.755),(.15,1.73),(.13,1.65),(-.13,1.65)],-.105,.045,HAIR,.006)
elliptical_frustum('Police_Cap_Crown',1.70,1.825,.215,.172,.235,.182,NAVY,12); elliptical_frustum('Police_Cap_Band',1.675,1.725,.216,.173,.218,.175,NAVY2,12)
brim_pts=[(-.195,-.145,1.705),(.195,-.145,1.705),(.155,-.305,1.680),(-.155,-.305,1.680),(-.195,-.145,1.680),(.195,-.145,1.680),(.155,-.305,1.657),(-.155,-.305,1.657)]
brim_faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]; mesh_obj('Police_Cap_Brim',brim_pts,brim_faces,NAVY2,.006)
shield=[(-.045,1.775),(-.032,1.805),(0,1.823),(.032,1.805),(.045,1.775),(.030,1.738),(0,1.720),(-.030,1.738)]; extruded_poly_y('Cap_Badge',shield,-.182,.018,GOLD,.003)
extruded_poly_y('Vest_Front_L',[(-.205,1.34),(-.025,1.34),(-.025,1.02),(-.225,1.02)],-.171,.068,VEST,.012); extruded_poly_y('Vest_Front_R',[(.025,1.34),(.205,1.34),(.225,1.02),(.025,1.02)],-.171,.068,VEST,.012); extruded_poly_y('Vest_Back',[(-.205,1.34),(.205,1.34),(.225,1.02),(-.225,1.02)],.171,.060,VEST,.012)
box('Vest_Strap_L',(-.17,0,1.36),(.075,.34,.055),VEST,.009); box('Vest_Strap_R',(.17,0,1.36),(.075,.34,.055),VEST,.009)
for x in (-.13,0,.13):
    box('Vest_Pouch_%+.2f'%x,(x,-.218,1.065),(.10,.050,.09),BLACK2,.010); box('Vest_Pouch_Flap_%+.2f'%x,(x,-.254,1.085),(.11,.014,.045),VEST,.006)
shield2=[(.075,1.30),(.09,1.325),(.12,1.34),(.15,1.325),(.165,1.30),(.152,1.255),(.12,1.235),(.088,1.255)]; extruded_poly_y('Chest_Badge',shield2,-.218,.014,GOLD,.0025)
box('Radio',(-.145,-.225,1.285),(.085,.050,.135),BLACK2,.009)
for i,z in enumerate((1.305,1.285,1.265)): box('Radio_Grille_%d'%i,(-.145,-.253,z),(.054,.008,.009),GRAY,.002)
cyl('Radio_Antenna',(-.175,-.222,1.395),.012,.13,BLACK2,vertices=8); box('Vest_Clip_L',(-.166,-.195,1.405),(.055,.030,.055),BLACK2,.006); box('Vest_Clip_R',(.166,-.195,1.405),(.055,.030,.055),BLACK2,.006)
box('Duty_Belt_Front',(0,-.145,.955),(.47,.055,.075),BLACK,.010); box('Duty_Belt_Back',(0,.145,.955),(.47,.055,.075),BLACK,.010); box('Duty_Belt_Left',(-.235,0,.955),(.055,.27,.075),BLACK,.009); box('Duty_Belt_Right',(.235,0,.955),(.055,.27,.075),BLACK,.009); box('Belt_Buckle',(0,-.178,.955),(.095,.028,.070),GRAY,.007)
box('Belt_Pouch_L',(-.185,-.183,.965),(.085,.07,.105),BLACK2,.010); box('Belt_Pouch_R',(.185,-.183,.965),(.085,.07,.105),BLACK2,.010); box('Holster_R',(.285,-.025,.88),(.085,.11,.22),BLACK2,.012); box('Back_Pouch_L',(-.15,.182,.955),(.10,.065,.115),BLACK2,.010); box('Back_Pouch_R',(.15,.182,.955),(.10,.065,.115),BLACK2,.010)

bpy.ops.mesh.primitive_plane_add(size=8,location=(0,0,.015)); floor=bpy.context.object; floor.name='Studio_Floor'; floor.data.materials.append(mat('Floor_Mat',(.025,.028,.035),.95)); register(floor)
char_col=bpy.data.collections.new('POLICE_OFFICER_REFERENCE'); scene.collection.children.link(char_col)
for o in list(created):
    if o is floor: continue
    if o.name not in char_col.objects: char_col.objects.link(o)
    for c in list(o.users_collection):
        if c!=char_col: c.objects.unlink(o)

cam_data=bpy.data.cameras.new('Reference_Camera'); cam_data.type='ORTHO'; cam_data.ortho_scale=2.08
cam=bpy.data.objects.new('Reference_Camera',cam_data); scene.collection.objects.link(cam); scene.camera=cam

def set_camera(angle_deg,dist=5.0):
    a=math.radians(angle_deg); target=Vector((0,0,.95)); pos=Vector((math.sin(a)*dist,-math.cos(a)*dist,1.08)); cam.location=pos; cam.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()

views=[('front',0),('three_quarter',35),('side',90),('back',180),('three_quarter_back',145)]
for name,ang in views:
    set_camera(ang); scene.render.filepath=os.path.join(VIEWS,name+'.png'); bpy.ops.render.render(write_still=True)
set_camera(0)
report={'reference_target':'single canonical stylized low-poly patrol police sheet generated in-chat','build':'from-scratch master mesh; no Hoodie/Punk final geometry','style':'faceted low-poly, faceless, navy shirt/pants, black vest/belt/boots, gold badges','views':[v[0] for v in views],'mesh_object_count':sum(1 for o in created if o.type=='MESH'),'material_count':len(bpy.data.materials),'overall_height_m':1.83,'parts':['faceless head','dark hair','police cap + cap badge','police shirt + collar','short sleeves','bare forearms + hands','black vest front/back + shoulder straps','chest badge','radio + antenna','duty belt + buckle + pouches + holster','navy cargo pants','black boots'],'rigged':False,'animation':False,'purpose':'visual shape approval before rigging'}
with open(os.path.join(ART,'qc_report.json'),'w',encoding='utf-8') as f: json.dump(report,f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Officer_Reference.blend'))
print('POLICE_REFERENCE_BUILD_PASS'); print(json.dumps(report,indent=2))
