"""A tiny, model-agnostic agent harness that drives a fleet slot over the
llama.cpp OpenAI-compatible endpoint, with engram memory and a few safe tools.
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from fleet.models import resolve
from fleet.memory import get_memory

# Default timeout (seconds) for HTTP calls to the local llama.cpp server.
_HTTP_TIMEOUT = int(__import__("os").environ.get("FLEET_HTTP_TIMEOUT", "120"))


def chat(slot: str, messages: list, overrides=None, temperature=0.6, max_tokens=1024) -> str:
    """Send *messages* to *slot* and return the assistant reply text.

    Raises ValueError on empty messages, KeyError/IndexError on malformed
    server responses, and urllib.error.URLError on network failures — all with
    clear, actionable messages.
    """
    if not messages:
        raise ValueError("messages list must not be empty")
    slots = resolve(overrides)
    if slot not in slots:
        raise ValueError(f"unknown slot '{slot}'; known: {', '.join(slots)}")
    port = slots[slot]["port"]
    body = json.dumps({
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            raw = r.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"[{slot}] could not reach llama.cpp on port {port}: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError(
            f"[{slot}] request timed out after {_HTTP_TIMEOUT}s"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"[{slot}] server returned non-JSON response: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"[{slot}] unexpected response shape (missing choices/message/content): {exc}"
        ) from exc


TOOLS_DOC = """You can use tools by emitting a single line:
TOOL::run_bash <cmd>
TOOL::read_file <path>
TOOL::write_file <path>|||<content>
When done, emit:  FINAL:: <answer>"""


def _run_tool(line: str) -> str:
    try:
        verb, _, rest = line.partition(" ")
        if verb == "run_bash":
            if not rest.strip():
                return "tool error: empty command"
            return subprocess.run(
                rest, shell=True, capture_output=True, text=True, timeout=60
            ).stdout[:4000]
        if verb == "read_file":
            path = rest.strip()
            if not path:
                return "tool error: no path given"
            p = Path(path)
            if not p.exists():
                return f"tool error: file not found: {path}"
            return p.read_text(encoding="utf-8", errors="ignore")[:4000]
        if verb == "write_file":
            path, _, content = rest.partition("|||")
            path = path.strip()
            if not path:
                return "tool error: no path given"
            Path(path).write_text(content, encoding="utf-8")
            return f"wrote {path}"
    except Exception as e:  # noqa: BLE001
        return f"tool error: {e}"
    return "unknown tool"


def agent(task: str, slot: str = "uncensored", overrides=None, max_steps: int = 8) -> str:
    if not task or not task.strip():
        raise ValueError("task must not be empty")
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    mem = get_memory()
    context = mem.recall(task)
    sys_msg = {
        "role": "system",
        "content": f"You are a Cognis fleet agent. {TOOLS_DOC}\nRelevant memory: {context}",
    }
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
