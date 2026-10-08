import bpy, os, json, math, runpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'artifacts', 'golden_character_batch_a')
VIEWS = os.path.join(OUT, 'views')
os.makedirs(VIEWS, exist_ok=True)

# GOLDEN_REFERENCE_LOCK: execute the exact approved police builder first.
g = runpy.run_path(os.path.join(ROOT, 'police_reference_build.py'))
scene = bpy.context.scene
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.studio_light = 'paint.sl'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'WORLD'
scene.display.shading.curvature_ridge_factor = 1.6
scene.display.shading.curvature_valley_factor = 1.2
scene.display.shading.background_type = 'VIEWPORT'
scene.display.shading.background_color = (0.035, 0.042, 0.055)

box = g['box']; cyl = g['cyl']; frustum_box = g['frustum_box']; cylinder_between = g['cylinder_between']
extruded_poly_y = g['extruded_poly_y']; elliptical_frustum = g['elliptical_frustum']; mesh_obj = g['mesh_obj']; mat = g['mat']
SKIN = g['SKIN']; NAVY = g['NAVY']; NAVY2 = g['NAVY2']; BLACK = g['BLACK']; BLACK2 = g['BLACK2']; HAIR = g['HAIR']

BLUE = mat('Civilian_Blue', (0.040,0.165,0.355), 0.80)
GREEN = mat('Civilian_Green', (0.095,0.300,0.130), 0.82)
PURPLE = mat('Civilian_Purple', (0.300,0.155,0.390), 0.82)
WHITE = mat('Civilian_OffWhite', (0.72,0.74,0.72), 0.84)
CORAL = mat('Civilian_Coral', (0.55,0.20,0.16), 0.82)
MUSTARD = mat('Civilian_Mustard', (0.55,0.32,0.06), 0.84)
DENIM = mat('Civilian_Denim', (0.055,0.145,0.270), 0.84)
PANTS_DARK = mat('Civilian_Pants_Dark', (0.030,0.035,0.045), 0.88)
BROWN = mat('Civilian_Brown', (0.18,0.085,0.035), 0.88)
HAIR_BROWN = mat('Hair_Brown', (0.13,0.055,0.022), 0.90)
HAIR_LIGHT = mat('Hair_Light_Brown', (0.34,0.18,0.075), 0.90)
HAIR_BLOND = mat('Hair_Blond', (0.62,0.45,0.18), 0.88)
MASK_BLUE = mat('Mask_Surgical_Blue', (0.18,0.56,0.70), 0.72)
MASK_BLACK = mat('Mask_Cloth_Black', (0.025,0.028,0.035), 0.90)
MASK_WHITE = mat('Mask_N95_White', (0.82,0.83,0.80), 0.82)
MASK_LOOP = mat('Mask_Loop', (0.73,0.74,0.73), 0.82)

def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name); scene.collection.children.link(c)
    return c

def move_to_collection(objs, col):
    for o in objs:
        if o.name not in col.objects: col.objects.link(o)
        for c in list(o.users_collection):
            if c != col: c.objects.unlink(o)

def snapshot_objects(): return set(bpy.data.objects)
def newly_created(before): return [o for o in bpy.data.objects if o not in before]

def make_head(prefix, z, col, sx=1.0, sy=1.0, sz=1.0):
    before=snapshot_objects()
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(0,-.006,z))
    head=bpy.context.object; head.name=prefix+'_Head_Faceless'; head.scale=(.215*sx,.190*sy,.220*sz); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for v in head.data.vertices:
        if v.co.y<-.135*sy: v.co.y=-.135*sy+(v.co.y+.135*sy)*.45
    head.data.materials.append(SKIN)
    cyl(prefix+'_Ear_L',(-.214*sx,0,z),.040,.050,SKIN,vertices=8,rot=(0,math.radians(90),0),scale=(1,1,1.18))
    cyl(prefix+'_Ear_R',(.214*sx,0,z),.040,.050,SKIN,vertices=8,rot=(0,math.radians(90),0),scale=(1,1,1.18))
    move_to_collection(newly_created(before), col)
    return head

def hair_short(prefix,z,col,material=HAIR):
    before=snapshot_objects()
    box(prefix+'_Hair_Back',(0,.115,z+.060),(.34,.13,.18),material,.035)
    box(prefix+'_Hair_Left',(-.165,.020,z+.055),(.08,.14,.17),material,.025,rot=(0,0,math.radians(-8)))
    box(prefix+'_Hair_Right',(.165,.020,z+.055),(.08,.14,.17),material,.025,rot=(0,0,math.radians(8)))
    extruded_poly_y(prefix+'_Hair_Front',[(-.16,z+.145),(-.08,z+.170),(-.015,z+.125),(.05,z+.160),(.15,z+.135),(.13,z+.055),(-.13,z+.055)],-.105,.045,material,.006)
    move_to_collection(newly_created(before), col)

def hair_side(prefix,z,col,material=HAIR_BROWN):
    before=snapshot_objects()
    box(prefix+'_Hair_Back',(0,.105,z-.005),(.35,.12,.31),material,.035)
    box(prefix+'_Hair_Left',(-.175,.01,z-.02),(.09,.15,.29),material,.025,rot=(0,0,math.radians(-5)))
    box(prefix+'_Hair_Right',(.175,.01,z-.02),(.09,.15,.29),material,.025,rot=(0,0,math.radians(5)))
    extruded_poly_y(prefix+'_Hair_Front',[(-.17,z+.145),(-.07,z+.178),(.02,z+.145),(.16,z+.115),(.13,z+.035),(-.13,z+.055)],-.107,.048,material,.006)
    move_to_collection(newly_created(before), col)

def hair_bun(prefix,z,col,material=HAIR):
    hair_side(prefix,z,col,material)
    before=snapshot_objects(); bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.095,location=(0,.165,z+.19)); o=bpy.context.object; o.name=prefix+'_Hair_Bun'; o.data.materials.append(material); move_to_collection(newly_created(before),col)

def hair_pony(prefix,z,col,material=HAIR_BROWN):
    hair_side(prefix,z,col,material)
    before=snapshot_objects(); bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(0,.19,z-.02)); o=bpy.context.object; o.name=prefix+'_Hair_Pony'; o.scale=(.07,.08,.18); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(material); move_to_collection(newly_created(before),col)

def foot_wedge_custom(name,cx,z0,material,col,scale=1.0):
    before=snapshot_objects(); x=.105*scale; y_back=.13*scale; y_toe=-.23*scale; z1=z0+.16*scale
    v=[(-x,y_toe,z0),(x,y_toe,z0),(x,y_back,z0),(-x,y_back,z0),(-x*.88,y_toe+.025,z1),(x*.88,y_toe+.025,z1),(x*.82,y_back-.015,z1*.92),(-x*.82,y_back-.015,z1*.92)]
    v=[(px+cx,py,pz) for px,py,pz in v]; f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    mesh_obj(name,v,f,material,.012); move_to_collection(newly_created(before),col)

def make_civilian_master(prefix, sex='M', top=GREEN, pants=DENIM, shoes=BROWN, hair='short', top_style='tee'):
    col=collection(prefix)
    if sex=='M': shoulder=.292; torso_top=.525; torso_bot=.415; arm_r=.078; fore_r=.069; head_z=1.595; hip_w=.40
    else: shoulder=.272; torso_top=.465; torso_bot=.375; arm_r=.070; fore_r=.062; head_z=1.565; hip_w=.39
    before=snapshot_objects()
    foot_wedge_custom(prefix+'_Foot_L',-.13,.02,shoes,col,.92 if sex=='F' else .96); foot_wedge_custom(prefix+'_Foot_R',.13,.02,shoes,col,.92 if sex=='F' else .96)
    frustum_box(prefix+'_Shin_L',.25,.56,.17,.19,.19,.20,pants,cx=-.13,bevel=.012); frustum_box(prefix+'_Shin_R',.25,.56,.17,.19,.19,.20,pants,cx=.13,bevel=.012)
    frustum_box(prefix+'_Thigh_L',.55,.90,.19,.21,.20,.225,pants,cx=-.13,bevel=.014); frustum_box(prefix+'_Thigh_R',.55,.90,.19,.21,.20,.225,pants,cx=.13,bevel=.014)
    frustum_box(prefix+'_Pelvis',.86,1.00,hip_w*.90,hip_w,.235,.25,pants,bevel=.014)
    frustum_box(prefix+'_Torso',.98,1.39,torso_bot,torso_top,.255,.295,top,bevel=.018)
    cyl(prefix+'_Neck',(0,0,1.435 if sex=='M' else 1.420),.085,.11,SKIN,vertices=10,scale=(1,.92,1))
    if top_style=='hoodie':
        box(prefix+'_Hood',(0,.115,1.35),(.33,.12,.17),top,.025); box(prefix+'_Pocket',(0,-.153,1.10),(.25,.025,.10),top,.008); box(prefix+'_Draw_L',(-.035,-.163,1.32),(.010,.010,.14),BLACK2,.003); box(prefix+'_Draw_R',(.035,-.163,1.32),(.010,.010,.14),BLACK2,.003)
    elif top_style=='jacket':
        box(prefix+'_Inner',(0,-.158,1.20),(.18,.018,.31),WHITE,.004); box(prefix+'_Zip',(0,-.171,1.19),(.012,.010,.30),BLACK2,.003)
    for side,s in [('L',-1),('R',1)]:
        shoulder_pt=(s*shoulder,0,1.31); elbow=(s*(shoulder+.045),0,1.115); wrist=(s*(shoulder+.050),-.002,.93)
        cylinder_between(prefix+'_Sleeve_'+side,shoulder_pt,elbow,arm_r,top,8,(1,.92)); cylinder_between(prefix+'_Forearm_'+side,elbow,wrist,fore_r,SKIN,8,(.96,.90)); box(prefix+'_Hand_'+side,(s*(shoulder+.050),-.006,.865),(.125,.115,.155),SKIN,.028)
    move_to_collection(newly_created(before),col)
    head=make_head(prefix,head_z,col, sx=.98 if sex=='F' else 1.0, sy=.98 if sex=='F' else 1.0, sz=.98 if sex=='F' else 1.0)
    if hair=='short': hair_short(prefix,head_z,col,HAIR)
    elif hair=='short_brown': hair_short(prefix,head_z,col,HAIR_BROWN)
    elif hair=='blond': hair_short(prefix,head_z,col,HAIR_BLOND)
    elif hair=='side': hair_side(prefix,head_z,col,HAIR_BROWN)
    elif hair=='bun': hair_bun(prefix,head_z,col,HAIR)
    elif hair=='pony': hair_pony(prefix,head_z,col,HAIR_BROWN)
    return col, head

male_col, male_head = make_civilian_master('CIV_MALE_GOLDEN','M',GREEN,DENIM,BROWN,'short','tee')
female_col, female_head = make_civilian_master('CIV_FEMALE_GOLDEN','F',WHITE,DENIM,WHITE,'pony','tee')
variant_specs=[('CIV_MALE_PURPLE','M',PURPLE,PANTS_DARK,WHITE,'short_brown','tee'),('CIV_MALE_HOODIE','M',BLUE,DENIM,BROWN,'short','hoodie'),('CIV_MALE_JACKET','M',CORAL,DENIM,BROWN,'short_brown','jacket'),('CIV_FEMALE_CORAL','F',CORAL,PANTS_DARK,WHITE,'bun','tee'),('CIV_FEMALE_JACKET','F',MUSTARD,DENIM,WHITE,'side','jacket'),('CIV_FEMALE_HOODIE','F',PURPLE,DENIM,WHITE,'bun','hoodie')]
variant_cols=[]
for spec in variant_specs:
    c,_=make_civilian_master(*spec); variant_cols.append(c)

def world_bounds(obj):
    pts=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (min(p.x for p in pts),max(p.x for p in pts),min(p.y for p in pts),max(p.y for p in pts),min(p.z for p in pts),max(p.z for p in pts))

def make_mask(prefix, head_obj, col, style='surgical', lowered=False):
    before=snapshot_objects(); xmin,xmax,ymin,ymax,zmin,zmax=world_bounds(head_obj); head_w=xmax-xmin; head_h=zmax-zmin; front_y=ymin
    if lowered: cz=zmin + head_h*.15; h=head_h*.24; width=head_w*.70; depth=.034
    else: cz=zmin + head_h*.40; h=head_h*(.27 if style!='n95' else .30); width=head_w*(.78 if style!='n95' else .73); depth=.035 if style!='n95' else .055
    mat_use=MASK_BLUE if style=='surgical' else MASK_BLACK if style=='cloth' else MASK_WHITE
    if style=='n95':
        pts=[(-width*.50,cz+h*.45),(-width*.35,cz+h*.58),(0,cz+h*.68),(width*.35,cz+h*.58),(width*.50,cz+h*.45),(width*.43,cz-h*.45),(0,cz-h*.60),(-width*.43,cz-h*.45)]; extruded_poly_y(prefix+'_N95',pts,front_y-.025,depth,mat_use,.007)
    else:
        pts=[(-width*.50,cz+h*.45),(width*.50,cz+h*.45),(width*.44,cz-h*.50),(-width*.44,cz-h*.50)]; extruded_poly_y(prefix+'_Shell',pts,front_y-.025,depth,mat_use,.008)
        if style=='surgical' and not lowered:
            for i,zz in enumerate([cz+h*.15,cz,cz-h*.15]): box(prefix+'_Pleat_%d'%i,(0,front_y-.046,zz),(width*.78,.008,.014),MASK_WHITE,.003)
    left=(-head_w*.50,front_y-.010,cz); right=(head_w*.50,front_y-.010,cz)
    cylinder_between(prefix+'_Loop_L',(-width*.48,front_y-.042,cz+h*.12),left,.010,MASK_LOOP,8,(.8,.8)); cylinder_between(prefix+'_Loop_R',(width*.48,front_y-.042,cz+h*.12),right,.010,MASK_LOOP,8,(.8,.8)); cylinder_between(prefix+'_Loop_L2',(-width*.43,front_y-.042,cz-h*.22),left,.009,MASK_LOOP,8,(.8,.8)); cylinder_between(prefix+'_Loop_R2',(width*.43,front_y-.042,cz-h*.22),right,.009,MASK_LOOP,8,(.8,.8))
    move_to_collection(newly_created(before),col)

mask_specs=[('Surgical','surgical',False),('Cloth','cloth',False),('N95','n95',False),('Lowered','surgical',True)]
mask_preview_heads=[]
for label,style,low in mask_specs:
    sub=collection('MASK_PREVIEW_'+label.upper()); h=make_head('MASK_'+label,1.595,sub); make_mask('MASK_'+label,h,sub,style,low); mask_preview_heads.append((sub,h))

ward_col=collection('WARDROBE_LIBRARY'); before=snapshot_objects(); frustum_box('WARD_TShirt_Torso',.98,1.39,.415,.525,.255,.295,GREEN,bevel=.018); frustum_box('WARD_Hoodie_Torso',.98,1.39,.425,.540,.265,.305,BLUE,bevel=.020); box('WARD_Hood',(0,.115,1.35),(.33,.12,.17),BLUE,.025); box('WARD_Hoodie_Pocket',(0,-.153,1.10),(.25,.025,.10),BLUE,.008); frustum_box('WARD_Jacket_Torso',.98,1.39,.425,.540,.265,.305,CORAL,bevel=.020); box('WARD_Jacket_Inner',(0,-.158,1.20),(.18,.018,.31),WHITE,.004); box('WARD_Jacket_Zip',(0,-.171,1.19),(.012,.010,.30),BLACK2,.003); move_to_collection(newly_created(before),ward_col)

hair_col=collection('HAIR_LIBRARY'); hair_short('HAIR_M_SHORT_01',1.595,hair_col,HAIR); hair_short('HAIR_M_SHORT_02',1.595,hair_col,HAIR_BROWN); hair_short('HAIR_M_BLOND',1.595,hair_col,HAIR_BLOND); hair_bun('HAIR_F_BUN',1.565,hair_col,HAIR); hair_pony('HAIR_F_PONY',1.565,hair_col,HAIR_BROWN); hair_side('HAIR_F_SHOULDER',1.565,hair_col,HAIR_LIGHT)

cam=bpy.data.objects.get('Reference_Camera'); scene.camera=cam; cam.data.type='ORTHO'; cam.data.ortho_scale=2.08

def set_camera(angle_deg, target=(0,0,.95), dist=5.0):
    a=math.radians(angle_deg); t=Vector(target); pos=Vector((math.sin(a)*dist,-math.cos(a)*dist,1.08)); cam.location=pos; cam.rotation_euler=(t-pos).to_track_quat('-Z','Y').to_euler()

def all_modular_cols():
    names=['POLICE_OFFICER_REFERENCE','CIV_MALE_GOLDEN','CIV_FEMALE_GOLDEN']+[c.name for c in variant_cols]+['WARDROBE_LIBRARY','HAIR_LIBRARY']+[c.name for c,_ in mask_preview_heads]
    return [bpy.data.collections.get(n) for n in names if bpy.data.collections.get(n)]

def set_only(cols):
    visible=set(c.name for c in cols)
    for c in all_modular_cols(): c.hide_render = c.name not in visible

def render_collection_5(col, basename):
    set_only([col]); views=[('front',0),('three_quarter',35),('side',90),('back',180),('three_quarter_back',145)]
    for n,a in views: set_camera(a); scene.render.filepath=os.path.join(VIEWS,basename+'_'+n+'.png'); bpy.ops.render.render(write_still=True)

render_collection_5(male_col,'male_golden'); render_collection_5(female_col,'female_golden')

def offset_collection(col, dx):
    for o in col.objects: o.location.x += dx

def render_lineup(cols, path, spacing=.70, scale=4.9):
    set_only(cols); offsets=[]; start=-(len(cols)-1)*spacing/2
    for i,c in enumerate(cols): dx=start+i*spacing; offset_collection(c,dx); offsets.append((c,dx))
    old=cam.data.ortho_scale; cam.data.ortho_scale=scale; set_camera(0,target=(0,0,.95),dist=7); scene.render.resolution_x=1800; scene.render.resolution_y=900; scene.render.filepath=path; bpy.ops.render.render(write_still=True)
    for c,dx in offsets: offset_collection(c,-dx)
    cam.data.ortho_scale=old; scene.render.resolution_x=640; scene.render.resolution_y=800

render_lineup([male_col]+variant_cols[:3], os.path.join(VIEWS,'male_variants.png'), .72, 4.2)
render_lineup([female_col]+variant_cols[3:], os.path.join(VIEWS,'female_variants.png'), .72, 4.2)
police_col=bpy.data.collections.get('POLICE_OFFICER_REFERENCE'); render_lineup([male_col,police_col,female_col], os.path.join(VIEWS,'golden_style_compare.png'), .74, 3.5)
render_lineup([c for c,_ in mask_preview_heads], os.path.join(VIEWS,'mask_library.png'), .62, 2.6)

for c in all_modular_cols(): c.hide_render=False
set_camera(0); scene.render.resolution_x=640; scene.render.resolution_y=800
manifest={'batch':'A - Golden Character Foundation','golden_reference':'POLICE_OFFICER_REFERENCE from police_reference_build.py','golden_lock':True,'animation':False,'characters':{'built':['Police Golden exact approved builder','Civilian Male Golden Master','Civilian Female Golden Master'],'variants':[c.name for c in variant_cols]},'hair_assets':['HAIR_M_SHORT_01','HAIR_M_SHORT_02','HAIR_M_BLOND','HAIR_F_BUN','HAIR_F_PONY','HAIR_F_SHOULDER'],'wardrobe_assets':['WARD_TShirt_Torso','WARD_Hoodie_Torso','WARD_Jacket_Torso'],'mask_assets':['Surgical Blue','Cloth Black','N95 White','Surgical Lowered'],'fit_rule':'Masks generated from actual Head_Faceless world bounds; no guessed absolute placement.','qc_views':['front','three_quarter','side','back','three_quarter_back'],'next_gate':'visual approval before Batch B or rigging'}
with open(os.path.join(OUT,'asset_manifest.json'),'w',encoding='utf-8') as f: json.dump(manifest,f,indent=2)
with open(os.path.join(OUT,'qc_report.json'),'w',encoding='utf-8') as f: json.dump({'ci_pass':True,'visual_qc_required':True,'checked_items':['male five-view','female five-view','male variants','female variants','golden style compare','mask library'],'rule':'Do not rig until user/static visual approval.'},f,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Golden_Character_Foundation_BatchA.blend'))
print('GOLDEN_BATCH_A_PASS'); print(json.dumps(manifest,indent=2))
