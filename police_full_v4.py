import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
HOOD=os.path.join(ROOT,'assets','police_full','hoodie_character.glb')
PUNK=os.path.join(ROOT,'assets','police_full','punk.glb')
ART=os.path.join(ROOT,'artifacts','police_full_v4')
FRAMES=os.path.join(ART,'frames'); os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)
def import_glb(path):
    bo=set(bpy.data.objects);ba=set(bpy.data.actions);bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]
def armature(objs):
    a=[o for o in objs if o.type=='ARMATURE']
    if not a:raise RuntimeError('No armature')
    return max(a,key=lambda o:len(o.data.bones))
def find_walk(actions):
    a=[x for x in actions if 'walk' in x.name.lower()]
    if not a:raise RuntimeError('No walk')
    e=[x for x in a if x.name.lower().endswith('|walk')];return e[0] if e else a[0]
def mesh(objs,token):
    a=[o for o in objs if o.type=='MESH' and token.lower() in o.name.lower()]
    if not a:return None
    return max(a,key=lambda o:len(o.data.vertices))
def bounds_raw(o):
    p=[o.matrix_world@v.co for v in o.data.vertices]
    return Vector((min(v.x for v in p),min(v.y for v in p),min(v.z for v in p))),Vector((max(v.x for v in p),max(v.y for v in p),max(v.z for v in p)))
def eval_bounds(objs):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();pts=[]
    for o in objs:
        if o.type!='MESH' or o.hide_render:continue
        e=o.evaluated_get(dg);m=e.to_mesh()
        try:pts.extend(e.matrix_world@v.co for v in m.vertices)
        finally:e.to_mesh_clear()
    if not pts:raise RuntimeError('No geometry')
    return Vector((min(v.x for v in pts),min(v.y for v in pts),min(v.z for v in pts))),Vector((max(v.x for v in pts),max(v.y for v in pts),max(v.z for v in pts)))
def eval_center(o):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);m=e.to_mesh()
    try:
        pts=[e.matrix_world@v.co for v in m.vertices];return sum(pts,Vector())/len(pts)
    finally:e.to_mesh_clear()
def find_bone(arm,cands,tokens=()):
    d={b.name:b for b in arm.pose.bones}
    for n in cands:
        if n in d:return d[n]
    for t in tokens:
        m=[b for b in arm.pose.bones if t.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    return None
def bp(arm,b,tail=False):return arm.matrix_world@(b.tail if tail else b.head)
def mkmat(name,c,rough=.8,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.roughness=rough;m.metallic=metal;return m
def box(name,loc,dims,mat,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel>0:
        md=o.modifiers.new('EdgeSoft','BEVEL');md.width=bevel;md.segments=1;md.limit_method='ANGLE'
    return o
def cyl(name,loc,r,depth,mat,verts=10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o
def parent_keep(o,arm,b):
    w=o.matrix_world.copy();o.parent=arm;o.parent_type='BONE';o.parent_bone=b.name;o.matrix_world=w

def setup_walk(arm,act):
    ad=arm.animation_data_create();ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]);span=max(1,a1-a0);tr=ad.nla_tracks.new();st=tr.strips.new('Walk',0,act);st.action_frame_start=a0;st.action_frame_end=a1;st.scale=2;st.repeat=1;st.blend_type='REPLACE';return int(round(span*2))
def swap_modular_part(obj,base_arm,material=None):
    mods=[m for m in obj.modifiers if m.type=='ARMATURE']
    if not mods:raise RuntimeError(obj.name+' has no Armature modifier')
    for m in mods:m.object=base_arm
    if material:
        obj.data.materials.clear();obj.data.materials.append(material)
        for p in obj.data.polygons:p.material_index=0
    bone_names=set(b.name for b in base_arm.data.bones);groups=set(v.name for v in obj.vertex_groups);match=len(bone_names&groups)
    if match<4:raise RuntimeError(obj.name+' modular groups do not match base rig; matched '+str(match))
    return match

def make_vest(body,arm,black,gold):
    lo,hi=bounds_raw(body);sz=hi-lo;cx=(lo.x+hi.x)/2;torso=find_bone(arm,['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest'))
    ul=find_bone(arm,['UpperArmL','UpperArm.L'],('upperarml','upperarm.l'));ur=find_bone(arm,['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r'))
    if not torso:raise RuntimeError('No torso')
    shoulder=abs(bp(arm,ul).x-bp(arm,ur).x) if ul and ur else sz.x*.16;vw=max(sz.x*.14,min(sz.x*.205,shoulder*1.36));vh=sz.z*.46;zmid=lo.z+sz.z*.56;zt=zmid+vh*.5;zb=zmid-vh*.5;tw=vw*.82;gap=max(vw*.055,.012);fy=lo.y-max(sz.y*.035,.008);by=fy-max(sz.y*.055,.012);rf=hi.y+max(sz.y*.025,.006);rb=rf+max(sz.y*.05,.01)
    def prism(name,outline,yf,yb):
        n=len(outline);verts=[]
        for y in (yf,yb):verts += [(x,y,z) for x,z in outline]
        faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
        for i in range(n):j=(i+1)%n;faces.append((i,j,n+j,n+i))
        me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(black);md=o.modifiers.new('EdgeSoft','BEVEL');md.width=max(sz.z*.006,.003);md.segments=1;return o
    pcs=[];left=[(cx-tw/2,zt),(cx-gap/2,zt),(cx-gap/2,zb),(cx-vw/2,zb)];right=[(cx+gap/2,zt),(cx+tw/2,zt),(cx+vw/2,zb),(cx+gap/2,zb)]
    for n,ol in [('VestFrontL',left),('VestFrontR',right)]:o=prism(n,ol,fy,by);parent_keep(o,arm,torso);pcs.append(o)
    o=prism('VestBack',[(cx-tw/2,zt),(cx+tw/2,zt),(cx+vw/2,zb),(cx-vw/2,zb)],rf,rb);parent_keep(o,arm,torso);pcs.append(o)
    for s,l in [(-1,'L'),(1,'R')]:o=box('VestStrap'+l,Vector((cx+s*vw*.31,(by+rf)/2,zt+sz.z*.006)),(vw*.17,rf-by,max(sz.z*.035,.018)),black,max(sz.z*.004,.002));parent_keep(o,arm,torso);pcs.append(o)
    badge=box('ChestBadge',Vector((cx-vw*.23,fy-max(sz.y*.035,.01),zmid+vh*.17)),(vw*.14,max(sz.y*.035,.01),vh*.18),gold,max(sz.z*.002,.001));parent_keep(badge,arm,torso);pcs.append(badge)
    radio=box('Radio',Vector((cx+vw*.26,fy-max(sz.y*.055,.015),zmid+vh*.14)),(vw*.16,max(sz.y*.07,.02),vh*.26),black,max(sz.z*.002,.001));parent_keep(radio,arm,torso);pcs.append(radio)
    return pcs,{'cx':cx,'fy':fy,'vw':vw,'vh':vh,'zmid':zmid,'shoulder':shoulder},torso

def make_cap(head,arm,navy,black,gold):
    hb=find_bone(arm,['Head'],('head',));
    if not hb:raise RuntimeError('No head bone')
    lo,hi=bounds_raw(head);sz=hi-lo;cx=(lo.x+hi.x)/2;cy=(lo.y+hi.y)/2;top=hi.z;pcs=[];z=top-sz.z*.015
    crown=cyl('PoliceCapCrown',Vector((cx,cy,z)),sz.x*.48,sz.z*.16,navy,10);crown.scale.y=.9;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parent_keep(crown,arm,hb);pcs.append(crown)
    band=box('PoliceCapBand',Vector((cx,lo.y+sz.y*.10,z-sz.z*.07)),(sz.x*.88,sz.y*.70,sz.z*.065),black,max(sz.z*.012,.002));parent_keep(band,arm,hb);pcs.append(band)
    brim=box('PoliceCapBrim',Vector((cx,lo.y-sz.y*.20,z-sz.z*.085)),(sz.x*.76,sz.y*.38,sz.z*.045),navy,max(sz.z*.010,.002));brim.rotation_euler.x=math.radians(-4);parent_keep(brim,arm,hb);pcs.append(brim)
    cb=box('CapBadge',Vector((cx,lo.y-sz.y*.17,z+sz.z*.015)),(sz.x*.16,max(sz.y*.035,.008),sz.z*.18),gold,max(sz.z*.008,.001));parent_keep(cb,arm,hb);pcs.append(cb)
    return pcs

def make_belt(arm,vest_spec,black,gold):
    hips=find_bone(arm,['Hips','Pelvis'],('hips','pelvis'))
    if not hips:raise RuntimeError('No hips')
    hp=bp(arm,hips);w=vest_spec['shoulder']*.62;d=w*.38;z=hp.z+.005;pcs=[]
    belt=box('DutyBelt',Vector((hp.x,hp.y,z)),(w,d,.055),black,.006);parent_keep(belt,arm,hips);pcs.append(belt)
    buck=box('BeltBuckle',Vector((hp.x,hp.y-d*.54,z)),(w*.12,.018,.038),gold,.003);parent_keep(buck,arm,hips);pcs.append(buck)
    for i,s in enumerate((-.34,.24,.39)):
        p=box('Pouch'+str(i+1),Vector((hp.x+w*s,hp.y-d*.56,z-.025)),(w*.14,.065,.09),black,.004);parent_keep(p,arm,hips);pcs.append(p)
    return pcs

def qc(parts,gear,end):
    sc=bpy.context.scene;fs=[0,end//4,end//2,3*end//4,end];cent=[]
    for f in fs:
        sc.frame_set(f);cent.append([eval_center(o) for o in parts])
    amp=max((cent[j][i]-cent[0][i]).length for j in range(1,len(cent)) for i in range(len(parts)))
    gearpos=[]
    for f in fs:
        sc.frame_set(f);bpy.context.view_layer.update();gearpos.append([o.matrix_world.translation.copy() for o in gear])
    gamp=max((gearpos[j][i]-gearpos[0][i]).length for j in range(1,len(gearpos)) for i in range(len(gear)))
    if amp<.02:raise RuntimeError('Swapped modular parts static')
    if gamp<.003:raise RuntimeError('Gear static')
    return fs,round(amp,5),round(gamp,5)
def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));bpy.context.object.data.materials.append(mkmat('Floor',(.055,.06,.07),.95))
def camera(lo,hi):
    c=(lo+hi)*.5;h=hi.z-lo.z;d=bpy.data.cameras.new('Camera');d.type='ORTHO';d.ortho_scale=h*1.24;cam=bpy.data.objects.new('Camera',d);bpy.context.collection.objects.link(cam);cam.location=c+Vector((h*.62,-h*3.5,h*.04));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=cam

def main():
    reset();base_objs,base_actions=import_glb(HOOD);base_arm=armature(base_objs);walk=find_walk(base_actions);base_mesh=[o for o in base_objs if o.type=='MESH'];body=mesh(base_objs,'body');head=mesh(base_objs,'head');base_legs=mesh(base_objs,'legs');base_feet=mesh(base_objs,'feet')
    if not all([body,head,base_legs,base_feet]):raise RuntimeError('Base modular pieces missing')
    punk_objs,punk_actions=import_glb(PUNK);punk_arm=armature(punk_objs);p_legs=mesh(punk_objs,'legs');p_feet=mesh(punk_objs,'feet')
    if not p_legs or not p_feet:raise RuntimeError('Punk legs/feet missing')
    navy=mkmat('PoliceNavy',(0.025,.07,.155),.84);black=mkmat('PoliceBlack',(.015,.02,.03),.9);gold=mkmat('PoliceGold',(.96,.62,.1),.55,.1)
    leg_match=swap_modular_part(p_legs,base_arm,navy);feet_match=swap_modular_part(p_feet,base_arm,black);base_legs.hide_render=True;base_feet.hide_render=True
    # remove every Punk object except the two swapped meshes; armature is no longer needed
    for o in list(punk_objs):
        if o not in (p_legs,p_feet):bpy.data.objects.remove(o,do_unlink=True)
    # Full gear on proven base
    vest,vs,torso=make_vest(body,base_arm,black,gold);cap=make_cap(head,base_arm,navy,black,gold);belt=make_belt(base_arm,vs,black,gold);gear=vest+cap+belt
    sc=bpy.context.scene;sc.frame_start=0;sc.render.fps=60;end=setup_walk(base_arm,walk);sc.frame_end=end;fs,part_amp,gear_amp=qc([p_legs,p_feet],gear,end)
    sc.frame_set(end//2);visible=[o for o in base_mesh if not o.hide_render]+[p_legs,p_feet]+gear;lo,hi=eval_bounds(visible);h=hi.z-lo.z;floor(lo.z-.015,max(4,h*3));camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.studio_light='paint.sl';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.display.shading.cavity_type='WORLD';sc.render.resolution_x=640;sc.render.resolution_y=640;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=os.path.join(FRAMES,'frame_')
    rep={'blender':bpy.app.version_string,'base':'Quaternius Hoodie Character','swapped_from':'Quaternius Punk','walk':walk.name,'fps':60,'frame_end':end,'punk_legs_vertex_group_matches':leg_match,'punk_feet_vertex_group_matches':feet_match,'gear_count':len(gear),'qc_frames':fs,'modular_part_motion':part_amp,'gear_motion':gear_amp,'pipeline':'same-pack modular swap: Hoodie body/head + Punk long pants/feet, original weights retained; vest/cap/belt rigid gear; base Walk untouched','no_auto_weight':True,'no_retarget':True,'no_bone_edit':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(rep,f,indent=2)
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Officer_Modular.blend'));bpy.ops.render.render(animation=True);print('POLICE_FULL_V4_PASS');print(json.dumps(rep,indent=2))
main()
