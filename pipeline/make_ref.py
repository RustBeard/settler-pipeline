# Build a color-coded reference .aseprite file: 8 directions x N frames, one tag per direction.
# Layer 0 = reference (part colors, half opacity, not exported), layer 1 = empty layer to draw on.
import struct, zlib, sys, json, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, RAW
from pixelize import analyze

DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
# part id -> RGBA. Character's LEFT = red tones, RIGHT = green tones (like ship lights).
COLORS = {
    # Left side = warm (red, yellow), right side = cool (blue, green). Hands strong, feet light.
    1: (112, 112, 112, 255),  # body – dark gray
    2: (238, 238, 238, 255),  # head – light gray
    3: (224, 32, 32, 255),    # hand.L – red
    4: (32, 96, 224, 255),    # hand.R – blue
    5: (245, 208, 0, 255),    # foot.L – yellow
    6: (32, 176, 64, 255),    # foot.R – green
    7: (122, 74, 40, 255),    # hair – brown
    9: (0, 0, 0, 255),        # eyes
}

def color_frame(path):
    lab, _, _ = analyze(path)
    out = np.zeros((*lab.shape, 4), np.uint8)
    for pid, c in COLORS.items(): out[lab == pid] = c
    return out

# ---------- minimal Aseprite writer (spec: aseprite/docs/ase-file-specs.md) ----------
def s_str(t):
    b = t.encode("utf-8"); return struct.pack("<H", len(b)) + b
def chunk(ctype, data): return struct.pack("<IH", 6 + len(data), ctype) + data

def layer_chunk(name, flags, opacity):
    return chunk(0x2004, struct.pack("<HHHHHHB3x", flags, 0, 0, 0, 0, 0, opacity) + s_str(name))

def cel_chunk(layer, img, duration_unused=None):
    ys, xs = np.where(img[:, :, 3] > 0)
    if len(ys) == 0: return None
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = np.ascontiguousarray(img[y0:y1, x0:x1])
    head = struct.pack("<HhhBHh5x", layer, int(x0), int(y0), 255, 2, 0)
    return chunk(0x2005, head + struct.pack("<HH", x1 - x0, y1 - y0) + zlib.compress(crop.tobytes()))

def tags_chunk(tags):
    d = struct.pack("<H8x", len(tags))
    for name, a, b in tags:
        d += struct.pack("<HHBH6x3Bx", a, b, 0, 0, 0, 0, 0) + s_str(name)
    return chunk(0x2018, d)

def palette_chunk(cols):
    d = struct.pack("<III8x", len(cols), 0, len(cols) - 1)
    for c in cols: d += struct.pack("<H4B", 0, *c)
    return chunk(0x2019, d)

def frame_bytes(chunks, duration):
    body = b"".join(chunks)
    return struct.pack("<IHHH2xI", 16 + len(body), 0xF1FA, min(len(chunks), 0xFFFF), duration, len(chunks)) + body

def write_ase(path, frames, w, h, layers, tags, duration, palette):
    out = []
    for i, cels in enumerate(frames):
        ch = []
        if i == 0:
            ch.append(palette_chunk(palette))
            ch += [layer_chunk(n, f, o) for n, f, o in layers]
            ch.append(tags_chunk(tags))
        ch += [c for c in cels if c]
        out.append(frame_bytes(ch, duration))
    body = b"".join(out)
    header = struct.pack("<IHHHHHIH II B3x H BB hhHH 84x".replace(" ", ""),
                         128 + len(body), 0xA5E0, len(frames), w, h, 32, 1, 100, 0, 0, 0,
                         len(palette), 1, 1, 0, 0, 16, 16)
    assert len(header) == 128
    open(path, "wb").write(header + body)

if __name__ == "__main__":
    anim = sys.argv[1] if len(sys.argv) > 1 else "walk"
    nf = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    dur = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    raw = RAW
    frames, tags, imgs = [], [], []
    for di, d in enumerate(DIRS):
        tags.append((f"{anim}_{d}", di * nf, di * nf + nf - 1))
        for f in range(nf):
            img = color_frame(f"{raw}/{anim}_{di}_{d}_{f}.png")
            imgs.append(img); frames.append([cel_chunk(0, img)])
    H, W = imgs[0].shape[:2]
    # reference layer: visible(1) + reference(64), half opacity; draw layer: visible(1) + editable(2)
    layers = [("wzorzec 3D", 1 | 64, 128), ("rysuj tutaj", 1 | 2, 255)]
    pal = [(0, 0, 0, 0)] + list(COLORS.values()) + [(238, 238, 238, 255), (206, 206, 206, 255)]
    dst = os.path.join(OUT, f"settler_{anim}_ref.aseprite")
    write_ase(dst, frames, W, H, layers, tags, dur, pal)
    # preview sheet: rows = directions, cols = frames
    sheet = np.zeros((H * 8, W * nf, 4), np.uint8)
    for i, img in enumerate(imgs):
        r, c = divmod(i, nf); sheet[r * H:(r + 1) * H, c * W:(c + 1) * W] = img
    bg = Image.new("RGBA", (W * nf, H * 8), (60, 60, 64, 255)); bg.alpha_composite(Image.fromarray(sheet))
    bg.resize((W * nf * 8, H * 8 * 8), Image.NEAREST).save(os.path.join(OUT, f"{anim}_ref_preview_x8.png"))
    print("wrote", dst, os.path.getsize(dst), "bytes,", len(frames), "frames")
