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
    "GormanBrothers": "object_in", "Gorman": "object_ah", "Grog": "object_hs",
    "GuruGuru": "object_fu", "Kafei": "object_test3", "Kamaro": "object_mk",
    "MadameAroma": "object_al", "MadameAromaBright": "object_al", "MayorDotour": "object_dt",
    "Postman": "object_pm", "Romani": "object_ma1", "RosaSisters": "object_rz",
    "Shiro": "object_sdn", "Toto": "object_zm", "ToiletHand": "object_bjt",
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


def parse_anim(d):
    p = o2r.HDR
    if struct.unpack("<I", d[p:p + 4])[0] != 0:
        return None                                   # only "Normal" animations
    p += 4 + 2
    n = struct.unpack("<I", d[p:p + 4])[0]
    p += 4
    vals = np.frombuffer(d[p:p + 2 * n], "<i2").astype(np.int32)
    p += 2 * n
    m = struct.unpack("<I", d[p:p + 4])[0]
    p += 4
    idx = np.frombuffer(d[p:p + 6 * m], "<u2").reshape(m, 3).astype(np.int32)
    return vals, idx


def _rot(rx, ry, rz):
    a, b, c = (v * np.pi / 32768.0 for v in (rx, ry, rz))
    X = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    Y = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    Z = np.array([[np.cos(c), -np.sin(c), 0], [np.sin(c), np.cos(c), 0], [0, 0, 1]])
    return Z @ Y @ X                                   # Matrix_RotateZYX: X applied first


def posed(files, skel_path, obj):
    """world matrices (row-vector 4x4) per limb, frame 0 of the object's idle animation,
    and the flex matrix list (limbs with a display list, in draw order)"""
    names = parse_skel(files[skel_path])
    limbs = [parse_limb(files[n]) if n in files else None for n in names]
    anims = [n for n in files if n.startswith(f"objects/{obj}/") and o2r.rtype(files[n]) == "OANM"]
    anims.sort(key=lambda n: (0 if re.search(r"(Idle|Wait|Stand)", n) else 1, n))
    frame = None
    for a in anims:
        pa = parse_anim(files[a])
        if pa and len(pa[1]) == len(limbs) + 1:
            frame = pa
            break
    world, flex = {}, []

    def val(i):
        return int(frame[0][i]) if frame is not None and i < len(frame[0]) else 0

    def walk(i, parent):
        if i == 0xFF or i >= len(limbs) or limbs[i] is None:
            return
        lb = limbs[i]
        t = lb["t"]
        if i == 0 and frame is not None:
            t = tuple(val(k) for k in frame[1][0])
        r = tuple(val(k) for k in frame[1][i + 1]) if frame is not None else (0, 0, 0)
        C = np.eye(4)
        C[:3, :3] = _rot(*r)
        C[:3, 3] = t
        W = parent @ C
        world[i] = W
        if lb["dl"]:
            flex.append(W.T.astype(np.float32))
        walk(lb["child"], W)
        walk(lb["sib"], parent)
    walk(0, np.eye(4))
    return limbs, {i: W.T.astype(np.float32) for i, W in world.items()}, flex


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
        limbs, world, flex = posed(files, sk, obj)
        for i, lb in enumerate(limbs):
            if not lb or not lb["dl"] or lb["dl"] not in files or i not in world:
                continue
            tex = dl_textures(arc, lb["dl"])
            eyes = any((isinstance(t, tuple) and t[1] == 8) or (isinstance(t, str) and "Eye" in t) for t in tex)
            if eyes:
                parts = [(lb["dl"], world[i])]
                c = lb["child"]                    # hair, hats, masks hang off the head
                while c != 0xFF and c < len(limbs) and limbs[c]:
                    if limbs[c]["dl"] in files and c in world:
                        parts.append((limbs[c]["dl"], world[c]))
                    c = limbs[c]["sib"]
                if best is None or len(limbs) > best[0]:
                    best = (len(limbs), parts, flex)
    return (best[1], best[2]) if best else (None, None)


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
    parts, flex = head_parts(arc, files, obj)
    if not parts:
        return None
    R = Renderer(arc, size * ss, cull=True)
    R.segments = face_segments(files, obj)
    R.limb_mtx = flex
    marks = {t for dl, _ in parts for t in dl_textures(arc, dl) if isinstance(t, str) and re.search(r"(Eye|Face)", t)}
    if R.segments.get(8):
        marks.add(R.segments[8])
    R.mark = marks
    best = None
    for y in (0, 45, 90, 135, 180, 225, 270, 315):      # the view that shows the most of the eyes
        for pt in (-20, 5):
            img = R.draw(parts, y, pt, 0, margin=0.12)
            score = R.mark_px
            if best is None or score > best[0]:
                best = (score, img)
    big = best[1]
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
