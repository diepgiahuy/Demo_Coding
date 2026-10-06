"""Refine box-blocked vehicle silhouettes. Safe to run once per freshly built kit."""
import bpy,math
from pathlib import Path
def refine():
    for col in bpy.data.collections:
        if col.name not in ['VEH_Sedan','VEH_Taxi','VEH_Police','VEH_Ambulance','VEH_DeliveryVan','FX_BurntCar']:continue
        if col.get('vehicle_refinement')=='1':continue
        van=col.name in ['VEH_Ambulance','VEH_DeliveryVan']
        for o in list(col.objects):
            if o.type!='MESH':continue
            base=o.name.split('.')[0]
            if base=='Cabin':
                for v in o.data.vertices:
                    if v.co.z>0:v.co.x*=.88;v.co.y*=.65
            if base=='Cab':
                for v in o.data.vertices:
                    if v.co.z>0 and v.co.y<0:v.co.y+=.28
            if base=='Windshield':
                o.location.y=-2.315 if van else -.901
                o.location.z=1.53 if van else 1.405
                o.rotation_euler.x=-.319 if van else -.527
            if base=='RearGlass' and not van:
                o.location.y=1.007;o.rotation_euler.x=.527
            if base=='SideWindow' and not van:
                sgn=1 if o.location.x>0 else -1
                front=o.location.y<0
                lower=(-.97,.015) if front else (.065,1.08)
                upper=(-.64,.015) if front else (.065,.76)
                verts=[(sgn*.806,lower[0],1.22),(sgn*.806,lower[1],1.22),(sgn*.718,upper[1],1.655),(sgn*.718,upper[0],1.655)]
                # Coordinates world/root local; root is identity in source collections.
                mesh=bpy.data.meshes.new('Tapered_Window');mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.materials.append(bpy.data.materials['glass'])
                o.data=mesh;o.location=(0,0,0);o.rotation_euler=(0,0,0)
                for mod in list(o.modifiers):o.modifiers.remove(mod)
        col['vehicle_refinement']='1'
if __name__=='__main__':
    OUT=Path(__file__).resolve().parent
    for file in ['Outbreak_Asset_Library.blend','Outbreak_Street_Demo.blend']:
        bpy.ops.wm.open_mainfile(filepath=str(OUT/file));refine();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/file))
        if 'Demo' in file:
            bpy.context.scene.render.filepath=str(OUT/'Street_Demo.png');bpy.ops.render.render(write_still=True)
