import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets" / "city_outbreak"
ART = ROOT / "artifacts" / "city_outbreak"
FRAMES = ART / "frames"
ART.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)
START, END, FPS = 1, 60, 30

report = {
    "blender_version": bpy.app.version_string,
    "scene": "city outbreak POC",
    "assets": [],
    "people": [],
    "fx": {},
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgba, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = rgba
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.62
        if emission:
            for key in ("Emission Color", "Emission"):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = rgba
                    break
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = emission
    return m


def box(name, loc, scl, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scl
    o.data.materials.append(mat)
    return o


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def import_fbx(path):
    before_o = set(bpy.data.objects)
    before_a = set(bpy.data.actions)
    try:
        bpy.ops.wm.fbx_import(filepath=str(path))
    except Exception:
        bpy.ops.import_scene.fbx(filepath=str(path))
    return ([o for o in bpy.data.objects if o not in before_o],
            [a for a in bpy.data.actions if a not in before_a])


def bounds(objects):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objects:
        if o.type == "MESH":
            ev = o.evaluated_get(dg)
            pts.extend(ev.matrix_world @ Vector(c) for c in ev.bound_box)
    if not pts:
        raise RuntimeError("No mesh bounds")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def normalize(objects, name, height, loc, rz=0):
    lo, hi = bounds(objects)
    scale = height / max(hi.z - lo.z, 0.001)
    center = (lo + hi) * 0.5
    root = bpy.data.objects.new(name + "_Root", None)
    anchor = bpy.data.objects.new(name + "_Anchor", None)
    bpy.context.collection.objects.link(root)
    bpy.context.collection.objects.link(anchor)
    objset = set(objects)
    for o in [x for x in objects if x.parent not in objset]:
        world = o.matrix_world.copy()
        o.parent = root
        o.matrix_world = world
    root.scale = (scale,) * 3
    root.location = (-center.x * scale, -center.y * scale, -lo.z * scale)
    root.parent = anchor
    anchor.location = loc
    anchor.rotation_euler[2] = rz
    return anchor, scale


def asset(path, name, height, loc, rz, category):
    objs = import_glb(path)
    anchor, scale = normalize(objs, name, height, loc, rz)
    report["assets"].append({
        "name": name, "category": category,
        "source": str(path.relative_to(ROOT)),
        "objects": len(objs), "scale": scale,
    })
    return anchor


def road():
    asphalt = material("Asphalt", (0.07, 0.08, 0.09, 1))
    pavement = material("Pavement", (0.28, 0.29, 0.30, 1))
    white = material("RoadWhite", (0.88, 0.88, 0.84, 1))
    yellow = material("RoadYellow", (0.9, 0.7, 0.18, 1))
    box("Road_NS", (0, 0, -0.12), (4.5, 22, 0.1), asphalt)
    box("Road_EW", (0, 0, -0.11), (22, 4.5, 0.1), asphalt)
    box("Side_W", (-6, 0, -0.01), (1.4, 22, 0.12), pavement)
    box("Side_E", (6, 0, -0.01), (1.4, 22, 0.12), pavement)
    box("Side_N", (0, 6, -0.01), (22, 1.4, 0.12), pavement)
    box("Side_S", (0, -6, -0.01), (22, 1.4, 0.12), pavement)
    for y in (-17, -11, 11, 17):
        box("LaneY", (0, y, 0.01), (0.06, 2.2, 0.015), yellow)
    for x in (-17, -11, 11, 17):
        box("LaneX", (x, 0, 0.01), (2.2, 0.06, 0.015), yellow)
    for i in range(-4, 5):
        box("Crosswalk", (i * 0.75, -5.0, 0.02), (0.22, 0.75, 0.02), white)


def armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("Person has no armature")
    return max(arms, key=lambda o: len(o.data.bones))


def walk_action(actions):
    hits = [a for a in actions if "walk" in a.name.lower()]
    if not hits:
        raise RuntimeError(f"No walk action: {[a.name for a in actions]}")
    return sorted(hits, key=lambda a: len(a.name))[0]


def set_walk_loop(arm, action):
    data = arm.animation_data_create()
    data.action = None
    track = data.nla_tracks.new()
    track.name = "WalkLoop"
    a0 = int(math.floor(action.frame_range[0]))
    a1 = int(math.ceil(action.frame_range[1]))
    strip = track.strips.new(action.name, START, action)
    strip.action_frame_start = a0
    strip.action_frame_end = a1
    strip.repeat = max(1.0, (END - START + 1) / max(a1 - a0, 1) + 1.0)


def person(path, name, p0, p1):
    objs, actions = import_fbx(path)
    arm = armature(objs)
    act = walk_action(actions)
    set_walk_loop(arm, act)
    anchor, scale = normalize(objs, name, 1.75, p0, 0)
    d = Vector(p1) - Vector(p0)
    if d.length > 0.001:
        anchor.rotation_euler[2] = math.atan2(d.y, d.x) - math.pi / 2
    anchor.location = p0
    anchor.keyframe_insert(data_path="location", frame=START)
    anchor.location = p1
    anchor.keyframe_insert(data_path="location", frame=END)
    report["people"].append({
        "name": name, "source": str(path.relative_to(ROOT)),
        "bones": len(arm.data.bones), "walk_action": act.name,
        "scale": scale,
    })


def flame(loc):
    orange = material("FlameOrange", (1.0, 0.10, 0.01, 1), 7)
    yellow = material("FlameYellow", (1.0, 0.65, 0.03, 1), 9)
    out = []
    for i, m in enumerate((orange, yellow, orange)):
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.48 - i*0.08,
            radius2=0.03, depth=1.7-i*0.15,
            location=(loc[0] + (i-1)*0.14, loc[1]+i*0.05, loc[2]+0.75))
        o = bpy.context.object
        o.name = f"Flame_{i}"
        o.data.materials.append(m)
        base = o.scale.copy()
        for f, k in ((1,.8),(10,1.2),(20,.85),(30,1.25),(40,.8),(50,1.15),(60,.9)):
            o.scale = base * k
            o.keyframe_insert(data_path="scale", frame=f)
        out.append(o)
    return out


def smoke(loc, count=11):
    m = material("Smoke", (0.065, 0.065, 0.075, 1))
    out = []
    for i in range(count):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.5+i*.025,
            location=(loc[0]+math.sin(i*1.5)*.3, loc[1]+math.cos(i)*.2, loc[2]+.7+i*.4))
        o = bpy.context.object
        o.name = f"Smoke_{i:02d}"
        o.data.materials.append(m)
        f0 = 1+i*3
        o.scale = (.2,)*3
        o.keyframe_insert(data_path="scale", frame=f0)
        o.keyframe_insert(data_path="location", frame=f0)
        o.scale = (1+i*.04, 1+i*.04, 1.15+i*.05)
        o.location.z += 2.0+i*.1
        o.location.x += math.sin(i)*.4
        f1 = min(END, f0+26)
        o.keyframe_insert(data_path="scale", frame=f1)
        o.keyframe_insert(data_path="location", frame=f1)
        out.append(o)
    return out


def explosion(loc):
    m = material("Explosion", (1.0, .18, .01, 1), 12)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=loc)
    blast = bpy.context.object
    blast.name = "ExplosionFlash"
    blast.data.materials.append(m)
    for f, s in ((1,.001),(25,.001),(28,.8),(32,2.5),(37,.45),(42,.001),(60,.001)):
        blast.scale = (s,)*3
        blast.keyframe_insert(data_path="scale", frame=f)
    dm = material("Debris", (.12,.09,.07,1))
    debris=[]
    for i in range(14):
        a = math.tau*i/14
        bpy.ops.mesh.primitive_cube_add(size=.16+(i%3)*.05, location=loc)
        o=bpy.context.object
        o.name=f"Debris_{i:02d}"
        o.data.materials.append(dm)
        o.keyframe_insert(data_path="location", frame=27)
        dist=2+(i%4)*.55
        o.location=(loc[0]+math.cos(a)*dist, loc[1]+math.sin(a)*dist, loc[2]+1+(i%5)*.4)
        o.rotation_euler=(a*1.2,a*1.8,a*2.1)
        o.keyframe_insert(data_path="location", frame=40)
        o.keyframe_insert(data_path="rotation_euler", frame=40)
        o.location.z=.12
        o.keyframe_insert(data_path="location", frame=60)
        debris.append(o)
    return blast,debris


def lighting():
    world=bpy.data.worlds.new("World")
    bpy.context.scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value=(.025,.035,.055,1)
    bg.inputs["Strength"].default_value=.55
    sd=bpy.data.lights.new("Sun","SUN"); sd.energy=2.0
    sun=bpy.data.objects.new("Sun",sd); bpy.context.collection.objects.link(sun)
    sun.rotation_euler=(math.radians(35),math.radians(-20),math.radians(30))
    ad=bpy.data.lights.new("Fill","AREA"); ad.energy=900; ad.shape="DISK"; ad.size=12
    ao=bpy.data.objects.new("Fill",ad); bpy.context.collection.objects.link(ao); ao.location=(-8,-8,14)
    ao.rotation_euler=(math.radians(25),0,math.radians(-35))
    for name,loc,col,energy in (
        ("Red",(5,-2.5,2.2),(1,0.01,0.01),650),
        ("Blue",(5.6,-2.5,2.2),(0.01,0.05,1),650),
        ("Fire",(-2.8,3.1,2.0),(1,.08,.01),1000)):
        ld=bpy.data.lights.new(name,"POINT"); ld.energy=energy; ld.color=col; ld.shadow_soft_size=1.8
        lo=bpy.data.objects.new(name,ld); bpy.context.collection.objects.link(lo); lo.location=loc
        if name in ("Red","Blue"):
            for f,e in ((1,40),(8,650),(15,40),(22,650),(30,40),(38,650),(46,40),(54,650),(60,40)):
                ld.energy=e; ld.keyframe_insert(data_path="energy", frame=f)


def camera():
    d=bpy.data.cameras.new("Camera"); d.lens=43
    c=bpy.data.objects.new("Camera",d); bpy.context.collection.objects.link(c)
    c.location=(21,-25,15.5)
    target=Vector((0,1,1.7))
    c.rotation_euler=(target-c.location).to_track_quat("-Z","Y").to_euler()
    bpy.context.scene.camera=c


def render_setup():
    s=bpy.context.scene
    s.render.engine="BLENDER_WORKBENCH"
    s.display.shading.light="STUDIO"
    s.display.shading.color_type="MATERIAL"
    s.display.shading.show_shadows=True
    s.display.shading.show_cavity=True
    s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100
    s.render.fps=FPS; s.frame_start=START; s.frame_end=END
    s.render.image_settings.file_format="PNG"; s.render.image_settings.color_mode="RGB"
    s.render.filepath=str(FRAMES/"frame_")
    report["renderer"]="BLENDER_WORKBENCH"


def main():
    reset(); road()
    city=ASSETS/"city"; cars=ASSETS/"cars"
    for name,file,h,loc,rz in (
        ("House_A","house_type02.glb",6.2,(-11,11,.1),math.pi),
        ("House_B","house_type06.glb",7.0,(11,11,.1),math.pi),
        ("House_C","house_type12.glb",6.3,(-11,-11,.1),0),
        ("House_D","house_type17.glb",6.7,(11,-11,.1),0)):
        asset(city/file,name,h,loc,rz,"building")
    for i,p in enumerate(((-6.5,10,.12),(6.5,10,.12),(-6.5,-10,.12),(6.5,-10,.12),(-10,6.5,.12),(10,6.5,.12))):
        file="tree_large.glb" if i%2==0 else "tree_small.glb"
        asset(city/file,f"Tree_{i}",4.0 if i%2==0 else 3.0,p,0,"tree")
    asset(cars/"ambulance.glb","Ambulance",1.9,(5.2,-2.5,.08),math.pi/2,"ambulance")
    asset(cars/"police.glb","Police",1.55,(-4.5,-2.2,.08),-math.pi/2,"police")
    asset(cars/"sedan.glb","Sedan_A",1.45,(2.6,10,.08),0,"car")
    asset(cars/"sedan.glb","Sedan_B",1.45,(-2.5,-11,.08),math.pi,"car")
    wreck=asset(cars/"sedan.glb","Wreck",1.45,(-2.8,3.2,.15),math.radians(35),"wreck")
    wreck.rotation_euler[0]=math.radians(18)
    men=ASSETS/"people"/"men"/"FBX"; women=ASSETS/"people"/"women"/"FBX"
    person(men/"Male_Casual.fbx","Walker_M1",(-7,-15,.12),(-7,4.5,.12))
    person(men/"Male_Suit.fbx","Walker_M2",(7,15,.12),(7,-4,.12))
    person(women/"Female_Casual.fbx","Walker_W1",(-15,7,.12),(2,7,.12))
    person(women/"Female_Dress.fbx","Walker_W2",(15,-7,.12),(-2,-7,.12))
    flames=flame((-2.8,3.2,.15)); puffs=smoke((-2.8,3.2,.1)); blast,debris=explosion((-2.7,3,1))
    report["fx"]={"flames":len(flames),"smoke_puffs":len(puffs),"explosion_flash":blast.name,"debris":len(debris)}
    lighting(); camera(); render_setup()
    bpy.context.scene.frame_set(START); bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(ART/"city_outbreak_poc.blend"))
    (ART/"qc_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    bpy.ops.render.render(animation=True)
    print("CITY_OUTBREAK_POC_PASS")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()