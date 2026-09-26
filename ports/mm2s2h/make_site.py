"""Assemble the public site from the web build and the clean archives.

    python -m ports.mm2s2h.make_site <build dir (build-web/mm)> <clean mm.o2r> <clean 2ship.o2r> <site dir>

No ROM and no retail data: mm.o2r is the clean-room archive (taint scan 0 failing),
2ship.o2r is the port's own archive with its retail-derived textures regenerated.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

NOTICE = """The Legend of Zelda: Majora's Mask - clean room web build

Engine: 2 Ship 2 Harkinian (https://github.com/HarbourMasters/2ship2harkinian), CC0 1.0,
built from the zeldaret/mm decompilation; libultraship (MIT, Copyright (c) 2022 kenix3).
Web port patches, clean-room asset generation: https://github.com/andrewnakas/mm-cleanroom

Every asset the game takes from the ROM was regenerated: textures from a coarse colour grid and
alpha outline plus our own detail, text re-typeset in OFL fonts (Marcellus, Montserrat, Noto Sans JP),
faces, title art and labels drawn from our own descriptions, instruments and sound effects
resynthesised from coarse outlines. Kept as facts: code, geometry, text, note sequences.

This is a fan project, not affiliated with Nintendo. The Legend of Zelda is a trademark of Nintendo.
"""


def main(argv):
    build, mm, ship, site = argv[1:5]
    os.makedirs(site, exist_ok=True)
    for f in ("2ship.js", "2ship.wasm"):
        shutil.copyfile(os.path.join(build, f), os.path.join(site, f))
    shutil.copyfile(mm, os.path.join(site, "mm.o2r"))
    shutil.copyfile(ship, os.path.join(site, "2ship.o2r"))
    ver = str(int(os.path.getmtime(mm)))
    html = open(os.path.join(build, "2ship.html"), encoding="utf-8").read()
    html = html.replace("<head>", f"<head><script>window.MM_VER='{ver}';</script>", 1)
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(html)
    lic = os.path.join(site, "licenses")
    os.makedirs(lic, exist_ok=True)
    open(os.path.join(site, "NOTICE.txt"), "w", encoding="utf-8").write(NOTICE)
    for src, dst in (("D:/n64work/mm/2s2h/LICENSE", "2ship2harkinian-CC0.txt"),
                     ("D:/n64work/mm/2s2h/libultraship/LICENSE", "libultraship-MIT.txt")):
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(lic, dst))
    fonts = os.path.join(ROOT, "games", "mm", "fonts")
    for f in os.listdir(fonts):
        if f.startswith("OFL"):
            shutil.copyfile(os.path.join(fonts, f), os.path.join(lic, f))
    open(os.path.join(site, ".nojekyll"), "w").close()
    print("site:", sorted(os.listdir(site)))


if __name__ == "__main__":
    main(sys.argv)
