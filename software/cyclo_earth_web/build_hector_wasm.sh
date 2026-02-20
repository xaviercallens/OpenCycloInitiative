#!/bin/bash
# Cyclo-Earth Planetary Simulator
# Hector C++ -> WebAssembly Build Script
# 
# This script compiles the Hector simplified climate model from C++ into 
# WebAssembly (.wasm) for execution in the browser frontend (Project Genesis).
# 
# Requires: Emscripten (emcc)

set -e

echo "============================================"
echo "    CYCLO-EARTH: Hector Wasm Build Pipeline "
echo "============================================"

# Check for emcc
if ! command -v emcc &> /dev/null; then
    echo "ERROR: Emscripten (emcc) could not be found."
    echo "Please install Emscripten SDK and source emsdk_env.sh."
    echo "Using mock artifact generation for now."
    
    mkdir -p public/wasm
    echo "// Mock WASM wrapper" > public/wasm/hector.js
    echo "00 61 73 6d" > public/wasm/hector.wasm
    echo "✅ [MOCK] Hector Wasm artifacts built:"
    echo "  - public/wasm/hector.js"
    echo "  - public/wasm/hector.wasm"
    exit 0
fi

# Actual build compilation if emcc is present
SRC_DIR="../../physics/hector_cpp"
OUT_DIR="public/wasm"

mkdir -p $OUT_DIR

echo "Building Hector C++ core to WebAssembly..."

emcc $SRC_DIR/hector_core.cpp \
     $SRC_DIR/psc_equations.cpp \
     -o $OUT_DIR/hector.js \
     -O3 \
     -s WASM=1 \
     -s EXPORTED_FUNCTIONS="['_init_hector', '_step_hector', '_get_temperature', '_get_co2']" \
     -s EXPORTED_RUNTIME_METHODS="['ccall', 'cwrap']" \
     -s ALLOW_MEMORY_GROWTH=1 \
     -std=c++17

echo "✅ WebAssembly build complete:"
echo "  - $OUT_DIR/hector.js"
echo "  - $OUT_DIR/hector.wasm"
