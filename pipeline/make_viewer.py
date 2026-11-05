# Build the preview page: 3D model with animation, synced pixel-art animation, sprite sheets, comparison.
import base64, io, sys, json, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, RAW, HERE
from pixelize import pixelize
from make_ref import color_frame

DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
anim, NF = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else ("walk", 6)

def sheet(fn):
    imgs = [fn(f"{RAW}/{anim}_{di}_{d}_{f}.png") for di, d in enumerate(DIRS) for f in range(NF)]
    H, Wd = imgs[0].shape[:2]
    s = np.zeros((H * 8, Wd * NF, 4), np.uint8)
    for i, im in enumerate(imgs):
        r, c = divmod(i, NF); s[r * H:(r + 1) * H, c * Wd:(c + 1) * Wd] = im
    return Image.fromarray(s), Wd, H

def b64png(img):
    b = io.BytesIO(); img.save(b, "PNG"); return base64.b64encode(b.getvalue()).decode()

gray, CW, CH = sheet(pixelize)
color, _, _ = sheet(color_frame)
gray.save(f"{OUT}/settler_{anim}_sheet.png"); color.save(f"{OUT}/settler_{anim}_ref_sheet.png")
t = open(f"{HERE}/viewer_template.html").read()
cfg = {"anim": anim, "nf": NF, "cw": CW, "ch": CH, "dirs": DIRS}
t = (t.replace("__CFG__", json.dumps(cfg))
      .replace("__GLB__", base64.b64encode(open(f"{OUT}/settler.glb", "rb").read()).decode())
      .replace("__GRAY__", b64png(gray)).replace("__COLOR__", b64png(color))
      .replace("__CMP__", base64.b64encode(open(f"{OUT}/compare.png", "rb").read()).decode() if os.path.exists(f"{OUT}/compare.png") else "")
      .replace("__CMP_HIDDEN__", "" if os.path.exists(f"{OUT}/compare.png") else "hidden"))
open(f"{OUT}/viewer.html", "w").write(t)
print("viewer ok", len(t))
