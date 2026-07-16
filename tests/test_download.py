"""Tests for fleet.download — path resolution and the download fallback chain."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import fleet.download as download
from fleet.models import SLOTS


def _reload_with_models_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("FLEET_MODELS_DIR", str(tmp_path))
    return importlib.reload(download)


def test_model_path_uses_env_dir(monkeypatch, tmp_path):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    p = dl.model_path("coding")
    assert p == tmp_path / "coding" / SLOTS["coding"]["file"]
    importlib.reload(download)  # restore default for other tests


def test_pull_skips_existing_file(monkeypatch, tmp_path, capsys):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    spec = dl.resolve()["coding"]
    dest = tmp_path / "coding"
    dest.mkdir(parents=True)
    (dest / spec["file"]).write_text("stub", encoding="utf-8")

    called = {"n": 0}
    monkeypatch.setattr(dl, "_hf_lib", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or True)
    result = dl.pull("coding")
    assert result == dest / spec["file"]
    assert called["n"] == 0  # never attempted a download
    assert "already present" in capsys.readouterr().out
    importlib.reload(download)


def test_pull_uses_first_successful_backend(monkeypatch, tmp_path):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    spec = dl.resolve()["coding"]
    order = []

    def make(name, ok):
        def fn(repo, fname, dest):
            order.append(name)
            if ok:
                (Path(dest) / fname).write_text("x", encoding="utf-8")
            return ok
        return fn

    monkeypatch.setattr(dl, "_hf_lib", make("lib", False))
    monkeypatch.setattr(dl, "_hf_cli", make("cli", True))
    monkeypatch.setattr(dl, "_direct", make("direct", True))
    out = dl.pull("coding")
    assert out.name == spec["file"]
    # tried lib, then cli succeeded, never fell through to direct
    assert order == ["lib", "cli"]
    importlib.reload(download)


def test_pull_raises_when_all_backends_fail(monkeypatch, tmp_path):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    monkeypatch.setattr(dl, "_hf_lib", lambda *a, **k: False)
    monkeypatch.setattr(dl, "_hf_cli", lambda *a, **k: False)
    monkeypatch.setattr(dl, "_direct", lambda *a, **k: False)
    with pytest.raises(SystemExit):
        dl.pull("coding")
    importlib.reload(download)


def test_pull_fetches_mmproj_for_vision(monkeypatch, tmp_path):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    fetched = []

    def fake_lib(repo, fname, dest):
        fetched.append(fname)
        (Path(dest) / fname).write_text("x", encoding="utf-8")
        return True

    monkeypatch.setattr(dl, "_hf_lib", fake_lib)
    dl.pull("vision")
    assert SLOTS["vision"]["file"] in fetched
    assert SLOTS["vision"]["mmproj"] in fetched
    importlib.reload(download)


def test_direct_url_shape(monkeypatch, tmp_path):
    dl = _reload_with_models_dir(monkeypatch, tmp_path)
    captured = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, *a): return b""

    def fake_urlopen(url, *a, **k):
        captured["url"] = url
        return FakeResp()

    monkeypatch.setattr(dl.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(dl.shutil, "copyfileobj", lambda *a, **k: None)
    dest = tmp_path / "coding"
    dest.mkdir(parents=True)
    dl._direct("org/repo", "m.gguf", dest)
    assert captured["url"] == "https://huggingface.co/org/repo/resolve/main/m.gguf?download=true"
    importlib.reload(download)
