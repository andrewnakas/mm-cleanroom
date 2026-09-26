# The Legend of Zelda: Majora's Mask — clean room (web)

**Play:** https://andrewnakas.github.io/mm-cleanroom/ (no ROM needed)

A playable web build of Majora's Mask in which **every asset the game takes from the ROM was regenerated**.
The engine is [2 Ship 2 Harkinian](https://github.com/HarbourMasters/2ship2harkinian) (the MM PC port, built
from the [zeldaret/mm](https://github.com/zeldaret/mm) decompilation), compiled to WebAssembly/WebGL2 with Emscripten.

Controls: `WASD` stick · `X` A · `C` B · `Z` Z · `Space` Start · `E`/`R` L/R · arrows C buttons · `Esc` port menu · gamepads work.
Saves are kept in your browser (IndexedDB).

## What is regenerated, what is kept
- **Regenerated:** all 13,542 textures (coarse 4x4 colour grid + 2-bit alpha outline + our own detail; ~4,800 drawn outright:
  message font, HUD glyphs, text labels re-typeset in OFL fonts, faces from our own descriptions, title art),
  all 682 samples (resynthesised from coarse spectral outlines, our own VADPCM books).
- **Kept as facts:** code, geometry, collision, animation, text, note sequences, soundfont layout.
- **Taint scan:** 28,739 generated streams vs retail, 0 failing (no shared run of 32+ bytes).

## Rebuild (you need your own US ROM)
```
python tools/mm_decompress.py <baserom.us.z64> baserom.dec.z64                 # dirty room
python -m ports.mm2s2h.web_patches <2ship2harkinian checkout>                    # web port (+ ports/mm2s2h/lus_web.diff)
bash ports/mm2s2h/build_web.sh ZAPD && node ZAPD.js ed ... --otrfile mm.o2r      # dirty mm.o2r (never published)
python -m games.mm.extract_spec dirty/mm.o2r <xml N64_US> games/mm/spec spec_local
python -m games.mm.generate games/mm/spec spec_local/kept.o2r clean/mm.o2r
python -m ports.mm2s2h.clean_2ship dirty/2ship.o2r clean/2ship.o2r
python -m games.mm.taint_report dirty/mm.o2r clean/mm.o2r clean/2ship.o2r         # must print 0 failing
bash ports/mm2s2h/build_web.sh 2ship
python -m ports.mm2s2h.make_site <build-web/mm> clean/mm.o2r clean/2ship.o2r site
```
Details and decisions: `STATUS.md`.

Fan project, not affiliated with Nintendo. 2 Ship 2 Harkinian is CC0; libultraship is MIT; fonts are OFL.
