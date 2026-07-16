"""Tests for fleet.harness — tools, the chat wire format, and the agent loop."""
from __future__ import annotations

import json

import fleet.harness as harness


# ---- tools ---------------------------------------------------------------

def test_run_tool_write_then_read(tmp_path):
    f = tmp_path / "note.txt"
    msg = harness._run_tool(f"write_file {f}|||hello world")
    assert "wrote" in msg
    assert f.read_text(encoding="utf-8") == "hello world"
    assert harness._run_tool(f"read_file {f}") == "hello world"


def test_run_tool_read_missing_file_returns_error():
    out = harness._run_tool("read_file /no/such/path/xyz.txt")
    assert out.startswith("tool error:")


def test_run_tool_unknown_verb():
    assert harness._run_tool("teleport now") == "unknown tool"


def test_run_tool_run_bash_captures_stdout():
    out = harness._run_tool('run_bash echo fleet-ok')
    assert "fleet-ok" in out


def test_run_tool_read_truncates_to_4000(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("A" * 10000, encoding="utf-8")
    assert len(harness._run_tool(f"read_file {f}")) == 4000


# ---- chat wire format ----------------------------------------------------

def test_chat_posts_openai_shape(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "pong"}}]}).encode()

    def fake_urlopen(req, *a, **k):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data)
        return FakeResp()

    monkeypatch.setattr(harness.urllib.request, "urlopen", fake_urlopen)
    out = harness.chat("coding", [{"role": "user", "content": "ping"}])
    assert out == "pong"
    assert captured["url"] == "http://127.0.0.1:8773/v1/chat/completions"
    assert captured["body"]["messages"][0]["content"] == "ping"
    assert "temperature" in captured["body"] and "max_tokens" in captured["body"]


def test_chat_honors_port_override(monkeypatch):
    seen = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "x"}}]}).encode()

    def fake_urlopen(req, *a, **k):
        seen["url"] = req.full_url
        return FakeResp()

    monkeypatch.setattr(harness.urllib.request, "urlopen", fake_urlopen)
    harness.chat("coding", [{"role": "user", "content": "hi"}], overrides={"coding": {"port": 9001}})
    assert ":9001/" in seen["url"]


# ---- agent loop ----------------------------------------------------------

class _FakeMemory:
    def __init__(self):
        self.stored = []
    def recall(self, task):
        return "prior context"
    def remember(self, task, ans):
        self.stored.append((task, ans))


def test_agent_returns_final_and_remembers(monkeypatch):
    mem = _FakeMemory()
    monkeypatch.setattr(harness, "get_memory", lambda: mem)
    monkeypatch.setattr(harness, "chat", lambda slot, msgs, ov=None: "thinking...\nFINAL:: done")
    out = harness.agent("do it")
    assert out == "done"
    assert mem.stored == [("do it", "done")]


def test_agent_runs_tool_then_finishes(monkeypatch):
    mem = _FakeMemory()
    monkeypatch.setattr(harness, "get_memory", lambda: mem)
    replies = iter(["TOOL::run_bash echo hi", "FINAL:: complete"])
    seen_msgs = {}

    def fake_chat(slot, msgs, ov=None):
        seen_msgs["last"] = msgs
        return next(replies)

    monkeypatch.setattr(harness, "chat", fake_chat)
    monkeypatch.setattr(harness, "_run_tool", lambda line: "tool-output")
    out = harness.agent("task")
    assert out == "complete"
    # a TOOL_RESULT message was appended before the second chat call
    assert any("TOOL_RESULT: tool-output" in m["content"] for m in seen_msgs["last"])


def test_agent_returns_plain_output_when_no_protocol(monkeypatch):
    mem = _FakeMemory()
    monkeypatch.setattr(harness, "get_memory", lambda: mem)
    monkeypatch.setattr(harness, "chat", lambda slot, msgs, ov=None: "just an answer")
    out = harness.agent("q")
    assert out == "just an answer"
    assert mem.stored == [("q", "just an answer")]


def test_agent_stops_at_max_steps(monkeypatch):
    mem = _FakeMemory()
    monkeypatch.setattr(harness, "get_memory", lambda: mem)
    monkeypatch.setattr(harness, "chat", lambda slot, msgs, ov=None: "TOOL::run_bash echo loop")
    monkeypatch.setattr(harness, "_run_tool", lambda line: "again")
    out = harness.agent("loop", max_steps=3)
    assert out == "(max steps reached)"


def test_agent_recall_feeds_system_prompt(monkeypatch):
    mem = _FakeMemory()
    monkeypatch.setattr(harness, "get_memory", lambda: mem)
    captured = {}

    def fake_chat(slot, msgs, ov=None):
        captured["sys"] = msgs[0]["content"]
        return "FINAL:: ok"

    monkeypatch.setattr(harness, "chat", fake_chat)
    harness.agent("task")
    assert "prior context" in captured["sys"]
