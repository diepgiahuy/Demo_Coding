import bpy, os, json
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_vest','hoodie_character.glb')
ART=os.path.join(ROOT,'artifacts','police_vest')
FRAMES=os.path.join(ART,'frames')
os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)

def import_glb(path):
    bo=set(bpy.data.objects); ba=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]

def get_arm(objs):
    arms=[o for o in objs if o.type=='ARMATURE']
    if not arms: raise RuntimeError('No armature')
    return max(arms,key=lambda o:len(o.data.bones))

def get_walk(actions):
    walks=[a for a in actions if 'walk' in a.name.lower()]
    if not walks: raise RuntimeError('No walk action')
    exact=[a for a in walks if a.name.lower().endswith('|walk')]
    return exact[0] if exact else walks[0]

def find_bone(arm,candidates,contains=()):
    by={b.name:b for b in arm.pose.bones}
    for n in candidates:
        if n in by:return by[n]
    for token in contains:
        m=[b for b in arm.pose.bones if token.lower() in b.name.lower()]
        if len(m)==1:return m[0]
    raise RuntimeError(f'Bone not found candidates={candidates}; available={[b.name for b in arm.pose.bones]}')

def mat(name,color):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.roughness=.78
    return m

def box(name,loc,dims,material,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel>0:
        b=o.modifiers.new('LowPolyEdge','BEVEL'); b.width=bevel; b.segments=1; b.limit_method='ANGLE'
    o.data.materials.append(material); return o

def bone_world(arm,bone,tail=False):
    return arm.matrix_world@(bone.tail if tail else bone.head)

def parent_bone_keep_world(obj,arm,bone):
    w=obj.matrix_world.copy(); obj.parent=arm; obj.parent_type='BONE'; obj.parent_bone=bone.name; obj.matrix_world=w

def all_bounds(meshes):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in meshes:
        e=o.evaluated_get(dg); me=e.to_mesh()
        try:pts.extend(e.matrix_world@v.co for v in me.vertices)
        finally:e.to_mesh_clear()
    if not pts:raise RuntimeError('No geometry')
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))

def make_vest(arm,height):
    torso=find_bone(arm,['Torso','Chest','Spine2','Spine.002','Spine1','Spine'],('torso','chest'))
    a=bone_world(arm,torso); b=bone_world(arm,torso,True); c=(a+b)*.5
    black=mat('Police_Vest_MAT',(0.018,0.027,0.042))
    pieces=[]
    # Slim patrol-vest proportions, based on the supplied reference board.
    total_w=height*.225
    panel_h=height*.175
    panel_d=height*.030
    gap=height*.014
    side_w=(total_w-gap)/2
    front_y=c.y-height*.052
    back_y=c.y+height*.046
    zc=c.z-height*.008
    bevel=height*.004
    # two clean front panels create a central opening instead of a bulky armor brick
    for sign,label in [(-1,'L'),(1,'R')]:
        x=c.x+sign*(gap/2+side_w/2)
        p=box(f'Police_Vest_Front_{label}',Vector((x,front_y,zc)),(side_w,panel_d,panel_h),black,bevel)
        parent_bone_keep_world(p,arm,torso); pieces.append(p)
    # thinner back plate
    back=box('Police_Vest_Back',Vector((c.x,back_y,zc)),(total_w,height*.022,panel_h*.96),black,bevel)
    parent_bone_keep_world(back,arm,torso); pieces.append(back)
    # shoulder straps: narrow, visually connect front/back without covering the arms
    strap_w=height*.042; strap_d=height*.090; strap_h=height*.024
    strap_z=zc+panel_h*.50
    for sign,label in [(-1,'L'),(1,'R')]:
        x=c.x+sign*(total_w*.31)
        s=box(f'Police_Vest_Shoulder_{label}',Vector((x,c.y-height*.003,strap_z)),(strap_w,strap_d,strap_h),black,bevel*.7)
        parent_bone_keep_world(s,arm,torso); pieces.append(s)
    # small lower side tabs give vest silhouette without wrapping the whole torso
    tab_w=height*.035; tab_d=height*.075; tab_h=height*.045
    tab_z=zc-panel_h*.38
    for sign,label in [(-1,'L'),(1,'R')]:
        x=c.x+sign*(total_w*.48)
        t=box(f'Police_Vest_Side_{label}',Vector((x,c.y-height*.002,tab_z)),(tab_w,tab_d,tab_h),black,bevel*.6)
        parent_bone_keep_world(t,arm,torso); pieces.append(t)
    return pieces,torso.name,{'width':round(total_w,4),'height':round(panel_h,4),'depth':round(panel_d,4),'piece_count':len(pieces)}

def setup_walk(arm,act):
    ad=arm.animation_data_create(); ad.action=None
    for t in list(ad.nla_tracks):ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]); span=max(1,a1-a0)
    tr=ad.nla_tracks.new(); tr.name='Walk_60fps'; st=tr.strips.new('Walk',0,act)
    st.action_frame_start=a0; st.action_frame_end=a1; st.scale=2; st.repeat=1; st.blend_type='REPLACE'
    return int(round(span*2))

def centers(objs):
    bpy.context.view_layer.update(); return [o.matrix_world.translation.copy() for o in objs]

def qc_motion(pieces,end,height):
    sc=bpy.context.scene; fs=sorted(set([0,end//4,end//2,3*end//4,end])); snaps=[]
    for f in fs:sc.frame_set(f); bpy.context.view_layer.update(); snaps.append(centers(pieces))
    ref=snaps[0]; amp=max((snaps[j][i]-ref[i]).length for j in range(1,len(snaps)) for i in range(len(pieces)))
    max_piece=max(max(o.dimensions) for o in pieces)
    if amp<.005:raise RuntimeError(f'Vest did not follow torso: {amp}')
    if amp>height*.75:raise RuntimeError(f'Vest transform exploded: {amp}')
    if max_piece>height*.35:raise RuntimeError(f'Vest piece too large: {max_piece}')
    return fs,round(amp,5)

def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z)); o=bpy.context.object; m=mat('Floor',(0.055,0.06,0.07)); o.data.materials.append(m)

def camera(lo,hi):
    c=(lo+hi)*.5; h=max(.5,hi.z-lo.z); d=bpy.data.cameras.new('Camera'); d.type='ORTHO'; d.ortho_scale=h*1.24
    cam=bpy.data.objects.new('Camera',d); bpy.context.collection.objects.link(cam); cam.location=c+Vector((h*.70,-h*3.25,h*.05)); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=cam

def main():
    reset(); objs,acts=import_glb(ASSET); arm=get_arm(objs); meshes=[o for o in objs if o.type=='MESH']; walk=get_walk(acts)
    lo0,hi0=all_bounds(meshes); height=hi0.z-lo0.z
    pieces,torso_name,spec=make_vest(arm,height)
    sc=bpy.context.scene; sc.frame_start=0; sc.render.fps=60; end=setup_walk(arm,walk); sc.frame_end=end
    fs,amp=qc_motion(pieces,end,height)
    sc.frame_set(end//2); lo,hi=all_bounds(meshes+pieces); floor(lo.z-.01,max(4,height*3)); camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'; sc.display.shading.show_shadows=True; sc.display.shading.show_cavity=True
    sc.render.resolution_x=512; sc.render.resolution_y=512; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.filepath=os.path.join(FRAMES,'frame_')
    report={'blender':bpy.app.version_string,'base':'Quaternius Hoodie Character','walk':walk.name,'fps':60,'frame_end':end,'torso_bone':torso_name,'vest_spec':spec,'vest_pieces':[o.name for o in pieces],'qc_frames':fs,'vest_center_motion':amp,'strategy':'stylized rigid patrol vest made of separate low-poly panels bone-parented to existing Torso; original body rig weights Walk untouched','no_retarget':True,'no_auto_weight':True,'no_body_mesh_edit':True,'no_bone_edit':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(report,f,indent=2)
    sc.frame_set(0); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Citizen_A_Police_Vest.blend')); bpy.ops.render.render(animation=True)
    print('POLICE_VEST_V3_PASS'); print(json.dumps(report,indent=2))
main()
