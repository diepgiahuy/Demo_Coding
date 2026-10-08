---
name: blender-reference-character-reconstruction
description: Reconstruct a user-supplied character reference as a real editable Blender 3D asset, including asset collection, custom modeling, five-view QC, .blend delivery, and optional rig/animation.
version: 1.1.0
updated: 2026-10-08
project: blender
---

# Blender Reference Character Reconstruction

## 0. Outcome

Use this skill when the user provides one or more character images and asks to build the same character in Blender.

This is not an image-description skill and not an asset-list-only skill.

Unless the user explicitly asks only for planning/research, the task is not complete until there is a real editable `.blend` plus rendered visual proof.

Default workflow:

```text
user reference
→ analyze visible design
→ create component inventory
→ collect/reuse/custom-build decisions
→ define hidden-view assumptions
→ lock style and palette
→ build actual 3D static master in Blender
→ render five canonical views
→ visually inspect and refine
→ save .blend
→ rig only after static approval
→ animate only after deformation approval
```

# 1. Governing rules

## Reference controls appearance

The user image is the visual authority.

Do not replace the target style with the nearest stock character because that stock asset already has a rig.

```text
REFERENCE CONTROLS APPEARANCE
RIG CONTROLS MOTION
DO NOT LET THE RIG CHOOSE THE APPEARANCE
```

## Static match before rigging

Final rigging must not begin until the static character passes:

- FRONT
- 3/4 FRONT
- SIDE
- BACK
- 3/4 BACK

## Visual QC overrides CI

A successful script/workflow proves only that the script ran.

A character is successful only after actual rendered frames are inspected.

# 2. Reference intake

Extract:

- head/body ratio
- shoulder width
- torso length and taper
- hip width
- arm/leg thickness
- hand/foot scale
- hair/headwear silhouette
- clothing layers
- material/color blocks
- pockets/panels
- straps/belts
- role props
- overall art style

Classify reference completeness:

```text
A — front only
B — front + 3/4
C — front + side + back
D — full turnaround/model sheet
E — exact source 3D model exists
```

Anything not visible is a reconstruction decision, not verified source information.

# 3. Hidden-view completion

Before final modeling, define missing areas such as:

- back of hair/headwear
- garment thickness
- side/back of vest or jacket
- rear belt layout
- hidden straps
- heel/sole
- accessory rear faces
- chest/back depth

Label every component decision as one of:

```text
EXACT SOURCE
VISIBLE REFERENCE
REUSABLE PROJECT PART
EXTERNAL LICENSED PART
CUSTOM BUILD
DESIGN ASSUMPTION
```

Never present a DESIGN ASSUMPTION as source fact.

# 4. Mandatory component inventory

Create the inventory before modeling.

```text
BODY
- Head
- Ear_L / Ear_R
- Neck
- Torso
- UpperArm_L / UpperArm_R
- Forearm_L / Forearm_R
- Hand_L / Hand_R
- Pelvis
- Thigh_L / Thigh_R
- Shin_L / Shin_R
- Foot_L / Foot_R

HEAD / HAIR
- Hair_Front
- Hair_Side_L / Hair_Side_R
- Hair_Back
- Hat/Cap/Helmet pieces

CLOTHING
- Shirt/Jacket_Torso
- Collar_L / Collar_R
- Sleeve_L / Sleeve_R
- Sleeve_Cuff_L / Sleeve_Cuff_R
- Pants_Pelvis
- Pants_Thigh_L / Pants_Thigh_R
- Pants_Shin_L / Pants_Shin_R
- Boots/Shoes

OUTER GEAR
- Vest_Front_L
- Vest_Front_R
- Vest_Back
- Shoulder_Strap_L / Shoulder_Strap_R
- clips
- pockets
- panels

ACCESSORIES
- Belt
- Buckle
- Radio
- Antenna
- Badge
- Holster
- Pouches
- Backpack
- role-specific props
```

Remove unused pieces and add character-specific ones.

# 5. Asset collection protocol

Do not search for one complete character and force it to fit.

Collect by component in this priority order:

```text
1. exact source asset of the character, legally usable
2. same creator / same pack / same art style part
3. existing project part that visually matches
4. permissively licensed external part
5. custom-build from the reference
```

Usually worth sourcing when they do not change silhouette:

- generic radio
- belt buckle
- simple pouch
- boot sole base
- simple cap base
- compatible skeleton
- compatible animation

Usually custom-build when identity depends on shape:

- head silhouette
- hair silhouette
- torso
- main shirt/jacket
- vest
- cap/helmet silhouette
- pants silhouette
- characteristic props

For every external asset record:

```json
{
  "component": "ComponentName",
  "source": "https://...",
  "creator": "Creator",
  "license": "CC0 / permissive / ...",
  "use": "direct | modified | reference-only",
  "status": "approved | rejected"
}
```

Never assume public download means reusable.

# 6. Style lock

Write a short style contract before detail modeling.

Example for the current city/outbreak project:

```text
STYLE: stylized low-poly
FACE: faceless/minimal
HEAD: slightly oversized
TORSO: compact/blocky
LIMBS: chunky, never stick-thin
EDGES: lightly beveled
SURFACES: readable flat planes
MATERIALS: mostly solid colors
DETAIL: silhouette first, micro-detail second
```

Do not mix a realistic tactical asset into a stylized target simply because it is detailed.

# 7. Blender build strategy

## 7.1 Static major masses first

Build:

- head
- torso
- pelvis
- upper/lower arms
- hands
- upper/lower legs
- feet

Render front, side and 3/4 immediately.

Fix silhouette before details.

## 7.2 Clothing may be the visible body

For opaque stylized clothing, the garment may replace hidden body surfaces.

Prefer:

```text
Police_Shirt_Torso
Police_Pants_Thigh_L
Police_Pants_Thigh_R
```

instead of stacking thick shells over unnecessary hidden body geometry.

## 7.3 Detail hierarchy

```text
large silhouette-changing pieces
→ medium panels/pockets
→ role-defining props
→ small clips/seams
```

Do not polish small accessories while proportions are wrong.

## 7.4 Primitive rule

Boxes, cylinders, frustums and extruded polygons are valid construction tools and blockout primitives.

They are not automatically acceptable final geometry.

Final visible geometry must be reshaped until its silhouette matches the reference.

## 7.5 Deterministic Python build pattern

The police reference build used an empty Blender scene plus a Python builder.

Useful helper concepts:

```python
make_material(...)
box(...)
cylinder(...)
frustum_box(...)
extruded_polygon(...)
elliptical_frustum(...)
camera_for_view(...)
render_view(...)
```

Scripting is used for repeatability and deterministic assembly, not as an excuse for crude geometry.

# 8. POLICE CASE STUDY — what failed and why the final method worked

This section is mandatory reading before building a new reference character.

## Target

Stylized patrol officer:

- faceless low-poly head
- slightly oversized head
- short dark hair
- navy patrol cap
- navy short-sleeve shirt
- compact black vest
- gold badge
- radio
- duty belt
- holster/pouches
- navy pants
- black boots
- chunky stylized limbs

## Failure A — use Quaternius SWAT directly

What passed technically:

- clean mesh
- original rig
- original skin weights
- original Walk

Why it failed:

- SWAT/tactical silhouette
- helmet/gear language
- too militarized
- did not match patrol-police reference

Lesson:

```text
GOOD RIG ≠ CORRECT CHARACTER
```

## Failure B — put crude primitive police gear on a stock body

What passed:

- gear followed body

Why it failed:

- vest looked like attached plates
- accessories looked pasted on
- target silhouette was wrong

Lesson:

Primitive blockout must be reshaped before final use.

## Failure C — swap parts between imported characters/armatures

What happened:

- body parts shifted to wrong positions
- imported object/bind transforms differed
- CI could pass while the frame visibly failed

Lesson:

Never assume compatible packs share identical imported transform/bind spaces. Verify the rendered result.

## Failure D — rebuild a walking body from rigid primitive bone pieces

What happened:

- movement followed bones
- visual proportions became mechanical and worse

Lesson:

Do not sacrifice the approved visual target for animation convenience.

## Successful change in strategy

The key realization was:

```text
STOP FORCING AN ANIMATED STOCK BODY TO BECOME THE REFERENCE.
BUILD THE REFERENCE FIRST.
```

The successful static police proof started from an empty Blender scene and created the target geometry part-by-part.

Actual build order:

```text
1. boots
2. boot cuffs
3. shins
4. thighs
5. pelvis
6. police shirt torso
7. neck
8. collar
9. sleeves
10. forearms
11. hands
12. faceless head
13. ears
14. hair
15. cap crown
16. cap band
17. cap brim
18. cap badge
19. vest front L/R
20. vest back
21. vest shoulder straps
22. vest pouches
23. chest badge
24. radio
25. radio grille/antenna
26. belt
27. buckle
28. holster
29. belt pouches
30. cargo/knee panels
```

Then the workflow rendered:

```text
FRONT
3/4 FRONT
SIDE
BACK
3/4 BACK
```

The actual rendered frames were inspected, then the geometry was refined:

- head enlarged
- body thickened
- cap lowered/widened
- limbs thickened
- vest silhouette cleaned

That is why this approach worked better: **the reference controlled geometry instead of the stock rig controlling geometry.**

# 9. Police example inventory

```text
HEAD
- Head_Faceless
- Ear_L
- Ear_R
- Hair_Front
- Hair_Side_L
- Hair_Side_R
- Hair_Back
- Police_Cap_Crown
- Police_Cap_Band
- Police_Cap_Brim
- Cap_Badge

UPPER BODY
- Neck
- Police_Shirt_Torso
- Collar_L
- Collar_R
- Sleeve_L
- Sleeve_R
- Sleeve_Cuff_L
- Sleeve_Cuff_R
- Forearm_L
- Forearm_R
- Hand_L
- Hand_R

VEST
- Vest_Front_L
- Vest_Front_R
- Vest_Back
- Vest_Strap_L
- Vest_Strap_R
- Vest_Clip_L
- Vest_Clip_R
- Vest_Pouch_01
- Vest_Pouch_02
- Vest_Pouch_03

POLICE DETAILS
- Chest_Badge
- Radio
- Radio_Grille
- Radio_Antenna

BELT
- Belt
- Buckle
- Holster
- Pouch_L
- Pouch_R
- Rear_Pouch

LOWER BODY
- Police_Pelvis
- Pant_Thigh_L
- Pant_Thigh_R
- Pant_Shin_L
- Pant_Shin_R
- Cargo_L
- Cargo_R
- Knee_L
- Knee_R
- Boot_L
- Boot_R
- Boot_Cuff_L
- Boot_Cuff_R
```

# 10. Reference implementation in the Blender project

Repository:

```text
diepgiahuy/Demo_Coding
```

Concrete implementation:

```text
branch: police-ref-build
builder: police_reference_build.py
workflow: .github/workflows/police-reference-build.yml
output: Police_Officer_Reference.blend
```

Another agent with repository access should inspect this implementation before building a new reference character.

Use it to learn:

- empty-scene setup
- deterministic named-part generation
- material creation
- multi-view camera setup
- render output
- QC/report generation
- `.blend` saving

Do not blindly copy police geometry for another role.

# 11. Five-view QC

Mandatory:

```text
FRONT
3/4 FRONT
SIDE
BACK
3/4 BACK
```

Use consistent camera scale/lighting.

When matching source views exist, overlay render and reference.

Compare:

- top of head/hat
- chin
- shoulders
- elbows
- wrists
- waist
- crotch
- knees
- ankles
- toe tip

Fix silhouette before surface detail.

# 12. Static approval gate

Do not rig until:

- character reads immediately as the same design
- front passes
- side passes
- back is coherent
- 3/4 transitions are coherent
- head size passes
- clothing proportions pass
- accessory locations pass
- palette passes
- no obvious floating/intersecting components

# 13. Rigging after static approval

```text
approved static master
→ choose/prove skeleton
→ fit skeleton to final character
→ bind carefully
→ test deformation
→ reuse proven Walk if compatible
→ render motion QC
```

The project may reuse Quaternius animation data as a motion source, but final visual geometry must not be distorted to become a Quaternius stock body.

Do not:

- blindly auto-weight and call it done
- blindly retarget
- invent a procedural walk if a compatible proven Walk exists
- change approved proportions just to fit a rig

Check shoulders, elbows, wrists, knees, ankles, foot contact, root motion and loop continuity.

# 14. Mandatory deliverables

Static:

```text
<Character>.blend
<Character>_front.png
<Character>_three_quarter.png
<Character>_side.png
<Character>_back.png
<Character>_three_quarter_back.png
<Character>_contact_sheet.png
asset_manifest.json
qc_report.json
```

Animated additionally:

```text
<Character>_walk_60fps.mp4
```

The `.blend` must contain real editable 3D meshes/materials.

# 15. Definition of DONE

DONE only when:

1. component inventory exists
2. source/license/use decisions are recorded
3. hidden surfaces are labeled source vs assumption
4. actual Blender geometry exists
5. `.blend` opens
6. five-view renders exist
7. contact sheet was visually inspected
8. obvious silhouette problems were corrected
9. if animated, deformation was visually checked
10. success is not based only on CI/script output

# 16. Handoff instruction for another agent

Provide:

```text
A. original user reference(s)
B. this SKILL.md
C. component inventory
D. style/palette spec
E. asset_manifest.json
F. hidden-view assumptions
G. reference implementation path
```

Recommended prompt:

```text
Use blender-reference-character-reconstruction.
Do not stop at planning.
Build the real Blender asset.
Treat my image as the visual authority.
Read the police case study and inspect the reference builder.
Use police only as a workflow example, not as geometry to copy.
Return the .blend plus five-view QC renders.
```
