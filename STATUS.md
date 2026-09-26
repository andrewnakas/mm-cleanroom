# The Legend of Zelda: Majora's Mask clean room: status

_Last update: 2026-09-25 ~23:40_

## For the morning
- (in progress) Web build of 2 Ship 2 Harkinian; nothing to look at yet.

## Decisions (log)
1. **Web route = 2 Ship 2 Harkinian (2S2H, the MM PC port) built with Emscripten**, porting zalo's SoH web patches.
   - The OoT clean room (C:/Users/andre/n64work/oot-cleanroom) proved this path with SoH: WebGL2, IndexedDB saves, gamepad/keyboard, no ROM at runtime.
   - 2S2H uses the same engine (libultraship + ZAPDTR/OTRExporter o2r archives). zalo's LUS diff is ~190 lines and applied almost cleanly to 2S2H's LUS (7f9b86a); the game-side changes were re-done for 2S2H (`ports/mm2s2h/web_patches.py`).
   - Why not the others: no Emscripten PC port exists for MM; a clean ROM + WASM emulator needs the IDO decomp built on Windows (no WSL/docker here) and runs slower; N64Recomp is the last resort.
   - Checked: HarbourMasters/2ship2harkinian `develop` (e8757c1), US ROM sha1 d6133ace5afaa0882cf214cf88daba39e266c078.
2. **Web port design** (same as zalo's SoH port): single-threaded (no pthreads, so no COOP/COEP needed on GitHub Pages); the browser drives the loop with requestAnimationFrame; game ticks run at 60/R_UPDATE_RATE Hz; audio is mixed inline once per tick; frames between ticks are re-rendered with 2S2H's own frame interpolation (`Graph_WebRedraw`). Opus custom audio is stubbed (not used by the game). The in-game ROM extractor is not built for the web.
3. **Dirty extraction** of mm.o2r: ZAPD built with Emscripten as a node CLI (NODERAWFS), run by 2S2H's own `extract_assets.py` flow. Output stays in `D:/n64work/mm/dirty`, never published.
4. **Clean-room pipeline**: reuse of the OoT o2r tooling (`games/mm/` started as a copy of `games/oot/`: o2r reader, spec extractor, generator, taint report, faces, labels, icons, dlrender).

## Layout
- `D:/n64work/mm/2s2h` engine checkout (patched), `D:/n64work/mm/build-web` web build, `D:/n64work/mm/rom` ROM (never published).
- `ports/mm2s2h/` web patches, shell, build script.

## Next
- Build web + ZAPD, extract dirty mm.o2r, boot with dirty data (dev only) to validate the port.
- Spec + generate clean mm.o2r, taint scan, publish.
