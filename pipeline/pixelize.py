# Turn raw data renders (R=part id, G=depth, B=normal z) into pixel-art frames
# using the original palette: light #EEEEEE, shadow #CECECE, outline #000000.
import numpy as np, sys, json, glob, os, re
from PIL import Image
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, RAW, PX, HERE, ROOT

P = json.load(open(sys.argv[1])) if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else {}
def p(k, d): return P.get(k, d)
F = p("supersample", 8)
SHADOW_NZ = p("shadow_nz", -0.25)
NO_LINE = {frozenset(x) for x in p("no_line_pairs", [[1, 2], [2, 7], [1, 7]])}  # body-head: no inner line
LIGHT, SHADE, INK = (238, 238, 238, 255), (206, 206, 206, 255), (0, 0, 0, 255)
EYE = 9
HAIR = 7
HAIR_L, HAIR_S = (120, 104, 96, 255), (96, 82, 76, 255)

def load(path):
    a = np.array(Image.open(path)).astype(np.float64)
    if a.max() > 255: a /= 65535.0
    else: a /= 255.0
    return a

def analyze(path):
    """Downscale a raw data render to sprite pixels: returns part labels, depth, normal z."""
    a = load(path)
    H, W = a.shape[0] // F, a.shape[1] // F
    a = a[:H * F, :W * F].reshape(H, F, W, F, 4).transpose(0, 2, 1, 3, 4).reshape(H, W, F * F, 4)
    lab = np.zeros((H, W), int); dep = np.zeros((H, W)); nz = np.zeros((H, W))
    for y in range(H):
        for x in range(W):
            blk = a[y, x]; cov = blk[:, 3] > 0.5
            if cov.mean() < p("coverage", 0.5): continue
            ids = np.rint(blk[cov, 0] * 16).astype(int)
            vals, cnt = np.unique(ids, return_counts=True)
            # eyes win if they cover a decent part of the block
            if EYE in vals and cnt[list(vals).index(EYE)] >= p("eye_cov", 0.15) * F * F: L = EYE
            else: L = vals[np.argmax(cnt)]
            sel = cov.copy(); sel[cov] = ids == L
            lab[y, x] = L; dep[y, x] = blk[sel, 1].mean(); nz[y, x] = blk[sel, 2].mean() * 2 - 1
    # pixel-art convention: an eye never touches the outline – keep one head pixel between them
    if p("eye_inward", True):
        moves = []
        for y, x in zip(*np.where(lab == EYE)):
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                q = (y + dy, x + dx)
                if 0 <= q[0] < H and 0 <= q[1] < W and lab[q] == 0:
                    t = (y - dy, x - dx)
                    if 0 <= t[0] < H and 0 <= t[1] < W and lab[t] in (2, HAIR):
                        moves.append(((y, x), t)); break
        for src, dst in moves:
            lab[src] = lab[dst]; dep[src] = dep[dst]; nz[src] = nz[dst]
        for src, dst in moves: lab[dst] = EYE
    return lab, dep, nz

def pixelize(path):
    lab, dep, nz = analyze(path)
    H, W = lab.shape
    out = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        for x in range(W):
            L = lab[y, x]
            nb = [(y + dy, x + dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= y + dy < H and 0 <= x + dx < W]
            if L == 0:
                if any(lab[q] != 0 for q in nb): out[y, x] = INK
                continue
            if L == EYE: out[y, x] = INK; continue
            behind = any(lab[q] not in (0, EYE, L) and frozenset((L, lab[q])) not in NO_LINE
                         and dep[y, x] > dep[q] + p("depth_eps", 0.012) for q in nb)
            if behind: out[y, x] = INK
            elif L == HAIR: out[y, x] = HAIR_S if nz[y, x] < SHADOW_NZ else HAIR_L
            else: out[y, x] = SHADE if nz[y, x] < SHADOW_NZ else LIGHT
    return out

if __name__ == "__main__":
    src, dst = RAW, PX
    os.makedirs(dst, exist_ok=True)
    for f in sorted(glob.glob(f"{src}/*.png")):
        Image.fromarray(pixelize(f)).save(f"{dst}/{os.path.basename(f)}")
    print("pixelized", len(glob.glob(f"{dst}/*.png")))
