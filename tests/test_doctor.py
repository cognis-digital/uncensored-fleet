"""Tests for fleet.doctor — the read-only environment diagnostics."""
from __future__ import annotations

from fleet import doctor


def test_python_check_passes_on_supported_runtime():
    c = doctor.python_check()
    assert c["name"] == "python" and c["ok"] is True


def test_llama_server_check_reports_absence(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    c = doctor.llama_server_check()
    assert c["ok"] is False and c["warn"] is True
    assert "PATH" in c["detail"]


def test_llama_server_check_reports_presence(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/opt/llama/llama-server")
    c = doctor.llama_server_check()
    assert c["ok"] is True and c["warn"] is False
    assert "/opt/llama/llama-server" in c["detail"]


def test_disk_check_warns_when_low(monkeypatch, tmp_path):
    import collections
    usage = collections.namedtuple("u", "total used free")
    monkeypatch.setattr(doctor.shutil, "disk_usage",
                        lambda p: usage(0, 0, 1 * 1024 ** 3))  # 1 GB free
    c = doctor.disk_check(tmp_path)
    assert c["ok"] is False and c["warn"] is True


def test_disk_check_ok_when_ample(monkeypatch, tmp_path):
    import collections
    usage = collections.namedtuple("u", "total used free")
    monkeypatch.setattr(doctor.shutil, "disk_usage",
                        lambda p: usage(0, 0, 500 * 1024 ** 3))
    c = doctor.disk_check(tmp_path)
    assert c["ok"] is True


def test_slots_check_counts_downloaded(monkeypatch, tmp_path):
    # pretend only 'coding' is downloaded and 'uncensored' port is live
    def fake_model_path(slot, overrides=None):
        return tmp_path / ("present.gguf" if slot == "coding" else "absent.gguf")

    (tmp_path / "present.gguf").write_text("x", encoding="utf-8")
    monkeypatch.setattr(doctor, "model_path", fake_model_path)
    monkeypatch.setattr(doctor, "_port_up", lambda port: port == 8774)
    c = doctor.slots_check()
    assert c["downloaded"] == ["coding"]
    assert c["live"] == ["uncensored"]
    assert "1/" in c["detail"]


def test_diagnose_structure_and_soft_ok(monkeypatch, tmp_path):
    # even with no binary / no models, hard checks (python) pass -> ok True
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    monkeypatch.setattr(doctor, "model_path", lambda slot, overrides=None: tmp_path / "none.gguf")
    monkeypatch.setattr(doctor, "_port_up", lambda port: False)
    rep = doctor.diagnose()
    assert set(rep) == {"ok", "version", "models_dir", "checks"}
    assert rep["ok"] is True  # soft failures do not fail the report
    names = {c["name"] for c in rep["checks"]}
    assert names == {"python", "llama-server", "disk", "slots"}


def test_format_report_renders_marks():
    report = {
        "version": "0.3.0", "models_dir": "/tmp/models", "ok": True,
        "checks": [
            {"name": "python", "ok": True, "warn": False, "detail": "3.12"},
            {"name": "llama-server", "ok": False, "warn": True, "detail": "missing"},
        ],
    }
    text = doctor.format_report(report)
    assert "[ok  ] python" in text
    assert "[warn] llama-server" in text
    assert "healthy" in text
