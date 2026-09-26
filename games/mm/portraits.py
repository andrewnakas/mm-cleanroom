"""NPC portraits rendered from the game's own skeletons with our textures.

    python -m games.mm.portraits <clean mm.o2r> <out dir> [--sheet sheet.png] [--only regex]

Bombers' Notebook photos (32x32) are head shots: the head limb (the one whose display list
draws the eyes) plus its child limbs, in bind pose, on the notebook's light-blue backdrop,
with our drawn eyes/mouth bound to the segments the actor code would set.
Also a dev view of in-game faces (--all-heads).
"""
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

from games.mm import o2r
from games.mm.dlrender import Archive, Renderer

PHOTOS = {   # notebook photo -> character object (skeleton owner)
    "Anju": "object_an1", "AnjusGrandmother": "object_nb", "BombShopLady": "object_bba",
    "Bombers": "object_cs", "Cremia": "object_ma2", "CuriosityShopMan": "object_fsn",
    "GormanBrothers": "object_in", "Gorman": "object_ah", "Grog": "object_ds2n",
    "GuruGuru": "object_fu", "Kafei": "object_test3", "Kamaro": "object_mk",
    "MadameAroma": "object_al", "MadameAromaBright": "object_al", "MayorDotour": "object_dt",
    "Postman": "object_pm", "Romani": "object_ma1", "RosaSisters": "object_rz",
    "Shiro": "object_sdn", "Toto": "object_zm", "ToiletHand": "object_tsn",
}


def _str(d, p):
    n = struct.unpack("<i", d[p:p + 4])[0]
    return d[p + 4:p + 4 + n].decode("latin1"), p + 4 + n


def parse_limb(d):
    p = o2r.HDR
    ltype, skin = d[p], d[p + 1]
    p += 2
    _, p = _str(d, p)                                   # skinDList
    p += 2
    nmod = struct.unpack("<I", d[p:p + 4])[0]
    p += 4
    for _ in range(nmod):
        p += 2
        nv = struct.unpack("<i", d[p:p + 4])[0]
        p += 4 + nv * 10
        nt = struct.unpack("<i", d[p:p + 4])[0]
        p += 4 + nt * 8
    _, p = _str(d, p)                                   # skinDList2
    p += 12 + 6
    child, p = _str(d, p)
    sib, p = _str(d, p)
    dl, p = _str(d, p)
    dl2, p = _str(d, p)
    tx, ty, tz = struct.unpack("<3h", d[p:p + 6])
    ci, si = d[p + 6], d[p + 7]
    return {"dl": dl.replace("__OTR__", ""), "t": (tx, ty, tz), "child": ci, "sib": si}


def parse_skel(d):
    p = o2r.HDR
    p += 2
    limb_count, dl_count = struct.unpack("<II", d[p:p + 8])
    p += 8 + 1
    n = struct.unpack("<I", d[p:p + 4])[0]
    p += 4
    limbs = []
    for _ in range(n):
        s, p = _str(d, p)
        limbs.append(s.replace("__OTR__", ""))
    return limbs


def bind_pose(files, skel_path):
    names = parse_skel(files[skel_path])
    limbs = [parse_limb(files[n]) if n in files else None for n in names]
    pos = {}

    def walk(i, base):
        if i == 0xFF or i >= len(limbs) or limbs[i] is None:
            return
        lb = limbs[i]
        here = (base[0] + lb["t"][0], base[1] + lb["t"][1], base[2] + lb["t"][2])
        pos[i] = here
        walk(lb["child"], here)
        walk(lb["sib"], base)
    walk(0, (0, 0, 0))
    return limbs, pos


def dl_textures(arc, name, depth=0, out=None):
    """texture paths and segment numbers a display list (and its calls) loads"""
    out = out if out is not None else set()
    d = arc.files.get(name)
    if d is None or depth > 10:
        return out
    p = o2r.HDR + 4
    while p % 8:
        p += 1
    while p + 8 <= len(d):
        w0, w1 = struct.unpack("<II", d[p:p + 8])
        op = w0 >> 24
        if op in (0x20, 0x31, 0x32, 0x33, 0x35, 0x36):
            hi, lo = struct.unpack("<II", d[p + 8:p + 16])
            ref = arc.by_hash.get((hi << 32) | lo)
            if op == 0x20 and ref:
                out.add(ref)
            if op == 0x31 and ref:
                dl_textures(arc, ref, depth + 1, out)
            p += 16
            continue
        if op == 0xFD:
            out.add(("seg", (w1 >> 24) & 0xF))
        if op == 0xDF:
            break
        p += 8
    return out


def head_parts(arc, files, obj):
    skels = [n for n in files if n.startswith(f"objects/{obj}/") and o2r.rtype(files[n]) == "OSKL"]
    best = None
    for sk in skels:
        limbs, pos = bind_pose(files, sk)
        for i, lb in enumerate(limbs):
            if not lb or not lb["dl"] or lb["dl"] not in files:
                continue
            tex = dl_textures(arc, lb["dl"])
            eyes = any((isinstance(t, tuple) and t[1] == 8) or (isinstance(t, str) and "Eye" in t) for t in tex)
            if eyes:
                parts = [(lb["dl"], pos[i])]
                c = lb["child"]                    # hair, hats, masks hang off the head
                while c != 0xFF and c < len(limbs) and limbs[c]:
                    if limbs[c]["dl"] in files:
                        parts.append((limbs[c]["dl"], pos.get(c, pos[i])))
                    c = limbs[c]["sib"]
                if best is None or len(limbs) > best[0]:
                    best = (len(limbs), parts)
    return best[1] if best else None


def face_segments(files, obj):
    tex = [n for n in files if n.startswith(f"objects/{obj}/") and o2r.rtype(files[n]) == "OTEX"]
    def pick(words, avoid=("Closed", "Half", "Blink")):
        c = [t for t in tex if any(w in t.rsplit("/", 1)[1] for w in words)]
        good = [t for t in c if not any(a in t for a in avoid)]
        return (good or c or [None])[0]
    seg = {}
    e = pick(("EyeOpen", "EyesOpen", "Eye"))
    m = pick(("MouthClosed", "Mouth"), ("Open",))
    if e:
        seg[8] = e
    if m:
        seg[9] = m
    return seg


def render(arc, files, obj, size=32, ss=4, yaw=0, pitch=5):
    parts = head_parts(arc, files, obj)
    if not parts:
        return None
    R = Renderer(arc, size * ss, cull=True)
    R.segments = face_segments(files, obj)
    big = R.draw(parts, yaw, pitch, 0, margin=0.12)
    small = big.reshape(size, ss, size, ss, 4).mean((1, 3))
    a = small[..., 3:4]
    rgb = np.where(a > 0, small[..., :3] / np.maximum(a, 1e-6), 0)
    bg = np.zeros((size, size, 3), np.float32)
    yy = np.linspace(0, 1, size)[:, None]
    bg[:] = (np.array([0.62, 0.78, 0.95]) * (1 - 0.25 * yy[..., None]))[:, :, :]
    out = rgb * a + bg * (1 - a)
    out[:2, :] = out[-2:, :] = 0.55                    # the photo's grey frame
    out[:, :2] = out[:, -2:] = 0.55
    return np.concatenate([out, np.ones((size, size, 1), np.float32)], -1)


def main(argv):
    src, outdir = argv[1], argv[2]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    os.makedirs(outdir, exist_ok=True)
    files = o2r.read_all(src)
    arc = Archive(files)
    imgs = {}
    for photo, obj in PHOTOS.items():
        if only and not re.search(only, photo):
            continue
        img = render(arc, files, obj)
        if img is None:
            print("no head limb:", photo, obj)
            continue
        name = f"gBombersNotebookPhoto{photo}Tex"
        imgs[name] = img
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(outdir, name + ".png"))
    if "--sheet" in argv and imgs:
        tiles = [np.kron((v[..., :3] * 255).astype(np.uint8), np.ones((4, 4, 1), np.uint8)) for v in imgs.values()]
        cols = 7
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.concatenate(tiles[i:i + cols], 1) for i in range(0, len(tiles), cols)]
        Image.fromarray(np.concatenate(rows, 0)).save(argv[argv.index("--sheet") + 1])
    print(f"portraits: {len(imgs)} -> {outdir}")


if __name__ == "__main__":
    main(sys.argv)
