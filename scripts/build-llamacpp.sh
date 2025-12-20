#!/usr/bin/env bash
# Build llama.cpp with a sensible GPU backend (CUDA/Metal/Vulkan auto-ish).
set -euo pipefail
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
if command -v nvcc >/dev/null; then BACKEND="-DGGML_CUDA=ON";
elif [ "$(uname)" = "Darwin" ]; then BACKEND="-DGGML_METAL=ON";
elif command -v vulkaninfo >/dev/null; then BACKEND="-DGGML_VULKAN=ON";
else BACKEND=""; fi
cmake -B build $BACKEND && cmake --build build --config Release -j
echo "Add to PATH: $(pwd)/build/bin   (provides llama-server)"
