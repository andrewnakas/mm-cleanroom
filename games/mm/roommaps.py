"""Pause/minimap room floor plans (map_grand_static) from each room's own geometry.

    python -m games.mm.roommaps <clean mm.o2r> <out dir> [--sheet s.png] [--only regex] [--flip fx,fy,rot]

Each scene's minimap list (scene command 0x1C) names the map id of every room; map id 0x100+i is
gMapGrandStatic1xxTex. The room's display lists are rendered top-down as a silhouette, then drawn in
the map style: flat grey floor, bright outline with a soft glow, black outside (I4, tinted in game).
"""
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

from games.mm import o2r
from games.mm.dlrender import Archive, Renderer


def minimap_lists(files):
    out = {}
    for n in files:
        parts = n.split("/")
        if not (n.startswith("scenes/nonmq/") and len(parts) == 4 and parts[2] == parts[3]):
            continue
        d = files[n]
        for p in range(o2r.HDR, len(d) - 10):
            if struct.unpack_from("<I", d, p)[0] != 0x1C:
                continue
            cnt = struct.unpack_from("<I", d, p + 4)[0]
            if not 1 <= cnt <= 40 or p + 10 + cnt * 10 > len(d):
                continue
            ents = [struct.unpack_from("<5H", d, p + 10 + i * 10) for i in range(cnt)]
            if all(e[0] < 0x162 or e[0] == 0xFFFF for e in ents) and any(0x100 <= e[0] < 0x162 for e in ents):
                out[n] = ents
                break
    return out


def room_of_map(files):
    """map id -> (scene path, room index, flags)"""
    res = {}
    for scene, ents in sorted(minimap_lists(files).items()):
        for room, e in enumerate(ents):
            if 0x100 <= e[0] < 0x162 and e[0] not in res:
                res[e[0]] = (scene, room, e[4])
    return res


def silhouette(arc, scene, room, w, h, ss=3, margin=0.08):
    base = f"{scene}_room_{room:02d}"
    dls = sorted(n for n in arc.files if n.startswith(base) and n != base and o2r.rtype(arc.files[n]) == "ODLT")
    if not dls:
        return None
    S = max(w, h) * ss
    R = Renderer(arc, S, cull=False, alpha_min=-1)
    img = R.draw(dls, yaw=0, pitch=90, roll=0, margin=margin)
    cov = img[..., 3]
    ys, xs = np.nonzero(cov > 0.5)
    if not len(ys):
        return None
    cov = cov[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # fit into the texture keeping the aspect, with a margin for the glow
    ch, cw = cov.shape
    sc = min((w * ss * (1 - 2 * margin)) / cw, (h * ss * (1 - 2 * margin)) / ch)
    im = Image.fromarray((cov * 255).astype(np.uint8)).resize((max(1, int(cw * sc)), max(1, int(ch * sc))), Image.BILINEAR)
    canvas = Image.new("L", (w * ss, h * ss), 0)
    canvas.paste(im, ((w * ss - im.width) // 2, (h * ss - im.height) // 2))
    a = np.asarray(canvas, np.float32) / 255
    return a.reshape(h, ss, w, ss).mean((1, 3))


def style(m, fx=False, fy=False, rot=0):
    if fx:
        m = m[:, ::-1]
    if fy:
        m = m[::-1]
    if rot:
        m = np.rot90(m, rot)
    inside = (m > 0.5).astype(np.float32)
    edge = inside.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            edge = np.minimum(edge, np.roll(np.roll(inside, dy, 0), dx, 1))
    edge = inside - edge                                   # 1-px inner outline
    glow = np.zeros_like(inside)
    for r in (1, 2):
        g = np.zeros_like(inside)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                g = np.maximum(g, np.roll(np.roll(edge, dy, 0), dx, 1))
        glow = np.maximum(glow, g * (0.55 if r == 1 else 0.25))
    v = inside * 0.42 + glow * (1 - inside) + edge * 1.0
    return np.clip(v, 0, 1)


def main(argv):
    src, outdir = argv[1], argv[2]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    fx, fy, rot = (0, 1, 0)             # top-down render is upside down relative to the map
    if "--flip" in argv:
        fx, fy, rot = (int(v) for v in argv[argv.index("--flip") + 1].split(","))
    os.makedirs(outdir, exist_ok=True)
    files = o2r.read_all(src)
    arc = Archive(files)
    import json
    T = json.load(open(os.path.join(os.path.dirname(__file__), "spec", "textures.json")))
    rooms = room_of_map(files)
    done = {}
    for mid, (scene, room, flags) in sorted(rooms.items()):
        name = f"gMapGrandStatic{mid:X}Tex"
        path = f"map_grand_static/{name}"
        if path not in T or (only and not re.search(only, name)):
            continue
        d = T[path]
        m = silhouette(arc, scene, room, d["w"], d["h"])
        if m is None:
            continue
        v = style(m, bool(fx) ^ bool(flags & 1), bool(fy) ^ bool(flags & 2), rot)
        img = np.zeros((d["h"], d["w"], 4), np.uint8)
        img[..., :3] = (v * 255)[..., None].astype(np.uint8)
        img[..., 3] = 255
        Image.fromarray(img, "RGBA").save(os.path.join(outdir, name + ".png"))
        done[name] = img
    if "--sheet" in argv and done:
        tiles = [Image.fromarray(v).resize((v.shape[1] * 2, v.shape[0] * 2), Image.NEAREST) for v in done.values()]
        W = 1600
        x = y = rowh = 0
        S = Image.new("RGB", (W, 2000), (40, 40, 60))
        for t in tiles:
            if x + t.width > W:
                x, y, rowh = 0, y + rowh + 4, 0
            S.paste(t.convert("RGB"), (x, y))
            x += t.width + 4
            rowh = max(rowh, t.height)
        S.crop((0, 0, W, y + rowh)).save(argv[argv.index("--sheet") + 1])
    print(f"room maps: {len(done)} -> {outdir}")


if __name__ == "__main__":
    main(sys.argv)
