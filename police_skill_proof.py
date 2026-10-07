import bpy, os, json
from mathutils import Vector

ROOT=os.path.dirname(os.path.abspath(__file__))
ASSET=os.path.join(ROOT,'assets','police_skill','swat.glb')
ART=os.path.join(ROOT,'artifacts','police_skill')
FRAMES=os.path.join(ART,'frames')
os.makedirs(FRAMES,exist_ok=True)

def reset(): bpy.ops.wm.read_factory_settings(use_empty=True)

def import_glb(path):
    bo=set(bpy.data.objects); ba=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in bo],[a for a in bpy.data.actions if a not in ba]

def find_armature(objs):
    arms=[o for o in objs if o.type=='ARMATURE']
    if not arms: raise RuntimeError('No armature')
    return max(arms,key=lambda o:len(o.data.bones))

def find_walk(actions):
    ws=[a for a in actions if 'walk' in a.name.lower()]
    if not ws: raise RuntimeError('No Walk action: '+','.join(a.name for a in actions))
    exact=[a for a in ws if a.name.lower().endswith('|walk') or a.name.lower()=='walk']
    return exact[0] if exact else ws[0]

def bounds(meshes):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in meshes:
        e=o.evaluated_get(dg); m=e.to_mesh()
        try: pts += [e.matrix_world@v.co for v in m.vertices]
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No mesh vertices')
    lo=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
    hi=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
    return lo,hi

def sample(meshes,limit=100):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); out=[]
    for o in meshes:
        e=o.evaluated_get(dg); m=e.to_mesh()
        try:
            step=max(1,len(m.vertices)//max(1,limit))
            out += [e.matrix_world@m.vertices[i].co for i in range(0,len(m.vertices),step)][:limit]
        finally: e.to_mesh_clear()
    return out

def setup_walk_60(arm,action):
    ad=arm.animation_data_create(); ad.action=None
    for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
    a0=float(action.frame_range[0]); a1=float(action.frame_range[1]); span=max(1.0,a1-a0)
    tr=ad.nla_tracks.new(); tr.name='Walk_60fps'
    st=tr.strips.new('Walk',0,action); st.action_frame_start=a0; st.action_frame_end=a1; st.scale=2.0; st.repeat=1.0; st.blend_type='REPLACE'
    return int(round(span*2.0))

def motion_qc(meshes,end):
    sc=bpy.context.scene; fs=[0,end//4,end//2,3*end//4,end]; snaps=[]
    for f in fs: sc.frame_set(f); snaps.append(sample(meshes))
    n=min(len(s) for s in snaps); ref=snaps[0][:n]
    if n<20: raise RuntimeError('Too few mesh samples')
    amp=max((snaps[j][i]-ref[i]).length for j in range(1,len(snaps)) for i in range(n))
    if amp<0.03: raise RuntimeError('Visible SWAT mesh is not following Walk')
    return fs,round(amp,6)

def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z)); o=bpy.context.object
    m=bpy.data.materials.new('Floor'); m.diffuse_color=(0.07,0.08,0.10,1); o.data.materials.append(m)

def camera(lo,hi):
    c=(lo+hi)*.5; h=max(.5,hi.z-lo.z); d=bpy.data.cameras.new('Camera'); d.type='ORTHO'; d.ortho_scale=h*1.25
    cam=bpy.data.objects.new('Camera',d); bpy.context.collection.objects.link(cam); bpy.context.scene.camera=cam
    cam.location=c+Vector((h*.62,-h*3.0,h*.035)); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()

def main():
    reset(); objs,actions=import_glb(ASSET); arm=find_armature(objs); meshes=[o for o in objs if o.type=='MESH']; walk=find_walk(actions)
    rigged=[o for o in meshes if any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
    if not rigged: raise RuntimeError('Original SWAT skin binding missing')
    sc=bpy.context.scene; sc.render.fps=60; sc.frame_start=0; end=setup_walk_60(arm,walk); sc.frame_end=end
    fs,amp=motion_qc(rigged,end); sc.frame_set(0); lo,hi=bounds(meshes); h=hi.z-lo.z; floor(lo.z-.01,max(4.5,h*3.2)); camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'; sc.display.shading.show_shadows=True; sc.display.shading.show_cavity=True
    sc.render.resolution_x=720; sc.render.resolution_y=720; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.image_settings.compression=25; sc.render.filepath=os.path.join(FRAMES,'frame_')
    report={'blender_version':bpy.app.version_string,'asset':'SWAT by Quaternius, Ultimate Modular Men Pack','license':'CC0 1.0','walk_action':walk.name,'fps':60,'frame_end':end,'mesh_count':len(meshes),'original_rigged_mesh_count':len(rigged),'bone_count':len(arm.data.bones),'sample_frames':fs,'max_visible_mesh_displacement':amp,'strategy':'original SWAT mesh + original armature + original skin weights + original embedded Walk; NLA scale 2 for 60fps preview; no retarget, no auto-weight, no replacement body, no procedural walk'}
    with open(os.path.join(ART,'qc_report.json'),'w') as f: json.dump(report,f,indent=2)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Police_SWAT_SkillProof.blend')); bpy.ops.render.render(animation=True)
    print('POLICE_SKILL_PROOF_PASS'); print(json.dumps(report,indent=2))
main()
