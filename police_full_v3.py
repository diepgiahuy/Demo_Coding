import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_full','hoodie_character.glb')
ART=os.path.join(ROOT,'artifacts','police_full_v3')
FRAMES=os.path.join(ART,'frames'); os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)
def import_glb(p):
    bo=set(bpy.data.objects);ba=set(bpy.data.actions);bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]
def find_arm(objs):
    a=[o for o in objs if o.type=='ARMATURE']
    if not a:raise RuntimeError('No armature')
    return max(a,key=lambda o:len(o.data.bones))
def find_walk(actions):
    a=[x for x in actions if 'walk' in x.name.lower()]
    if not a:raise RuntimeError('No walk')
    e=[x for x in a if x.name.lower().endswith('|walk')];return e[0] if e else a[0]
def bone(arm,cands,tokens=()):
    d={b.name:b for b in arm.data.bones}
    for n in cands:
        if n in d:return d[n]
    for t in tokens:
        m=[b for b in arm.data.bones if t.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    return None
def wp(arm,b,tail=False):return arm.matrix_world@(b.tail_local if tail else b.head_local)
def mkmat(name,c,rough=.78,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.roughness=rough;m.metallic=metal;return m
def box(name,loc,dims,mat,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel>0:
        md=o.modifiers.new('EdgeSoft','BEVEL');md.width=bevel;md.segments=1;md.limit_method='ANGLE'
    return o
def ico(name,loc,scale,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);return o
def cyl(name,loc,r,depth,mat,verts=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o

def rigid_skin(o,arm,b):
    # Bake current world geometry into armature-object space, then give every vertex weight 1 to exactly one bone.
    bpy.context.view_layer.update();rel=arm.matrix_world.inverted()@o.matrix_world;o.data.transform(rel);o.matrix_world=arm.matrix_world.copy()
    vg=o.vertex_groups.new(name=b.name);vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
    md=o.modifiers.new('RigidArmature','ARMATURE');md.object=arm;md.use_vertex_groups=True

def segment(name,arm,b,p0,p1,width,depth,mat,f0=0,f1=1,bevel=.003):
    a=p0.lerp(p1,f0);z=p0.lerp(p1,f1);v=z-a;L=max(v.length,.001);o=box(name,(a+z)*.5,(width,depth,L),mat,bevel);o.rotation_euler=v.to_track_quat('Z','Y').to_euler();rigid_skin(o,arm,b);return o

def build(arm,char_h):
    skin=mkmat('Skin',(0.78,0.48,0.27),.88);hair=mkmat('Hair',(0.045,0.030,0.022),.94);navy=mkmat('PoliceNavy',(0.025,0.070,0.155),.84);navy2=mkmat('PoliceNavyDark',(0.015,0.040,0.095),.88);black=mkmat('GearBlack',(0.015,0.020,0.028),.90);gold=mkmat('BadgeGold',(0.96,0.62,0.10),.52,.10)
    req={'Hips':(['Hips','Pelvis'],('hips','pelvis')),'Torso':(['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest')),'Neck':(['Neck','Neck1'],('neck',)),'Head':(['Head'],('head',)),'UAL':(['UpperArmL','UpperArm.L'],('upperarml','upperarm.l')),'UAR':(['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r')),'LAL':(['LowerArmL','LowerArm.L'],('lowerarml','lowerarm.l')),'LAR':(['LowerArmR','LowerArm.R'],('lowerarmr','lowerarm.r')),'WL':(['WristL','HandL','Wrist.L','Hand.L'],('wristl','wrist.l','handl','hand.l')),'WR':(['WristR','HandR','Wrist.R','Hand.R'],('wristr','wrist.r','handr','hand.r')),'ULL':(['UpperLegL','UpperLeg.L'],('upperlegl','upperleg.l','thigh.l')),'ULR':(['UpperLegR','UpperLeg.R'],('upperlegr','upperleg.r','thigh.r')),'LLL':(['LowerLegL','LowerLeg.L'],('lowerlegl','lowerleg.l','calf.l')),'LLR':(['LowerLegR','LowerLeg.R'],('lowerlegr','lowerleg.r','calf.r')),'FL':(['FootL','Foot.L'],('footl','foot.l')),'FR':(['FootR','Foot.R'],('footr','foot.r'))}
    B={k:bone(arm,*v) for k,v in req.items()};miss=[k for k,v in B.items() if not v]
    if miss:raise RuntimeError('Missing bones '+str(miss))
    pieces=[];shL=wp(arm,B['UAL']);shR=wp(arm,B['UAR']);shoulder=abs(shL.x-shR.x);hips=wp(arm,B['Hips']);neck=wp(arm,B['Neck']);torso_w=shoulder*.72;torso_h=max((neck-hips).length*.72,char_h*.27);torso_d=torso_w*.42;tc=Vector(((shL.x+shR.x)/2,(shL.y+shR.y)/2,(hips.z+neck.z)/2+char_h*.015))
    o=box('Police_Shirt_Torso',tc,(torso_w,torso_d,torso_h),navy,max(char_h*.005,.004));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    o=box('Police_Pants_Waist',hips+Vector((0,0,-char_h*.035)),(torso_w*.72,torso_d*.88,char_h*.12),navy2,max(char_h*.004,.003));rigid_skin(o,arm,B['Hips']);pieces.append(o)
    h0,h1=wp(arm,B['Head']),wp(arm,B['Head'],True);hc=(h0+h1)*.5+Vector((0,0,char_h*.015));head_w=torso_w*.58;head_h=head_w*.98;head_d=head_w*.88
    o=ico('Police_Head',hc,(head_w*.5,head_d*.5,head_h*.5),skin);rigid_skin(o,arm,B['Head']);pieces.append(o)
    for n,off,dims in [('Hair_Top',(0,0,head_h*.34),(head_w*.86,head_d*.82,head_h*.24)),('Hair_Back',(0,head_d*.34,head_h*.08),(head_w*.82,head_d*.18,head_h*.55)),('Hair_Fringe',(-head_w*.15,-head_d*.34,head_h*.20),(head_w*.48,head_d*.16,head_h*.22))]:
        o=box(n,hc+Vector(off),dims,hair,max(char_h*.003,.002));rigid_skin(o,arm,B['Head']);pieces.append(o)
    for side,U,L,W in [('L',B['UAL'],B['LAL'],B['WL']),('R',B['UAR'],B['LAR'],B['WR'])]:
        u0,u1=wp(arm,U),wp(arm,U,True);pieces.append(segment('Sleeve_'+side,arm,U,u0,u1,char_h*.060,char_h*.054,navy,0,.38));pieces.append(segment('UpperArmSkin_'+side,arm,U,u0,u1,char_h*.050,char_h*.046,skin,.32,1.02));l0,l1=wp(arm,L),wp(arm,L,True);pieces.append(segment('Forearm_'+side,arm,L,l0,l1,char_h*.048,char_h*.043,skin,-.02,1.02));wc=wp(arm,W);o=box('Hand_'+side,wc,(char_h*.052,char_h*.045,char_h*.072),skin,max(char_h*.003,.002));rigid_skin(o,arm,W);pieces.append(o)
    for side,U,L,F in [('L',B['ULL'],B['LLL'],B['FL']),('R',B['ULR'],B['LLR'],B['FR'])]:
        u0,u1=wp(arm,U),wp(arm,U,True);pieces.append(segment('Thigh_'+side,arm,U,u0,u1,char_h*.080,char_h*.068,navy2,-.03,1.03));l0,l1=wp(arm,L),wp(arm,L,True);pieces.append(segment('Calf_'+side,arm,L,l0,l1,char_h*.068,char_h*.058,navy2,-.04,1.04));f0,f1=wp(arm,F),wp(arm,F,True);fc=(f0+f1)*.5+Vector((0,-char_h*.035,-char_h*.010));o=box('Boot_'+side,fc,(char_h*.088,char_h*.150,char_h*.062),black,max(char_h*.004,.003));rigid_skin(o,arm,F);pieces.append(o)
    # Vest
    fy=tc.y-torso_d*.55;by=tc.y+torso_d*.55;vh=torso_h*.70;vw=torso_w*.86;vz=tc.z+torso_h*.03;gap=vw*.05
    for s,l in [(-1,'L'),(1,'R')]:
        x=tc.x+s*(vw*.25+gap*.25);o=box('VestFront_'+l,Vector((x,fy-char_h*.010,vz)),(vw*.47,char_h*.032,vh),black,max(char_h*.004,.003));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    o=box('VestBack',Vector((tc.x,by+char_h*.010,vz)),(vw,char_h*.032,vh),black,max(char_h*.004,.003));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    for s,l in [(-1,'L'),(1,'R')]:
        o=box('VestStrap_'+l,Vector((tc.x+s*vw*.31,tc.y,tc.z+vh*.50)),(vw*.15,torso_d*1.05,char_h*.038),black,max(char_h*.003,.002));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    o=box('ChestBadge',Vector((tc.x-vw*.25,fy-char_h*.032,tc.z+vh*.20)),(vw*.13,char_h*.024,vh*.16),gold,max(char_h*.003,.002));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    o=box('Radio',Vector((tc.x+vw*.27,fy-char_h*.040,tc.z+vh*.17)),(vw*.14,char_h*.050,vh*.25),black,max(char_h*.003,.002));rigid_skin(o,arm,B['Torso']);pieces.append(o)
    belt_z=hips.z-char_h*.010;o=box('DutyBelt',Vector((hips.x,hips.y-char_h*.010,belt_z)),(torso_w*.78,torso_d*.98,char_h*.045),black,max(char_h*.003,.002));rigid_skin(o,arm,B['Hips']);pieces.append(o)
    o=box('BeltBuckle',Vector((hips.x,hips.y-torso_d*.53,belt_z)),(torso_w*.11,char_h*.020,char_h*.032),gold,max(char_h*.002,.001));rigid_skin(o,arm,B['Hips']);pieces.append(o)
    for i,s in enumerate((-0.28,0.16,0.34)):
        o=box('Pouch_'+str(i+1),Vector((hips.x+torso_w*s,hips.y-torso_d*.57,belt_z-char_h*.025)),(torso_w*.14,char_h*.060,char_h*.085),black,max(char_h*.003,.002));rigid_skin(o,arm,B['Hips']);pieces.append(o)
    capz=hc.z+head_h*.57;o=cyl('PoliceCapCrown',Vector((hc.x,hc.y,capz)),head_w*.56,head_h*.20,navy,10);o.scale.y=.90;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);rigid_skin(o,arm,B['Head']);pieces.append(o)
    o=box('PoliceCapBand',Vector((hc.x,hc.y-head_d*.08,capz-head_h*.08)),(head_w*.94,head_d*.78,head_h*.08),black,max(char_h*.003,.002));rigid_skin(o,arm,B['Head']);pieces.append(o)
    o=box('PoliceCapBrim',Vector((hc.x,hc.y-head_d*.48,capz-head_h*.11)),(head_w*.82,head_d*.42,head_h*.055),navy,max(char_h*.003,.002));o.rotation_euler.x=math.radians(-5);rigid_skin(o,arm,B['Head']);pieces.append(o)
    o=box('CapBadge',Vector((hc.x,hc.y-head_d*.47,capz+head_h*.015)),(head_w*.17,char_h*.018,head_h*.22),gold,max(char_h*.002,.001));rigid_skin(o,arm,B['Head']);pieces.append(o)
    return pieces,{'char_h':char_h,'shoulder':round(shoulder,4),'torso_w':round(torso_w,4),'torso_h':round(torso_h,4),'piece_count':len(pieces)}

def setup_walk(arm,act):
    arm.data.pose_position='POSE';ad=arm.animation_data_create();ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]);span=max(1,a1-a0);tr=ad.nla_tracks.new();st=tr.strips.new('Walk',0,act);st.action_frame_start=a0;st.action_frame_end=a1;st.scale=2;st.repeat=1;st.blend_type='REPLACE';return int(round(span*2))
def eval_center(o):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);m=e.to_mesh()
    try:
        pts=[e.matrix_world@v.co for v in m.vertices];return sum(pts,Vector())/len(pts)
    finally:e.to_mesh_clear()
def eval_bounds(objs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in objs:
        e=o.evaluated_get(dg);m=e.to_mesh()
        try:pts.extend(e.matrix_world@v.co for v in m.vertices)
        finally:e.to_mesh_clear()
    return Vector((min(v.x for v in pts),min(v.y for v in pts),min(v.z for v in pts))),Vector((max(v.x for v in pts),max(v.y for v in pts),max(v.z for v in pts)))
def qc(pieces,end,char_h):
    sc=bpy.context.scene;fs=[0,end//4,end//2,3*end//4,end];sn=[]
    for f in fs:sc.frame_set(f);sn.append([eval_center(o) for o in pieces])
    amp=max((sn[j][i]-sn[0][i]).length for j in range(1,len(sn)) for i in range(len(pieces)))
    if not .003<amp<char_h*1.3:raise RuntimeError('motion invalid '+str(amp))
    return fs,round(amp,5)
def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));bpy.context.object.data.materials.append(mkmat('Floor',(.055,.060,.070),.95))
def camera(lo,hi):
    c=(lo+hi)*.5;h=hi.z-lo.z;d=bpy.data.cameras.new('Camera');d.type='ORTHO';d.ortho_scale=h*1.18;cam=bpy.data.objects.new('Camera',d);bpy.context.collection.objects.link(cam);cam.location=c+Vector((h*.62,-h*3.6,h*.03));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=cam

def main():
    reset();objs,acts=import_glb(ASSET);arm=find_arm(objs);act=find_walk(acts)
    if arm.animation_data:arm.animation_data_clear()
    arm.data.pose_position='REST';bpy.context.scene.frame_set(0);bpy.context.view_layer.update();src=[o for o in objs if o.type=='MESH']
    # derive character height from source before hiding
    lo0,hi0=eval_bounds(src);char_h=hi0.z-lo0.z;pieces,spec=build(arm,char_h)
    for o in src:o.hide_render=True;o.hide_viewport=True
    sc=bpy.context.scene;sc.frame_start=0;sc.render.fps=60;end=setup_walk(arm,act);sc.frame_end=end;fs,amp=qc(pieces,end,char_h);sc.frame_set(end//2);lo,hi=eval_bounds(pieces);diag=(hi-lo).length
    if diag>char_h*2.0:raise RuntimeError('bounds exploded '+str(diag))
    floor(lo.z-.015,max(4,char_h*3));camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studio_light='paint.sl';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='WORLD';sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=os.path.join(FRAMES,'frame_')
    rep={'blender':bpy.app.version_string,'source_rig':'Quaternius Hoodie Character','walk':act.name,'fps':60,'frame_end':end,'style':'faceless blocky patrol police','spec':spec,'qc_frames':fs,'motion':amp,'bounds_diag':round(diag,4),'source_mesh_hidden':True,'rigid_skinning':'each generated part has 100% weight to exactly one existing bone','no_auto_weight':True,'no_retarget':True,'no_bone_edit':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(rep,f,indent=2)
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Officer_Stylized.blend'));bpy.ops.render.render(animation=True);print('POLICE_FULL_V3_PASS');print(json.dumps(rep,indent=2))
main()
