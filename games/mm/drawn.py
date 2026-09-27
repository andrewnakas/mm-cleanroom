"""Drawn textures for Majora's Mask: fonts, re-typeset labels, button glyphs, faces.

texture(path, d) -> RGBA float array (h, w, 4) or None (use the digest).
Text uses OFL fonts in games/mm/fonts (Marcellus for the message font,
Montserrat for labels, Noto Sans JP for the Shift-JIS font). Nothing here
reads retail pixels.
"""
import json
import os
import re
import unicodedata

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from games.mm import mm_labels as labels
from cleanroom.decomp.gen import from_digest, unpack_alpha2

HERE = os.path.dirname(__file__)
SERIF = os.path.join(HERE, "fonts", "Marcellus-Regular.ttf")
SANS = os.path.join(HERE, "fonts", "Montserrat-VF.ttf")
JP = os.path.join(HERE, "fonts", "NotoSansJP-Regular.ttf")
SS = 4                                   # supersampling
_fonts = {}


def font(which, px):
    k = (which, px)
    if k not in _fonts:
        f = ImageFont.truetype({"serif": SERIF, "jp": JP}.get(which, SANS), px)
        if which in ("sans", "sansx"):
            try:
                f.set_variation_by_name("ExtraBold" if which == "sansx" else "Bold")
            except Exception:
                pass
        _fonts[k] = f
    return _fonts[k]


def _down(m, w, h):
    return m.reshape(h, SS, w, SS).mean((1, 3))


def text_mask(lines, w, h, which="sans", align="center", size=None, pad_x=1, squeeze=0.62):
    """Coverage (h, w) of lines of text, auto-sized to fit, supersampled.
    Text that is too wide is first squeezed horizontally (down to `squeeze`), then shrunk."""
    W, H = w * SS, h * SS
    n = len(lines)
    lh = H / n
    px = size * SS if size else int(lh * 0.95)
    avail = W - 2 * pad_x * SS
    sq = 1.0
    while px > 4:
        f = font(which, px)
        widths = [f.getbbox(t)[2] - f.getbbox(t)[0] if t else 0 for t in lines]
        asc, desc = f.getmetrics()
        if (asc * 0.8 + desc * 0.35) <= lh * 1.02:
            need = max(widths) / max(avail, 1)
            if need <= 1:
                break
            if need <= 1 / squeeze:
                sq = 1 / need
                break
        px -= 1
    f = font(which, px)
    WW = int(W / sq)
    img = Image.new("L", (WW, H), 0)
    d = ImageDraw.Draw(img)
    cap = f.getbbox("H")
    ch = cap[3] - cap[1]
    pad = pad_x * SS / sq
    for i, t in enumerate(lines):
        if not t:
            continue
        bb = f.getbbox(t)
        tw = bb[2] - bb[0]
        x = {"center": (WW - tw) / 2, "left": pad, "right": WW - tw - pad}[align] - bb[0]
        y = i * lh + (lh - ch) / 2 - cap[1]
        d.text((x, y), t, font=f, fill=255)
    if WW != W:
        img = img.resize((W, H), Image.LANCZOS)
    return _down(np.asarray(img, np.float32) / 255.0, w, h)


def dilate(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx or dy:
                out = np.maximum(out, np.roll(np.roll(m, dy, 0), dx, 1) * (1.0 if abs(dx) + abs(dy) <= r else 0.7))
    return out


def outlined(m, fill=(255, 255, 255), edge=(10, 10, 10), r=1):
    h, w = m.shape
    o = dilate(m, r)
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = np.asarray(edge, np.float32)
    img[..., :3] = img[..., :3] * (1 - m[..., None]) + np.asarray(fill, np.float32) * m[..., None]
    img[..., 3] = np.clip(np.maximum(o, m), 0, 1) * 255
    return img


def grey_img(cov):
    h, w = cov.shape
    img = np.zeros((h, w, 4), np.float32)
    img[..., :] = (np.clip(cov, 0, 1) * 255)[..., None]
    return img


# ------------------------------------------------------------ message font

def _font_char(code, name):
    if code == 0x5C:
        return "¥"
    if 0x20 <= code < 0x7F:
        return chr(code)
    if code == 0x96:                     # MM: German sharp s in the Greek-beta slot
        return "ß"
    m = re.match(r"((Latin|Greek)\w+|Inverted\w+|FeminineOrdinalIndicator)", name)
    if m:
        words = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", m.group(1)).upper()
        try:
            return unicodedata.lookup(words)
        except KeyError:
            return None
    return None


def _disc(w, h, cx, cy, r):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    return np.clip(r + 0.5 - np.hypot(xx - cx, yy - cy), 0, 1)


def _tri(w, h, pts):
    img = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(img).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    return _down(np.asarray(img, np.float32) / 255, w, h)


def button_glyph(kind, w=16, h=16):
    """I4 button symbols: shape = 1, knocked-out letter/arrow = 0."""
    cx, cy = 7.5, 8.0
    if kind in ("A", "B", "C"):
        m = _disc(w, h, cx, cy, 6.6)
        t = text_mask([kind], w, h, "sansx", size=10)
        return np.clip(m - t, 0, 1)
    if kind in ("L", "R", "Z"):
        m = np.zeros((h, w), np.float32)
        m[2:14, 1:14] = 1
        t = text_mask([kind], w, h, "sansx", size=10)
        return np.clip(m - t, 0, 1)
    if kind.startswith("C"):
        m = _disc(w, h, cx, cy, 6.6)
        tri = {"CUp": [(7.5, 4), (11.5, 11), (3.5, 11)], "CDown": [(3.5, 5), (11.5, 5), (7.5, 12)],
               "CLeft": [(4, 8), (11, 4), (11, 12)], "CRight": [(4, 4), (4, 12), (11, 8)]}[kind]
        return np.clip(m - _tri(w, h, tri), 0, 1)
    if kind == "ZTarget":
        return _tri(w, h, [(3, 3), (12, 3), (7.5, 13)])
    if kind == "Stick":
        m = _disc(w, h, 7.5, 5.5, 4.2)
        m = np.maximum(m, _tri(w, h, [(6.5, 8), (8.5, 8), (9, 12), (6, 12)]))
        m = np.maximum(m, _tri(w, h, [(2, 12), (13, 12), (12, 15), (3, 15)]))
        return m
    return None


BUTTONS = {0xB0: "A", 0xB1: "B", 0xB2: "C", 0xB3: "L", 0xB4: "R", 0xB5: "Z", 0xB6: "CUp", 0xB7: "CDown",
           0xB8: "CLeft", 0xB9: "CRight", 0xBA: "ZTarget", 0xBB: "Stick"}


def glyph_mask(ch, w, h, cap_px=11, baseline=13, x0=1):
    """One message-font character, left aligned: cap height cap_px, baseline row."""
    f = font("serif", int(cap_px * SS / 0.70))
    img = Image.new("L", (w * SS, h * SS), 0)
    dr = ImageDraw.Draw(img)
    bb = f.getbbox(ch)
    capb = f.getbbox("H")
    base_y = baseline * SS - capb[3]
    dr.text((x0 * SS - bb[0], base_y), ch, font=f, fill=255, stroke_width=1, stroke_fill=255)
    return np.clip(_down(np.asarray(img, np.float32) / 255, w, h) * 1.15, 0, 1)


def font_glyph(path, d):
    m = re.search(r"gMsgChar([0-9A-F]{2})(\w*)Tex", path)
    if not m:
        return None
    code, name = int(m.group(1), 16), m.group(2)
    w, h = d["w"], d["h"]
    if code in BUTTONS:
        cov = button_glyph(BUTTONS[code], w, h)
    else:
        ch = _font_char(code, name)
        cov = np.zeros((h, w), np.float32) if (ch is None or ch.strip() == "") else glyph_mask(ch, w, h)
    return grey_img(cov)


# ------------------------------------------------------------ Hylian script (our own invented glyphs)

_STROKES = [((0.2, 0.1), (0.2, 0.9)), ((0.8, 0.1), (0.8, 0.9)), ((0.1, 0.2), (0.9, 0.2)), ((0.1, 0.8), (0.9, 0.8)),
            ((0.1, 0.5), (0.9, 0.5)), ((0.5, 0.1), (0.5, 0.9)), ((0.15, 0.15), (0.85, 0.85)), ((0.85, 0.15), (0.15, 0.85)),
            ((0.2, 0.9), (0.5, 0.1)), ((0.5, 0.1), (0.8, 0.9)), ((0.2, 0.5), (0.5, 0.9)), ((0.5, 0.9), (0.8, 0.5))]


def hylian_mask(key, w, h, weight=0.14):
    """coverage of one invented Hylian glyph (2-4 strokes chosen from `key`)"""
    from cleanroom.decomp.gen import h32
    rng = np.random.default_rng(h32("hylian", key))
    n = int(rng.integers(2, 5))
    idx = rng.choice(len(_STROKES), n, replace=False)
    W, H = w * SS, h * SS
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    lw = max(SS, int(weight * min(W, H)))
    for i in idx:
        (x0, y0), (x1, y1) = _STROKES[i]
        dr.line([(x0 * W, y0 * H), (x1 * W, y1 * H)], fill=255, width=lw)
    if rng.random() < 0.4:                              # a dot
        cx, cy = rng.uniform(0.3, 0.7, 2)
        r = lw * 0.8
        dr.ellipse([cx * W - r, cy * H - r, cx * W + r, cy * H + r], fill=255)
    return _down(np.asarray(img, np.float32) / 255, w, h)


def hylian_text(path, d):
    """inscriptions and signs in Hylian: rows of our glyphs over the regenerated base"""
    from cleanroom.decomp.gen import h32
    w, h = d["w"], d["h"]
    base = from_digest(path, d).astype(np.float32)
    rows = max(1, int(round(h / 14)))
    rh = h / rows
    gw = max(4, int(rh * 0.8))
    cov = np.zeros((h, w), np.float32)
    k = 0
    for r in range(rows):
        y0 = int(r * rh + rh * 0.15)
        gh = max(3, int(rh * 0.7))
        for x0 in range(1, w - gw + 1, gw + max(1, gw // 5)):
            if y0 + gh > h:
                break
            m = hylian_mask(f"{path}:{k}", gw, gh)
            cov[y0:y0 + gh, x0:x0 + gw] = np.maximum(cov[y0:y0 + gh, x0:x0 + gw], m)
            k += 1
    lum = base[..., :3].mean(-1)
    opaque = base[..., 3] > 127
    ref = lum[opaque].mean() if opaque.any() else lum.mean()
    ink = np.array([30, 25, 20], np.float32) if ref > 110 else np.array([235, 230, 215], np.float32)
    base[..., :3] = base[..., :3] * (1 - cov[..., None]) + ink * cov[..., None]
    if d["type"] in (5, 6, 7, 8, 9, 10):              # intensity formats: the glyphs carry the alpha too
        base[..., 3] = np.maximum(base[..., 3] * 0.35, cov * 255) if "alpha2" in d else base[..., 3]
    return base


def kanji_glyph(path, d):
    """Shift-JIS font cell (16x16 I4): the character from the name's code."""
    m = re.search(r"gMsgKanji([0-9A-F]{4})", path)
    if not m:
        return None
    try:
        ch = bytes.fromhex(m.group(1)).decode("shift_jis")
    except UnicodeDecodeError:
        ch = ""
    w, h = d["w"], d["h"]
    cov = np.zeros((h, w), np.float32)
    if ch.strip() and ch != "　":
        f = font("jp", 15 * SS)
        img = Image.new("L", (w * SS, h * SS), 0)
        dr = ImageDraw.Draw(img)
        bb = f.getbbox("漢")                       # a full-height ideograph fixes the frame
        cb = f.getbbox(ch)
        cw = cb[2] - cb[0]
        x = (w * SS - cw) / 2 - cb[0]
        y = (h * SS - (bb[3] - bb[1])) / 2 - bb[1]
        dr.text((x, y), ch, font=f, fill=255, stroke_width=2, stroke_fill=255)
        cov = np.clip(_down(np.asarray(img, np.float32) / 255, w, h) * 1.1, 0, 1)
    return grey_img(cov)


# ------------------------------------------------------------ labels

def daytelop(path, d):
    """"Dawn of / The First Day": one phrase across the Left and Right textures."""
    m = re.search(r"gDaytelop(First|Second|Final|New)Day(Left|Right)NESTex$", path)
    if not m:
        return None
    day = {"First": "The First Day", "Second": "The Second Day", "Final": "The Final Day", "New": "A New Day"}[m.group(1)]
    w, h = d["w"], d["h"]
    W = 2 * w
    top = text_mask(["Dawn of"], W, int(h * 0.38), "serif", size=int(h * 0.3))
    bot = text_mask([day], W, h - int(h * 0.38), "serif")
    cov = np.concatenate([top, bot], 0)
    img = outlined(cov, fill=(255, 255, 255), edge=(20, 10, 30), r=1)
    return img[:, :w] if m.group(2) == "Left" else img[:, w:]


def label_tex(path, d, lines):
    w, h = d["w"], d["h"]
    base = path.rsplit("/", 1)[1]
    align = "left" if ("FileSel" in base and "Button" not in base and len(lines[0]) > 8) else "center"
    if "TitleCard" in base and len(lines) == 2:          # boss: small subtitle, big name
        top = text_mask([lines[0]], w, h // 3, "sans")
        bot = text_mask([lines[1].upper()], w, h - h // 3, "sansx")
        m = np.concatenate([top, bot], 0)
    elif "TitleCard" in base:
        m = text_mask([lines[0].upper()], w, h, "sansx", squeeze=0.5)
    elif "DoAction" in base:                             # button labels sit on round buttons: keep them compact
        m = text_mask(lines, w, h, "sansx", align="center", pad_x=2, squeeze=0.5)
    else:
        m = text_mask(lines, w, h, "sansx" if h >= 16 else "sans", align=align)
    if "Button" in base and d["type"] == 9:              # file select buttons: grey bevel, dark text
        img = np.zeros((h, w, 4), np.float32)
        g = np.linspace(200, 120, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
        img[..., :3] = g[..., None]
        img[..., :3] *= (1 - 0.85 * m[..., None])
        img[..., 3] = 255
        img[0, :, :3] = 240
        img[-1, :, :3] = 60
        img[:, 0, :3] = 230
        img[:, -1, :3] = 70
        if "alpha2" in d:
            img[..., 3] = unpack_alpha2(d["alpha2"], w, h)
        return img
    return outlined(m, r=1)


# ------------------------------------------------------------ stone panels

def fbm(seed, w, h, cells=(24, 12, 6, 3, 1.5)):
    from cleanroom.decomp.gen import detail
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for k, c in enumerate(cells):
        out += amp * (detail(seed + k, w, h, 1.0, float(c)) - 1.0)
        tot += amp
        amp *= 0.6
    return out / tot


def stone(path, d):
    """Carved-stone look for pause-page tiles: grid colours, our fractal grain, bevelled edges of the kept alpha."""
    from cleanroom.decomp.gen import upsample_grid, h32
    w, h = d["w"], d["h"]
    n = int(round(len(d["grid"]) ** 0.5))
    img = upsample_grid(d["grid"], n, w, h)
    g = fbm(h32("stone", path), w, h)
    lum = img[..., :3].mean(-1, keepdims=True)
    grey = lum * 0.55 + img[..., :3] * 0.45
    img[..., :3] = grey * (0.82 + 0.45 * g[..., None])
    if "alpha2" in d:
        a = unpack_alpha2(d["alpha2"], w, h)
        m = (a > 127).astype(np.float32)
        up = np.clip(m - np.roll(m, 1, 0), 0, 1) + np.clip(m - np.roll(m, 1, 1), 0, 1)
        dn = np.clip(m - np.roll(m, -1, 0), 0, 1) + np.clip(m - np.roll(m, -1, 1), 0, 1)
        img[..., :3] = img[..., :3] * (1 + 0.35 * np.clip(up, 0, 1)[..., None]) * (1 - 0.45 * np.clip(dn, 0, 1)[..., None])
        img[..., 3] = a
    else:
        img[..., 3] = 255
    return np.clip(img, 0, 255)


# ------------------------------------------------------------ pause page headers

_SPEC = None


def spec():
    global _SPEC
    if _SPEC is None:
        _SPEC = json.load(open(os.path.join(HERE, "spec", "textures.json")))
    return _SPEC


PAUSE_TITLES = {"SelectItem": "SELECT ITEM", "QuestStatus": "QUEST STATUS", "Masks": "MASKS",
                "Map": "MAP", "Save": "SAVE", "GameOver": "GAME OVER"}
_PAUSE_INDEX = None


def _find(page, col, row):
    global _PAUSE_INDEX
    if _PAUSE_INDEX is None:
        _PAUSE_INDEX = {p.rsplit("/", 1)[1]: p for p in spec() if "/gPause" in p}
    return _PAUSE_INDEX.get(f"gPause{page}{col}{row}ENGTex") or _PAUSE_INDEX.get(f"gPause{page}{col}{row}Tex")


def pause_header(path, d):
    m = re.search(r"gPause(SelectItem|QuestStatus|Masks|Map|Save|GameOver)(\d)(\d)(ENG)?Tex$", path)
    if not m or m.group(3) != "0" or not m.group(4):
        return None
    page, col = m.group(1), int(m.group(2))
    T = spec()
    cols = [c for c in range(3) if _find(page, c, 0)]
    w, h = d["w"], d["h"]
    strip = np.concatenate([stone(_find(page, c, 0), T[_find(page, c, 0)]).astype(np.float32) for c in cols], 1)
    W = strip.shape[1]
    tm = np.roll(text_mask([PAUSE_TITLES[page]], W, h, "sansx", size=15), -3, 0)
    hi = np.roll(np.roll(tm, 1, 0), 1, 1)
    rgb = strip[..., :3]
    rgb = rgb * (1 - 0.6 * hi[..., None]) + 235 * 0.6 * hi[..., None]
    rgb = rgb * (1 - tm[..., None]) + np.asarray([45, 38, 30], np.float32) * tm[..., None]
    strip[..., :3] = rgb
    k = cols.index(col)
    return strip[:, k * w:(k + 1) * w]


# ------------------------------------------------------------ dispatch

def _alpha_or_full(d):
    return unpack_alpha2(d["alpha2"], d["w"], d["h"]).astype(np.float32) if "alpha2" in d else np.full((d["h"], d["w"]), 255.0, np.float32)


def _bevel(a):
    """Light from the upper left on the kept silhouette: (+) lit edge, (-) shadow edge."""
    m = (a > 127).astype(np.float32)
    up = np.clip(m - np.roll(m, 1, 0), 0, 1) + np.clip(m - np.roll(m, 1, 1), 0, 1)
    up2 = np.clip(m - np.roll(m, 2, 0), 0, 1) + np.clip(m - np.roll(m, 2, 1), 0, 1)
    dn = np.clip(m - np.roll(m, -1, 0), 0, 1) + np.clip(m - np.roll(m, -1, 1), 0, 1)
    dn2 = np.clip(m - np.roll(m, -2, 0), 0, 1) + np.clip(m - np.roll(m, -2, 1), 0, 1)
    return np.clip(up + 0.5 * up2, 0, 1) - np.clip(dn + 0.5 * dn2, 0, 1)


def mm_zelda_logo(path, d):
    """ZELDA lettering: the kept letter silhouette filled with our own brushed violet metal."""
    from cleanroom.decomp.gen import h32
    w, h = d["w"], d["h"]
    a = _alpha_or_full(d)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = yy / h
    base = np.stack([150 + 70 * (1 - t), 95 + 50 * (1 - t), 200 + 40 * (1 - t)], -1)
    streak = fbm(h32("zelda", path), w, h, (w / 3, 6, 2))[..., None]
    base = base * (0.9 + 0.2 * streak) + 30 * np.clip(np.sin(xx / w * 9 + yy / h * 3), 0, 1)[..., None] ** 8
    bev = _bevel(a)[..., None]
    rgb = base * (1 + 0.45 * np.clip(bev, 0, 1)) * (1 - 0.55 * np.clip(-bev, 0, 1))
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = np.clip(rgb, 0, 255)
    out[..., 3] = a
    return out


def mm_title_mask(path, d):
    """Majora's Mask picture: heart-shaped face, spikes, two round eyes, painted inside the kept silhouette."""
    from cleanroom.gfx import facepaint
    from cleanroom.decomp.gen import h32
    w, h = d["w"], d["h"]
    a = _alpha_or_full(d)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    # heart body: two lobes and a point, our own proportions
    body = ((((u - 0.36) / 0.2) ** 2 + ((v - 0.42) / 0.2) ** 2) <= 1) | ((((u - 0.64) / 0.2) ** 2 + ((v - 0.42) / 0.2) ** 2) <= 1)
    body |= (v > 0.42) & (np.abs(u - 0.5) < 0.4 * (1 - (v - 0.42) / 0.45))
    spikes = np.stack([220 - 60 * v, 200 - 30 * v, 80 + 20 * v], -1)            # yellow-green horns
    face = np.stack([70 + 40 * (1 - v), 45 + 20 * (1 - v), 120 + 60 * (1 - v)], -1)   # dusk violet
    rgb = np.where(body[..., None], face, spikes)
    g = fbm(h32("mask", path), w, h, (16, 8, 3))[..., None]
    rgb = rgb * (0.88 + 0.22 * g)
    # carved band across the brow and a lower face split
    band = body & (np.abs(v - 0.3 - 0.08 * np.abs(u - 0.5)) < 0.03)
    rgb[band] = [150, 110, 60]
    split = body & (np.abs(u - 0.5) < 0.012) & (v > 0.55)
    rgb[split] = [30, 20, 40]
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = a
    ops = []
    for cx in (0.35, 0.65):
        ops += [{"e": [cx, 0.47, 0.115, 0.13], "c": [200, 50, 20]}, {"e": [cx, 0.47, 0.085, 0.1], "c": [250, 130, 30]},
                {"e": [cx, 0.47, 0.05, 0.06], "c": [250, 210, 70]}, {"e": [cx + 0.01, 0.47, 0.025, 0.03], "c": [120, 160, 30]},
                {"hl": [cx - 0.04, 0.42, 0.018], "c": [255, 250, 230]}]
    eyes = facepaint.render({"base": [0, 0, 0], "ops": ops}, w, h)
    em = np.zeros((h, w), bool)
    for cx in (0.35, 0.65):
        em |= (((u - cx) / 0.115) ** 2 + ((v - 0.47) / 0.13) ** 2) <= 1
    out[em, :3] = eyes[em, :3]
    bev = _bevel(a)[..., None]
    out[..., :3] = np.clip(out[..., :3] * (1 + 0.3 * np.clip(bev, 0, 1)) * (1 - 0.5 * np.clip(-bev, 0, 1)), 0, 255)
    return out


def mm_balloon(path, d):
    """The Skull Kid's balloon: Majora's Mask painted on violet cloth with a soft highlight (our drawing)."""
    from cleanroom.gfx import facepaint
    from cleanroom.decomp.gen import h32
    w, h = d["w"], d["h"]
    mask = mm_title_mask(path, {"w": w, "h": h})              # full-alpha mask picture
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    bg = np.stack([60 + 40 * (1 - v), 40 + 20 * (1 - v), 120 + 50 * (1 - v)], -1)
    g = fbm(h32("balloon", path), w, h, (8, 4, 2))[..., None]
    bg = bg * (0.9 + 0.2 * g)
    hl = np.exp(-(((u - 0.72) / 0.12) ** 2 + ((v - 0.2) / 0.12) ** 2))[..., None]
    bg = bg * (1 - 0.8 * hl) + 240 * 0.8 * hl
    # the mask shape: heart + horns (as in mm_title_mask), scaled into the middle
    body = ((((u - 0.36) / 0.2) ** 2 + ((v - 0.45) / 0.2) ** 2) <= 1) | ((((u - 0.64) / 0.2) ** 2 + ((v - 0.45) / 0.2) ** 2) <= 1)
    body |= (v > 0.45) & (np.abs(u - 0.5) < 0.4 * (1 - (v - 0.45) / 0.45))
    horns = np.zeros_like(body)
    for ang in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        tip = (0.5 + 0.47 * np.cos(ang), 0.5 + 0.44 * np.sin(ang))
        dist = np.abs((u - 0.5) * np.sin(ang) - (v - 0.5) * np.cos(ang))
        along = (u - 0.5) * np.cos(ang) + (v - 0.5) * np.sin(ang)
        horns |= (along > 0.2) & (along < 0.46) & (dist < 0.05 * (0.46 - along) / 0.26)
    out = np.zeros((h, w, 4), np.float32)
    out[..., :3] = bg
    spike = np.stack([230 - 60 * v, 200 - 30 * v, 70 + 20 * v], -1)
    out[horns & ~body, :3] = spike[horns & ~body]
    out[body, :3] = mask[body, :3] * 1.25
    edge = body & ~(np.roll(body, 1, 0) & np.roll(body, -1, 0) & np.roll(body, 1, 1) & np.roll(body, -1, 1))
    out[edge, :3] = (25, 12, 30)
    out[..., 3] = 255
    return np.clip(out, 0, 255)


_WIN = None


def file_window(path, d):
    """File-select window (4x5 IA16 tiles, tinted by the game): one bevelled panel drawn whole.
    Alpha: every tile's kept 2-bit outline assembled into one panel and smoothed (the fade)."""
    global _WIN
    m = re.search(r"gFileSelWindow(\d)(\d)Tex$", path)
    if not m:
        return None
    r, c = int(m.group(1)), int(m.group(2))
    W, H = 240, 160
    X0 = [0, 64, 128, 192]
    if _WIN is None:
        from cleanroom.decomp.gen import h32
        T = spec()
        alpha = np.full((H, W), 255.0, np.float32)
        for p, t in T.items():
            mm = re.search(r"gFileSelWindow(\d)(\d)Tex$", p)
            if mm and "alpha2" in t:
                rr, cc = int(mm.group(1)), int(mm.group(2))
                alpha[rr * 32:rr * 32 + t["h"], X0[cc]:X0[cc] + t["w"]] = unpack_alpha2(t["alpha2"], t["w"], t["h"])
        k = 15                                               # smooth the 2-bit steps into a fade
        pad = np.pad(alpha, k, mode="edge")
        cs = np.cumsum(np.cumsum(pad, 0), 1)
        cs = np.pad(cs, ((1, 0), (1, 0)))
        box = (cs[2 * k + 1:, 2 * k + 1:] - cs[:-2 * k - 1, 2 * k + 1:] - cs[2 * k + 1:, :-2 * k - 1] + cs[:-2 * k - 1, :-2 * k - 1])
        smooth = box[:H, :W] / (2 * k + 1) ** 2
        alpha = np.where((alpha < 8) & (xx_cut := (np.mgrid[0:H, 0:W][1] < 150)), 0, smooth)   # crisp corners, soft right fade
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        lum = 130 + 30 * (1 - yy / H)
        sheen = np.sin((xx + 0.8 * yy) / 26.0) * 0.5 + 0.5  # diagonal sheen bands
        lum = lum + 95 * sheen ** 3
        lum = lum * (0.95 + 0.1 * fbm(h32("filewin", "x"), W, H, (48, 24, 8)))
        rim = 5
        lum = np.where((yy < rim) | (xx < rim), 230, lum)
        lum = np.where((yy >= H - rim) | (xx >= W - rim), 70, lum)
        inset = (((np.abs(yy - 24) < 1) & (xx >= 12)) | ((np.abs(xx - 12) < 1) & (yy >= 24))) & (yy <= H - 12)
        lum = np.where(inset, 40, lum)
        _WIN = (np.clip(lum, 0, 255), np.clip(alpha, 0, 255))
    lum, alpha = _WIN
    x0 = X0[c]
    img = np.zeros((d["h"], d["w"], 4), np.float32)
    img[..., :3] = lum[r * 32:r * 32 + d["h"], x0:x0 + d["w"]][..., None]
    img[..., 3] = alpha[r * 32:r * 32 + d["h"], x0:x0 + d["w"]]
    return img


def title_logo(path, d):
    """Title logo: our own shield, sword and ZELDA lettering inside the kept silhouette."""
    w, h = d["w"], d["h"]
    W, H = w * SS, h * SS
    base = from_digest(path, d).astype(np.float32)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # sword, lower-left to upper-right behind the shield
    dr.line([(0.10 * W, 0.88 * H), (0.60 * W, 0.12 * H)], fill=(215, 225, 240, 255), width=int(0.05 * W))
    dr.line([(0.10 * W, 0.88 * H), (0.60 * W, 0.12 * H)], fill=(160, 175, 200, 255), width=int(0.015 * W))
    dr.line([(0.50 * W, 0.20 * H), (0.62 * W, 0.30 * H)], fill=(60, 70, 160, 255), width=int(0.05 * W))   # guard
    dr.line([(0.58 * W, 0.16 * H), (0.66 * W, 0.08 * H)], fill=(70, 80, 170, 255), width=int(0.035 * W))  # grip
    # shield
    sh = [(0.08 * W, 0.32 * H), (0.46 * W, 0.26 * H), (0.46 * W, 0.62 * H), (0.27 * W, 0.84 * H), (0.08 * W, 0.62 * H)]
    dr.polygon(sh, fill=(150, 160, 170, 255))
    inner = [(x * 0.86 + 0.27 * W * 0.14, y * 0.86 + 0.55 * H * 0.14) for x, y in sh]
    dr.polygon(inner, fill=(35, 55, 140, 255))
    tri = [(0.27 * W, 0.34 * H), (0.36 * W, 0.50 * H), (0.18 * W, 0.50 * H)]
    dr.polygon(tri, fill=(245, 205, 60, 255))
    mid = [((tri[0][0] + tri[1][0]) / 2, (tri[0][1] + tri[1][1]) / 2), ((tri[1][0] + tri[2][0]) / 2, tri[1][1]),
           ((tri[0][0] + tri[2][0]) / 2, (tri[0][1] + tri[2][1]) / 2)]
    dr.polygon(mid, fill=(35, 55, 140, 255))
    dr.polygon([(0.20 * W, 0.58 * H), (0.34 * W, 0.58 * H), (0.27 * W, 0.70 * H)], fill=(190, 40, 40, 255))   # crest
    # lettering
    f = font("serif", int(0.30 * H))
    txt = "ZELDA"
    bb = f.getbbox(txt)
    sx = (0.90 * W) / (bb[2] - bb[0])
    layer = Image.new("L", (int((bb[2] - bb[0]) + 40), int((bb[3] - bb[1]) + 40)), 0)
    ImageDraw.Draw(layer).text((20 - bb[0], 20 - bb[1]), txt, font=f, fill=255, stroke_width=int(0.012 * H), stroke_fill=255)
    layer = layer.resize((int(layer.width * sx), int(layer.height * 1.15)))
    m = np.asarray(layer, np.float32) / 255
    ox, oy = int(0.08 * W - 20 * sx), int(0.34 * H - 20)
    full = np.zeros((H, W), np.float32)
    y0, x0 = max(0, oy), max(0, ox)
    y1, x1 = min(H, oy + m.shape[0]), min(W, ox + m.shape[1])
    full[y0:y1, x0:x1] = m[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    arr = np.asarray(img, np.float32)
    edge = dilate(full, 4 * SS // 2)
    gold = np.asarray([235, 190, 70], np.float32)
    red = np.stack([np.linspace(215, 120, H)[:, None] * np.ones((1, W)), np.full((H, W), 20.0),
                    np.full((H, W), 35.0)], -1)
    arr[..., :3] = arr[..., :3] * (1 - edge[..., None]) + gold * edge[..., None]
    arr[..., 3] = np.maximum(arr[..., 3], edge * 255)
    arr[..., :3] = arr[..., :3] * (1 - full[..., None]) + red * full[..., None]
    arr[..., 3] = np.maximum(arr[..., 3], full * 255)
    arr = arr.reshape(h, SS, w, SS, 4).mean((1, 3))
    a = arr[..., 3:4] / 255
    out = base.copy()
    out[..., :3] = arr[..., :3] / np.maximum(a, 1e-6) * a + base[..., :3] * (1 - a)
    out[..., 3] = np.maximum(base[..., 3], arr[..., 3])
    return np.clip(out, 0, 255)


ICON_DIR = os.path.join(HERE, "overrides", "icons")


def icon_override(path, d):
    """Rendered item icons (games.mm.icons): the game's own models with our textures."""
    f = os.path.join(ICON_DIR, path.rsplit("/", 1)[1] + ".png")
    if not os.path.exists(f):
        return None
    im = np.asarray(Image.open(f).convert("RGBA").resize((d["w"], d["h"])), np.float32)
    return im


PIC_DIR = os.path.join(HERE, "overrides", "pictures")


TEX_DIR = os.path.join(HERE, "overrides", "textures")


def texture_override(path, d):
    """Generated surface textures (games.mm.aitex)."""
    f = os.path.join(TEX_DIR, path.rsplit("/", 1)[1] + ".png")
    if not os.path.exists(f):
        return None
    return np.asarray(Image.open(f).convert("RGBA").resize((d["w"], d["h"])), np.float32)


def picture_override(path, d):
    """Pictures rendered from the game's own geometry (e.g. games.mm.worldmap)."""
    f = os.path.join(PIC_DIR, path.rsplit("/", 1)[1] + ".png")
    if not os.path.exists(f):
        return None
    return np.asarray(Image.open(f).convert("RGBA").resize((d["w"], d["h"])), np.float32)


def soft_cloud(path, d):
    """World-map fog patch: billowy cloud that fades to nothing at the texture edges
    (the patches overlap on the map, so hard edges show as rectangles)."""
    from cleanroom.decomp.gen import upsample_grid, h32
    w, h = d["w"], d["h"]
    n = int(round(len(d["grid"]) ** 0.5))
    g = upsample_grid(d["grid"], n, w, h)[..., 0] / 255.0
    billow = fbm(h32("cloud", path), w, h, (max(4, w // 4), max(2, w // 8), 2))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ex = np.minimum(xx + 0.5, w - 0.5 - xx) / (w * 0.35)
    ey = np.minimum(yy + 0.5, h - 0.5 - yy) / (h * 0.35)
    edge = np.clip(np.minimum(ex, ey), 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    v = np.clip(0.55 + 0.8 * billow + 0.3 * (g - 0.5), 0, 1) * edge
    return grey_img(v)


def hud_symbols(path, d):
    """pause-screen button symbols and dungeon-map floor buttons: our letters over the kept outline"""
    w, h = d["w"], d["h"]
    name = path.rsplit("/", 1)[1]
    m = re.match(r"g([AB])BtnSymbolTex$", name)
    if m:
        return outlined(np.clip(text_mask([m.group(1)], w, h, "sansx", pad_x=0) * 1.3, 0, 1), r=1)
    if name == "gCBtnSymbolsTex":                      # the three C buttons as arrows
        cov = np.zeros((h, w), np.float32)
        step = w / 3.0
        for i, k in enumerate(("CLeft", "CDown", "CRight")):
            g = 1 - button_glyph(k, 16, 16)
            g = g * _disc(16, 16, 7.5, 8.0, 6.6)
            x0 = int(i * step + (step - 16) / 2)
            cov[:, max(0, x0):max(0, x0) + 16] = np.maximum(cov[:, max(0, x0):max(0, x0) + 16], g[:h, :min(16, w - max(0, x0))])
        return outlined(cov, fill=(250, 230, 60), r=1)
    m = re.match(r"g([RZ])ButtonTex$", name)
    if m:
        base = from_digest(path, d).astype(np.float32)
        t = text_mask([m.group(1)], w, h, "sansx", pad_x=2)
        base[..., :3] = base[..., :3] * (1 - t[..., None]) + 245 * t[..., None]
        return base
    m = re.match(r"gDungeonMap(\d|B\d)(F?)ButtonTex$", name)
    if m:
        txt = m.group(1) + m.group(2)
        base = from_digest(path, d).astype(np.float32)
        t = text_mask([txt], w, h, "sansx", pad_x=2)
        base[..., :3] = base[..., :3] * (1 - t[..., None]) + np.array([30, 25, 20], np.float32) * t[..., None]
        return base
    if name == "gFileSelBackspaceButtonTex":
        base = from_digest(path, d).astype(np.float32)
        t = _tri(w, h, [(w * 0.25, h * 0.5), (w * 0.6, h * 0.2), (w * 0.6, h * 0.8)])
        t = np.maximum(t, ((np.abs(np.mgrid[0:h, 0:w][0] + 0.5 - h * 0.5) < h * 0.12) &
                           (np.mgrid[0:h, 0:w][1] > w * 0.5) & (np.mgrid[0:h, 0:w][1] < w * 0.8)).astype(np.float32))
        base[..., :3] = base[..., :3] * (1 - t[..., None]) + 40 * t[..., None]
        return base
    return None


def hud_glyph(path, d):
    """HUD counters, message markers, ocarina buttons."""
    w, h = d["w"], d["h"]
    name = path.rsplit("/", 1)[1]
    m = re.match(r"g(Ammo|Counter)Digit(\d)Tex", name)
    if m:
        if m.group(1) == "Ammo":
            cov = np.clip(text_mask([m.group(2)], w, h, "sansx", size=h + 2, pad_x=0) * 1.4, 0, 1)
            return outlined(cov, r=1)
        cov = text_mask([m.group(2)], w, h, "sansx", size=h - 3)
        return grey_img(cov)
    if name == "gCounterColonTex":
        return grey_img(text_mask([":"], w, h, "sansx", size=h - 3))
    if name == "gMessageContinueTriangleTex":
        return grey_img(_tri(w, h, [(3, 4), (13, 4), (8, 12)]))
    if name == "gMessageEndSquareTex":
        m = np.zeros((h, w), np.float32)
        m[4:12, 4:12] = 1
        return grey_img(m)
    if name == "gMessageArrowTex":
        return grey_img(_tri(w, h, [(4, 3), (13, 8), (4, 13)]))
    m = re.match(r"gOcarinaBtnIcon(A|CUp|CDown|CLeft|CRight)Tex", name)
    if m:
        return grey_img(button_glyph(m.group(1), w, h))
    return None


def fairy(path, d):
    """Navi / fairy light: halves of a soft round glow, and a translucent wing."""
    w, h = d["w"], d["h"]
    name = path.rsplit("/", 1)[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    if name.startswith("gCircleGlow"):
        cx = w if name.endswith("LTex") else 0.0          # left half: centre on the right edge, and vice versa
        r = np.hypot(xx - cx, yy - h / 2) / (h / 2)
        sharp = name.replace("gCircleGlow", "").startswith("S")
        core = np.clip(1 - r, 0, 1)
        v = core ** (1.2 if sharp else 2.2) + (0.35 * np.exp(-(r / 0.25) ** 2) if sharp else 0.25 * np.exp(-(r / 0.35) ** 2))
        return grey_img(np.clip(v, 0, 1))
    if name == "gFairyWingTex":
        # teardrop wing along the texture's long axis, bright rim and faint veins
        u = (xx / w - 0.5) * 2
        t = yy / h
        width = 0.95 * np.sin(np.clip(t, 0, 1) * np.pi) ** 0.7 * (1 - 0.35 * t)
        inside = np.clip((width - np.abs(u)) * 6, 0, 1)
        rim = np.clip(1 - np.abs(width - np.abs(u)) * 8, 0, 1)
        vein = np.clip(1 - np.abs(np.sin(t * 9 + u * 2)) * 6, 0, 1) * 0.25
        return grey_img(np.clip(inside * (0.35 + vein) + rim * 0.6, 0, 1) * inside)
    return None


def texture(path, d):
    img = _texture("/" + path.lstrip("/"), d)     # MM archive folders are top level ("nes_font_static/...")
    return img


def _texture(path, d):
    if "/gameplay_keep/" in path and ("gCircleGlow" in path or path.endswith("gFairyWingTex")):
        img = fairy(path, d)
        if img is not None:
            return img
    if "/parameter_static/" in path or "/message_static/" in path:
        img = hud_glyph(path, d)
        if img is not None:
            return img
    if "gWorldMapCloud" in path:
        return soft_cloud(path, d)
    img = picture_override(path, d)
    if img is not None:
        return img
    img = texture_override(path, d)
    if img is not None:
        return img
    if path.endswith("gTitleZeldaShieldLogoTex"):
        return title_logo(path, d)
    img = hud_symbols(path, d) if re.search(r"(BtnSymbol|[RZ]ButtonTex|DungeonMap\w*ButtonTex|BackspaceButton)", path) else None
    if img is not None:
        return img
    if "/icon_item_static" in path or "/icon_item_24_static" in path:
        img = icon_override(path, d)
        if img is not None:
            return img
    mh = re.search(r"gMsgKanji[0-9A-F]{4}Hylian(\w+?)Tex$", path)
    if mh:
        return grey_img(hylian_mask(mh.group(1), d["w"] - 2, d["h"] - 2).__array__() if False else
                        np.pad(hylian_mask(mh.group(1), d["w"] - 4, d["h"] - 4), 2))
    if "/kanji/" in path:
        return kanji_glyph(path, d)
    if re.search(r"(Inscription|SignText|PostalAddress)\w*Tex$", path) and             not re.search(r"(Triforce|CouplesMask|TingleMap|DungeonMap)", path):   # those are pictures, not script
        return hylian_text(path, d)
    if "/nes_font_static/" in path:
        return font_glyph(path, d)
    if "gFileSelWindow" in path:
        img = file_window(path, d)
        if img is not None:
            return img
    if path.endswith("object_fusen/object_fusen_Tex_000E08"):
        return mm_balloon(path, d)
    if path.endswith("gTitleScreenZeldaLogoTex"):
        return mm_zelda_logo(path, d)
    if path.endswith("gTitleScreenMajorasMaskTex"):
        return mm_title_mask(path, d)
    if path.endswith("gTitleScreenMajorasMaskSubtitleTex") or path.endswith("gTitleScreenMajorasMaskSubtitleMaskTex"):
        return grey_img(np.clip(text_mask(["MAJORA'S MASK ™"], d["w"], d["h"], "sans") * 1.3, 0, 1))
    if path.endswith("gTitleScreenCopyright2000NintendoTex"):
        return grey_img(text_mask(["© 2000 Nintendo"], d["w"], d["h"], "sansx"))
    if path.endswith("gNintendo64LogoTextTex"):
        w, h = d["w"], d["h"]
        m = np.maximum(text_mask(["NINTENDO"], int(w * 0.84), h, "sansx"),
                       0)
        m = np.concatenate([m, np.zeros((h, w - m.shape[1]), np.float32)], 1)
        m64 = text_mask(["64"], w - int(w * 0.84), h // 2, "sansx")
        m[: h // 2, int(w * 0.84):] = np.maximum(m[: h // 2, int(w * 0.84):], m64)
        return grey_img(m)
    if path.endswith("nintendo_rogo_static_Tex_000000"):       # the wordmark under the N64 logo
        return grey_img(text_mask(["Nintendo"], d["w"], d["h"], "sansx", size=26))
    if "gPause" in path and re.search(r"gPause(SelectItem|QuestStatus|Masks|Map|Save|GameOver)\d\d", path):
        img = pause_header(path, d)
        if img is not None:
            return img
        return stone(path, d)
    img = daytelop(path, d)
    if img is not None:
        return img
    lines = labels.label(path)
    if lines:
        return label_tex(path, d, lines)
    try:
        from games.mm import faces
        img = faces.texture(path.lstrip("/"), d)
        if img is not None:
            return img
    except FileNotFoundError:
        pass
    return None


# ------------------------------------------------------------ samples

VOICE_DIR = os.path.join(HERE, "voices")
_VOICE_LINES = None


def sample(path, d):
    """Voice slots: our placeholder TTS take (games/mm/voices/<name>.wav, built by
    cleanroom.voice.voices from voice_lines.json), already at the slot's rate and length."""
    global _VOICE_LINES
    if _VOICE_LINES is None:
        f = os.path.join(HERE, "voice_lines.json")
        _VOICE_LINES = json.load(open(f)) if os.path.exists(f) else {}
    if path not in _VOICE_LINES:
        return None
    f = os.path.join(VOICE_DIR, os.path.basename(path)[:-5] + ".wav")
    if not os.path.exists(f):
        return None
    import wave
    with wave.open(f) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
