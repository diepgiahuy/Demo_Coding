import bpy, bmesh, os, json, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(ROOT, 'assets', 'police_vest', 'hoodie_character.glb')
ART = os.path.join(ROOT, 'artifacts', 'police_vest')
FRAMES = os.path.join(ART, 'frames')
os.makedirs(FRAMES, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before_o = set(bpy.data.objects)
    before_a = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before_o], [a for a in bpy.data.actions if a not in before_a]


def find_armature(objs):
    arms = [o for o in objs if o.type == 'ARMATURE']
    if not arms:
        raise RuntimeError('No armature found')
    return max(arms, key=lambda a: len(a.data.bones))


def find_walk(actions):
    walks = [a for a in actions if 'walk' in a.name.lower()]
    if not walks:
        raise RuntimeError('No Walk action found')
    exact = [a for a in walks if a.name.lower().endswith('|walk') or a.name.lower() == 'walk']
    return exact[0] if exact else walks[0]


def find_body(meshes):
    named = [o for o in meshes if 'body' in o.name.lower()]
    pool = named if named else meshes
    if not pool:
        raise RuntimeError('No mesh body found')
    return max(pool, key=lambda o: len(o.data.vertices))


def local_bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def find_bone(arm, exact_names=(), contains=()):
    by_lower = {b.name.lower(): b for b in arm.data.bones}
    for n in exact_names:
        b = by_lower.get(n.lower())
        if b:
            return b
    for b in arm.data.bones:
        low = b.name.lower()
        if any(k.lower() in low for k in contains):
            return b
    return None


def bone_point_in_obj(arm, bone, obj, tail=False):
    p = bone.tail_local if tail else bone.head_local
    world = arm.matrix_world @ p
    return obj.matrix_world.inverted() @ world


def make_vest(body, arm):
    vest = body.copy()
    vest.data = body.data.copy()
    vest.animation_data_clear()
    bpy.context.collection.objects.link(vest)
    vest.name = 'Police_Vest'
    vest.data.name = 'Police_Vest_Mesh'

    lo, hi = local_bounds(body)
    size = hi - lo
    h = max(size.z, 1e-5)

    hips = find_bone(arm, ('Hips', 'Pelvis'), ('hip', 'pelvis'))
    neck = find_bone(arm, ('Neck', 'Neck1'), ('neck',))
    ua_l = find_bone(arm, ('UpperArmL', 'UpperArm.L', 'upper_arm.L'), ('upperarm.l', 'upperarml', 'upper_arm.l'))
    ua_r = find_bone(arm, ('UpperArmR', 'UpperArm.R', 'upper_arm.R'), ('upperarm.r', 'upperarmr', 'upper_arm.r'))

    z_low = lo.z + size.z * 0.45
    z_high = lo.z + size.z * 0.79
    if hips:
        hp = bone_point_in_obj(arm, hips, body)
        z_low = max(z_low, hp.z + size.z * 0.05)
    if neck:
        np = bone_point_in_obj(arm, neck, body)
        z_high = min(z_high, np.z - size.z * 0.015)

    x_left = lo.x + size.x * 0.20
    x_right = hi.x - size.x * 0.20
    if ua_l and ua_r:
        xl = bone_point_in_obj(arm, ua_l, body).x
        xr = bone_point_in_obj(arm, ua_r, body).x
        mn, mx = min(xl, xr), max(xl, xr)
        pad = max(size.x * 0.045, 0.01)
        x_left = max(lo.x, mn + pad)
        x_right = min(hi.x, mx - pad)

    bm = bmesh.new()
    bm.from_mesh(vest.data)
    bm.faces.ensure_lookup_table()
    delete_faces = []
    for f in bm.faces:
        c = f.calc_center_median()
        keep = (z_low <= c.z <= z_high and x_left <= c.x <= x_right)
        if not keep:
            delete_faces.append(f)
    bmesh.ops.delete(bm, geom=delete_faces, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(vest.data)
    bm.free()
    vest.data.update()

    if len(vest.data.polygons) < 20:
        raise RuntimeError(f'Vest extraction too small: {len(vest.data.polygons)} faces')

    # One clean material only; body itself remains untouched.
    vest.data.materials.clear()
    mat = bpy.data.materials.new('Police_Vest_MAT')
    mat.diffuse_color = (0.025, 0.045, 0.075, 1.0)
    mat.roughness = 0.72
    vest.data.materials.append(mat)
    for p in vest.data.polygons:
        p.material_index = 0

    # Preserve the original Armature modifier/weights from the duplicated torso.
    arm_mods = [m for m in vest.modifiers if m.type == 'ARMATURE']
    if not arm_mods:
        mod = vest.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm
    else:
        for m in arm_mods:
            m.object = arm

    # Deform first, then keep the vest slightly outside the animated shirt.
    shrink = vest.modifiers.new('Vest_Fit', 'SHRINKWRAP')
    shrink.target = body
    shrink.wrap_method = 'NEAREST_SURFACEPOINT'
    shrink.wrap_mode = 'OUTSIDE_SURFACE'
    shrink.offset = max(size.z * 0.0065, 0.008)

    solid = vest.modifiers.new('Vest_Thickness', 'SOLIDIFY')
    solid.thickness = max(size.z * 0.006, 0.008)
    solid.offset = 1.0
    solid.use_even_offset = True

    bevel = vest.modifiers.new('Vest_Edge_Soften', 'BEVEL')
    bevel.width = max(size.z * 0.0035, 0.004)
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'

    return vest, {
        'z_low': round(z_low, 5), 'z_high': round(z_high, 5),
        'x_left': round(x_left, 5), 'x_right': round(x_right, 5),
        'faces': len(vest.data.polygons), 'vertices': len(vest.data.vertices)
    }


def setup_walk_60(arm, action):
    ad = arm.animation_data_create()
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    a0, a1 = float(action.frame_range[0]), float(action.frame_range[1])
    span = max(1.0, a1 - a0)
    tr = ad.nla_tracks.new(); tr.name = 'Walk_60fps'
    st = tr.strips.new('Walk', 0, action)
    st.action_frame_start = a0
    st.action_frame_end = a1
    st.scale = 2.0
    st.repeat = 1.0
    st.blend_type = 'REPLACE'
    return int(round(span * 2.0))


def evaluated_bounds(objs):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in objs:
        e = obj.evaluated_get(dg)
        m = e.to_mesh()
        try:
            pts.extend(e.matrix_world @ v.co for v in m.vertices)
        finally:
            e.to_mesh_clear()
    if not pts:
        raise RuntimeError('No evaluated geometry')
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def evaluated_sample(obj, limit=120):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    e = obj.evaluated_get(dg)
    m = e.to_mesh()
    try:
        if not m.vertices:
            return []
        step = max(1, len(m.vertices) // limit)
        return [e.matrix_world @ m.vertices[i].co for i in range(0, len(m.vertices), step)][:limit]
    finally:
        e.to_mesh_clear()


def motion_qc(obj, end):
    scene = bpy.context.scene
    samples = sorted(set([0, end//4, end//2, (3*end)//4, end]))
    snaps = []
    for f in samples:
        scene.frame_set(f)
        snaps.append(evaluated_sample(obj))
    n = min(len(s) for s in snaps)
    if n < 10:
        raise RuntimeError('Too few vest sample vertices')
    ref = snaps[0][:n]
    amp = max((snaps[j][i] - ref[i]).length for j in range(1, len(snaps)) for i in range(n))
    if amp < 0.02:
        raise RuntimeError(f'Vest does not visibly follow animation: {amp}')
    return samples, round(amp, 6)


def create_floor(z, span):
    bpy.ops.mesh.primitive_plane_add(size=span, location=(0,0,z))
    obj = bpy.context.object
    mat = bpy.data.materials.new('Floor_MAT')
    mat.diffuse_color = (0.055, 0.06, 0.07, 1)
    mat.roughness = 0.9
    obj.data.materials.append(mat)


def create_camera(lo, hi):
    center = (lo + hi) * 0.5
    h = max(0.5, hi.z - lo.z)
    data = bpy.data.cameras.new('Camera')
    data.type = 'ORTHO'
    data.ortho_scale = h * 1.28
    cam = bpy.data.objects.new('Camera', data)
    bpy.context.collection.objects.link(cam)
    # 3/4 front view so the vest silhouette is easy to judge.
    cam.location = center + Vector((h * 0.85, -h * 3.0, h * 0.08))
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam


def main():
    reset()
    objs, actions = import_glb(ASSET)
    arm = find_armature(objs)
    meshes = [o for o in objs if o.type == 'MESH']
    body = find_body(meshes)
    walk = find_walk(actions)

    vest, cut = make_vest(body, arm)

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.render.fps = 60
    end = setup_walk_60(arm, walk)
    scene.frame_end = end

    sample_frames, vest_motion = motion_qc(vest, end)
    scene.frame_set(end // 2)
    lo, hi = evaluated_bounds(meshes + [vest])
    h = hi.z - lo.z
    create_floor(lo.z - 0.01, max(4.0, h * 3.0))
    create_camera(lo, hi)

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.studio_light = 'paint.sl'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = 'WORLD'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 30
    scene.render.filepath = os.path.join(FRAMES, 'frame_')

    report = {
        'blender_version': bpy.app.version_string,
        'base_asset': 'Quaternius Hoodie Character',
        'base_mesh': body.name,
        'walk_action': walk.name,
        'fps': 60,
        'frame_end': end,
        'vest_strategy': 'duplicate original rigged torso surface; crop torso faces; preserve original vertex groups + armature modifier; Shrinkwrap outside animated body; Solidify; Bevel',
        'vest_cut': cut,
        'vest_motion_sample_frames': sample_frames,
        'vest_visible_motion_amplitude': vest_motion,
        'no_retarget': True,
        'no_auto_weight': True,
        'no_bone_edits': True,
    }
    with open(os.path.join(ART, 'qc_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ART, 'Citizen_A_Police_Vest.blend'))
    bpy.ops.render.render(animation=True)
    print('POLICE_VEST_TEST_PASS')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
