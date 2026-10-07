import bpy, os, json, math
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_skill','swat.glb')
ART=os.path.join(ROOT,'artifacts','police_skill')
FRAMES=os.path.join(ART,'frames')
os.makedirs(FRAMES,exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before_o=set(bpy.data.objects); before_a=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before_o],[a for a in bpy.data.actions if a not in before_a]


def find_armature(objs):
    arms=[o for o in objs if o.type=='ARMATURE']
    if not arms: raise RuntimeError('No armature in SWAT GLB')
    return max(arms,key=lambda o:len(o.data.bones))


def find_walk(actions):
    ws=[a for a in actions if 'walk' in a.name.lower()]
    if not ws: raise RuntimeError('No Walk action. Actions='+','.join(a.name for a in actions))
    exact=[a for a in ws if a.name.lower().endswith('|walk') or a.name.lower()=='walk']
    return exact[0] if exact else ws[0]


def eval_points(meshes, limit_per_mesh=80):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for obj in meshes:
        e=obj.evaluated_get(dg); m=e.to_mesh()
        try:
            n=max(1,min(len(m.vertices),limit_per_mesh))
            step=max(1,len(m.vertices)//n)
            for i in range(0,len(m.vertices),step):
                pts.append(e.matrix_world @ m.vertices[i].co)
                if len(pts)>=limit_per_mesh*len(meshes): break
        finally: e.to_mesh_clear()
    return pts


def bounds(meshes):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for obj in meshes:
        e=obj.evaluated_get(dg); m=e.to_mesh()
        try:
            pts.extend(e.matrix_world @ v.co for v in m.vertices)
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No mesh points')
    lo=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    hi=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return lo,hi


def setup_walk_60(arm,action):
    ad=arm.animation_data_create(); ad.action=None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    a0=float(action.frame_range[0]); a1=float(action.frame_range[1]); span=max(1.0,a1-a0)
    tr=ad.nla_tracks.new(); tr.name='Walk_60fps'
    st=tr.strips.new('Walk',0,action)
    st.action_frame_start=a0; st.action_frame_end=a1; st.scale=2.0; st.repeat=1.0; st.blend_type='REPLACE'
    return int(round(span*2.0))


def add_floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z))
    f=bpy.context.object; f.name='Floor'
    m=bpy.data.materials.new('FloorMat'); m.diffuse_color=(0.08,0.09,0.11,1)
    f.data.materials.append(m)


def add_camera(lo,hi):
    c=(lo+hi)*0.5; h=max(0.5,hi.z-lo.z)
    data=bpy.data.cameras.new('Camera'); data.type='ORTHO'; data.ortho_scale=h*1.30
    cam=bpy.data.objects.new('Camera',data); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam
    cam.location=c+Vector((h*0.72,-h*3.0,h*0.05)); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()


def mesh_motion_qc(meshes,scene_end):
    scene=bpy.context.scene
    sample=[0,max(1,scene_end//4),max(1,scene_end//2),max(1,3*scene_end//4),scene_end]
    snapshots=[]
    for f in sample:
        scene.frame_set(f); snapshots.append(eval_points(meshes))
    count=min(len(x) for x in snapshots)
    if count<10: raise RuntimeError('Too few evaluated mesh points')
    ref=snapshots[0][:count]
    amps=[]
    for snap in snapshots[1:]:
        amps.append(max((snap[i]-ref[i]).length for i in range(count)))
    max_amp=max(amps)
    if max_amp<0.03: raise RuntimeError(f'Visible mesh did not animate; max displacement={max_amp}')
    return sample,round(max_amp,6)


def main():
    reset(); objs,actions=import_glb(ASSET)
    arm=find_armature(objs); meshes=[o for o in objs if o.type=='MESH']
    walk=find_walk(actions)

    # Hard validation: preserve original skinning.
    rigged=[]
    for o in meshes:
        mods=[m for m in o.modifiers if m.type=='ARMATURE' and m.object==arm]
        if mods: rigged.append(o)
    if not rigged: raise RuntimeError('No original SWAT mesh is skinned to its original armature')

    scene=bpy.context.scene; scene.render.fps=60; scene.frame_start=0
    scene_end=setup_walk_60(arm,walk); scene.frame_end=scene_end
    sample,max_disp=mesh_motion_qc(rigged,scene_end)
    scene.frame_set(0); lo,hi=bounds(meshes); h=hi.z-lo.z
    add_floor(lo.z-0.01,max(4.5,h*3.2)); add_camera(lo,hi)

    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
    scene.render.resolution_x=720; scene.render.resolution_y=720; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.image_settings.compression=25
    scene.render.filepath=os.path.join(FRAMES,'frame_')

    report={
      'blender_version':bpy.app.version_string,
      'asset':'Quaternius SWAT — Ultimate Modular Men Pack',
      'license':'CC0 1.0',
      'walk_action':walk.name,
      'fps':60,
      'frame_end':scene_end,
      'mesh_count':len(meshes),
      'original_rigged_mesh_count':len(rigged),
      'bone_count':len(arm.data.bones),
      'mesh_motion_sample_frames':sample,
      'max_visible_mesh_displacement':max_disp,
      'strategy':'original SWAT mesh + original SWAT armature + original skin weights + original embedded Walk; NLA scale 2 at 60 fps; no retarget; no auto-weight; no bone edits'
    }
    os.makedirs(ART,exist_ok=True)
    with open(os.path.join(ART,'qc_report.json'),'w') as f: json.dump(report,f,indent=2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_SWAT_SkillProof.blend'))
    bpy.ops.render.render(animation=True)
    print('POLICE_SKILL_PROOF_PASS')
    print(json.dumps(report,indent=2))

main()
