import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
ASSET_ROOT = ROOT / "assets" / "city_outbreak"
PEOPLE_ROOT = ASSET_ROOT / "people"
ART_ROOT = ROOT / "artifacts" / "city_outbreak"
FRAME_ROOT = ART_ROOT / "frames"
ART_ROOT.mkdir(parents=True, exist_ok=True)
FRAME_ROOT.mkdir(parents=True, exist_ok=True)

FRAME_START = 1
FRAME_END = 60
FPS = 30

REPORT = {
    "blender_version": bpy.app.version_string,
    "scene": "city outbreak POC",
    "sources": {
        "city": "Kenney City Kit Suburban GLB files",
        "vehicles": "Kenney Car Kit GLB files",
        "people": "Quaternius Animated Men/Women FBX files",
        "fx": "Blender procedural geometry and lights",
    },
    "assets": [],
    "people": [],
    "fx": {},
}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_material(name, color, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (*color[:3], color[3])
        for key in ("Roughness",):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = 0.6
        if emission > 0:
            for key in ("Emission Color", "Emission"):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = (*color[:3], color[3])
                    break
            for key in ("Emission Strength",):
                if key in bsdf.inputs:
                    bsdf.inputs[key].default_value = emission
    mat.diffuse_color = color
    return mat


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]


def import_fbx(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    try:
        bpy.ops.wm.fbx_import(filepath=str(path))
    except Exception:
        bpy.ops.import_scene.fbx(filepath=str(path))
    objects = [o for o in bpy.data.objects if o not in before_objects]
    actions = [a for a in bpy.data.actions if a not in before_actions]
    return objects, actions


def mesh_bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(depsgraph)
        for corner in ev.bound_box:
            points.append(ev.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("No mesh bounds")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def normalize_asset(objects, name, target_height, location, rotation_z=0.0):
    lo, hi = mesh_bounds(objects)
    height = max(hi.z - lo.z, 0.001)
    scale = target_height / height
    center = (lo + hi) * 0.5

    root = bpy.data.objects.new(name + "_Normalize", None)
    anchor = bpy.data.objects.new(name + "_Anchor", None)
    bpy.context.collection.objects.link(root)
    bpy.context.collection.objects.link(anchor)

    object_set = set(objects)
    top = [o for o in objects if o.parent not in object_set]
    for obj in top:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

    root.scale = (scale, scale, scale)
    root.location = (-center.x * scale, -center.y * scale, -lo.z * scale)
    root.parent = anchor
    anchor.location = location
    anchor.rotation_euler[2] = rotation_z
    return anchor, root, scale


def add_asset(path, name, height, location, rotation_z=0.0, category="asset"):
    objects = import_glb(path)
    anchor, root, scale = normalize_asset(objects, name, height, location, rotation_z)
    REPORT["assets"].append({
        "name": name,
        "category": category,
        "source": str(path.relative_to(ROOT)),
        "object_count": len(objects),
        "target_height": height,
        "scale": scale,
    })
    return anchor, root, objects


def add_box(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def add_road():
    asphalt = new_material("Asphalt", (0.08, 0.09, 0.10, 1.0))
    sidewalk = new_material("Sidewalk", (0.28, 0.29, 0.30, 1.0))
    line = new_material("RoadLine", (0.85, 0.82, 0.60, 1.0))

    add_box("Road_NS", (0, 0, -0.12), (4.5, 22, 0.1), asphalt)
    add_box("Road_EW", (0, 0, -0.11), (22, 4.5, 0.1), asphalt)

    add_box("Sidewalk_W", (-6.0, 0, -0.02), (1.4, 22, 0.12), sidewalk)
    add_box("Sidewalk_E", (6.0, 0, -0.02), (1.4, 22, 0.12), sidewalk)
    add_box("Sidewalk_S", (0, -6.0, -0.015), (22, 1.4, 0.12), sidewalk)
    add_box("Sidewalk_N", (0, 6.0, -0.015), (22, 1.4, 0.12), sidewalk)

    for y in (-17, -11, 11, 17):
        add_box(f"Lane_NS_{y}", (0, y, 0.005), (0.08, 2.2, 0.015), line)
    for x in (-17, -11, 11, 17):
        add_box(f"Lane_EW_{x}", (x, 0, 0.005), (2.2, 0.08, 0.015), line)

    white = new_material("Crosswalk", (0.85, 0.85, 0.82, 1.0))
    for i in range(-4, 5):
        add_box(f"Crosswalk_{i}", (i * 0.75, -5.1, 0.015), (0.22, 0.75, 0.02), white)


def find_armature(objects):
    arms = [o for o in objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("No armature in person asset")
    return max(arms, key=lambda a: len(a.data.bones))


def find_walk(actions):
    walks = [a for a in actions if "walk" in a.name.lower()]
    if not walks:
        raise RuntimeError(f"No walk action in {[a.name for a in actions]}")
    return sorted(walks, key=lambda a: len(a.name))[0]


def loop_action(armature, action):
    data = armature.animation_data_create()
    data.action = None
    track = data.nla_tracks.new()
    track.name = "WalkLoop"
    start = int(math.floor(action.frame_range[0]))
    end = int(math.ceil(action.frame_range[1]))
    strip = track.strips.new(action.name, FRAME_START, action)
    duration = max(end - start, 1)
    strip.action_frame_start = start
    strip.action_frame_end = end
    strip.repeat = max(1.0, (FRAME_END - FRAME_START + 1) / duration + 1.0)
    return action.name


def add_person(path, name, start, end, target_height=1.75):
    objects, actions = import_fbx(path)
    arm = find_armature(objects)
    walk = find_walk(actions)
    action_name = loop_action(arm, walk)
    anchor, root, scale = normalize_asset(objects, name, target_height, start, 0.0)

    direction = Vector(end) - Vector(start)
    if direction.length > 0.001:
        anchor.rotation_euler[2] = math.atan2(direction.y, direction.x) - math.pi / 2
    anchor.location = start
    anchor.keyframe_insert(data_path="location", frame=FRAME_START)
    anchor.location = end
    anchor.keyframe_insert(data_path="location", frame=FRAME_END)
    if anchor.animation_data and anchor.animation_data.action:
        for curve in anchor.animation_data.action.fcurves:
            for kp in curve.keyframe_points:
                kp.interpolation = "LINEAR"

    REPORT["people"].append({
        "name": name,
        "source": str(path.relative_to(ROOT)),
        "bones": len(arm.data.bones),
        "walk_action": action_name,
        "target_height": target_height,
        "scale": scale,
    })
    return anchor


def add_flame(location, name, scale=1.0, phase=0):
    orange = bpy.data.materials.get("FlameOrange") or new_material("FlameOrange", (1.0, 0.16, 0.015, 1.0), 5.0)
    yellow = bpy.data.materials.get("FlameYellow") or new_material("FlameYellow", (1.0, 0.65, 0.05, 1.0), 7.0)
    objs = []
    for i, mat in enumerate((orange, yellow, orange)):
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.45 * scale * (1.0 - i * 0.16), radius2=0.02, depth=1.8 * scale, location=(location[0] + (i-1)*0.16, location[1] + i*0.06, location[2] + 0.8*scale))
        obj = bpy.context.object
        obj.name = f"{name}_{i}"
        obj.data.materials.append(mat)
        base = obj.scale.copy()
        for frame, factor in ((1, 0.75), (10 + phase, 1.15), (20 + phase, 0.85), (35 + phase, 1.2), (50 + phase, 0.8), (60, 1.0)):
            f = max(FRAME_START, min(FRAME_END, frame))
            obj.scale = base * factor
            obj.keyframe_insert(data_path="scale", frame=f)
        objs.append(obj)
    return objs


def add_smoke(location, count=10):
    smoke_mat = bpy.data.materials.get("Smoke") or new_material("Smoke", (0.08, 0.08, 0.09, 1.0))
    puffs = []
    for i in range(count):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.55 + i*0.035, location=(location[0] + math.sin(i*1.7)*0.35, location[1] + math.cos(i*1.1)*0.25, location[2] + 0.8 + i*0.42))
        obj = bpy.context.object
        obj.name = f"Smoke_{i:02d}"
        obj.data.materials.append(smoke_mat)
        start = 1 + i * 3
        obj.scale = (0.25, 0.25, 0.25)
        obj.keyframe_insert(data_path="scale", frame=start)
        obj.keyframe_insert(data_path="location", frame=start)
        obj.scale = (1.0 + i*0.05, 1.0 + i*0.05, 1.0 + i*0.08)
        obj.location.z += 2.2 + i*0.12
        obj.location.x += math.sin(i) * 0.45
        obj.keyframe_insert(data_path="scale", frame=min(FRAME_END, start + 28))
        obj.keyframe_insert(data_path="location", frame=min(FRAME_END, start + 28))
        puffs.append(obj)
    return puffs


def add_explosion(location):
    blast_mat = new_material("Blast", (1.0, 0.24, 0.01, 1.0), 10.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=location)
    blast = bpy.context.object
    blast.name = "ExplosionFlash"
    blast.data.materials.append(blast_mat)
    for frame, s in ((1, 0.001), (25, 0.001), (28, 0.8), (32, 2.6), (37, 0.5), (42, 0.001), (60, 0.001)):
        blast.scale = (s, s, s)
        blast.keyframe_insert(data_path="scale", frame=frame)

    debris_mat = new_material("Debris", (0.12, 0.10, 0.08, 1.0))
    debris = []
    for i in range(14):
        angle = (math.tau / 14) * i
        bpy.ops.mesh.primitive_cube_add(size=0.18 + (i % 3)*0.05, location=location)
        obj = bpy.context.object
        obj.name = f"Debris_{i:02d}"
        obj.data.materials.append(debris_mat)
        obj.keyframe_insert(data_path="location", frame=27)
        obj.rotation_euler = (angle * 0.3, angle * 0.5, angle)
        obj.keyframe_insert(data_path="rotation_euler", frame=27)
        distance = 2.0 + (i % 4) * 0.6
        obj.location = (location[0] + math.cos(angle)*distance, location[1] + math.sin(angle)*distance, location[2] + 1.2 + (i % 5)*0.45)
        obj.rotation_euler = (angle * 2.0, angle * 1.3, angle * 1.8)
        obj.keyframe_insert(data_path="location", frame=40)
        obj.keyframe_insert(data_path="rotation_euler", frame=40)
        obj.location.z = 0.12
        obj.keyframe_insert(data_path="location", frame=60)
        debris.append(obj)
    return blast, debris


def add_lights():
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.025, 0.035, 0.055, 1.0)
        bg.inputs["Strength"].default_value = 0.45

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 2.2
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(28))

    area_data = bpy.data.lights.new("Fill", "AREA")
    area_data.energy = 800
    area_data.shape = "DISK"
    area_data.size = 12
    area = bpy.data.objects.new("Fill", area_data)
    bpy.context.collection.objects.link(area)
    area.location = (-8, -8, 14)
    area.rotation_euler = (math.radians(25), 0, math.radians(-35))

    for name, loc, color in (
        ("EmergencyRed", (4.2, -2.8, 2.4), (1.0, 0.02, 0.01)),
        ("EmergencyBlue", (5.0, -2.8, 2.4), (0.01, 0.08, 1.0)),
        ("FireLight", (-2.5, 3.0, 2.4), (1.0, 0.12, 0.01)),
    ):
        data = bpy.data.lights.new(name, "POINT")
        data.energy = 550 if name != "FireLight" else 900
        data.color = color
        data.shadow_soft_size = 2.0
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        if name.startswith("Emergency"):
            for frame, energy in ((1, 50), (8, 700), (15, 50), (22, 700), (30, 50), (38, 700), (46, 50), (54, 700), (60, 50)):
                data.energy = energy
                data.keyframe_insert(data_path="energy", frame=frame)


def add_camera():
    data = bpy.data.cameras.new("Camera")
    data.lens = 43
    camera = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(camera)
    camera.location = (21, -25, 15.5)
    target = Vector((0.0, 1.0, 1.8))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(FRAME_ROOT / "frame_")
    scene.render.film_transparent = False


def main():
    reset_scene()
    add_road()

    city = ASSET_ROOT / "city"
    cars = ASSET_ROOT / "cars"

    house_specs = [
        ("House_A", "house_type02.glb", 6.2, (-11.0, 11.0, 0.1), math.radians(180)),
        ("House_B", "house_type06.glb", 7.0, (11.0, 11.0, 0.1), math.radians(180)),
        ("House_C", "house_type12.glb", 6.3, (-11.0, -11.0, 0.1), 0.0),
        ("House_D", "house_type17.glb", 6.7, (11.0, -11.0, 0.1), 0.0),
    ]
    for name, filename, height, loc, rot in house_specs:
        add_asset(city / filename, name, height, loc, rot, "building")

    tree_positions = [(-6.5, 10, 0.12), (6.5, 10, 0.12), (-6.5, -10, 0.12), (6.5, -10, 0.12), (-10, 6.5, 0.12), (10, 6.5, 0.12)]
    for i, pos in enumerate(tree_positions):
        filename = "tree_large.glb" if i % 2 == 0 else "tree_small.glb"
        add_asset(city / filename, f"Tree_{i:02d}", 4.0 if i % 2 == 0 else 3.0, pos, 0.0, "tree")

    add_asset(cars / "ambulance.glb", "Ambulance", 1.9, (5.2, -2.5, 0.08), math.radians(90), "ambulance")
    add_asset(cars / "police.glb", "Police", 1.55, (-4.5, -2.2, 0.08), math.radians(-90), "police")
    add_asset(cars / "sedan.glb", "Sedan_A", 1.45, (2.6, 10.0, 0.08), 0.0, "car")
    add_asset(cars / "sedan.glb", "Sedan_B", 1.45, (-2.5, -11.0, 0.08), math.radians(180), "car")
    wreck_anchor, _, _ = add_asset(cars / "sedan.glb", "Wreck", 1.45, (-2.8, 3.2, 0.15), math.radians(35), "wreck")
    wreck_anchor.rotation_euler[0] = math.radians(18)

    men = PEOPLE_ROOT / "men" / "FBX"
    women = PEOPLE_ROOT / "women" / "FBX"
    add_person(men / "Male_Casual.fbx", "Walker_M1", (-7.0, -15.0, 0.12), (-7.0, 4.5, 0.12))
    add_person(men / "Male_Suit.fbx", "Walker_M2", (7.0, 15.0, 0.12), (7.0, -4.0, 0.12))
    add_person(women / "Female_Casual.fbx", "Walker_W1", (-15.0, 7.0, 0.12), (2.0, 7.0, 0.12))
    add_person(women / "Female_Dress.fbx", "Walker_W2", (15.0, -7.0, 0.12), (-2.0, -7.0, 0.12))

    flames = add_flame((-2.8, 3.2, 0.15), "VehicleFire", 1.2)
    smoke = add_smoke((-2.8, 3.2, 0.1), 11)
    blast, debris = add_explosion((-2.7, 3.0, 1.0))
    REPORT["fx"] = {
        "flames": len(flames),
        "smoke_puffs": len(smoke),
        "explosion_flash": blast.name,
        "debris": len(debris),
    }

    add_lights()
    add_camera()
    configure_render()

    scene = bpy.context.scene
    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()

    blend_path = ART_ROOT / "city_outbreak_poc.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    with open(ART_ROOT / "qc_report.json", "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=2)

    bpy.ops.render.render(animation=True)
    print("CITY_OUTBREAK_POC_PASS")
    print(json.dumps(REPORT, indent=2))


if __name__ == "__main__":
    main()
