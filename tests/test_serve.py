"""Tests for fleet.serve — state file, status rows, teardown, and launch guards."""
from __future__ import annotations

import importlib

import pytest

import fleet.serve as serve


def _reload(monkeypatch, tmp_path):
    monkeypatch.setenv("FLEET_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("FLEET_MODELS_DIR", str(tmp_path / "models"))
    import fleet.download
    importlib.reload(fleet.download)
    return importlib.reload(serve)


def test_load_default_when_missing(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    assert sv._load() == {"running": {}}


def test_save_then_load_roundtrip(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    sv._save({"running": {"coding": {"pid": 42, "port": 8773}}})
    assert sv._load()["running"]["coding"]["pid"] == 42


def test_status_reports_rows_for_all_slots(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    monkeypatch.setattr(sv, "_port_up", lambda port: port == 8774)
    rows = dict((slot, (port, state)) for slot, port, state, role in sv.status())
    assert rows["uncensored"][1] == "UP"
    assert rows["coding"][1] == "down"
    # one row per registered slot
    assert len(rows) == len(sv.resolve())


def test_down_removes_from_state(monkeypatch, tmp_path, capsys):
    sv = _reload(monkeypatch, tmp_path)
    sv._save({"running": {"coding": {"pid": 12345, "port": 8773},
                          "math": {"pid": 23456, "port": 8772}}})
    killed = []
    monkeypatch.setattr(sv.os, "kill", lambda pid, sig: killed.append(pid))
    sv.down("coding")
    st = sv._load()
    assert "coding" not in st["running"] and "math" in st["running"]
    assert 12345 in killed
    assert "stopped" in capsys.readouterr().out


def test_down_all_when_no_slot(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    sv._save({"running": {"coding": {"pid": 1, "port": 8773},
                          "math": {"pid": 2, "port": 8772}}})
    monkeypatch.setattr(sv.os, "kill", lambda pid, sig: None)
    sv.down()
    assert sv._load()["running"] == {}


def test_down_survives_dead_pid(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    sv._save({"running": {"coding": {"pid": 999999, "port": 8773}}})

    def boom(pid, sig):
        raise ProcessLookupError

    monkeypatch.setattr(sv.os, "kill", boom)
    sv.down("coding")  # must not raise
    assert sv._load()["running"] == {}


def test_up_requires_llama_server(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    monkeypatch.setattr(sv.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit):
        sv.up("coding")


def test_up_requires_downloaded_model(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    monkeypatch.setattr(sv.shutil, "which", lambda name: "/usr/bin/llama-server")
    with pytest.raises(SystemExit) as e:
        sv.up("coding")
    assert "not downloaded" in str(e.value)


def test_up_launches_and_records_pid(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    monkeypatch.setattr(sv.shutil, "which", lambda name: "/usr/bin/llama-server")
    # create the model file so the guard passes
    mp = sv.model_path("coding")
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text("stub", encoding="utf-8")

    captured = {}

    class FakePopen:
        def __init__(self, cmd, **kw):
            captured["cmd"] = cmd
            self.pid = 4242

    monkeypatch.setattr(sv.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sv, "_port_up", lambda port: True)
    sv.up("coding")
    st = sv._load()
    assert st["running"]["coding"]["pid"] == 4242
    assert "llama-server" in captured["cmd"][0]
    assert str(mp) in captured["cmd"]


def test_up_evicts_conflicting_slot(monkeypatch, tmp_path):
    sv = _reload(monkeypatch, tmp_path)
    monkeypatch.setattr(sv.shutil, "which", lambda name: "/usr/bin/llama-server")
    # reasoning is currently 'running' and conflicts with uncensored
    sv._save({"running": {"reasoning": {"pid": 111, "port": 8771}}})
    mp = sv.model_path("uncensored")
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(sv.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(sv.subprocess, "Popen", lambda cmd, **kw: type("P", (), {"pid": 7})())
    monkeypatch.setattr(sv, "_port_up", lambda port: True)
    sv.up("uncensored")
    st = sv._load()
    assert "reasoning" not in st["running"]
    assert st["running"]["uncensored"]["pid"] == 7
