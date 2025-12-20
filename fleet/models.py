"""Fleet model registry. Each slot is one local model served by llama.cpp.

GGUF repos are sensible defaults; override in fleet.yaml. Vision needs an mmproj file.
"""
from __future__ import annotations

# slot -> spec. role explains what the slot is for; the harness routes to slots by role.
SLOTS = {
    "reasoning": {
        "repo": "bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF",
        "file": "DeepSeek-R1-Distill-Qwen-7B-Q5_K_M.gguf",
        "port": 8771, "ctx": 16384, "ngl": 99, "vram_gb": 7, "role": "planning, analysis, chain-of-thought",
    },
    "math": {
        "repo": "bartowski/Qwen2.5-Math-7B-Instruct-GGUF",
        "file": "Qwen2.5-Math-7B-Instruct-Q5_K_M.gguf",
        "port": 8772, "ctx": 8192, "ngl": 99, "vram_gb": 7, "role": "math, SymPy-verifiable problems",
    },
    "coding": {
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q5_K_M.gguf",
        "port": 8773, "ctx": 32768, "ngl": 99, "vram_gb": 7, "role": "code generation + edits",
    },
    "vision": {
        "repo": "bartowski/Qwen2-VL-7B-Instruct-GGUF",
        "file": "Qwen2-VL-7B-Instruct-Q4_K_M.gguf",
        "mmproj": "mmproj-Qwen2-VL-7B-Instruct-f16.gguf",
        "port": 8775, "ctx": 8192, "ngl": 99, "vram_gb": 8, "role": "image understanding / OCR",
    },
    # The 'uncensored' commander slot — an abliterated model for unrestricted local reasoning.
    "uncensored": {
        "repo": "Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1-gguf",
        "file": "Josiefied-Qwen3-8B-abliterated-v1-Q5_K_M.gguf",
        "port": 8774, "ctx": 16384, "ngl": 99, "vram_gb": 9, "role": "lead/commander, unrestricted local reasoning",
    },
}

# slots that cannot be co-resident (VRAM); the launcher evicts conflicts.
SLOT_CONFLICTS = {"uncensored": ["reasoning"], "reasoning": ["uncensored"]}

def resolve(overrides: dict | None = None) -> dict:
    import copy
    s = copy.deepcopy(SLOTS)
    for slot, ov in (overrides or {}).items():
        s.setdefault(slot, {}).update(ov)
    return s
