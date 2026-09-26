"""Eyes and mouths, painted from our own descriptions.

Every face texture is classified by its name (eye / eyes strip / mouth) and
its state (open, half, closed, looking left, shocked, smiling...). Colours
come from face_briefs.json (per character, keyed by object folder) with the
skin tone taken from the texture's kept colour grid. Output goes through
cleanroom.gfx.facepaint, with the kept alpha outline when there is one.
"""
import json
import os
import re

import numpy as np

from cleanroom.gfx import facepaint
from cleanroom.decomp.gen import unpack_alpha2

HERE = os.path.dirname(__file__)
_B = None

EYE_WORDS = r"(Eyes?|Pupil|Iris)"
MOUTH_WORDS = r"(Mouth|Lips?)"


def briefs():
    global _B
    if _B is None:
        _B = json.load(open(os.path.join(HERE, "face_briefs.json")))
    return _B


# Link's masks: our own colours per mask (skin = the mask's surface)
MASKS = {
    "BunnyHoodEye": {"kind": "eye1", "skin": [236, 228, 214], "iris": [30, 20, 20], "sclera": [30, 20, 20], "brows": False, "pupil": 0.0},
    "GerudoMaskEye": {"kind": "eye1", "skin": [190, 130, 80], "iris": [210, 160, 40], "brow": [180, 40, 30]},
    "GerudoMaskMouth": {"kind": "mouth", "skin": [190, 130, 80], "lip": [150, 60, 50]},
    "GoronMaskEye": {"kind": "eye1", "skin": [150, 115, 70], "iris": [40, 25, 15], "brow": [80, 55, 30], "sclera": [230, 220, 200]},
    "GoronMaskMouth": {"kind": "mouth", "skin": [150, 115, 70], "lip": [90, 60, 35]},
    "SkullMaskEye": {"kind": "eye1", "skin": [226, 218, 196], "iris": [20, 15, 10], "sclera": [20, 15, 10], "brows": False, "pupil": 0.0},
    "ZoraMaskEye": {"kind": "eye1", "skin": [190, 215, 240], "iris": [90, 50, 140], "brows": False},
    "ZoraMaskMouth": {"kind": "mouth", "skin": [190, 215, 240], "lip": [120, 150, 190]},
}


def mask_brief(path):
    name = path.rsplit("/", 1)[1]
    for k, v in MASKS.items():
        if k in name:
            return v
    return None


def classify(path, d):
    name = path.rsplit("/", 1)[1]
    mb = mask_brief(path)
    if mb:
        return mb["kind"]
    if re.search(r"(TLUT|Pal|Brow|Lash|Boarder|Border|Mask|Hood)", name):
        return None
    obj = path.split("/")[1]
    b = briefs()
    if obj not in b["chars"]:
        return None
    if re.search(MOUTH_WORDS, name):
        return "mouth"
    if re.search(EYE_WORDS, name):
        return "eyes2" if d["w"] >= 1.6 * d["h"] and b["chars"][obj].get("pair", True) else "eye1"
    return None


def state(name):
    n = name.lower()
    st = {"lid": 0.0, "look": [0.0, 0.0], "irisr": 0.52, "brow": 0.0, "closed": False, "wide": False}
    if re.search(r"(closed|shut|blink|close\b|sleep)", n) and "closing" not in n:
        st["closed"] = True
    if re.search(r"(half|closing|opening|tired|squint|unk2|sleepy)", n):
        st["lid"] = 0.5
    if "closing" in n or "opening" in n:
        st["lid"] = 0.7
    if re.search(r"(left|\bin\b|eyein|lookin)", n) or n.endswith("intex") and "eyein" in n:
        st["look"] = [-0.42, 0.05]
    if re.search(r"(right|eyeout|lookout)", n):
        st["look"] = [0.42, 0.05]
    if re.search(r"(up\b|lookup|eyesup|eyeup)", n):
        st["look"] = [0.0, -0.35]
    if re.search(r"(down|lookdown)", n):
        st["look"] = [0.0, 0.3]
    if re.search(r"eyes?happy|happyeye|eyesmil|eyejoy", n):
        st["happy"] = True
    if re.search(r"(winc|pain|hurt)", n):
        st["wince"] = True
    if re.search(r"(shock|wide|surpri|surprise|scared|fear)", n):
        st["wide"] = True
        st["irisr"] = 0.36
    if re.search(r"(angry|mad|unk1|serious|glare|stern)", n):
        st["brow"] = 1.0
        st["lid"] = max(st["lid"], 0.2)
    if re.search(r"(sad|worried|cry|troubled)", n):
        st["brow"] = -1.0
        st["lid"] = max(st["lid"], 0.25)
    return st


def skin_from(d, fallback):
    g = np.asarray(d["grid"], np.float32)
    if "alpha2" in d:
        g = g[g[:, 3] > 128] if (g[:, 3] > 128).any() else g
    # the brightest quarter of the grid is skin (eyes / brows are darker)
    lum = g[:, :3].mean(1)
    top = g[lum >= np.percentile(lum, 60)][:, :3]
    return [int(v) for v in top.mean(0)] if len(top) else fallback


def eye_ops(cx, cy, rx, ry, st, c, mirror=False):
    ops = []
    look = list(st["look"])
    if mirror:
        look[0] = -look[0]
    brow_c = c["brow"]
    by = cy - ry * 1.55
    tilt = st["brow"] * 0.10 * (-1 if mirror else 1)
    if c.get("brows", True):
        ops.append({"line": [[cx - rx * 1.1, by + tilt], [cx, by - ry * 0.25], [cx + rx * 1.1, by - tilt]],
                    "w": ry * 0.32, "c": brow_c})
    if st.get("happy"):
        ops.append({"arc": [cx, cy + ry * 0.35, rx * 0.9, ry * 0.7, 200, 340], "w": ry * 0.24, "c": c["lash"]})
        return ops
    if st.get("wince"):
        s = 1 if mirror else -1
        ops.append({"line": [[cx - rx * s, cy - ry * 0.5], [cx + rx * 0.7 * s, cy], [cx - rx * s, cy + ry * 0.5]],
                    "w": ry * 0.25, "c": c["lash"]})
        return ops
    if st["closed"]:
        ops.append({"arc": [cx, cy - ry * 0.1, rx * 0.95, ry * 0.45, 10, 170], "w": ry * 0.22, "c": c["lash"]})
        return ops
    ry2 = ry * (1.15 if st["wide"] else 1.0)
    ops.append({"eye": {"c": [cx, cy], "r": [rx, ry2], "sclera": c["sclera"], "iris": c["iris"],
                        "irisr": st["irisr"] if c.get("irisr") is None else c["irisr"] * st["irisr"] / 0.52,
                        "irisy": c.get("irisy", 1.25), "pupil": c.get("pupil", 0.45), "look": look,
                        "lid": st["lid"], "lidc": c["skin"], "lash": c["lash"], "lashw": ry * 0.12,
                        "border": 0.10, "borderc": c["lash"]}})
    return ops


def mouth_ops(name, c):
    n = name.lower()
    lip, dark, teeth = c["lip"], c.get("inner", [90, 20, 25]), [245, 240, 230]
    if re.search(r"(open|talk|shout|surpri|shock|aah|scream|laugh|3\b|mouth3)", n):
        o = [{"e": [0.5, 0.52, 0.30, 0.26], "c": lip}, {"e": [0.5, 0.53, 0.25, 0.20], "c": dark},
             {"rect": [0.3, 0.33, 0.7, 0.42], "c": teeth}]
        if re.search(r"(surpri|shock)", n):
            o = [{"e": [0.5, 0.52, 0.16, 0.22], "c": lip}, {"e": [0.5, 0.53, 0.11, 0.16], "c": dark}]
        return o
    if re.search(r"(smil|happy|grin|joy|4\b|mouth4)", n):
        return [{"arc": [0.5, 0.35, 0.34, 0.28, 20, 160], "w": 0.09, "c": lip},
                {"poly": [[0.24, 0.42], [0.76, 0.42], [0.5, 0.62]], "c": teeth if "grin" in n else lip}]
    if re.search(r"(frown|sad|angry|serious|worr|pout|unhappy)", n):
        return [{"arc": [0.5, 0.68, 0.30, 0.2, 200, 340], "w": 0.08, "c": lip}]
    if re.search(r"(2\b|mouth2|teeth)", n):
        return [{"e": [0.5, 0.5, 0.28, 0.12], "c": lip}, {"rect": [0.3, 0.46, 0.7, 0.54], "c": teeth}]
    return [{"line": [[0.28, 0.5], [0.5, 0.53], [0.72, 0.5]], "w": 0.08, "c": lip},
            {"arc": [0.5, 0.55, 0.14, 0.08, 20, 160], "w": 0.04, "c": [int(v * 0.8) for v in c["skin"]]}]


def _alpha(d):
    return unpack_alpha2(d["alpha2"], d["w"], d["h"]) if "alpha2" in d else None


def styled_eye(path, d, c, st):
    """Monster eyes: concentric glowing rings (orb) or a soft glowing blob (Deku), our own colours."""
    from cleanroom.decomp.gen import h32
    rings = c["rings"]
    lx, ly = st["look"][0] * 0.25, st["look"][1] * 0.25
    ops = []
    n = len(rings)
    for k, col in enumerate(rings):
        r = 0.5 * (1 - k / (n + 0.4))
        if c["style"] == "blob":
            ops.append({"glow": [0.5 + lx * k / n, 0.5 + ly * k / n, r * 1.25, r * 1.25], "c": col})
        else:
            ops.append({"e": [0.5 + lx * k / n, 0.5 + ly * k / n, r, r], "c": col})
    ops.append({"hl": [0.36 + lx, 0.34 + ly, 0.08], "c": [255, 255, 250]})
    if st["closed"]:
        ops = [{"e": [0.5, 0.5, 0.5, 0.5], "c": rings[0]}, {"line": [[0.1, 0.52], [0.9, 0.52]], "w": 0.1, "c": [20, 10, 10]}]
    return facepaint.render({"base": rings[0], "detail": 0.03, "ops": ops}, d["w"], d["h"], alpha=_alpha(d),
                            seed=h32("face", path) & 0xFFFF)


def almond_eyes(path, d, c, st, pair):
    """Zora eyes: dark almonds with a bright highlight on pale skin."""
    from cleanroom.decomp.gen import h32
    iris, hi = c["iris"], c.get("hi", [230, 250, 250])
    ops = []
    centres = [(0.27, True), (0.73, False)] if pair else [(0.5, False)]
    for cx, mirror in centres:
        rx = 0.19 if pair else 0.38
        s = -1 if mirror else 1
        if st["closed"]:
            ops.append({"arc": [cx, 0.5, rx, 0.18, 20, 160], "w": 0.07, "c": iris})
            continue
        ry = (0.16 if pair else 0.3) * (1 - 0.5 * st["lid"]) * (1.2 if st["wide"] else 1)
        rot = 22 * (1 if mirror else -1)
        lx = st["look"][0] * rx * 0.5
        ops.append({"e": [cx, 0.55, rx, ry], "rot": rot, "c": iris})
        ops.append({"e": [cx + lx, 0.55 + st["look"][1] * 0.15, rx * 0.34, rx * 0.34], "c": [min(255, v + 25) for v in iris]})
        ops.append({"hl": [cx + lx - rx * 0.12, 0.5 + st["look"][1] * 0.15, rx * 0.16], "c": hi})
    return facepaint.render({"base": c["skin"], "detail": 0.04, "ops": ops}, d["w"], d["h"], alpha=_alpha(d),
                            seed=h32("face", path) & 0xFFFF)


def texture(path, d):
    if path.endswith("gLinkChildKeatonMaskEyeBrowTex"):      # the fox mask's arched brows
        ops = [{"arc": [0.5, 0.95, 0.42, 0.6, 200, 340], "w": 0.16, "c": [60, 35, 10]}]
        return facepaint.render({"base": [236, 200, 40], "detail": 0.04, "ops": ops}, d["w"], d["h"])
    kind = classify(path, d)
    if not kind:
        return None
    b = briefs()
    obj = path.split("/")[1]
    c = dict(b["default"])
    c.update(mask_brief(path) or b["chars"][obj])
    if c.get("skin") in (None, "grid"):
        c["skin"] = skin_from(d, [230, 190, 150])
    # step flat colours off the 5-bit grid values a retail texture would also land on
    c["skin"] = [min(255, int(v) + 10) if i != 2 else max(0, int(v) - 7) for i, v in enumerate(c["skin"])]
    c["sclera"] = [min(v, 236) - (4 if i == 2 else 0) for i, v in enumerate(c["sclera"])]
    c.setdefault("lip", [int(c["skin"][0] * 0.62), int(c["skin"][1] * 0.38), int(c["skin"][2] * 0.34)])
    name = path.rsplit("/", 1)[1]
    w, h = d["w"], d["h"]
    style = c.get("style", "human")
    if style in ("orb", "blob") and kind != "mouth":
        return styled_eye(path, d, c, state(name))
    if style == "almond" and kind != "mouth":
        return almond_eyes(path, d, c, state(name), kind == "eyes2")
    if kind == "mouth":
        ops = mouth_ops(name, c)
    else:
        st = state(name)
        if kind == "eyes2":
            ops = eye_ops(0.28, 0.6, 0.19, 0.30, st, c, mirror=True) + eye_ops(0.72, 0.6, 0.19, 0.30, st, c)
        else:
            ops = eye_ops(0.5, 0.58, 0.33, 0.27, st, c)
    alpha = unpack_alpha2(d["alpha2"], w, h) if "alpha2" in d else None
    from cleanroom.decomp.gen import h32
    return facepaint.render({"base": c["skin"], "detail": 0.05, "ops": ops}, w, h, alpha=alpha,
                            seed=h32("face", path) & 0xFFFF)     # stable across runs (str hash() is salted)
