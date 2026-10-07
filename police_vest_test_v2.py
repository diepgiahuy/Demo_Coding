import bpy, bmesh, os, json
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

def armature(objs):
    a=[o for o in objs if o.type=='ARMATURE']
    if not a: raise RuntimeError('No armature')
    return max(a,key=lambda x:len(x.data.bones))

def walk_action(actions):
    a=[x for x in actions if 'walk' in x.name.lower()]
    if not a: raise RuntimeError('No Walk action')
    exact=[x for x in a if x.name.lower().endswith('|walk')]
    return exact[0] if exact else a[0]

def body_mesh(meshes):
    b=[o for o in meshes if 'body' in o.name.lower()]
    if not b: raise RuntimeError('No Body mesh')
    return max(b,key=lambda o:len(o.data.vertices))

def raw_world_bounds(obj):
    p=[obj.matrix_world@v.co for v in obj.data.vertices]
    return Vector((min(x.x for x in p),min(x.y for x in p),min(x.z for x in p))),Vector((max(x.x for x in p),max(x.y for x in p),max(x.z for x in p)))

def evaluated_bounds(objs):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        e=o.evaluated_get(dg); m=e.to_mesh()
        try: pts.extend(e.matrix_world@v.co for v in m.vertices)
        finally: e.to_mesh_clear()
    if not pts: raise RuntimeError('No evaluated points')
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))

def build_vest(body,arm):
    lo,hi=raw_world_bounds(body); sz=hi-lo; h=sz.z
    # Casual_Body includes horizontally extended arms in rest pose.  Keeping the
    # central 24% of its full width isolates the torso while leaving clear arm holes.
    x0=lo.x+sz.x*0.38; x1=hi.x-sz.x*0.38
    z0=lo.z+sz.z*0.30; z1=lo.z+sz.z*0.85

    vest=body.copy(); vest.data=body.data.copy(); bpy.context.collection.objects.link(vest)
    vest.name='Police_Vest'; vest.data.name='Police_Vest_Mesh'

    bm=bmesh.new(); bm.from_mesh(vest.data); bm.faces.ensure_lookup_table()
    drop=[]
    for f in bm.faces:
        c=body.matrix_world@f.calc_center_median()
        if not (x0<=c.x<=x1 and z0<=c.z<=z1): drop.append(f)
    bmesh.ops.delete(bm,geom=drop,context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
    if len(bm.faces)<30: raise RuntimeError(f'Vest patch too small: {len(bm.faces)} faces')

    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    offset=max(h*0.012,0.004)
    for v in bm.verts:
        v.normal_update()
        if v.normal.length>1e-6: v.co += v.normal.normalized()*offset
    bm.to_mesh(vest.data); bm.free(); vest.data.update()

    vest.data.materials.clear()
    mat=bpy.data.materials.new('Police_Vest_MAT'); mat.diffuse_color=(0.018,0.035,0.060,1); mat.roughness=0.76
    vest.data.materials.append(mat)
    for p in vest.data.polygons: p.material_index=0

    am=[m for m in vest.modifiers if m.type=='ARMATURE']
    if not am:
        m=vest.modifiers.new('Armature','ARMATURE'); m.object=arm
    else:
        for m in am: m.object=arm
    solid=vest.modifiers.new('Vest_Thickness','SOLIDIFY'); solid.thickness=max(h*0.012,0.006); solid.offset=0.0; solid.use_even_offset=True

    return vest,{'faces':len(vest.data.polygons),'vertices':len(vest.data.vertices),'x0':round(x0,4),'x1':round(x1,4),'z0':round(z0,4),'z1':round(z1,4),'normal_offset':round(offset,4)}

def setup_walk(arm,act):
    ad=arm.animation_data_create(); ad.action=None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    a0,a1=float(act.frame_range[0]),float(act.frame_range[1]); span=max(1,a1-a0)
    tr=ad.nla_tracks.new(); tr.name='Walk_60fps'; st=tr.strips.new('Walk',0,act)
    st.action_frame_start=a0; st.action_frame_end=a1; st.scale=2.0; st.repeat=1.0; st.blend_type='REPLACE'
    return int(round(span*2))

def sample_points(obj,n=100):
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get(); e=obj.evaluated_get(dg); m=e.to_mesh()
    try:
        if not m.vertices:return []
        step=max(1,len(m.vertices)//n); return [e.matrix_world@m.vertices[i].co for i in range(0,len(m.vertices),step)][:n]
    finally:e.to_mesh_clear()

def qc_motion(vest,end,character_meshes):
    sc=bpy.context.scene; frames=sorted(set([0,end//4,end//2,3*end//4,end])); snaps=[]
    for f in frames: sc.frame_set(f); snaps.append(sample_points(vest))
    n=min(len(x) for x in snaps)
    if n<10: raise RuntimeError('Too few vest QC points')
    ref=snaps[0][:n]; amp=max((snaps[j][i]-ref[i]).length for j in range(1,len(snaps)) for i in range(n))
    sc.frame_set(0); clo,chi=evaluated_bounds(character_meshes); vlo,vhi=evaluated_bounds([vest])
    char_diag=(chi-clo).length; vest_diag=(vhi-vlo).length
    if amp<0.02: raise RuntimeError(f'Vest static: {amp}')
    if amp>char_diag*1.2: raise RuntimeError(f'Vest exploded by motion: amp {amp}, character diag {char_diag}')
    if vest_diag>char_diag*0.9: raise RuntimeError(f'Vest bounds too large: vest {vest_diag}, character {char_diag}')
    return frames,round(amp,5),round(vest_diag/char_diag,4)

def floor(z,size):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,0,z)); o=bpy.context.object
    m=bpy.data.materials.new('Floor'); m.diffuse_color=(0.06,0.065,0.075,1); m.roughness=.9; o.data.materials.append(m)

def camera(lo,hi):
    c=(lo+hi)*.5; h=max(.5,hi.z-lo.z); d=bpy.data.cameras.new('Camera'); d.type='ORTHO'; d.ortho_scale=h*1.25
    cam=bpy.data.objects.new('Camera',d); bpy.context.collection.objects.link(cam); cam.location=c+Vector((h*.75,-h*3.2,h*.06)); cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=cam

def main():
    reset(); objs,acts=import_glb(ASSET); arm=armature(objs); meshes=[o for o in objs if o.type=='MESH']; body=body_mesh(meshes); walk=walk_action(acts)
    vest,cut=build_vest(body,arm)
    sc=bpy.context.scene; sc.frame_start=0; sc.render.fps=60; end=setup_walk(arm,walk); sc.frame_end=end
    frames,amp,ratio=qc_motion(vest,end,meshes)
    sc.frame_set(end//2); lo,hi=evaluated_bounds(meshes+[vest]); floor(lo.z-.01,max(4,(hi.z-lo.z)*3)); camera(lo,hi)
    sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'; sc.display.shading.show_shadows=True; sc.display.shading.show_cavity=True
    sc.render.resolution_x=512; sc.render.resolution_y=512; sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'; sc.render.filepath=os.path.join(FRAMES,'frame_')
    report={'blender':bpy.app.version_string,'base':'Quaternius Hoodie Character','body':body.name,'walk':walk.name,'fps':60,'frame_end':end,'vest':cut,'qc_frames':frames,'vest_motion':amp,'vest_to_character_diag_ratio':ratio,'strategy':'duplicate original rigged torso surface, crop central torso, offset rest vertices along normals, preserve original weights/armature, thin Solidify only','no_retarget':True,'no_auto_weight':True,'no_bone_edits':True}
    with open(os.path.join(ART,'qc_report.json'),'w') as f:json.dump(report,f,indent=2)
    sc.frame_set(0); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART,'Citizen_A_Police_Vest.blend')); bpy.ops.render.render(animation=True)
    print('POLICE_VEST_V2_PASS'); print(json.dumps(report,indent=2))
main()
