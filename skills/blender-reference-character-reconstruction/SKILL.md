# Blender Reference Character Reconstruction Skill

## Purpose
Build a reusable 3D character from one or more user-supplied reference images, with the goal of matching the reference as closely as possible in **shape, proportions, silhouette, materials, accessories and style from every important view**.

Use this skill when the user says things like:
- "build this exact character"
- "make the Blender model look like this image"
- "reconstruct this character in 3D"
- "collect all assets/parts needed from this image and build the full character"

This is a **visual reconstruction workflow**. It is different from the generic NPC modular pipeline. For high-fidelity reference matching, the reference image is the visual authority and a new master mesh may be required.

---

## Core rule
**Do not start rigging or animation until the static character matches the reference from the required views.**

The workflow is:

```text
user reference
-> analyze visible design
-> create canonical asset inventory
-> fill missing-view assumptions
-> collect/source reusable parts where appropriate
-> build static master mesh
-> render turnaround
-> compare against reference
-> refine until approved
-> only then rig + animate
```

---

## 1. Reference intake

### 1.1 Treat the user image as the primary visual source
Extract the following from the image before modeling:
- body proportions
- head/body ratio
- shoulder width
- torso length
- arm and leg thickness
- hand/foot scale
- silhouette
- clothing layers
- material/color blocks
- visible seams/panels
- hair/headwear
- accessories
- character style: realistic / stylized / low-poly / blocky / toon

Do not silently replace the style with the closest stock asset.

### 1.2 Determine reference completeness
Classify available information:

```text
A. front only
B. front + 3/4
C. front + side + back
D. full turnaround / model sheet
E. source 3D model exists
```

If only one image exists, every invisible surface must be explicitly treated as a **reconstruction assumption**, not factual source data.

### 1.3 Missing-view completion
Before 3D modeling, define missing areas:
- back of head/hair
- back and sides of clothing
- garment thickness
- side silhouette
- shoe sole and heel
- belt rear layout
- accessory rear surfaces
- hidden straps and connections

If needed, create a canonical concept/turnaround sheet for the project. This sheet becomes the design contract for parts not visible in the original image.

Important: an AI-generated or reconstructed turnaround is a **design decision**, not proof that the original hidden surfaces looked that way.

---

## 2. Mandatory asset inventory before building

Before opening Blender, create a complete part inventory.

### Standard human master inventory

```text
BODY
- Head
- Ears
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
- Hair_Back
- Hair_Side_L / Hair_Side_R
- Hair_Front
- Hat/Cap pieces if present

CLOTHING
- Shirt_Torso
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
- Vest_Strap_L
- Vest_Strap_R
- clips / flaps / pockets / panels

ACCESSORIES
- belt
- buckle
- radio
- antenna
- badge
- holster
- pouches
- straps
- role-specific props
```

For every new character, remove unused items and add reference-specific pieces.

### Asset inventory deliverable
Create one visual inventory image containing:
1. assembled front character,
2. front / 3/4 / side / back turnaround,
3. exploded or isolated major components,
4. material/color swatches,
5. labels for every build component.

This image is the build checklist for another agent.

---

## 3. Asset collection protocol

Do not search randomly for a complete character and force it to fit.

For each inventory component, use this priority order:

```text
1. Original/source asset of the exact character, if identifiable and legally usable.
2. Same creator / same asset pack / same art style component.
3. Existing project component already visually compatible.
4. CC0 / permissively licensed component with matching shape/style.
5. Custom-build the component from the reference.
```

### What should be sourced vs custom-built
Source assets when they save time **without changing the silhouette**:
- standard radio
- belt buckle
- generic pouch
- boot sole base
- simple cap base
- compatible skeleton / animation source

Custom-build when the reference identity depends on the exact shape:
- head silhouette
- torso silhouette
- vest shape
- hair silhouette
- cap silhouette
- main pants silhouette
- characteristic accessories

### Never collect assets by visual similarity alone
For every external asset record:
- asset name
- source URL
- creator
- license
- intended component
- whether it is used directly, modified, or only used as reference

Recommended manifest format:

```json
{
  "component": "Police_Radio",
  "source": "...",
  "creator": "...",
  "license": "CC0",
  "use": "reference-or-direct",
  "status": "approved"
}
```

Never assume a public download is reusable without checking its license.

---

## 4. Style lock before geometry

Create a small written style spec:

```text
STYLE: stylized low-poly
FACE: faceless/minimal
HEAD: oversized vs realistic human
TORSO: compact/blocky
LIMBS: chunky, not stick-thin
EDGES: lightly beveled
SURFACES: mostly flat planes
MATERIALS: solid color / low texture noise
DETAIL LEVEL: silhouette first, micro-detail second
```

Then define a fixed palette with material names and RGB/hex targets.

Once the style is approved, do not mix in realistic geometry or tactical-game assets that violate it.

---

## 5. Static modeling workflow

### Step 1 — blockout only
Build only major masses:
- head
- torso
- pelvis
- upper/lower arms
- upper/lower legs
- feet

Render front + side + 3/4 immediately.

Do not add accessories yet.

### Step 2 — match silhouette
Adjust until the following match the reference:
- total height ratio
- head size
- shoulder width
- torso taper
- hip width
- limb thickness
- hand size
- shoe size

Silhouette mismatch must be fixed before detail work.

### Step 3 — replace body areas with clothing geometry
For stylized low-poly characters, clothing often **is the visible body surface**.

Prefer:
- `Police_Shirt_Torso` instead of body torso + thick shirt shell
- `Police_Pants_Thigh` instead of body leg + floating trouser shell

Avoid unnecessary hidden body geometry under opaque clothing.

### Step 4 — outer gear
Add vest, cap, belt and major accessories only after the base silhouette passes.

### Step 5 — detail hierarchy
Add details in this order:

```text
large silhouette-changing pieces
-> medium panels/pockets
-> role-defining props
-> small clips/seams
```

Never spend time on micro-detail while head/torso/limb proportions are still wrong.

---

## 6. Geometry rules for this project

For the current stylized low-poly project:
- Use clean low-poly topology.
- Favor readable planar surfaces.
- Use bevels only to soften critical silhouette edges.
- No subdivision unless specifically required.
- Avoid crude large cubes as final costume geometry.
- Primitive meshes are acceptable for early blockout only.
- Final character parts must be shaped to the reference silhouette.
- Keep left/right symmetry where the reference is symmetrical.
- Keep accessories as separate named objects when modularity helps.

### Naming convention

```text
CHR_<Role>_<Part>_<Side>
```

Examples:

```text
CHR_Police_Head
CHR_Police_VestFront_L
CHR_Police_UpperArm_R
CHR_Police_Radio
```

---

## 7. Canonical view QC

A character is not approved from one attractive render.

Mandatory static QC views:
- FRONT
- 3/4 FRONT
- SIDE
- BACK
- 3/4 BACK

Use consistent camera scale and lighting.

### Overlay QC
When a corresponding reference view exists:
1. render the Blender model at matching camera orientation,
2. overlay the render against the reference,
3. compare silhouette and landmarks,
4. correct geometry,
5. repeat.

Priority landmarks:
- top of head/cap
- chin
- shoulders
- elbows
- wrists
- waist
- crotch
- knees
- ankles
- toe tip

Do not claim a percentage match without a defined comparison method.

---

## 8. Approval gate before rigging

Static model must pass all of the following:
- overall character reads as the same design immediately,
- front silhouette approved,
- side silhouette approved,
- back design coherent,
- 3/4 transition coherent,
- head size approved,
- clothing proportions approved,
- accessory positions approved,
- material palette approved,
- no obviously floating components.

Only after this gate should rigging begin.

---

## 9. Rigging and animation phase

For animation, prefer the proven project skeleton/Walk pipeline where possible, but do **not** distort the final model merely to preserve a stock body.

Safe order:

```text
approved static master mesh
-> choose/prove skeleton
-> fit skeleton inside final mesh
-> bind carefully
-> validate deformation
-> apply original/proven Walk when compatible
-> render motion QC
```

### Hard animation rules
- Never call auto-weighting successful without visual deformation checks.
- Never invent a walk if a proven compatible Walk exists.
- Do not alter the approved visual silhouette just to make rigging easier.
- Do not retarget blindly.
- Check wrists, elbows, knees, ankles and shoulders at multiple frames.

---

## 10. Mandatory build outputs

Every completed character task should return:

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

If animated:

```text
<Character>_walk_60fps.mp4
```

The `.blend` must contain real editable 3D meshes/materials and, when requested, rig/animation. Do not substitute AI images or billboards for the final 3D character.

---

## 11. Handoff package for another agent

When the user says "build this other character", first return a pre-build package containing:

### A. One canonical asset inventory image
Show all required parts and the full assembled target.

### B. Character build spec
Include:
- target style
- proportions
- palette
- object list
- source/reuse candidates
- custom-build parts
- assumptions for hidden surfaces

### C. Asset source manifest
Clearly distinguish:
- `EXACT SOURCE`
- `REUSABLE PROJECT PART`
- `EXTERNAL LICENSED PART`
- `CUSTOM BUILD`
- `DESIGN ASSUMPTION`

Then the build agent can execute without re-inventing the design.

---

## 12. Police reference example from this project

For the current stylized patrol police reference, the canonical component set is:

```text
HEAD
- faceless low-poly head
- ears
- short dark hair: front / sides / back
- patrol cap crown
- cap band
- cap brim
- cap badge

UPPER BODY
- neck
- navy police shirt torso
- split collar L/R
- short sleeves L/R
- sleeve cuffs L/R
- skin forearms L/R
- hands L/R

VEST
- front panel L
- front panel R
- back panel
- shoulder straps L/R
- vest clips
- three front pouches

POLICE DETAILS
- chest badge
- shoulder/chest radio
- radio grille
- radio antenna

BELT
- belt
- buckle
- holster
- left pouch
- right pouch
- rear pouch as needed

LOWER BODY
- navy pelvis
- thigh L/R
- shin L/R
- cargo pockets L/R
- knee panels L/R
- black boot L/R
- boot cuffs L/R
```

This component map should be used as the template for future role characters: replace the role-specific clothing/accessories while preserving the same asset-inventory-first workflow.

---

## Definition of DONE

A build is DONE only when:
1. the complete part inventory exists,
2. source/license decisions are recorded,
3. static model passes five-view visual QC,
4. `.blend` exists and opens,
5. all final visible parts are actual 3D meshes/materials,
6. contact sheet is visually inspected,
7. if animated, deformation is visually checked across the motion,
8. no claim of success is based only on script/CI output.

**Visual QC overrides CI success.**
