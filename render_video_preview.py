import bpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'video_preview_artifacts'
FRAMES = OUT / 'frames'
OUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)

scene = bpy.context.scene
scene.render.resolution_x = 360
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# Sample the full original 1..48 animation into 16 frames.
samples = [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 44, 48]
for idx, src_frame in enumerate(samples, 1):
    scene.frame_set(src_frame)
    scene.render.filepath = str(FRAMES / f'frame_{idx:03d}.png')
    print(f'RENDER_PREVIEW_FRAME {idx}/{len(samples)} source={src_frame}', flush=True)
    bpy.ops.render.render(write_still=True)

print('VIDEO_FRAME_RENDER_PASS', flush=True)
