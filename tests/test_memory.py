"""Tests for the fleet.memory sqlite fallback store."""
from __future__ import annotations

from fleet.memory import _Fallback, get_memory


def test_fallback_remember_and_recall(tmp_path):
    m = _Fallback(str(tmp_path / "mem.sqlite"))
    m.remember("build the parser", "used recursive descent")
    hits = m.recall("parser")
    assert hits and hits[0]["value"] == "used recursive descent"
    assert hits[0]["key"] == "build the parser"


def test_fallback_recall_matches_value_text(tmp_path):
    m = _Fallback(str(tmp_path / "mem.sqlite"))
    m.remember("k1", "contains SPECIAL token")
    assert m.recall("SPECIAL")
    assert m.recall("nonexistent-term") == []


def test_fallback_recall_orders_newest_first(tmp_path):
    m = _Fallback(str(tmp_path / "mem.sqlite"))
    m.remember("topic", "first")
    m.remember("topic", "second")
    vals = [h["value"] for h in m.recall("topic")]
    assert vals[0] == "second"


def test_fallback_recall_honors_limit(tmp_path):
    m = _Fallback(str(tmp_path / "mem.sqlite"))
    for i in range(10):
        m.remember("bulk", f"item-{i}")
    assert len(m.recall("bulk", k=3)) == 3


def test_get_memory_falls_back_to_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_MEMORY", str(tmp_path / "m.sqlite"))
    # ensure the optional engram package is not importable
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "engram":
            raise ImportError("no engram")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mem = get_memory()
    mem.remember("x", "y")
    assert mem.recall("x")[0]["value"] == "y"
