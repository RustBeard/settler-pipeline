# Side-by-side: original sprites (top) vs rendered idle frames (bottom), scaled up.
# Usage: compare.py <original.png> [pixel_scale]
# The original must hold 8 sprites in one row, in order S, SW, W, NW, N, NE, E, SE.
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import OUT, PX

DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
CELL = 24

def split_sprites(path, scale):
    a = np.array(Image.open(path).convert("RGBA"))[::scale, ::scale]
    cols = np.where((a[:, :, 3] > 0).any(0))[0]
    segs, s = [], cols[0]
    for c0, c1 in zip(cols, cols[1:]):
        if c1 != c0 + 1: segs.append((s, c0)); s = c1
    segs.append((s, cols[-1]))
    assert len(segs) == 8, f"expected 8 sprites, found {len(segs)}"
    return [a[:, x0:x1 + 1] for x0, x1 in segs]

def place(sheet, img, row, col):
    ys, xs = np.where(img[:, :, 3] > 0)
    crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape[:2]
    y0 = row * CELL + CELL - 2 - h; x0 = col * CELL + (CELL - w) // 2
    sheet[y0:y0 + h, x0:x0 + w] = crop

if __name__ == "__main__":
    orig = split_sprites(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    sheet = np.zeros((CELL * 2, CELL * 8, 4), np.uint8)
    for i in range(8):
        place(sheet, orig[i], 0, i)
        place(sheet, np.array(Image.open(f"{PX}/idle_{i}_{DIRS[i]}.png")), 1, i)
    bg = Image.new("RGBA", (sheet.shape[1], sheet.shape[0]), (120, 160, 200, 255))
    bg.alpha_composite(Image.fromarray(sheet))
    bg.resize((sheet.shape[1] * 8, sheet.shape[0] * 8), Image.NEAREST).save(f"{OUT}/compare.png")
    print("compare ok")
