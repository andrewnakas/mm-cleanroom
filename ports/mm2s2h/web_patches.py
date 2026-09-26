"""Emscripten (WebGL2) port of 2 Ship 2 Harkinian, as idempotent text patches.

    python -m ports.mm2s2h.web_patches <2s2h checkout>

Modelled on zalo's SoH web port (zalo/Shipwright feature/emscripten-web-port):
single-threaded (no pthreads), the browser drives the frame loop with
requestAnimationFrame, audio is mixed inline on each game tick, and frames between
game ticks are re-rendered with 2S2H's own frame interpolation.
The libultraship half is ports/mm2s2h/lus_web.diff (zalo's LUS diff rebased).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

WEB_LINK = r'''
if(BUILD_FOR_WEB)
    target_compile_options(${PROJECT_NAME} PRIVATE
        -sUSE_SDL=2 -sUSE_OGG=1 -sUSE_VORBIS=1 -sUSE_ZLIB=1
        -w
        $<$<COMPILE_LANGUAGE:CXX>:-fpermissive>
        $<$<COMPILE_LANGUAGE:C>:-Wno-implicit-function-declaration -Wno-incompatible-pointer-types -Wno-int-conversion>
    )
    target_link_options(${PROJECT_NAME} PRIVATE
        -sUSE_SDL=2 -sUSE_ZLIB=1 -sUSE_OGG=1 -sUSE_VORBIS=1
        -sALLOW_MEMORY_GROWTH=1
        -sINITIAL_MEMORY=536870912
        -sSTACK_SIZE=8388608
        -sMAX_WEBGL_VERSION=2 -sMIN_WEBGL_VERSION=2
        -sFULL_ES3=1
        -sFORCE_FILESYSTEM=1
        -sEXIT_RUNTIME=0
        -sEXPORTED_RUNTIME_METHODS=ccall,cwrap,FS,IDBFS,addRunDependency,removeRunDependency,stringToUTF8,UTF8ToString,lengthBytesUTF8
        -sEXPORTED_FUNCTIONS=_main,_malloc,_free
        -lidbfs.js
        --profiling-funcs
        --shell-file=${CMAKE_CURRENT_SOURCE_DIR}/2s2h/web/shell.html
    )
    set_target_properties(${PROJECT_NAME} PROPERTIES OUTPUT_NAME "2ship" SUFFIX ".html")
endif()
'''

PATCHES = [
    # ---------------------------------------------------------------- root CMake
    ("CMakeLists.txt",
     'project(2s2h VERSION 5.0.1 LANGUAGES C CXX)\n',
     'project(2s2h VERSION 5.0.1 LANGUAGES C CXX)\n'
     'if(EMSCRIPTEN OR CMAKE_SYSTEM_NAME STREQUAL "Emscripten")\n'
     '    set(BUILD_FOR_WEB ON)\n'
     'else()\n'
     '    set(BUILD_FOR_WEB OFF)\n'
     'endif()\n'),
    ("CMakeLists.txt",
     '# Enable the Gfx debugger in LUS to use libgfxd from ZAPDTR\nset(GFX_DEBUG_DISASSEMBLER ON)\n',
     '# Enable the Gfx debugger in LUS to use libgfxd from ZAPDTR\n'
     'if(BUILD_FOR_WEB)\n    set(GFX_DEBUG_DISASSEMBLER OFF)\nelse()\n    set(GFX_DEBUG_DISASSEMBLER ON)\nendif()\n'),
    ("CMakeLists.txt",
     '# Enable MPQ and OTR support\nset(INCLUDE_MPQ_SUPPORT ON)\n',
     '# Enable MPQ and OTR support (no MPQ on web: StormLib bundles K&R zlib)\n'
     'if(BUILD_FOR_WEB)\n    set(INCLUDE_MPQ_SUPPORT OFF)\nelse()\n    set(INCLUDE_MPQ_SUPPORT ON)\nendif()\n'),
    ("CMakeLists.txt",
     'else()\n    set(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG")\n',
     'elseif(BUILD_FOR_WEB)\n    set(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG")\n    set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG")\n'
     'else()\n    set(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG")\n'),
    ("CMakeLists.txt",
     'target_compile_definitions(libultraship PUBLIC INCLUDE_MPQ_SUPPORT)\n',
     'if(INCLUDE_MPQ_SUPPORT)\n    target_compile_definitions(libultraship PUBLIC INCLUDE_MPQ_SUPPORT)\nendif()\n'),

    # ---------------------------------------------------------------- game CMake
    # no in-game extractor on web (the clean room ships its archives)
    ("mm/CMakeLists.txt",
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS")\n    file(GLOB_RECURSE ship__Extractor',
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS" AND NOT BUILD_FOR_WEB)\n    file(GLOB_RECURSE ship__Extractor'),
    ("mm/CMakeLists.txt",
     'find_package(SDL2)\nset(SDL2-INCLUDE ${SDL2_INCLUDE_DIRS})\n',
     'if(NOT BUILD_FOR_WEB)\nfind_package(SDL2)\nset(SDL2-INCLUDE ${SDL2_INCLUDE_DIRS})\nendif()\n'),
    ("mm/CMakeLists.txt",
     '    else()\n        if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64")\n\t\tset(CPU_OPTION -msse2 -mfpmath=sse)\n',
     '    elseif(BUILD_FOR_WEB)\n' + WEB_LINK.replace('\n', '\n    ') + '\n'
     '    else()\n        if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64")\n\t\tset(CPU_OPTION -msse2 -mfpmath=sse)\n'),
    ("mm/CMakeLists.txt",
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS")\n    add_custom_command(\n        TARGET ${PROJECT_NAME}\n        POST_BUILD',
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS" AND NOT BUILD_FOR_WEB)\n    add_custom_command(\n        TARGET ${PROJECT_NAME}\n        POST_BUILD'),
    ("mm/CMakeLists.txt",
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS")\nadd_dependencies(${PROJECT_NAME}\n    ZAPDLib\n)\nendif()\n',
     'if(NOT CMAKE_SYSTEM_NAME MATCHES "NintendoSwitch|CafeOS" AND NOT BUILD_FOR_WEB)\nadd_dependencies(${PROJECT_NAME}\n    ZAPDLib\n)\nendif()\n'),
    ("mm/CMakeLists.txt",
     'else()\n    find_package(SDL2)\n    set(THREADS_PREFER_PTHREAD_FLAG ON)\n',
     'elseif(BUILD_FOR_WEB)\n    set(ADDITIONAL_LIBRARY_DEPENDENCIES "libultraship;")\n'
     'else()\n    find_package(SDL2)\n    set(THREADS_PREFER_PTHREAD_FLAG ON)\n'),
    ("mm/CMakeLists.txt",
     'find_program(CURL NAMES curl DOC "Path to the curl program.  Used to download files.")\nexecute_process(',
     'if(NOT BUILD_FOR_WEB)\nfind_program(CURL NAMES curl DOC "Path to the curl program.  Used to download files.")\nendif()\nif(NOT BUILD_FOR_WEB)\nexecute_process('),
    ("mm/CMakeLists.txt",
     '-o ${CMAKE_BINARY_DIR}/gamecontrollerdb.txt OUTPUT_VARIABLE RESULT)\n',
     '-o ${CMAKE_BINARY_DIR}/gamecontrollerdb.txt OUTPUT_VARIABLE RESULT)\nendif()\n'),

    # ---------------------------------------------------------------- ZAPD as a node CLI (dirty-room extraction)
    ("OTRExporter/OTRExporter/CMakeLists.txt",
     'find_package(nlohmann_json REQUIRED)\n',
     'if(NOT TARGET nlohmann_json::nlohmann_json)\nfind_package(nlohmann_json REQUIRED)\nendif()\n'),
    ("OTRExporter/OTRExporter/CMakeLists.txt",
     'find_package(spdlog REQUIRED)\n',
     'if(NOT TARGET spdlog::spdlog)\nfind_package(spdlog REQUIRED)\nendif()\n'),
    ("ZAPDTR/ZAPD/CMakeLists.txt",
     'find_package(PNG REQUIRED)\n',
     'if(EMSCRIPTEN)\n'
     '    # emscripten port (embuilder build libpng)\n'
     '    set(PNG_LIBRARY "$ENV{EM_CACHE}/sysroot/lib/wasm32-emscripten/libpng.a" CACHE FILEPATH "" FORCE)\n'
     '    set(PNG_PNG_INCLUDE_DIR "$ENV{EM_CACHE}/sysroot/include" CACHE PATH "" FORCE)\n'
     'endif()\n'
     'find_package(PNG REQUIRED)\n'),
    ("ZAPDTR/ZAPD/CMakeLists.txt",
     'target_link_libraries(ZAPD ${PROJECT_NAME})\n',
     'target_link_libraries(ZAPD ${PROJECT_NAME})\n'
     'if(EMSCRIPTEN)\n'
     '    target_link_options(ZAPD PRIVATE -sNODERAWFS=1 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=268435456 -sSTACK_SIZE=8388608 -sEXIT_RUNTIME=1 -sUSE_LIBPNG=1 -sUSE_ZLIB=1 -sENVIRONMENT=node)\n'
     '    target_compile_options(${PROJECT_NAME} PUBLIC -sUSE_LIBPNG=1 -sUSE_ZLIB=1)\n'
     '    set_target_properties(ZAPD PROPERTIES SUFFIX ".js")\n'
     'endif()\n'),

    # ---------------------------------------------------------------- BenPort.cpp
    ("mm/2s2h/BenPort.cpp",
     '#include "Extractor/Extract.h"\n',
     '#ifndef __EMSCRIPTEN__\n#include "Extractor/Extract.h"\n#else\n#include <emscripten.h>\n#endif\n'),
    # config lives next to the saves, which the page persists in IndexedDB
    ("mm/2s2h/BenPort.cpp",
     '    context = Ship::Context::CreateUninitializedInstance("2 Ship 2 Harkinian", appShortName, "2ship2harkinian.json");\n',
     '#ifdef __EMSCRIPTEN__\n'
     '    context = Ship::Context::CreateUninitializedInstance("2 Ship 2 Harkinian", appShortName, "saves/2ship2harkinian.json");\n'
     '#else\n'
     '    context = Ship::Context::CreateUninitializedInstance("2 Ship 2 Harkinian", appShortName, "2ship2harkinian.json");\n'
     '#endif\n'),
    ("mm/2s2h/BenPort.cpp",
     'void OTRGlobals::RunExtract(int argc, char* argv[]) {\n',
     'void OTRGlobals::RunExtract(int argc, char* argv[]) {\n#ifdef __EMSCRIPTEN__\n    return;\n#else\n'),
    ("mm/2s2h/BenPort.cpp",
     'void OTRGlobals::Initialize() {\n',
     '#endif\n#ifdef __EMSCRIPTEN__\n}\n#endif\n\nvoid OTRGlobals::Initialize() {\n'),
    ("mm/2s2h/BenPort.cpp",
     'uint32_t OTRGlobals::GetInterpolationFPS() {\n',
     'uint32_t OTRGlobals::GetInterpolationFPS() {\n#ifdef __EMSCRIPTEN__\n    return 60;\n#endif\n'),
    ("mm/2s2h/BenPort.cpp",
     'void OTRAudio_Thread() {\n',
     '#define SAMPLES_HIGH 560\n#define SAMPLES_LOW 528\n#define AUDIO_FRAMES_PER_UPDATE (R_UPDATE_RATE > 0 ? R_UPDATE_RATE : 1)\n#define NUM_AUDIO_CHANNELS 2\n'
     '#ifdef __EMSCRIPTEN__\n'
     '// no threads on web: mix one game tick of audio inline\n'
     'static void OTRAudio_ProcessInline() {\n'
     '    int samples_left = AudioPlayer_Buffered();\n'
     '    u32 num_audio_samples = samples_left < AudioPlayer_GetDesiredBuffered() ? SAMPLES_HIGH : SAMPLES_LOW;\n'
     '    static s16 audio_buffer[SAMPLES_HIGH * NUM_AUDIO_CHANNELS * 3];\n'
     '    for (int i = 0; i < AUDIO_FRAMES_PER_UPDATE; i++) {\n'
     '        AudioMgr_CreateNextAudioBuffer(audio_buffer + i * (num_audio_samples * NUM_AUDIO_CHANNELS), num_audio_samples);\n'
     '    }\n'
     '    AudioPlayer_Play((u8*)audio_buffer, num_audio_samples * (sizeof(int16_t) * NUM_AUDIO_CHANNELS * AUDIO_FRAMES_PER_UPDATE));\n'
     '}\n'
     '#endif\n'
     'void OTRAudio_Thread() {\n'),
    ("mm/2s2h/BenPort.cpp",
     '#define SAMPLES_HIGH 560\n#define SAMPLES_LOW 528\n\n#define AUDIO_FRAMES_PER_UPDATE (R_UPDATE_RATE > 0 ? R_UPDATE_RATE : 1)\n#define NUM_AUDIO_CHANNELS 2\n',
     ''),
    ("mm/2s2h/BenPort.cpp",
     '    if (!audio.running) {\n        audio.running = true;\n        audio.thread = std::thread(OTRAudio_Thread);\n    }\n',
     '#ifdef __EMSCRIPTEN__\n    audio.running = true;\n#else\n'
     '    if (!audio.running) {\n        audio.running = true;\n        audio.thread = std::thread(OTRAudio_Thread);\n    }\n#endif\n'),
    ("mm/2s2h/BenPort.cpp",
     '    // Wait until the audio thread quit\n    audio.thread.join();\n',
     '    // Wait until the audio thread quit\n#ifndef __EMSCRIPTEN__\n    audio.thread.join();\n#endif\n'),
    ("mm/2s2h/BenPort.cpp",
     'extern "C" void Messagebox_ShowErrorBox(char* title, char* body) {\n    Extractor::ShowErrorBox(title, body);\n',
     'extern "C" void Messagebox_ShowErrorBox(char* title, char* body) {\n#ifdef __EMSCRIPTEN__\n    SPDLOG_ERROR("{}: {}", title, body);\n#else\n    Extractor::ShowErrorBox(title, body);\n#endif\n'),
    ("mm/2s2h/BenPort.cpp",
     'extern "C" void Graph_ProcessGfxCommands(Gfx* commands) {\n    {\n',
     '#ifdef __EMSCRIPTEN__\n'
     'static Gfx* sWebLastCommands = NULL;\n'
     '// Called by the rAF loop (graph.c) between game ticks: redraw the last frame, interpolated.\n'
     'extern "C" void Graph_WebRedraw(float frac) {\n'
     '    int t = (int)(frac * 1000.0f);\n'
     '    if (sWebLastCommands == NULL || t >= 1000) {\n'
     '        return;\n'
     '    }\n'
     '    if (t < 1) {\n'
     '        t = 1;\n'
     '    }\n'
     '    RunCommands(sWebLastCommands, t, 0, 1000, 1);\n'
     '}\n'
     '#endif\n'
     'extern "C" void Graph_ProcessGfxCommands(Gfx* commands) {\n'
     '#ifdef __EMSCRIPTEN__\n'
     '    {\n'
     '        OTRAudio_ProcessInline();\n'
     '        auto wwnd = std::dynamic_pointer_cast<Fast::Fast3dWindow>(Ship::Context::GetRawInstance()->GetWindow());\n'
     '        if (wwnd != nullptr) {\n'
     '            wwnd->SetTargetFps(60);\n'
     '        }\n'
     '        sWebLastCommands = commands;\n'
     '        RunCommands(commands, 1000, 0, 1000, 1);\n'
     '        bool curAltAssets = CVarGetInteger("gEnhancements.Mods.AlternateAssets", 0);\n'
     '        if (prevAltAssets != curAltAssets) {\n'
     '            prevAltAssets = curAltAssets;\n'
     '            Ship::Context::GetRawInstance()->GetResourceManager()->SetAltAssetsEnabled(curAltAssets);\n'
     '            gfx_texture_cache_clear();\n'
     '        }\n'
     '        return;\n'
     '    }\n'
     '#endif\n'
     '    {\n'),

    # ---------------------------------------------------------------- threads elsewhere
    ("mm/2s2h/resource/importer/AudioSampleFactory.cpp",
     '            std::thread fileDecoderThread = std::thread(Mp3DecoderWorker, audioSample, sampleFile);\n            fileDecoderThread.detach();\n',
     '#ifdef __EMSCRIPTEN__\n            Mp3DecoderWorker(audioSample, sampleFile);\n#else\n'
     '            std::thread fileDecoderThread = std::thread(Mp3DecoderWorker, audioSample, sampleFile);\n            fileDecoderThread.detach();\n#endif\n'),
    ("mm/2s2h/resource/importer/AudioSampleFactory.cpp",
     '            std::thread fileDecoderThread = std::thread(OggDecoderWorker, audioSample, sampleFile, initData);\n            fileDecoderThread.detach();\n',
     '#ifdef __EMSCRIPTEN__\n            OggDecoderWorker(audioSample, sampleFile, initData);\n#else\n'
     '            std::thread fileDecoderThread = std::thread(OggDecoderWorker, audioSample, sampleFile, initData);\n            fileDecoderThread.detach();\n#endif\n'),
    ("mm/2s2h/resource/importer/AudioSampleFactory.cpp",
     '            std::thread fileDecoderThread = std::thread(FlacDecoderWorker, audioSample, sampleFile);\n            fileDecoderThread.detach();\n',
     '#ifdef __EMSCRIPTEN__\n            FlacDecoderWorker(audioSample, sampleFile);\n#else\n'
     '            std::thread fileDecoderThread = std::thread(FlacDecoderWorker, audioSample, sampleFile);\n            fileDecoderThread.detach();\n#endif\n'),
    ("mm/2s2h/mixer.c",
     '#include <opus/opus.h>\n#include <opusfile.h>\n',
     '#ifndef __EMSCRIPTEN__\n#include <opus/opus.h>\n#include <opusfile.h>\n#endif\n'),
    ("mm/2s2h/mixer.c",
     '                  uint32_t size) {\n    int readSamples = 0;\n',
     '                  uint32_t size) {\n#ifdef __EMSCRIPTEN__\n    memset(BUF_U8(dest_addr), 0, nbytes);\n    return;\n#else\n    int readSamples = 0;\n'),
    ("mm/2s2h/mixer.c",
     '        readSamples += ret;\n    }\n}\n\nvoid aOPUSFree(struct OggOpusFile* opusFile) {\n    op_free(opusFile);\n',
     '        readSamples += ret;\n    }\n#endif\n}\n\nvoid aOPUSFree(struct OggOpusFile* opusFile) {\n#ifndef __EMSCRIPTEN__\n    op_free(opusFile);\n#endif\n'),

    # ---------------------------------------------------------------- frame loop driven by requestAnimationFrame
    ("mm/src/code/graph.c",
     'void Graph_ThreadEntry(void* arg0) {\n    while (WindowIsRunning()) {\n        RunFrame();\n    }\n}\n',
     '#ifdef __EMSCRIPTEN__\n'
     '#include <emscripten.h>\n'
     'void Graph_WebRedraw(float frac);\n'
     'static double sWebLastTick = 0;\n'
     'static int sWebHaveFrame = 0;\n'
     'int gWebTicks = 0;\n'
     '// One rAF callback: run the game ticks that are due (60 / R_UPDATE_RATE per second),\n'
     '// otherwise redraw the last frame interpolated towards the next tick.\n'
     'static void RunFrameWeb(void) {\n'
     '    double now = emscripten_get_now() / 1000.0;\n'
     '    int rate = R_UPDATE_RATE;\n'
     '    if (rate < 1) {\n'
     '        rate = 1;\n'
     '    }\n'
     '    if (rate > 3) {\n'
     '        rate = 3;\n'
     '    }\n'
     '    double tick = rate / 60.0;\n'
     '    if (sWebLastTick == 0) {\n'
     '        sWebLastTick = now;\n'
     '    }\n'
     '    double elapsed = now - sWebLastTick;\n'
     '    if (elapsed >= tick || !sWebHaveFrame) {\n'
     '        int n = (int)(elapsed / tick);\n'
     '        if (n < 1) {\n'
     '            n = 1;\n'
     '        }\n'
     '        if (n > 3) {\n'
     '            n = 3;\n'
     '        }\n'
     '        for (int i = 0; i < n; i++) {\n'
     '            RunFrame();\n'
     '            gWebTicks++;\n'
     '        }\n'
     '        sWebLastTick += n * tick;\n'
     '        if (now - sWebLastTick > tick) {\n'
     '            sWebLastTick = now;\n'
     '        }\n'
     '        sWebHaveFrame = 1;\n'
     '    } else {\n'
     '        Graph_WebRedraw((float)(elapsed / tick));\n'
     '    }\n'
     '}\n'
     '#endif\n'
     'void Graph_ThreadEntry(void* arg0) {\n'
     '#ifdef __EMSCRIPTEN__\n'
     '    emscripten_set_main_loop(RunFrameWeb, 0, 1);\n'
     '#else\n'
     '    while (WindowIsRunning()) {\n        RunFrame();\n    }\n'
     '#endif\n'
     '}\n'),
]


def apply(root):
    changed = 0
    for rel, old, new in PATCHES:
        p = os.path.join(root, rel)
        s = open(p, encoding="utf8", newline="").read()
        if "\r\n" in s:
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        if new and new in s:
            continue
        if old not in s:
            if not new:
                continue
            print(f"FAIL anchor not found: {rel}: {old[:60]!r}")
            continue
        s = s.replace(old, new, 1)
        open(p, "w", encoding="utf8", newline="").write(s)
        changed += 1
    # web shell + extra sources
    web = os.path.join(root, "mm", "2s2h", "web")
    os.makedirs(web, exist_ok=True)
    src = os.path.join(HERE, "shell.html")
    if os.path.exists(src):
        open(os.path.join(web, "shell.html"), "w", encoding="utf8", newline="").write(
            open(src, encoding="utf8").read())
    # libultraship half
    lus = os.path.join(root, "libultraship")
    diff = os.path.join(HERE, "lus_web.diff")
    if os.path.exists(diff):
        r = subprocess.run(["git", "apply", "--check", diff], cwd=lus, capture_output=True)
        if r.returncode == 0:
            subprocess.run(["git", "apply", diff], cwd=lus, check=True)
            print("lus_web.diff applied")
    print(f"{changed} patches applied, {len(PATCHES)} total")


if __name__ == "__main__":
    apply(sys.argv[1])
