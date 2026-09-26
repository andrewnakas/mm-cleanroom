"""2S2H's own 2ship.o2r, with the textures that reuse retail pixels regenerated.

    python -m ports.mm2s2h.clean_2ship <2ship.o2r in> <2ship.o2r out>

2ship.o2r is the port's archive (menus, fonts, HD extras made by the port authors).
A few of its textures are edits of retail ones (the taint scan lists them); those are
regenerated like any retail texture: coarse colour grid + alpha outline + our detail.
"""
import sys

import numpy as np

from cleanroom.decomp.gen import from_digest, h32
from cleanroom.decomp.spec import grid, alpha2
from cleanroom.gfx import texfmt
from games.mm import o2r
from games.mm.extract_spec import FMT

REGEN = [
    "objects/object_box/gBoxChestLockMajorTex",
    "objects/object_box/gBoxChestCornerMajorTex",
]


def main(argv):
    files = o2r.read_all(argv[1])
    n = 0
    for path in REGEN:
        if path not in files:
            print("missing", path)
            continue
        t = o2r.tex_parse(files[path])
        fmt, siz = FMT[t["type"]]
        rgba = texfmt.decode(t["data"], t["w"], t["h"], fmt, siz)
        d = {"type": t["type"], "w": t["w"], "h": t["h"], "grid": grid(rgba, 4)}
        if (rgba[..., 3] < 250).any():
            d["alpha2"] = alpha2(rgba[..., 3])
        img = from_digest(path, d).astype(np.int16)
        img[..., :3] += np.random.default_rng(h32("2ship", path)).integers(-14, 15, img.shape[:2] + (3,), dtype=np.int16)
        img = np.clip(img, 0, 255).astype(np.uint8)
        files[path] = o2r.tex_replace(files[path], texfmt.encode(img, fmt, siz))
        n += 1
    o2r.write_all(argv[2], files)
    print(f"2ship.o2r: {n} textures regenerated -> {argv[2]}")


if __name__ == "__main__":
    main(sys.argv)
