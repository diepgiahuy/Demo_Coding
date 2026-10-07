import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_full','hoodie_character.glb')
ART=os.path.join(ROOT,'artifacts','police_full')
FRAMES=os.path.join(ART,'frames'); os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)
def import_glb(p):
    bo=set(bpy.data.objects); ba=set(bpy.data.actions); bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]
def find_arm(objs):
    a=[o for o in objs if o.type=='ARMATURE']
    if not a: raise RuntimeError('No armature')
    return max(a,key=lambda x:len(x.data.bones))
def find_walk(actions):
    a=[x for x in actions if 'walk' in x.name.lower()]
    if not a: raise RuntimeError('No Walk')
    e=[x for x in a if x.name.lower().endswith('|walk')]; return e[0] if e else a[0]
def find_mesh(meshes,token):
    a=[o for o in meshes if token.lower() in o.name.lower()]
    return max(a,key=lambda o:len(o.data.vertices)) if a else None
def raw_bounds(o):
    p=[o.matrix_world@v.co for v in o.data.vertices]
    return Vector((min(v.x for v in p),min(v.y for v in p),min(v.z for v in p))),Vector((max(v.x for v in p),max(v.y for v in p),max(v.z for v in p)))
def eval_bounds(objs):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        if o.type!='MESH': continue
        e=o.evaluated_get(dg); m=e.to_mesh()
        try: pts.extend(e.matrix_world@v.co for v in m.vertices)
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No evaluated geometry')
    return Vector((min(v.x for v in pts),min(v.y for v in pts),min(v.z for v in pts))),Vector((max(v.x for v in pts),max(v.y for v in pts),max(v.z for v in pts)))
def find_bone(arm,cands,tokens=()):
    d={b.name:b for b in arm.data.bones}
    for n in cands:
        if n in d:return d[n]
    for t in tokens:
        m=[b for b in arm.data.bones if t.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    return None
def bw(arm,b,tail=False): return arm.matrix_world@(b.tail_local if tail else b.head_local)
def mat(name,color,rough=.72,metal=0.0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.roughness=rough;m.metallic=metal;return m
def box(name,loc,dims,material,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
    if bevel>0:
        b=o.modifiers.new('LowPolyEdge','BEVEL');b.width=bevel;b.segments=1;b.limit_method='ANGLE'
    return o
def cylinder(name,loc,radius,depth,material,vertices=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(material);return o
def prism(name,outline,y_front,y_back,material,bevel=.003):
    n=len(outline);verts=[]
    for y in (y_front,y_back):verts += [(x,y,z) for x,z in outline]
    faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
    for i in range(n):
        j=(i+1)%n;faces.append((i,j,n+j,n+i))
    me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(material)
    if bevel>0:
        b=o.modifiers.new('LowPolyEdge','BEVEL');b.width=bevel;b.segments=1;b.limit_method='ANGLE'
    return o
def parent_bone(o,arm,b):
    w=o.matrix_world.copy();o.parent=arm;o.parent_type='BONE';o.parent_bone=b.name;o.matrix_world=w
def segment_box(name,p0,p1,width,depth,material,arm,bone,frac0=0.0,frac1=1.0,bevel=.003):
    a=p0.lerp(p1,frac0);b=p0.lerp(p1,frac1);v=b-a;L=max(v.length,.001);c=(a+b)*.5
    o=box(name,c,(width,depth,L),material,bevel);o.rotation_euler=v.to_track_quat('Z','Y').to_euler();parent_bone(o,arm,bone);return o

def make_vest(body_obj,arm,navy,black,gold):
    lo,hi=raw_bounds(body_obj);sz=hi-lo;cx=(lo.x+hi.x)/2
    torso=find_bone(arm,['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest'))
    if not torso:raise RuntimeError('No torso bone')
    ul=find_bone(arm,['UpperArmL','UpperArm.L'],('upperarml','upperarm.l'));ur=find_bone(arm,['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r'))
    shoulder=abs(bw(arm,ul).x-bw(arm,ur).x) if ul and ur else sz.x*.16
    vest_w=max(sz.x*.14,min(sz.x*.205,shoulder*1.36));vest_h=sz.z*.46;zmid=lo.z+sz.z*.56;zt=zmid+vest_h*.5;zb=zmid-vest_h*.5;tw=vest_w*.82;gap=max(vest_w*.055,.012)
    fy=lo.y-max(sz.y*.035,.008);by=fy-max(sz.y*.055,.012);rf=hi.y+max(sz.y*.025,.006);rb=rf+max(sz.y*.05,.01)
    pieces=[]
    left=[(cx-tw/2,zt),(cx-gap/2,zt),(cx-gap/2,zb),(cx-vest_w/2,zb)];right=[(cx+gap/2,zt),(cx+tw/2,zt),(cx+vest_w/2,zb),(cx+gap/2,zb)]
    for n,ol in [('Police_Vest_Front_L',left),('Police_Vest_Front_R',right)]:
        o=prism(n,ol,fy,by,black,max(sz.z*.006,.003));parent_bone(o,arm,torso);pieces.append(o)
    back=prism('Police_Vest_Back',[(cx-tw/2,zt),(cx+tw/2,zt),(cx+vest_w/2,zb),(cx-vest_w/2,zb)],rf,rb,black,max(sz.z*.006,.003));parent_bone(back,arm,torso);pieces.append(back)
    sw=vest_w*.17;ym=(by+rf)/2;strap_y=rf-by;strap_z=max(sz.z*.035,.018)
    for s,l in [(-1,'L'),(1,'R')]:
        o=box('Police_Vest_Shoulder_'+l,Vector((cx+s*vest_w*.31,ym,zt+strap_z*.18)),(sw,strap_y,strap_z),black,max(sz.z*.004,.002));parent_bone(o,arm,torso);pieces.append(o)
    # badge + radio on front
    badge=box('Police_Badge',Vector((cx-vest_w*.22,fy-max(sz.y*.02,.006),zmid+vest_h*.16)),(vest_w*.15,max(sz.y*.03,.01),vest_h*.17),gold,max(sz.z*.003,.002));parent_bone(badge,arm,torso);pieces.append(badge)
    radio=box('Police_Radio',Vector((cx+vest_w*.27,fy-max(sz.y*.025,.008),zmid+vest_h*.13)),(vest_w*.17,max(sz.y*.055,.016),vest_h*.25),black,max(sz.z*.003,.002));parent_bone(radio,arm,torso);pieces.append(radio)
    return pieces,torso,{'width':vest_w,'height':vest_h,'front_y':fy,'center':Vector((cx,fy,zmid)),'body_lo':lo,'body_hi':hi}

def make_cap(head_obj,arm,navy,black,gold):
    hb=find_bone(arm,['Head'],('head',));
    if not hb:raise RuntimeError('No head bone')
    lo,hi=raw_bounds(head_obj);sz=hi-lo;cx=(lo.x+hi.x)/2;cy=(lo.y+hi.y)/2;top=hi.z
    pieces=[]
    crown=cylinder('Police_Cap_Crown',Vector((cx,cy,top+sz.z*.025)),sz.x*.50,sz.z*.19,navy,vertices=10);crown.scale.y=.90;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parent_bone(crown,arm,hb);pieces.append(crown)
    band=box('Police_Cap_Band',Vector((cx,lo.y-sz.y*.02,top-sz.z*.035)),(sz.x*.88,sz.y*.72,sz.z*.09),black,max(sz.z*.02,.002));parent_bone(band,arm,hb);pieces.append(band)
    brim=box('Police_Cap_Brim',Vector((cx,lo.y-sz.y*.42,top-sz.z*.075)),(sz.x*.80,sz.y*.44,sz.z*.055),navy,max(sz.z*.015,.002));brim.rotation_euler.x=math.radians(-4);parent_bone(brim,arm,hb);pieces.append(brim)
    cb=box('Police_Cap_Badge',Vector((cx,lo.y-sz.y*.39,top+sz.z*.005)),(sz.x*.18,sz.y*.045,sz.z*.22),gold,max(sz.z*.01,.0015));parent_bone(cb,arm,hb);pieces.append(cb)
    return pieces,hb

def make_uniform_limbs(arm,char_h,navy,black):
    pieces=[]; req={
      'UpperArmL':(['UpperArmL','UpperArm.L'],('upperarml','upperarm.l')),
      'UpperArmR':(['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r')),
      'UpperLegL':(['UpperLegL','UpperLeg.L'],('upperlegl','upperleg.l','thigh.l')),
      'UpperLegR':(['UpperLegR','UpperLeg.R'],('upperlegr','upperleg.r','thigh.r')),
      'LowerLegL':(['LowerLegL','LowerLeg.L'],('lowerlegl','lowerleg.l','calf.l')),
      'LowerLegR':(['LowerLegR','LowerLeg.R'],('lowerlegr','lowerleg.r','calf.r')),
      'FootL':(['FootL','Foot.L'],('footl','foot.l')),
      'FootR':(['FootR','Foot.R'],('footr','foot.r'))}
    B={k:find_bone(arm,*v) for k,v in req.items()}
    missing=[k for k,v in B.items() if not v]
    if missing:raise RuntimeError('Missing limb bones '+str(missing))
    # short navy sleeves: top 44% of upper arm only
    for k,l in [('UpperArmL','L'),('UpperArmR','R')]:
        b=B[k];p0=bw(arm,b);p1=bw(arm,b,True);pieces.append(segment_box('Police_Sleeve_'+l,p0,p1,char_h*.060,char_h*.052,navy,arm,b,0,.44,max(char_h*.002,.002)))
    # long pants, two rigid blocks per leg
    for k,l in [('UpperLegL','L'),('UpperLegR','R')]:
        b=B[k];p0=bw(arm,b);p1=bw(arm,b,True);pieces.append(segment_box('Police_Thigh_'+l,p0,p1,char_h*.082,char_h*.070,navy,arm,b,.02,.98,max(char_h*.002,.002)))
    for k,l in [('LowerLegL','L'),('LowerLegR','R')]:
        b=B[k];p0=bw(arm,b);p1=bw(arm,b,True);pieces.append(segment_box('Police_Calf_'+l,p0,p1,char_h*.070,char_h*.060,navy,arm,b,.02,.98,max(char_h*.002,.002)))
    # shoes/boots at foot bones, slightly forward toward -Y
    for k,l in [('FootL','L'),('FootR','R')]:
        b=B[k];p0=bw(arm,b);p1=bw(arm,b,True);c=(p0+p1)*.5+Vector((0,-char_h*.028,-char_h*.012));o=box('Police_Boot_'+l,c,(char_h*.088,char_h*.145,char_h*.060),black,max(char_h*.003,.002));parent_bone(o,arm,b);pieces.append(o)
    return pieces,B

def make_belt(body_obj,arm,black,gold):
    hips=find_bone(arm,['Hips','Pelvis'],('hips','pelvis'))
    if not hips:raise RuntimeError('No hips bone')
    lo,hi=raw_bounds(body_obj);sz=hi-lo;cx=(lo.x+hi.x)/2;hp=bw(arm,hips);z=hp.z+sz.z*.015;front=lo.y-max(sz.y*.045,.010);back=hi.y+max(sz.y*.035,.008);w=sz.x*.20;pieces=[]
    for n,y in [('Police_Belt_Front',front),('Police_Belt_Back',back)]:
        o=box(n,Vector((cx,y,z)),(w,sz.y*.055,sz.z*.050),black,max(sz.z*.003,.002));parent_bone(o,arm,hips);pieces.append(o)
    buckle=box('Police_Belt_Buckle',Vector((cx,front-max(sz.y*.025,.007),z)),(w*.16,sz.y*.035,sz.z*.036),gold,max(sz.z*.002,.001));parent_bone(buckle,arm,hips);pieces.append(buckle)
    # three compact utility pouches
    for i,x in enumerate((cx-w*.34,cx+w*.02,cx+w*.34)):
        o=box('Police_Pouch_'+str(i+1),Vector((x,front-max(sz.y*.035,.010),z-sz.z*.015)),(w*.19,sz.y*.10,sz.z*.095),black,max(sz.z*.003,.002));parent_bone(o,arm,hips);pieces.append(o)
    return pieces,hips

def setup_walk(arm,act):
    ad=arm.animation_data_create();ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]);span=max(1,a1-a0);tr=ad.nla_tracks.new();tr.name='Walk_60fps';st=tr.strips.new('Walk',0,act);st.action_frame_start=a0;st.action_frame_end=a1;st.scale=2;st.repeat=1;st.blend_type='REPLACE';return int(round(span*2))
def qc(gear,end,char_h):
    sc=bpy.context.scene;fs=[0,end//4,end//2,3*end//4,end];sn=[]
    for f in fs:
        sc.frame_set(f);bpy.context.view_layer.update();sn.append([o.matrix_world.translation.copy() for o in gear])
    amp=max((sn[j][i]-sn[0][i]).length for j in range(1,len(sn)) for i in range(len(gear)))
    if not .003<amp<char_h*1.0:raise RuntimeError('Gear motion invalid '+str(amp))
    return fs,round(amp,5)
def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));o=bpy.context.object;m=mat('Floor',(.055,.060,.070),.95);o.data.materials.append(m)
def camera(lo,hi):
    c=(lo+hi)*.5;h=hi.z-lo.z;d=bpy.data.cameras.new('Camera');d.type='ORTHO';d.ortho_scale=h*1.20;cam=bpy.data.objects.new('Camera',d);bpy.context.collection.objects.link(cam);cam.location=c+Vector((h*.62,-h*3.45,h*.05));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=cam

def main():
    reset();objs,acts=import_glb(ASSET);arm=find_arm(objs);meshes=[o for o in objs if o.type=='MESH'];body=find_mesh(meshes,'body');head=find_mesh(meshes,'head');act=find_walk(acts)
    if not body or not head:raise RuntimeError('Body/head mesh missing')
    lo0,hi0=eval_bounds(meshes);char_h=hi0.z-lo0.z
    navy=mat('Police_Navy',(0.025,0.070,0.155),.78);black=mat('Police_Black',(0.018,0.022,0.030),.82);gold=mat('Police_Gold',(0.92,0.62,0.10),.55,.10)
    gear=[]
    v,torso,vs=make_vest(body,arm,navy,black,gold);gear+=v
    cap,headbone=make_cap(head,arm,navy,black,gold);gear+=cap
    uniform,bones=make_uniform_limbs(arm,char_h,navy,black);gear+=uniform
    belt,hipsbone=make_belt(body,arm,black,gold);gear+=belt
    sc=bpy.context.scene;sc.frame_start=0;sc.render.fps=60;end=setup_walk(arm,act);sc.frame_end=end;fs,amp=qc(gear,end,char_h)
    sc.frame_set(end//2);lo,hi=eval_bounds(meshes+gear);diag=(hi-lo).length
    if diag>char_h*2.2:raise RuntimeError('Full officer bounds exploded '+str(diag))
    floor(lo.z-.01,max(4,char_h*3));camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studio_light='paint.sl';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='WORLD';sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=os.path.join(FRAMES,'frame_')
    rep={'blender':bpy.app.version_string,'base_asset':'Quaternius Hoodie Character','walk':act.name,'fps':60,'frame_end':end,'gear_count':len(gear),'gear_names':[o.name for o in gear],'qc_frames':fs,'gear_motion':amp,'bounds_diag':round(diag,4),'char_height':round(char_h,4),'strategy':'proven original rig+weights+Walk untouched; stylized police gear bone-parented to existing bones; navy sleeves + rigid segmented long pants cover original shorts','no_auto_weight':True,'no_retarget':True,'no_bone_edit':True,'original_body_rig_untouched':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(rep,f,indent=2)
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Officer_Full.blend'));bpy.ops.render.render(animation=True);print('POLICE_FULL_V1_PASS');print(json.dumps(rep,indent=2))
main()
