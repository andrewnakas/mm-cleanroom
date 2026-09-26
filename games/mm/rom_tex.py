"""DIRTY ROOM (dev only): decode textures straight from the decompressed ROM + decomp XML.

    python -m games.mm.rom_tex <dec rom> <xml dir> <out.png> <name regex> [--scale 3] [--max 200]

For looking only (contact sheets to write briefs); outputs are never published.
"""
import glob
import os
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

from cleanroom.gfx import texfmt

FMTS = {"rgba32": (texfmt.RGBA, texfmt.B32), "rgba16": (texfmt.RGBA, texfmt.B16), "ci4": (texfmt.CI, texfmt.B4),
        "ci8": (texfmt.CI, texfmt.B8), "i4": (texfmt.I, texfmt.B4), "i8": (texfmt.I, texfmt.B8),
        "ia4": (texfmt.IA, texfmt.B4), "ia8": (texfmt.IA, texfmt.B8), "ia16": (texfmt.IA, texfmt.B16),
        "ia1": (texfmt.IA, texfmt.B4)}
HERE = os.path.dirname(os.path.abspath(__file__))


def files(rom, filelist):
    names = open(filelist).read().split()
    out = {}
    for i, n in enumerate(names):
        vs, ve, ps, pe = struct.unpack(">4I", rom[0x1A500 + 16 * i:0x1A510 + 16 * i])
        out[n] = rom[vs:ve]
    return out


def textures(xml_dir):
    """yield (file, name, fmt, w, h, offset, tlut_offset)"""
    for p in sorted(glob.glob(os.path.join(xml_dir, "**", "*.xml"), recursive=True)):
        txt = open(p, encoding="utf-8").read()
        for fm in re.finditer(r'<File Name="(\w+)"[^>]*>(.*?)</File>', txt, re.S):
            for m in re.finditer(r"<Texture ([^>]*)/>", fm.group(2)):
                a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
                if "Offset" not in a:
                    continue
                yield (fm.group(1), a["Name"], a["Format"].lower(), int(a["Width"]), int(a["Height"]),
                       int(a["Offset"], 16), int(a["TlutOffset"], 16) if "TlutOffset" in a else None)


def decode(fdata, fmt, w, h, off, tl):
    f, s = FMTS[fmt]
    n = texfmt.texel_bytes(w, h, s)
    data = fdata[off:off + n]
    pal = None
    if f == texfmt.CI:
        ne = 16 if s == texfmt.B4 else 256
        if tl is None:
            pal = np.stack([np.arange(ne) * (255 // (ne - 1))] * 3 + [np.full(ne, 255)], -1).astype(np.uint8)
        else:
            raw = fdata[tl:tl + 2 * ne]
            ne = len(raw) // 2
            pal = texfmt.decode(raw, ne, 1, texfmt.RGBA, texfmt.B16)[0]
            pal = np.concatenate([pal] * (256 // max(ne, 1) + 1))[:256]
    return texfmt.decode(data, w, h, f, s, palette=pal)


def main(argv):
    rom = open(argv[1], "rb").read()
    xml_dir, out, rx = argv[2], argv[3], re.compile(argv[4])
    scale = int(argv[argv.index("--scale") + 1]) if "--scale" in argv else 3
    mx = int(argv[argv.index("--max") + 1]) if "--max" in argv else 200
    fl = os.path.join(os.path.dirname(xml_dir.rstrip("/\\")), "..", "extractor", "filelists", "mm.txt")
    fs = files(rom, fl)
    tiles = []
    for fname, name, fmt, w, h, off, tl in textures(xml_dir):
        if not rx.search(fname + "/" + name) or fname not in fs:
            continue
        try:
            img = decode(fs[fname], fmt, w, h, off, tl)
        except Exception as e:  # noqa
            continue
        im = Image.fromarray(img, "RGBA")
        bg = Image.new("RGBA", im.size, (255, 0, 255, 255))
        bg.alpha_composite(im)
        tiles.append((f"{fname[:14]}/{name[1:30]}", bg.convert("RGB").resize((w * scale, h * scale), Image.NEAREST)))
        if len(tiles) >= mx:
            break
    cw = max(max(t[1].width for t in tiles), 200)
    ch = max(t[1].height for t in tiles) + 12
    cols = max(1, 1600 // cw)
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * cw, rows * ch), (40, 40, 40))
    d = ImageDraw.Draw(S)
    for k, (lab, im) in enumerate(tiles):
        x, y = (k % cols) * cw, (k // cols) * ch
        S.paste(im, (x, y + 12))
        d.text((x + 2, y), lab, fill=(255, 255, 0))
    S.save(out)
    print(len(tiles), "tiles ->", out, S.size)


if __name__ == "__main__":
    main(sys.argv)
