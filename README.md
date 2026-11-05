# settler-pipeline

A simple 3D settler model → rig → animation → reference for drawing pixel art in Aseprite.

The model is a **reference**, not a finished sprite. It shows where each body part is in every frame and in each of the 8 directions. You draw the final pixel art over it by hand.

## Quick start

```
pip install -r requirements.txt      # Blender as a Python module (bpy), about 1 min
python3 pipeline/run.py characters/base/params.json
```

Optionally, compare with your own sprites (8 sprites in one row: S, SW, W, NW, N, NE, E, SE):

```
python3 pipeline/run.py characters/base/params.json --original sprites.png --scale 10
```

A full run takes about 10 s. Output goes to `out/`.

## What you get in `out/`

| File | What it's for |
|---|---|
| `settler_walk_ref.aseprite` | Drawing reference: 8 directions × 6 frames, one tag per direction, a reference layer + an empty "rysuj tutaj" ("draw here") layer |
| `viewer.html` | Preview: 3D animation next to the pixel-art animation, 8 directions, frame stepping |
| `settler.glb` | Model with rig and animation (e.g. for Godot) |
| `settler.blend` | The same for Blender |
| `settler_walk_sheet.png` | Gray pixel art (rows = directions, columns = frames) |
| `settler_walk_ref_sheet.png` | Color reference as a sprite sheet |
| `compare.png` | Your sprite vs. the render (only with `--original`) |

## Reference colors

The character's left side is warm, the right side is cool.

| Part | Color |
|---|---|
| Head | light gray |
| Hair | brown |
| Torso | dark gray |
| Left hand | red |
| Left foot | yellow |
| Right hand | blue |
| Right foot | green |
| Eyes | black |

## Model

1 unit = 1 sprite pixel. The character faces −Y; the ground is z = 0.

- **Head** – superellipsoid (between a sphere and a cube), buzz-cut hair.
- **Torso** – cylinder.
- **Hands and feet** – spheres, no arms or legs.
- **Rig** – 7 bones: `root`, `body`, `head`, `hand.L`, `hand.R`, `foot.L`, `foot.R`. Each part is rigid (weight 1).

## Parameters (`characters/base/params.json`)

### Shape

| Parameter | What it does |
|---|---|
| `head_c`, `head_r` | Head center and radii (x, y, z) |
| `head_roundness_n` | 2 = sphere; higher = closer to a cube (currently 3.6) |
| `hairline_front`, `hairline_side`, `hairline_back` | Hairline height: above the forehead, above the ears, at the nape (−1…1) |
| `body_c`, `body_radius`, `body_height` | Torso |
| `hand_x`, `hand_y`, `hand_z`, `hand_radius` | Hands (mirrored) |
| `foot_x`, `foot_y`, `foot_radius` | Feet (mirrored) |
| `eye_dx`, `eye_dz`, `eye_r` | Eyes |

### Walk

| Parameter | What it does |
|---|---|
| `walk_frames` | Frames in the 3D loop (must be a multiple of the sprite frame count) |
| `phase_offset` | Which step phase the first frame starts from |
| `stance` | Share of the cycle a foot stays on the ground (0.6 = 60%) |
| `stride_front`, `stride_back` | How far the foot reaches forward and back |
| `lift` | How high the foot lifts |
| `heel_kick` | 0 = the foot is highest mid-swing; 1 = the heel lifts behind first, then the foot swings forward (makes the foot visible in the N view) |
| `hand_swing`, `hand_arc` | Arm swing and how much the front hand rises |
| `hand_cross` | How far the front hand moves toward the body's midline (the back hand moves half that outward); adds sideways hand motion in the S and N views |
| `hand_even` | 0 = the hand copies the foot's motion (fast back swing); 1 = even timing, half the cycle forward and half back |
| `bob_up` | Share of each step the torso is up; 0.67 = with 6 frames, 1 frame down (foot lands) and 2 up. Not set = up only at the peak of the foot swing |

The torso and head always bob by exactly 1 px, so the head shape doesn't "swim."

### Camera

| Parameter | What it does |
|---|---|
| `elev_deg` | Camera angle above the horizon (top-down view) |
| `target_z`, `cam_dx` | Centering in the 24×24 frame and alignment to the pixel grid |

## How it works

1. `build.py` – builds the model, rig and animation in Blender; exports `.blend` and `.glb`.
2. `render.py` – renders 8 directions. Each pixel stores the body part, depth and surface direction.
3. `pixelize.py` – downscales the render to sprite pixels (majority vote), adds the outline and shading.
4. `make_ref.py` – builds the color reference and writes the `.aseprite` file.
5. `make_viewer.py` – builds the preview page.
6. `run.py` – runs everything in order.
