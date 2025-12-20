"""A tiny, model-agnostic agent harness that drives a fleet slot over the
llama.cpp OpenAI-compatible endpoint, with hermes memory and a few safe tools.
"""
from __future__ import annotations
import json, subprocess, urllib.request
from pathlib import Path
from fleet.models import resolve
from fleet.memory import get_memory

def chat(slot: str, messages: list, overrides=None, temperature=0.6, max_tokens=1024) -> str:
    port = resolve(overrides)[slot]["port"]
    body = json.dumps({"messages": messages, "temperature": temperature, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

TOOLS_DOC = """You can use tools by emitting a single line:
TOOL::run_bash <cmd>
TOOL::read_file <path>
TOOL::write_file <path>|||<content>
When done, emit:  FINAL:: <answer>"""

def _run_tool(line: str) -> str:
    try:
        verb, _, rest = line.partition(" ")
        if verb == "run_bash":
            return subprocess.run(rest, shell=True, capture_output=True, text=True, timeout=60).stdout[:4000]
        if verb == "read_file":
            return Path(rest.strip()).read_text(encoding="utf-8", errors="ignore")[:4000]
        if verb == "write_file":
            path, _, content = rest.partition("|||")
            Path(path.strip()).write_text(content, encoding="utf-8"); return f"wrote {path.strip()}"
    except Exception as e:
        return f"tool error: {e}"
    return "unknown tool"

def agent(task: str, slot: str = "uncensored", overrides=None, max_steps: int = 8) -> str:
    mem = get_memory()
    context = mem.recall(task)
    sys_msg = {"role": "system", "content":
               f"You are a Cognis fleet agent. {TOOLS_DOC}\nRelevant memory: {context}"}
    msgs = [sys_msg, {"role": "user", "content": task}]
    for _ in range(max_steps):
        out = chat(slot, msgs, overrides)
        msgs.append({"role": "assistant", "content": out})
        if "FINAL::" in out:
            ans = out.split("FINAL::", 1)[1].strip()
            mem.remember(task, ans)
            return ans
        if "TOOL::" in out:
            line = out.split("TOOL::", 1)[1].splitlines()[0].strip()
            result = _run_tool(line)
            msgs.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
        else:
            mem.remember(task, out)
            return out
    return "(max steps reached)"
