import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_full','punk.glb')
ART=os.path.join(ROOT,'artifacts','police_full_v5')
FRAMES=os.path.join(ART,'frames'); os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)
def import_glb(p):
    bo=set(bpy.data.objects);ba=set(bpy.data.actions);bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]
def find_arm(objs):
    a=[o for o in objs if o.type=='ARMATURE']
    if not a: raise RuntimeError('No armature')
    return max(a,key=lambda o:len(o.data.bones))
def find_walk(actions):
    a=[x for x in actions if 'walk' in x.name.lower()]
    if not a: raise RuntimeError('No Walk action')
    e=[x for x in a if x.name.lower().endswith('|walk')];return e[0] if e else a[0]
def find_mesh(objs,token):
    a=[o for o in objs if o.type=='MESH' and token.lower() in o.name.lower()]
    return max(a,key=lambda o:len(o.data.vertices)) if a else None
def bounds_raw(o):
    pts=[o.matrix_world@v.co for v in o.data.vertices]
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
def eval_bounds(objs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in objs:
        if o.type!='MESH' or o.hide_render: continue
        e=o.evaluated_get(dg);m=e.to_mesh()
        try: pts.extend(e.matrix_world@v.co for v in m.vertices)
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No evaluated geometry')
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
def find_bone(arm,cands,tokens=()):
    d={b.name:b for b in arm.pose.bones}
    for n in cands:
        if n in d:return d[n]
    for t in tokens:
        m=[b for b in arm.pose.bones if t.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    return None
def bp(arm,b,tail=False): return arm.matrix_world@(b.tail if tail else b.head)
def mkmat(name,c,rough=.8,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.roughness=rough;m.metallic=metal;return m
def recolor(obj,material):
    obj.data.materials.clear();obj.data.materials.append(material)
    for p in obj.data.polygons:p.material_index=0
def box(name,loc,dims,material,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
    if bevel>0:
        md=o.modifiers.new('LowPolyEdge','BEVEL');md.width=bevel;md.segments=1;md.limit_method='ANGLE'
    return o
def cyl(name,loc,r,depth,material,verts=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(material);return o
def ico(name,loc,scale,material):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);return o
def parent_keep(o,arm,b):
    w=o.matrix_world.copy();o.parent=arm;o.parent_type='BONE';o.parent_bone=b.name;o.matrix_world=w

def setup_walk(arm,act):
    ad=arm.animation_data_create();ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]);span=max(1,a1-a0);tr=ad.nla_tracks.new();tr.name='Walk_60fps';st=tr.strips.new('Walk',0,act);st.action_frame_start=a0;st.action_frame_end=a1;st.scale=2.0;st.repeat=1.0;st.blend_type='REPLACE';return int(round(span*2))

def make_vest(body,arm,black,gold):
    lo,hi=bounds_raw(body);sz=hi-lo;cx=(lo.x+hi.x)/2
    torso=find_bone(arm,['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest'))
    ul=find_bone(arm,['UpperArmL','UpperArm.L'],('upperarml','upperarm.l'));ur=find_bone(arm,['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r'))
    if not torso:raise RuntimeError('No torso bone')
    shoulder=abs(bp(arm,ul).x-bp(arm,ur).x) if ul and ur else sz.x*.16
    vw=max(sz.x*.14,min(sz.x*.205,shoulder*1.36));vh=sz.z*.46;zmid=lo.z+sz.z*.56;zt=zmid+vh*.5;zb=zmid-vh*.5;tw=vw*.82;gap=max(vw*.055,.012)
    fy=lo.y-max(sz.y*.035,.008);by=fy-max(sz.y*.055,.012);rf=hi.y+max(sz.y*.025,.006);rb=rf+max(sz.y*.05,.01)
    def prism(name,outline,yf,yb):
        n=len(outline);verts=[]
        for y in (yf,yb):verts += [(x,y,z) for x,z in outline]
        faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
        for i in range(n):j=(i+1)%n;faces.append((i,j,n+j,n+i))
        me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(black);md=o.modifiers.new('LowPolyEdge','BEVEL');md.width=max(sz.z*.006,.003);md.segments=1;return o
    pcs=[]
    left=[(cx-tw/2,zt),(cx-gap/2,zt),(cx-gap/2,zb),(cx-vw/2,zb)];right=[(cx+gap/2,zt),(cx+tw/2,zt),(cx+vw/2,zb),(cx+gap/2,zb)]
    for n,ol in [('VestFrontL',left),('VestFrontR',right)]:o=prism(n,ol,fy,by);parent_keep(o,arm,torso);pcs.append(o)
    o=prism('VestBack',[(cx-tw/2,zt),(cx+tw/2,zt),(cx+vw/2,zb),(cx-vw/2,zb)],rf,rb);parent_keep(o,arm,torso);pcs.append(o)
    for s,l in [(-1,'L'),(1,'R')]:
        o=box('VestStrap'+l,Vector((cx+s*vw*.31,(by+rf)/2,zt+sz.z*.006)),(vw*.17,rf-by,max(sz.z*.035,.018)),black,max(sz.z*.004,.002));parent_keep(o,arm,torso);pcs.append(o)
    o=box('ChestBadge',Vector((cx-vw*.23,fy-max(sz.y*.035,.01),zmid+vh*.17)),(vw*.14,max(sz.y*.035,.01),vh*.18),gold,max(sz.z*.002,.001));parent_keep(o,arm,torso);pcs.append(o)
    o=box('Radio',Vector((cx+vw*.26,fy-max(sz.y*.055,.015),zmid+vh*.14)),(vw*.16,max(sz.y*.07,.02),vh*.26),black,max(sz.z*.002,.001));parent_keep(o,arm,torso);pcs.append(o)
    return pcs,{'shoulder':shoulder,'vw':vw,'vh':vh,'cx':cx,'zmid':zmid},torso

def make_head_cap(head_src,arm,skin,hair,navy,black,gold):
    hb=find_bone(arm,['Head'],('head',));
    if not hb:raise RuntimeError('No head bone')
    lo,hi=bounds_raw(head_src);sz=hi-lo;cx=(lo.x+hi.x)/2;cy=(lo.y+hi.y)/2;cz=(lo.z+hi.z)/2
    # replace source Punk head/mohawk with a clean faceless low-poly head
    head_src.hide_render=True;head_src.hide_viewport=True
    pcs=[];hd=ico('Police_Faceless_Head',Vector((cx,cy,cz)),(sz.x*.43,sz.y*.43,sz.z*.45),skin);parent_keep(hd,arm,hb);pcs.append(hd)
    # dark simple hair under cap, no facial geometry
    htop=box('Police_Hair_Top',Vector((cx,cy+sz.y*.02,cz+sz.z*.31)),(sz.x*.72,sz.y*.66,sz.z*.20),hair,max(sz.z*.012,.002));parent_keep(htop,arm,hb);pcs.append(htop)
    hback=box('Police_Hair_Back',Vector((cx,cy+sz.y*.34,cz+sz.z*.05)),(sz.x*.68,sz.y*.16,sz.z*.48),hair,max(sz.z*.010,.002));parent_keep(hback,arm,hb);pcs.append(hback)
    z=hi.z-sz.z*.04;crown=cyl('PoliceCapCrown',Vector((cx,cy,z)),sz.x*.48,sz.z*.16,navy,10);crown.scale.y=.9;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parent_keep(crown,arm,hb);pcs.append(crown)
    band=box('PoliceCapBand',Vector((cx,lo.y+sz.y*.10,z-sz.z*.07)),(sz.x*.88,sz.y*.70,sz.z*.065),black,max(sz.z*.012,.002));parent_keep(band,arm,hb);pcs.append(band)
    brim=box('PoliceCapBrim',Vector((cx,lo.y-sz.y*.20,z-sz.z*.085)),(sz.x*.76,sz.y*.38,sz.z*.045),navy,max(sz.z*.010,.002));brim.rotation_euler.x=math.radians(-4);parent_keep(brim,arm,hb);pcs.append(brim)
    cb=box('CapBadge',Vector((cx,lo.y-sz.y*.17,z+sz.z*.015)),(sz.x*.16,max(sz.y*.035,.008),sz.z*.18),gold,max(sz.z*.008,.001));parent_keep(cb,arm,hb);pcs.append(cb)
    return pcs

def make_sleeves(arm,body,navy):
    lo,hi=bounds_raw(body);h=hi.z-lo.z;pcs=[]
    for side,cands,tok in [('L',['UpperArmL','UpperArm.L'],('upperarml','upperarm.l')),('R',['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r'))]:
        b=find_bone(arm,cands,tok)
        if not b:continue
        p0,p1=bp(arm,b),bp(arm,b,True);v=p1-p0;L=v.length*.37;c=p0+v*.19
        o=box('Police_Sleeve_'+side,c,(h*.105,h*.085,L),navy,max(h*.006,.002));o.rotation_euler=v.to_track_quat('Z','Y').to_euler();parent_keep(o,arm,b);pcs.append(o)
    return pcs

def make_belt(arm,vest_spec,black,gold):
    hips=find_bone(arm,['Hips','Pelvis'],('hips','pelvis'))
    if not hips:raise RuntimeError('No hips bone')
    hp=bp(arm,hips);w=vest_spec['shoulder']*.62;d=w*.38;z=hp.z+.005;pcs=[]
    o=box('DutyBelt',Vector((hp.x,hp.y,z)),(w,d,.055),black,.006);parent_keep(o,arm,hips);pcs.append(o)
    o=box('BeltBuckle',Vector((hp.x,hp.y-d*.54,z)),(w*.12,.018,.038),gold,.003);parent_keep(o,arm,hips);pcs.append(o)
    for i,s in enumerate((-.34,.24,.39)):
        o=box('Pouch'+str(i+1),Vector((hp.x+w*s,hp.y-d*.56,z-.025)),(w*.14,.065,.09),black,.004);parent_keep(o,arm,hips);pcs.append(o)
    return pcs

def gear_qc(gear,end):
    sc=bpy.context.scene;fs=[0,end//4,end//2,3*end//4,end];sn=[]
    for f in fs:
        sc.frame_set(f);bpy.context.view_layer.update();sn.append([o.matrix_world.translation.copy() for o in gear])
    amp=max((sn[j][i]-sn[0][i]).length for j in range(1,len(sn)) for i in range(len(gear)))
    if amp<.003:raise RuntimeError('Gear is static')
    return fs,round(amp,5)
def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));bpy.context.object.data.materials.append(mkmat('Floor',(.055,.06,.07),.95))
def camera(lo,hi):
    c=(lo+hi)*.5;h=hi.z-lo.z;d=bpy.data.cameras.new('Camera');d.type='ORTHO';d.ortho_scale=h*1.22;cam=bpy.data.objects.new('Camera',d);bpy.context.collection.objects.link(cam);cam.location=c+Vector((h*.58,-h*3.5,h*.04));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=cam

def main():
    reset();objs,actions=import_glb(ASSET);arm=find_arm(objs);walk=find_walk(actions);meshes=[o for o in objs if o.type=='MESH'];body=find_mesh(objs,'body');head=find_mesh(objs,'head');legs=find_mesh(objs,'legs');feet=find_mesh(objs,'feet')
    if not all([body,head,legs,feet]):raise RuntimeError('Punk modular pieces missing')
    navy=mkmat('PoliceNavy',(0.025,.07,.155),.84);black=mkmat('PoliceBlack',(.015,.02,.03),.9);gold=mkmat('PoliceGold',(.96,.62,.1),.55,.1);skin=mkmat('PoliceSkin',(.78,.48,.27),.88);hair=mkmat('PoliceHair',(.045,.03,.022),.94)
    # Long pants and shoes are original Punk meshes with original weights/rig. Only materials change.
    recolor(legs,navy);recolor(feet,black)
    vest,vs,torso=make_vest(body,arm,black,gold);headgear=make_head_cap(head,arm,skin,hair,navy,black,gold);sleeves=make_sleeves(arm,body,navy);belt=make_belt(arm,vs,black,gold);gear=vest+headgear+sleeves+belt
    sc=bpy.context.scene;sc.frame_start=0;sc.render.fps=60;end=setup_walk(arm,walk);sc.frame_end=end;fs,gamp=gear_qc(gear,end)
    sc.frame_set(end//2);visible=[o for o in meshes if not o.hide_render]+gear;lo,hi=eval_bounds(visible);h=hi.z-lo.z;diag=(hi-lo).length
    if diag>h*1.8:raise RuntimeError('Visual bounds exploded '+str(diag/h))
    floor(lo.z-.015,max(4,h*3));camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studio_light='paint.sl';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='WORLD';sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=os.path.join(FRAMES,'frame_')
    rep={'blender':bpy.app.version_string,'base_asset':'Quaternius Punk','walk':walk.name,'fps':60,'frame_end':end,'gear_count':len(gear),'qc_frames':fs,'gear_motion':gamp,'visual_height':round(h,4),'bounds_diag':round(diag,4),'pipeline':'Punk original body/long legs/feet/rig/weights/Walk retained; Punk head hidden and replaced with faceless rigid head; proven vest + cap + sleeves + duty belt gear','original_punk_long_pants':True,'original_weights':True,'no_auto_weight':True,'no_retarget':True,'no_bone_edit':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(rep,f,indent=2)
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Officer_Patrol.blend'));bpy.ops.render.render(animation=True);print('POLICE_FULL_V5_PASS');print(json.dumps(rep,indent=2))
main()
