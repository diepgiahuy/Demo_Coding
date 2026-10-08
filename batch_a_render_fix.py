import bpy, os
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'artifacts','golden_character_batch_a')
VIEWS=os.path.join(OUT,'views')
blend=os.path.join(OUT,'Golden_Character_Foundation_BatchA.blend')
bpy.ops.wm.open_mainfile(filepath=blend)
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.render.image_settings.file_format='PNG'
scene.display.shading.light='STUDIO'
scene.display.shading.studio_light='paint.sl'
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='WORLD'
scene.display.shading.background_type='VIEWPORT'
scene.display.shading.background_color=(0.035,0.042,0.055)
cam=bpy.data.objects.get('Reference_Camera'); scene.camera=cam
mask_names=['MASK_PREVIEW_SURGICAL','MASK_PREVIEW_CLOTH','MASK_PREVIEW_N95','MASK_PREVIEW_LOWERED']
for c in bpy.data.collections:
    if c.name.startswith(('POLICE_OFFICER_REFERENCE','CIV_MALE_','CIV_FEMALE_','WARDROBE_LIBRARY','HAIR_LIBRARY','MASK_PREVIEW_')):
        c.hide_render=(c.name not in mask_names)
spacing=.56; start=-(len(mask_names)-1)*spacing/2; offsets=[]
for i,n in enumerate(mask_names):
    c=bpy.data.collections.get(n); dx=start+i*spacing
    for o in c.objects: o.location.x+=dx
    offsets.append((c,dx))
cam.data.type='ORTHO'; cam.data.ortho_scale=.92
t=Vector((0,0,1.595)); pos=Vector((0,-5,1.595)); cam.location=pos; cam.rotation_euler=(t-pos).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1800; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.filepath=os.path.join(VIEWS,'mask_library_qc.png')
bpy.ops.render.render(write_still=True)
for c,dx in offsets:
    for o in c.objects: o.location.x-=dx
for c in bpy.data.collections: c.hide_render=False
scene.render.resolution_x=640; scene.render.resolution_y=800
bpy.ops.wm.save_as_mainfile(filepath=blend)
print('MASK_LIBRARY_QC_PASS')
