"""DEV: dirty | clean face pairs for briefed characters (contact sheet, never published).

    python -m games.mm.face_preview <dec rom> <xml dir> <out.png> [object regex]
"""
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

from cleanroom.decomp.spec import grid, alpha2
from games.mm import faces
from games.mm.rom_tex import textures, files, decode


def main(argv):
    rom = open(argv[1], "rb").read()
    xml, out = argv[2], argv[3]
    rx = re.compile(argv[4] if len(argv) > 4 and not argv[4].startswith("--") else ".")
    fs = files(rom, xml.rstrip("/\\") + "/../../extractor/filelists/mm.txt")
    chars = faces.briefs()["chars"]
    use_drawn = "--drawn" in argv
    if use_drawn:
        from games.mm import drawn
    tiles = []
    for f, n, fmt, w, h, o, t in textures(xml):
        if use_drawn:
            if not rx.search(f + "/" + n) or "TLUT" in n:
                continue
        elif f not in chars or not rx.search(f) or "TLUT" in n or not re.search(r"(Eye|Mouth)", n):
            continue
        try:
            rgba = decode(fs[f], fmt, w, h, o, t)
        except (ValueError, KeyError):
            continue
        d = {"w": w, "h": h, "grid": grid(rgba, 4)}
        if (rgba[..., 3] < 250).any():
            d["alpha2"] = alpha2(rgba[..., 3])
        fmt_type = {"rgba32": 1, "rgba16": 2, "ci4": 3, "ci8": 4, "i4": 5, "i8": 6, "ia4": 7, "ia8": 8, "ia16": 9}.get(fmt, 0)
        d["type"] = fmt_type
        img = (drawn.texture(f"x/{f}/{n}", d) if use_drawn else faces.texture(f"objects/{f}/{n}", d))
        if img is None:
            continue
        pair = []
        for a in (rgba, np.clip(img, 0, 255).astype(np.uint8)):
            im = Image.fromarray(a, "RGBA")
            bg = Image.new("RGBA", im.size, (255, 0, 255, 255))
            bg.alpha_composite(im)
            s = min(96 / max(w, h), 3)
            pair.append(bg.convert("RGB").resize((int(w * s), int(h * s)), Image.NEAREST))
        tiles.append((f[7:] + " " + n[1:24], pair))
    cw, ch, cols = 200, 110, 8
    S = Image.new("RGB", (cw * cols, ch * ((len(tiles) + cols - 1) // cols)), (40, 40, 40))
    dr = ImageDraw.Draw(S)
    for k, (lab, (a, b)) in enumerate(tiles):
        x, y = (k % cols) * cw, (k // cols) * ch
        S.paste(a, (x, y + 12))
        S.paste(b, (x + a.width + 2, y + 12))
        dr.text((x + 1, y), lab, fill=(255, 255, 0))
    S.save(out)
    print(len(tiles), "pairs ->", out, S.size)


if __name__ == "__main__":
    main(sys.argv)
