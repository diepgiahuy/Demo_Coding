import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_skill','hoodie_character.glb')
ART=os.path.join(ROOT,'artifacts','police_skill')
FRAMES=os.path.join(ART,'frames')
os.makedirs(FRAMES,exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    bo=set(bpy.data.objects); ba=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]


def find_armature(objs):
    arms=[o for o in objs if o.type=='ARMATURE']
    if not arms: raise RuntimeError('No armature found')
    return max(arms,key=lambda o:len(o.data.bones))


def find_walk(actions):
    ws=[a for a in actions if 'walk' in a.name.lower()]
    if not ws: raise RuntimeError('No Walk action. Actions='+','.join(a.name for a in actions))
    exact=[a for a in ws if a.name.lower().endswith('|walk') or a.name.lower()=='walk']
    return exact[0] if exact else ws[0]


def find_bone(arm, exact, tokens=()):
    by={b.name.lower():b for b in arm.pose.bones}
    for n in exact:
        if n.lower() in by: return by[n.lower()]
    for t in tokens:
        hits=[b for b in arm.pose.bones if t.lower() in b.name.lower()]
        if len(hits)==1: return hits[0]
    raise RuntimeError('Bone not found '+repr(exact)+' available='+repr([b.name for b in arm.pose.bones]))


def bone_pos(arm,bone,tail=False):
    return arm.matrix_world @ (bone.tail if tail else bone.head)


def mat(name,color,rough=.65,metal=0.0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1)
    m.use_nodes=True; bs=m.node_tree.nodes.get('Principled BSDF')
    if bs:
        bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    return m


def cube(name,loc,dims,material,bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        md=o.modifiers.new('Bevel','BEVEL'); md.width=bevel; md.segments=1
    o.data.materials.append(material); return o


def cyl(name,loc,radius,depth,material,verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc); o=bpy.context.object; o.name=name; o.data.materials.append(material); return o


def bone_parent_keep_world(obj,arm,bone):
    world=obj.matrix_world.copy(); obj.parent=arm; obj.parent_type='BONE'; obj.parent_bone=bone.name; obj.matrix_world=world


def bounds(meshes):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for obj in meshes:
        e=obj.evaluated_get(dg); me=e.to_mesh()
        try: pts.extend(e.matrix_world @ v.co for v in me.vertices)
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No evaluated mesh points')
    lo=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    hi=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return lo,hi


def sample_points(meshes,limit=60):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); out=[]
    for obj in meshes:
        e=obj.evaluated_get(dg); me=e.to_mesh()
        try:
            step=max(1,len(me.vertices)//max(1,limit))
            out.extend(e.matrix_world @ me.vertices[i].co for i in range(0,len(me.vertices),step))
        finally: e.to_mesh_clear()
    return out[:limit*max(1,len(meshes))]


def setup_walk_60(arm,action):
    ad=arm.animation_data_create(); ad.action=None
    for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
    a0=float(action.frame_range[0]); a1=float(action.frame_range[1]); span=max(1.0,a1-a0)
    tr=ad.nla_tracks.new(); tr.name='Walk_60fps'
    st=tr.strips.new('Walk',0,action); st.action_frame_start=a0; st.action_frame_end=a1; st.scale=2.0; st.repeat=1.0; st.blend_type='REPLACE'
    return int(round(span*2.0))


def add_police_gear(arm,height):
    head=find_bone(arm,['Head'],['head'])
    torso=find_bone(arm,['Torso','Chest','Spine2','Spine1','Spine'],['torso','chest'])
    hips=find_bone(arm,['Hips','Pelvis'],['hips','pelvis'])

    navy=mat('Police_Navy',(0.025,0.075,0.18))
    black=mat('Police_Black',(0.018,0.022,0.03))
    gold=mat('Police_Badge',(0.92,0.64,0.12),.42,.18)
    white=mat('Police_Patch',(0.78,0.84,0.90),.6)
    gear=[]

    hp0=bone_pos(arm,head); hp1=bone_pos(arm,head,True); hc=(hp0+hp1)*0.5; top=max(hp0.z,hp1.z)
    cc=Vector((hc.x,hc.y,top+height*.030))
    crown=cyl('Police_Cap_Crown',cc,height*.100,height*.050,navy,12); bone_parent_keep_world(crown,arm,head); gear.append(crown)
    brim=cube('Police_Cap_Brim',cc+Vector((0,-height*.060,-height*.022)),(height*.170,height*.090,height*.013),navy,height*.0025); bone_parent_keep_world(brim,arm,head); gear.append(brim)
    cap_badge=cube('Police_Cap_Badge',cc+Vector((0,-height*.104,-height*.005)),(height*.027,height*.008,height*.032),gold,height*.0015); bone_parent_keep_world(cap_badge,arm,head); gear.append(cap_badge)

    p0=bone_pos(arm,torso); p1=bone_pos(arm,torso,True); tc=(p0+p1)*0.5
    badge=cube('Police_Chest_Badge',tc+Vector((-height*.055,-height*.066,height*.025)),(height*.024,height*.007,height*.034),gold,height*.0015); bone_parent_keep_world(badge,arm,torso); gear.append(badge)
    patch=cube('Police_Chest_Patch',tc+Vector((height*.060,-height*.066,height*.020)),(height*.070,height*.006,height*.026),white,height*.0015); bone_parent_keep_world(patch,arm,torso); gear.append(patch)
    radio=cube('Police_Radio',tc+Vector((height*.085,-height*.050,height*.060)),(height*.036,height*.025,height*.060),black,height*.002); bone_parent_keep_world(radio,arm,torso); gear.append(radio)

    hp=bone_pos(arm,hips)+Vector((0,0,height*.018))
    belt=cube('Police_Utility_Belt',hp,(height*.255,height*.105,height*.032),black,height*.0025); bone_parent_keep_world(belt,arm,hips); gear.append(belt)
    buckle=cube('Police_Belt_Buckle',hp+Vector((0,-height*.058,0)),(height*.036,height*.009,height*.027),gold,height*.0015); bone_parent_keep_world(buckle,arm,hips); gear.append(buckle)
    holster=cube('Police_Holster',hp+Vector((height*.105,0,-height*.055)),(height*.045,height*.045,height*.085),black,height*.002); bone_parent_keep_world(holster,arm,hips); gear.append(holster)
    return gear,{'head':head.name,'torso':torso.name,'hips':hips.name}


def mesh_motion_qc(meshes,end):
    sc=bpy.context.scene; frames=[0,max(1,end//4),max(1,end//2),max(1,3*end//4),end]; snaps=[]
    for f in frames: sc.frame_set(f); snaps.append(sample_points(meshes))
    n=min(len(x) for x in snaps); ref=snaps[0][:n]
    if n<10: raise RuntimeError('Too few points for visible-mesh QC')
    amp=max((snaps[j][i]-ref[i]).length for j in range(1,len(snaps)) for i in range(n))
    if amp<0.03: raise RuntimeError('Body mesh does not visibly follow Walk')
    return frames,round(amp,6)


def add_floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z)); o=bpy.context.object; o.data.materials.append(mat('Floor',(0.08,0.09,0.11)))


def add_camera(lo,hi):
    c=(lo+hi)*.5; h=max(.5,hi.z-lo.z); d=bpy.data.cameras.new('Camera'); d.type='ORTHO'; d.ortho_scale=h*1.28
    cam=bpy.data.objects.new('Camera',d); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam
    cam.location=c+Vector((h*.68,-h*3.0,h*.035)); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()


def main():
    reset(); objs,actions=import_glb(ASSET); arm=find_armature(objs); meshes=[o for o in objs if o.type=='MESH']; walk=find_walk(actions)
    rigged=[o for o in meshes if any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
    if not rigged: raise RuntimeError('Proven Hoodie mesh lost original armature binding')

    sc=bpy.context.scene; sc.render.fps=60; sc.frame_start=0; end=setup_walk_60(arm,walk); sc.frame_end=end
    motion_frames,motion_amp=mesh_motion_qc(rigged,end)
    sc.frame_set(0); lo0,hi0=bounds(meshes); height=hi0.z-lo0.z
    gear,bone_map=add_police_gear(arm,height)
    visible=meshes+[g for g in gear if g.type=='MESH']; lo,hi=bounds(visible)
    add_floor(lo.z-.01,max(4.5,height*3.2)); add_camera(lo,hi)

    sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'; sc.display.shading.show_shadows=True; sc.display.shading.show_cavity=True
    sc.render.resolution_x=720; sc.render.resolution_y=720; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.image_settings.compression=25; sc.render.filepath=os.path.join(FRAMES,'frame_')

    report={'blender_version':bpy.app.version_string,'base_asset':'Quaternius Hoodie Character (proven Citizen base)','license':'CC0 1.0','walk_action':walk.name,'fps':60,'frame_end':end,'bone_count':len(arm.data.bones),'original_rigged_mesh_count':len(rigged),'police_gear':[g.name for g in gear],'bone_map':bone_map,'mesh_motion_sample_frames':motion_frames,'max_visible_mesh_displacement':motion_amp,'strategy':'proven Hoodie mesh + original armature + original weights + original Walk; only rigid bone-parented police accessories; NLA scale 2 at 60fps; no retarget, no auto-weight, no bone edits, no replacement body'}
    with open(os.path.join(ART,'qc_report.json'),'w') as f: json.dump(report,f,indent=2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_Hoodie_SkillProof.blend'))
    bpy.ops.render.render(animation=True)
    print('POLICE_SKILL_PROOF_PASS'); print(json.dumps(report,indent=2))

main()
