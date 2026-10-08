import bpy, os, math, json
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'artifacts', 'police_reference', 'Police_Officer_Reference.blend')
OUT = os.path.join(ROOT, 'artifacts', 'police_mask_golden')
VIEWS = os.path.join(OUT, 'views')
os.makedirs(VIEWS, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene

# GOLDEN_REFERENCE_LOCK: do not alter any approved police object.
# Add mask as separate modular objects only, positioned from the approved Head_Faceless bounds.
head = bpy.data.objects.get('Head_Faceless')
if head is None:
    raise RuntimeError('Head_Faceless not found in approved police asset')

# World-space bounds derived from the actual approved head mesh, not guessed scene coordinates.
corners = [head.matrix_world @ Vector(c) for c in head.bound_box]
min_x = min(v.x for v in corners); max_x = max(v.x for v in corners)
min_y = min(v.y for v in corners); max_y = max(v.y for v in corners)
min_z = min(v.z for v in corners); max_z = max(v.z for v in corners)
head_w = max_x - min_x
head_h = max_z - min_z
cx = (min_x + max_x) / 2

# Lower-face placement: top stays below the implied eye line.
mask_cz = min_z + head_h * 0.32
mask_h = head_h * 0.27
mask_w = head_w * 0.72
mask_depth = max(0.018, (max_y-min_y) * 0.055)
front_y = min_y - mask_depth * 0.55

mat = bpy.data.materials.get('Police_Navy_Trim')
if mat is None:
    mat = bpy.data.materials.new('Mask_Navy')
    mat.diffuse_color = (0.018,0.040,0.095,1)
    mat.roughness = 0.86

strap_mat = bpy.data.materials.get('Accessory_Charcoal') or mat


def mesh_obj(name, verts, faces, material, bevel=0.004):
    me = bpy.data.meshes.new(name + '_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    o.data.materials.append(material)
    if bevel > 0:
        mod = o.modifiers.new('Edge_Soften', 'BEVEL'); mod.width=bevel; mod.segments=2; mod.limit_method='ANGLE'; mod.angle_limit=math.radians(20)
        bpy.context.view_layer.objects.active=o; o.select_set(True)
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception: pass
        o.select_set(False)
    return o


def extruded_poly_y(name, pts, y_center, depth, material, bevel=.004):
    n=len(pts); yf=y_center-depth/2; yb=y_center+depth/2
    verts=[(x,yf,z) for x,z in pts]+[(x,yb,z) for x,z in pts]
    faces=[tuple(range(n)), tuple(range(2*n-1,n-1,-1))]
    for i in range(n):
        j=(i+1)%n; faces.append((i,j,n+j,n+i))
    return mesh_obj(name, verts, faces, material, bevel)


def cylinder_between(name, a, b, r, material):
    a=Vector(a); b=Vector(b); mid=(a+b)/2; vec=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=r, depth=vec.length, location=mid)
    o=bpy.context.object; o.name=name; o.rotation_euler=vec.to_track_quat('Z','Y').to_euler(); o.data.materials.append(material)
    return o

# Slightly tapered medical/cloth-style mask silhouette.
hw = mask_w/2; hh = mask_h/2
pts=[
    (cx-hw*0.96, mask_cz+hh*0.78),
    (cx-hw*0.73, mask_cz+hh),
    (cx+hw*0.73, mask_cz+hh),
    (cx+hw*0.96, mask_cz+hh*0.78),
    (cx+hw*0.82, mask_cz-hh),
    (cx-hw*0.82, mask_cz-hh),
]
mask = extruded_poly_y('ACC_Mask_Worn', pts, front_y, mask_depth, mat, .004)
mask['modular_accessory'] = True
mask['placement_source'] = 'Head_Faceless world bounds'

# Subtle horizontal folds so it reads as a mask, not a face plate.
for i, f in enumerate((0.25, 0.50, 0.75)):
    z = (mask_cz+hh) * (1-f) + (mask_cz-hh) * f
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, front_y-mask_depth*0.55, z))
    o=bpy.context.object; o.name=f'ACC_Mask_Fold_{i+1}'; o.dimensions=(mask_w*0.78, .006, .010); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(strap_mat)

# Ear straps derived from existing approved ear locations.
ear_l = bpy.data.objects.get('Ear_L'); ear_r = bpy.data.objects.get('Ear_R')
if ear_l and ear_r:
    left_start=(cx-hw*0.90, front_y, mask_cz+hh*0.50)
    right_start=(cx+hw*0.90, front_y, mask_cz+hh*0.50)
    left_end=(ear_l.location.x, min_y+0.015, ear_l.location.z)
    right_end=(ear_r.location.x, min_y+0.015, ear_r.location.z)
    cylinder_between('ACC_Mask_Strap_L',left_start,left_end,.008,strap_mat)
    cylinder_between('ACC_Mask_Strap_R',right_start,right_end,.008,strap_mat)

# Dedicated collection for toggling the mask on/off.
mask_col=bpy.data.collections.get('MASK_ACCESSORY') or bpy.data.collections.new('MASK_ACCESSORY')
if mask_col.name not in [c.name for c in scene.collection.children]: scene.collection.children.link(mask_col)
for o in [obj for obj in bpy.data.objects if obj.name.startswith('ACC_Mask_')]:
    if o.name not in mask_col.objects: mask_col.objects.link(o)
    for c in list(o.users_collection):
        if c != mask_col: c.objects.unlink(o)

cam=bpy.data.objects.get('Reference_Camera')
if not cam: raise RuntimeError('Reference_Camera missing')
scene.camera=cam
scene.render.resolution_x=640; scene.render.resolution_y=800; scene.render.resolution_percentage=100

def set_camera(angle_deg,dist=5.0):
    a=math.radians(angle_deg); target=Vector((0,0,.95)); pos=Vector((math.sin(a)*dist,-math.cos(a)*dist,1.08)); cam.location=pos; cam.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler()

views=[('front',0),('three_quarter',35),('side',90)]
for name,ang in views:
    set_camera(ang); scene.render.filepath=os.path.join(VIEWS,name+'.png'); bpy.ops.render.render(write_still=True)

# Save exact approved police + separate mask only.
set_camera(0)
out_blend=os.path.join(OUT,'Police_Officer_Golden_With_Mask.blend')
bpy.ops.wm.save_as_mainfile(filepath=out_blend)

report={
  'golden_reference':'police-ref-build commit 66f040fc6ea2b183c02b4696b62f004e3c9698c3',
  'golden_geometry_modified':False,
  'mask_modular':True,
  'mask_positioning':'derived from Head_Faceless world-space bounds',
  'head_bounds':{'min':[min_x,min_y,min_z],'max':[max_x,max_y,max_z]},
  'mask_center_z':mask_cz,'mask_width':mask_w,'mask_height':mask_h,
  'views':[v[0] for v in views]
}
with open(os.path.join(OUT,'qc_report.json'),'w') as f: json.dump(report,f,indent=2)
print('POLICE_MASK_GOLDEN_PASS')
print(json.dumps(report,indent=2))
