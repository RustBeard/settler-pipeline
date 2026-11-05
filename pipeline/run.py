# One command for the whole pipeline: model -> renders -> Aseprite reference -> preview page.
# Usage:
#   python3 pipeline/run.py characters/base/params.json [--anim walk] [--frames 6] [--frame-ms 167]
#                           [--original path/to/sprites.png --scale 10]
import argparse, json, os, subprocess, sys, glob, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import OUT, RAW, PX

ap = argparse.ArgumentParser()
ap.add_argument("params")
ap.add_argument("--anim", default="walk")
ap.add_argument("--frames", type=int, default=6, help="frames per direction in the sprite output")
ap.add_argument("--frame-ms", type=int, default=167)
ap.add_argument("--original", help="optional: your 8 sprites in one row (S..SE) for comparison")
ap.add_argument("--scale", type=int, default=1, help="pixel scale of --original")
a = ap.parse_args()

P = json.load(open(a.params))
cam = {"target_z": P.get("target_z", 8.0), "cam_dx": P.get("cam_dx", 0.5), "elev_deg": P.get("elev_deg", 30)}
N = P.get("walk_frames", 12)
assert N % a.frames == 0, f"walk_frames ({N}) must be a multiple of --frames ({a.frames})"

def py(*args):
    subprocess.run([sys.executable, *args], check=True, stdout=subprocess.DEVNULL)
def tmpjson(d):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(d, f); f.close(); return f.name

for f in glob.glob(f"{RAW}/*.png") + glob.glob(f"{PX}/*.png"): os.remove(f)
print("1/5 model + rig + animation"); py(f"{HERE}/build.py", "--", os.path.abspath(a.params))
print("2/5 idle renders");            py(f"{HERE}/render.py", "--", tmpjson({**cam, "only_idle": True}))
from pixelize import pixelize
from PIL import Image
for f in glob.glob(f"{RAW}/idle_*.png"):
    Image.fromarray(pixelize(f)).save(f"{PX}/{os.path.basename(f)}")
if a.original: py(f"{HERE}/compare.py", a.original, str(a.scale))
print(f"3/5 {a.anim} renders")
py(f"{HERE}/render.py", "--", tmpjson({**cam, "anim": a.anim, "render_frames": list(range(0, N, N // a.frames))}))
print("4/5 Aseprite reference");      py(f"{HERE}/make_ref.py", a.anim, str(a.frames), str(a.frame_ms))
print("5/5 preview page");            py(f"{HERE}/make_viewer.py", a.anim, str(a.frames))
print("done ->", OUT)
for f in sorted(os.listdir(OUT)):
    if os.path.isfile(os.path.join(OUT, f)): print("  ", f)
