# Blender NPC Character Pipeline Skill

## Purpose
Build reusable low-poly Blender NPCs that stay visually consistent with the proven Citizen pack and animate correctly without re-inventing rigging or locomotion.

This skill is the default workflow for civilians, police, workers, guards, soldiers, medics, outbreak crowds, and similar human NPCs in the Blender project.

## Verified baseline

### Asset ecosystem
Use **Quaternius – Ultimate Modular Men Pack** for male bases and compatible modular variants.

Verified from Quaternius official page:
- 11 different characters.
- 24 animations.
- Each character is divided into 4 models that can be swapped to create new combinations.
- Formats include FBX, OBJ, glTF and Blend.
- CC0; free for personal and commercial use.

Official source:
https://quaternius.com/packs/ultimatemodularcharacters.html

Poly Pizza's pack index independently lists these characters in the same pack:
- Adventurer
- King
- Farmer
- Hoodie Character
- Beach Character
- Casual Character
- Worker
- Punk
- SWAT
- Business Man
- Astronaut

Reference:
https://poly.pizza/bundle/Ultimate-Modular-Men-Pack-ZiH8muWqwQ

### Proven project baseline
The existing Citizen pipeline already produced working Blender characters using original Quaternius mesh/rig/weights/Walk data. Treat that working pipeline as the golden baseline.

Known-good principle:
**original character mesh + original armature + original skin weights + original Walk action**.

Do not replace a working body merely to match a costume reference.

## Hard rules

### Must preserve
1. Original proven armature.
2. Original proven skin weights.
3. Original Walk action from the same compatible asset ecosystem.
4. Existing bone orientation and hierarchy.
5. Existing character proportions unless a modular part from the same pack intentionally changes them.

### Never do by default
- Do not replace the body with an external T-pose mesh.
- Do not auto-weight a new external body onto the proven rig.
- Do not retarget to a different skeleton when a same-pack modular solution exists.
- Do not procedurally invent a walk cycle.
- Do not manually rotate/re-orient bones to make an unrelated asset fit.
- Do not build the whole outfit by wrapping the body in large cubes.
- Do not call a build successful because scripts/CI pass if the rendered visual is wrong.

If one of these exceptions is genuinely required, it must be treated as a separate R&D task and visually proven before replacing the baseline pipeline.

## Character construction workflow

### Step 1 — choose a proven base
Pick the closest existing same-pack character for the role.

Examples:
- casual civilian -> Hoodie / Casual / Business Man
- laborer -> Worker
- tactical/security base -> SWAT

Prefer changing appearance over changing body/rig.

### Step 2 — modular swap inside the same pack
Use same-pack modular pieces whenever possible.

Because the pack is explicitly designed with 4 swappable character models per character, same-pack swaps are preferred over cross-asset skinning.

Examples:
- head/hair from one compatible character
- torso from another
- lower body from another
- role-specific same-pack gear such as SWAT-derived pieces

Before finalizing, verify the imported objects still use the expected armature and no mesh is left unbound.

### Step 3 — materials
Use material changes for role identity before adding geometry.

Police example:
- shirt: navy blue
- trousers: dark navy
- shoes: black
- vest/gear: black or charcoal
- badge: small gold/yellow accent

Do not destroy original skin weights simply to recolor clothing.

### Step 4 — rigid accessories
For small non-deforming accessories, bone-parent rigid meshes rather than re-skinning the whole character.

Typical mapping:
- cap / helmet -> Head
- badge / radio / rigid chest gear -> Chest / Torso / suitable Spine bone
- utility belt / holster -> Hips / Pelvis

Use the actual bone names discovered in the imported armature. Never guess bone names. Script must search/validate them and fail if the required bone is not found.

Keep accessories small enough not to hide the original body silhouette or interfere visibly with arm/leg motion.

## Police-specific recipe

Goal: patrol-police silhouette matching the project's low-poly Citizen style, not a full tactical SWAT silhouette unless requested.

Preferred construction:
1. Start from an already-proven Quaternius male base.
2. Keep its original rig, weights and Walk.
3. Use SWAT parts only where they improve the police silhouette and remain compatible.
4. Reduce tactical appearance for patrol police:
   - navy shirt
   - dark navy trousers
   - black shoes
   - light black/charcoal vest if needed
   - police cap
   - small badge
   - utility belt
5. External free police models may be used as visual reference for silhouette/color/gear, but must not replace the proven animated body unless separately proven.

## Animation workflow

### Source
Use the original embedded/proven Walk action.

Do not create a new walk if a compatible Walk already exists.

### 30 fps source -> 60 fps preview
Blender animation timing is frame-based. If a Walk authored/validated at about 30 fps is previewed in a 60 fps scene without changing its strip duration, it plays twice as fast in real time.

To create a smoother 60 fps preview while preserving real-time duration:
1. Set scene FPS to 60.
2. Put the original Walk action in an NLA strip.
3. Preserve the action frame range.
4. Set NLA Playback Scale to 2.0 (or equivalently double the strip's scene-frame duration while preserving the source action range).
5. Keep interpolation from the original Action; do not edit the source keys just to create extra frames.
6. Verify resulting video duration against the original 30 fps walk duration.

Blender documentation confirms Playback Scale makes an NLA strip play faster for scale < 1 and slower for scale > 1.

Verified Blender reference:
https://docs.blender.org/manual/en/dev/editors/nla/sidebar.html

API reference:
https://docs.blender.org/api/5.3/bpy.types.NlaStrip.html

### Important
60 fps is a render/evaluation improvement, not permission to change the skeleton or invent intermediate pose keys manually.

## Script design

Python is an assembly/validation layer, not a replacement character artist.

Use Python for:
- importing GLB/FBX
- selecting known-good character variants
- modular swaps
- material assignment
- rigid bone-parent accessories
- selecting the Walk Action
- NLA setup
- scene/render configuration
- QC measurements
- saving .blend
- rendering verification frames/video

Do not use Python to procedurally build an entire humanoid from primitive cubes/cylinders when a proven character asset already exists.

## Required validation gates

A build is not complete until both automated and visual QC pass.

### Structural QC
- Armature exists.
- Expected Walk Action exists.
- Character meshes have the expected Armature modifier or correct original parenting.
- Original weighted meshes retain vertex groups.
- Required bones used for accessories exist.
- No NaN/non-finite transforms.
- Render output exists and has the expected FPS/resolution/frame count.

### Motion QC
Sample at minimum:
- first frame
- 25%
- 50%
- 75%
- final frame

Confirm:
- both feet move
- both hands/wrists move
- left/right limbs are not swapped
- knees do not flip backwards
- elbows do not twist unnaturally
- hands remain attached to wrists
- feet remain attached to ankles
- mesh remains attached to the skeleton
- body is not stuck in T-pose
- animation does not explode or stretch unexpectedly

Numeric limb-motion checks are useful but are **not enough**. A T-pose body with a moving hidden rig can still pass a naive bone-motion test.

### Visual QC
Render a contact sheet or representative frames from the actual evaluated/rendered mesh.

Reject the result if any of the following is visible:
- T-pose while rig bones animate
- detached body parts
- broken skin weights
- flipped limbs
- character hidden behind oversized gear
- incorrect silhouette
- costume inconsistent with reference
- camera crops hands/feet unintentionally

The final visual must be inspected before saying "done".

## Done definition
A character is DONE only when all are true:
- .blend exists
- rendered walk preview exists
- expected Walk is active
- body visibly follows the Walk
- no T-pose
- no detached limbs
- no elbow/knee inversion
- no obvious foot/hand disconnection
- role silhouette is recognizable
- style remains consistent with the proven Citizen set
- visual QC passes

CI success alone is not DONE.

## Crowd reuse
Once one role variant passes QC, preserve it as a master asset.

For many citizens:
- Hero/near: full proven rig.
- Mid crowd: small pool of proven rigged variants/actions.
- Far crowd: bake proven animation to evaluated mesh/cache variants and instance those; do not assume Geometry Nodes gives independent armature Action phases automatically.

Do not clone a character at scale before its single-character Walk passes QC.

## Failure recovery rule
If a new approach breaks animation or appearance, revert to the last proven character pipeline instead of stacking more fixes on the broken variant.

Priority order:
1. proven base character
2. same-pack modular swap
3. material recolor
4. small rigid accessories
5. only then consider new skinning/retargeting as separate R&D

## Verified references
- Quaternius Ultimate Modular Men Pack: https://quaternius.com/packs/ultimatemodularcharacters.html
- Poly Pizza Ultimate Modular Men Pack index: https://poly.pizza/bundle/Ultimate-Modular-Men-Pack-ZiH8muWqwQ
- Blender NLA sidebar / Playback Scale: https://docs.blender.org/manual/en/dev/editors/nla/sidebar.html
- Blender NlaStrip API: https://docs.blender.org/api/5.3/bpy.types.NlaStrip.html

## Short execution rule
When asked to create a new human NPC in this Blender project:

> Reuse the proven Quaternius character ecosystem. Preserve original rig, skin weights and Walk. Prefer same-pack modular swaps, materials and rigid bone-parented accessories. Do not replace the body or auto-weight an external T-pose by default. Render and visually inspect representative Walk frames. A successful script is not sufficient; only deliver after the visible animated mesh passes QC.
