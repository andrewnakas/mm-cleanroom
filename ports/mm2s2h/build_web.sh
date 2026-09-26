#!/bin/bash
# Build 2S2H for the web (Emscripten) and ZAPD as a node CLI.
#   ports/mm2s2h/build_web.sh [target...]     (default: 2ship)
set -e
SRC=${SRC:-/d/n64work/mm/2s2h}
BUILD=${BUILD:-/d/n64work/mm/build-web}
EMSDK=/e/n64web/emsdk
export EMSDK EM_CACHE=E:/n64web/emcache
export PATH="$EMSDK/upstream/emscripten:$EMSDK/node/24.19.0_64bit:$EMSDK/python/3.13.3_64bit:$EMSDK/upstream/bin:$PATH"
export EM_CONFIG="$EMSDK/.emscripten"
mkdir -p /d/n64work/mm/tmp
export TMP=D:/n64work/mm/tmp TEMP=D:/n64work/mm/tmp TMPDIR=D:/n64work/mm/tmp
if [ ! -f "$BUILD/build.ninja" ]; then
  emcmake cmake -B "$BUILD" -S "$SRC" -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_OPENGLES=ON \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_CROWD_CONTROL=OFF \
    -DGIT_BRANCH=web -DGIT_COMMIT_HASH=clean 2>&1 | tail -25
fi
# C++ exceptions (ZAPD and LUS throw and catch): native wasm exceptions everywhere
if ! grep -q "fwasm-exceptions" "$BUILD/CMakeCache.txt"; then
  cmake "$BUILD" "-DCMAKE_CXX_FLAGS=-DFMT_CONSTEVAL= -fwasm-exceptions" "-DCMAKE_C_FLAGS=-fwasm-exceptions" \
    "-DCMAKE_EXE_LINKER_FLAGS=-fwasm-exceptions" 2>&1 | tail -3
fi
cmake --build "$BUILD" --target "${@:-2ship}" -j ${JOBS:-4} -- -k ${KEEP:-1} 2>&1 | grep -vE "(em\+\+|emcc)(\.exe)? " | grep -E "error|FAILED|^\[[0-9]+/[0-9]+\] Link" | head -40
echo "build exit: ${PIPESTATUS[0]}"
