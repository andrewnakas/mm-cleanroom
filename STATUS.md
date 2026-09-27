# The Legend of Zelda: Majora's Mask clean room: status

_Last update: 2026-09-26 ~18:00_

## For the morning
- **Play: https://andrewnakas.github.io/mm-cleanroom/** (repo public: andrewnakas/mm-cleanroom). Verified live in headless Edge: title, file select, name entry, Clock Town gameplay.
- Taint: 28,739 generated streams, **0 failing**.
- Please look at: file select + name entry (re-typeset), title screen (ZELDA logo, mask picture drawn inside the kept silhouettes), faces in Clock Town, the sky.
- Fixed (26 Sep evening): the freeze in the sound-effect lists (a sfx entry could be removed twice in one pass and the list walk looped forever). Removal is now idempotent and the walk is bounded (a damaged bank is rebuilt instead of hanging). Verified: repeated Clock Town runs no longer freeze.
- **HUD verified in game** (warp to East/West Clock Town): crisp hearts, model-rendered sword on B, typeset "Speak" on A, rupee counter, Three-Day Clock with "1st", title card "East Clock Town" in our font.
- Known issues: pause screen not yet seen in game (Start is ignored in my warp save; please open it with a real file); name-entry keyboard typing in scripted tests.
- **Voices to record**: practice pack at `D:/n64work/mm/practice_pack` (35 lines, 5 characters: link_child, link_adult, goron, fairy, man/Ingo).
  Play `practice_<character>_call_and_response.wav` and answer after each beep (SCRIPT.txt lists the lines), then
  `CLEANROOM_GAME=games/mm python -m cleanroom.voice.takes cut <recording> <character> <takes>/<character>`.
  Until then the slots use Piper TTS placeholders (`games/mm/voices`). Unnamed voice samples (Tatl, Deku/Zora Link, Skull Kid) still use resynthesised outlines.
- Item icons: 115 rendered (incl. the four boss remains, also on file select) from the game's own get-item models with our textures (`games/mm/overrides/icons`).
- Bombers' Notebook photos: 11 of 21 rendered from the characters' own skeletons (idle-animation pose, flex-skeleton matrices, our drawn eyes bound to segment 8; `games/mm/portraits.py`). The other 10 need correct object mappings/angles and still use the grid fallback.
- Faces verified on the characters' own posed heads (dev renders with the clean archive): Anju, Cremia, Romani, Kafei, Zoras, Gerudo, Guru-Guru, Ruto read correctly.
- Dungeon/area floor plans (map_grand_static, 98): 90 rendered top-down from each room's own geometry via the scenes' minimap lists (`games/mm/roommaps.py`), drawn in the map style (grey floor, glowing outline); the rest from their grid. Corner minimaps (map_i_static): 51 of 58 the same way, outline style, via the decomp's sMapIForMapGrand table.
- Pause world map of Termina: painted over the kept 16x16 colour layout (relief, canopy, water, snow ridges; ordered dither); fog clouds drawn soft.
- Hylian script: an invented glyph set for the Hylian syllabary cells and for signs, letters, deeds and grave inscriptions.
- HUD numerals/letters drawn: Three-Day Clock hours 1-12, final-hours countdown digits, Bombers' Notebook digits and 18:00, minigame 3/2/1/GO!, PERFECT letters, ocarina note buttons, "Continue playing?", 1/2 ammo.
- HUD icons drawn crisp: hearts (all fill states, defense too), C-button background disc, rupee, small key, timer clock.
- HUD symbols drawn: A/B/C button symbols, R/Z buttons, dungeon-map floor buttons (1F-8F, B1-B8), backspace arrow.
- File-select window drawn as one bevelled panel; Skull Kid balloon painted with Majora's Mask.
- Test hooks (dev, harmless on the live site): `?dev=cvar:value,...`, `?warp=0xD820&warpat=15`, `Module._web_gamestate()`, `Module._web_scene()`.

## Pipeline (all working)
1. `python tools/mm_decompress.py <rom> baserom.dec.z64` (dirty)
2. ZAPD as a node CLI (`bash ports/mm2s2h/build_web.sh ZAPD`, then `node ZAPD.js ed ... -se OTR --otrfile mm.o2r`) -> dirty mm.o2r (50,496 resources) + 2ship.o2r (port assets)
3. `python -m games.mm.extract_spec <dirty mm.o2r> <xml N64_US> games/mm/spec D:/n64work/mm/spec_local` (facts: 13,542 textures, 799 palettes, 682 samples)
4. `python -m games.mm.generate games/mm/spec <kept.o2r> clean/mm.o2r` (12,921 from facts, 621 drawn, 677 samples)
5. Web build: `python -m ports.mm2s2h.web_patches <2s2h>` + `bash ports/mm2s2h/build_web.sh 2ship` -> 2ship.html/js/wasm (22.8 MB)
   Fixes found on the way: wasm exceptions, wasm-sjlj libpng, OTRExporter tinyxml2/libzip, ZAPD without threads, and two C signature mismatches that trap in wasm (PadMgr_ThreadEntry, gfx_create_framebuffer).

## Decisions (log)
1. **Web route = 2 Ship 2 Harkinian (2S2H, the MM PC port) built with Emscripten**, porting zalo's SoH web patches.
   - The OoT clean room (C:/Users/andre/n64work/oot-cleanroom) proved this path with SoH: WebGL2, IndexedDB saves, gamepad/keyboard, no ROM at runtime.
   - 2S2H uses the same engine (libultraship + ZAPDTR/OTRExporter o2r archives). zalo's LUS diff is ~190 lines and applied almost cleanly to 2S2H's LUS (7f9b86a); the game-side changes were re-done for 2S2H (`ports/mm2s2h/web_patches.py`).
   - Why not the others: no Emscripten PC port exists for MM; a clean ROM + WASM emulator needs the IDO decomp built on Windows (no WSL/docker here) and runs slower; N64Recomp is the last resort.
   - Checked: HarbourMasters/2ship2harkinian `develop` (e8757c1), US ROM sha1 d6133ace5afaa0882cf214cf88daba39e266c078.
2. **Web port design** (same as zalo's SoH port): single-threaded (no pthreads, so no COOP/COEP needed on GitHub Pages); the browser drives the loop with requestAnimationFrame; game ticks run at 60/R_UPDATE_RATE Hz; audio is mixed inline once per tick; frames between ticks are re-rendered with 2S2H's own frame interpolation (`Graph_WebRedraw`). Opus custom audio is stubbed (not used by the game). The in-game ROM extractor is not built for the web.
3. **Dirty extraction** of mm.o2r: ZAPD built with Emscripten as a node CLI (NODERAWFS), run by 2S2H's own `extract_assets.py` flow. Output stays in `D:/n64work/mm/dirty`, never published.
4. **Clean-room pipeline**: reuse of the OoT o2r tooling (`games/mm/` started as a copy of `games/oot/`: o2r reader, spec extractor, generator, taint report, faces, labels, icons, dlrender).

## Done while the build is paused (no build needed)
- `tools/mm_decompress.py`: US ROM -> decompressed ROM for 2S2H's extractor (1513 Yaz0 files).
- `games/mm/rom_tex.py` (dirty, dev only): decodes any texture from the ROM via the decomp XML for contact sheets.
- `games/mm/mm_labels.py`: 242 text textures labelled from decomp names (item names, A-button actions, file select, pause, map points, boss cards, day telops).
- `games/mm/drawn.py` adapted to MM: message font with MM button codes (0xB0-0xBB) and accented glyphs, squeeze-to-fit labels, caps boss cards, "Dawn of / The First Day" across both halves, pause headers across 3 stone tiles, title screen (ZELDA metal inside the kept letter silhouette, Majora's Mask picture, subtitle, copyright, N64 wordmark).
- `games/mm/faces.py` + `face_briefs.json`: ~75 characters briefed; new styles for MM: orb (boss/Moon eyes), almond (Zora), blob (Deku); wince/happy states. Checked side by side (`games/mm/face_preview.py`, sheets in `D:/n64work/mm/sheets`).

## Layout
- `D:/n64work/mm/2s2h` engine checkout (patched), `D:/n64work/mm/build-web` web build, `D:/n64work/mm/rom` ROM (never published).
- `ports/mm2s2h/` web patches, shell, build script.

## Next
- File-select window panel: draw the bevelled frame (currently blocky grid tiles).
- Bombers' Notebook photos: fix the remaining 10 (object mapping for Curiosity Shop man, Gorman, Grog, Kamaro, Mayor, Postman, Rosa Sisters, Shiro, Toilet Hand, Toto).
- Voices: identify the unnamed voice samples (Tatl, Deku/Zora Link, Skull Kid) for TTS placeholders.
- Verify pause screen/HUD in a proper new game by hand: my synthetic keys reach file select and the New File menu (Start confirms it) but not name entry, and warp saves skip the HUD. Real keyboards/gamepads send proper events.
