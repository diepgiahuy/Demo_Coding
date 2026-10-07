import bpy, os, json
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_vest','hoodie_character.glb')
ART=os.path.join(ROOT,'artifacts','police_vest')
FRAMES=os.path.join(ART,'frames'); os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)
def import_glb(p):
    bo=set(bpy.data.objects); ba=set(bpy.data.actions); bpy.ops.import_scene.gltf(filepath=p)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]
def armature(objs):
    a=[o for o in objs if o.type=='ARMATURE'];
    if not a: raise RuntimeError('No armature')
    return max(a,key=lambda x:len(x.data.bones))
def walk(actions):
    a=[x for x in actions if 'walk' in x.name.lower()];
    if not a: raise RuntimeError('No Walk')
    e=[x for x in a if x.name.lower().endswith('|walk')]; return e[0] if e else a[0]
def body(meshes):
    a=[o for o in meshes if 'body' in o.name.lower()];
    if not a:raise RuntimeError('No body')
    return max(a,key=lambda o:len(o.data.vertices))
def bounds_raw(o):
    p=[o.matrix_world@v.co for v in o.data.vertices]
    return Vector((min(v.x for v in p),min(v.y for v in p),min(v.z for v in p))),Vector((max(v.x for v in p),max(v.y for v in p),max(v.z for v in p)))
def eval_bounds(objs):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); p=[]
    for o in objs:
        e=o.evaluated_get(dg); m=e.to_mesh()
        try:p.extend(e.matrix_world@v.co for v in m.vertices)
        finally:e.to_mesh_clear()
    return Vector((min(v.x for v in p),min(v.y for v in p),min(v.z for v in p))),Vector((max(v.x for v in p),max(v.y for v in p),max(v.z for v in p)))
def find_bone(arm,cands,tokens=()):
    d={b.name:b for b in arm.pose.bones}
    for n in cands:
        if n in d:return d[n]
    for t in tokens:
        m=[b for b in arm.pose.bones if t.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    return None
def bw(arm,b,tail=False): return arm.matrix_world@(b.tail if tail else b.head)
def material():
    m=bpy.data.materials.new('Police_Vest_MAT');m.diffuse_color=(0.014,0.024,0.040,1);m.roughness=.82;return m
def prism(name,outline_front,y_front,y_back,mat,bevel=.004):
    # outline points are (x,z), clockwise. Build a clean shallow prism.
    n=len(outline_front); verts=[]
    for y in (y_front,y_back): verts += [(x,y,z) for x,z in outline_front]
    faces=[]
    faces.append(tuple(range(n)))
    faces.append(tuple(range(2*n-1,n-1,-1)))
    for i in range(n):
        j=(i+1)%n; faces.append((i,j,n+j,n+i))
    me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(mat)
    if bevel>0:
        b=o.modifiers.new('LowPolyEdge','BEVEL');b.width=bevel;b.segments=1;b.limit_method='ANGLE'
    return o
def box(name,loc,dims,mat,bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel>0:
        b=o.modifiers.new('LowPolyEdge','BEVEL');b.width=bevel;b.segments=1;b.limit_method='ANGLE'
    return o
def parent_keep(o,arm,bone):
    w=o.matrix_world.copy();o.parent=arm;o.parent_type='BONE';o.parent_bone=bone.name;o.matrix_world=w
def make_vest(body_obj,arm):
    lo,hi=bounds_raw(body_obj); sz=hi-lo; cx=(lo.x+hi.x)/2
    torso=find_bone(arm,['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest'))
    if not torso:raise RuntimeError('No torso bone')
    ul=find_bone(arm,['UpperArmL','UpperArm.L'],('upperarml','upperarm.l'))
    ur=find_bone(arm,['UpperArmR','UpperArm.R'],('upperarmr','upperarm.r'))
    if ul and ur:
        shoulder=abs(bw(arm,ul).x-bw(arm,ur).x)
    else: shoulder=sz.x*.16
    # Clamp to body-derived range so a bad bone convention cannot create huge armor.
    vest_w=max(sz.x*.14,min(sz.x*.205,shoulder*1.36))
    vest_h=sz.z*.46
    z_mid=lo.z+sz.z*.56
    z_top=z_mid+vest_h*.5; z_bottom=z_mid-vest_h*.5
    top_w=vest_w*.82; bottom_w=vest_w
    gap=max(vest_w*.055,.012)
    # Actual raw body Y bounds anchor the vest close to the shirt surface.
    front_y=lo.y-max(sz.y*.035,.008); back_y=front_y-max(sz.y*.055,.012)
    rear_front=hi.y+max(sz.y*.025,.006); rear_back=rear_front+max(sz.y*.050,.010)
    mat=material(); pieces=[]
    # Split-front patrol vest with a narrow center opening and tapered shoulders.
    left=[(cx-top_w/2,z_top),(cx-gap/2,z_top),(cx-gap/2,z_bottom),(cx-bottom_w/2,z_bottom)]
    right=[(cx+gap/2,z_top),(cx+top_w/2,z_top),(cx+bottom_w/2,z_bottom),(cx+gap/2,z_bottom)]
    for name,ol in [('Police_Vest_Front_L',left),('Police_Vest_Front_R',right)]:
        o=prism(name,ol,front_y,back_y,mat,max(sz.z*.006,.003));parent_keep(o,arm,torso);pieces.append(o)
    # Back panel is one clean trapezoid, slightly narrower at the top.
    back_outline=[(cx-top_w/2,z_top),(cx+top_w/2,z_top),(cx+bottom_w/2,z_bottom),(cx-bottom_w/2,z_bottom)]
    back=prism('Police_Vest_Back',back_outline,rear_front,rear_back,mat,max(sz.z*.006,.003));parent_keep(back,arm,torso);pieces.append(back)
    # Shoulder straps bridge front/back and stay well inside arm joints.
    strap_w=vest_w*.17; strap_y=(rear_front-back_y); strap_z=max(sz.z*.035,.018)
    ymid=(back_y+rear_front)/2
    for sign,label in [(-1,'L'),(1,'R')]:
        x=cx+sign*vest_w*.31;o=box('Police_Vest_Shoulder_'+label,Vector((x,ymid,z_top+strap_z*.18)),(strap_w,strap_y,strap_z),mat,max(sz.z*.004,.002));parent_keep(o,arm,torso);pieces.append(o)
    return pieces,torso.name,{'body_bounds':[[round(v,4) for v in lo],[round(v,4) for v in hi]],'shoulder_measure':round(shoulder,4),'vest_width':round(vest_w,4),'vest_height':round(vest_h,4),'front_y':round(front_y,4),'back_surface_y':round(rear_front,4),'pieces':len(pieces)}
def setup_walk(arm,act):
    ad=arm.animation_data_create();ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]);span=max(1,a1-a0);tr=ad.nla_tracks.new();st=tr.strips.new('Walk',0,act);st.action_frame_start=a0;st.action_frame_end=a1;st.scale=2;st.repeat=1;return int(round(span*2))
def qc(pieces,end,char_h):
    sc=bpy.context.scene;fs=[0,end//4,end//2,3*end//4,end];sn=[]
    for f in fs:sc.frame_set(f);bpy.context.view_layer.update();sn.append([o.matrix_world.translation.copy() for o in pieces])
    amp=max((sn[j][i]-sn[0][i]).length for j in range(1,len(sn)) for i in range(len(pieces)))
    if not .003<amp<char_h*.6:raise RuntimeError(f'Vest motion invalid {amp}')
    return fs,round(amp,5)
def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z));o=bpy.context.object;m=bpy.data.materials.new('Floor');m.diffuse_color=(.055,.06,.07,1);o.data.materials.append(m)
def camera(lo,hi):
    c=(lo+hi)*.5;h=hi.z-lo.z;d=bpy.data.cameras.new('Camera');d.type='ORTHO';d.ortho_scale=h*1.22;cam=bpy.data.objects.new('Camera',d);bpy.context.collection.objects.link(cam);cam.location=c+Vector((h*.58,-h*3.4,h*.04));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=cam
def main():
    reset();objs,acts=import_glb(ASSET);arm=armature(objs);meshes=[o for o in objs if o.type=='MESH'];bod=body(meshes);act=walk(acts);lo0,hi0=eval_bounds(meshes);char_h=hi0.z-lo0.z
    pieces,tbone,spec=make_vest(bod,arm);sc=bpy.context.scene;sc.frame_start=0;sc.render.fps=60;end=setup_walk(arm,act);sc.frame_end=end;fs,amp=qc(pieces,end,char_h)
    sc.frame_set(end//2);lo,hi=eval_bounds(meshes+pieces);floor(lo.z-.01,max(4,char_h*3));camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL';sc.display.shading.show_shadows=True;sc.display.shading.show_cavity=True;sc.render.resolution_x=512;sc.render.resolution_y=512;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGBA';sc.render.filepath=os.path.join(FRAMES,'frame_')
    rep={'blender':bpy.app.version_string,'base':'Quaternius Hoodie Character','walk':act.name,'fps':60,'frame_end':end,'torso_bone':tbone,'vest_spec':spec,'qc_frames':fs,'vest_motion':amp,'strategy':'torso-measured thin trapezoid front/back vest panels + shoulder straps, rigid bone-parent to existing Torso; base mesh rig weights Walk untouched','no_body_mesh_edit':True,'no_auto_weight':True,'no_retarget':True,'no_bone_edit':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(rep,f,indent=2)
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Citizen_A_Police_Vest.blend'));bpy.ops.render.render(animation=True);print('POLICE_VEST_V4_PASS');print(json.dumps(rep,indent=2))
main()
