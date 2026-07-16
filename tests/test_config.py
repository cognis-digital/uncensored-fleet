"""Tests for fleet.config — fleet.yaml override loading and the minimal parser."""
from __future__ import annotations

from fleet import config
from fleet.config import _coerce, _minimal_yaml, load_overrides
from fleet.models import resolve


def test_coerce_types():
    assert _coerce("8801") == 8801 and isinstance(_coerce("8801"), int)
    assert _coerce("1.5") == 1.5
    assert _coerce("true") is True and _coerce("Off") is False
    assert _coerce("null") is None and _coerce("~") is None
    assert _coerce("hello") == "hello"
    assert _coerce('"8801"') == "8801"  # quoted stays a string


def test_minimal_yaml_nested_slots():
    text = """
# comment line
slots:
  uncensored:
    repo: myorg/my-gguf
    file: model-Q5.gguf
    port: 8900
  coding:
    port: 8901
top_level: 7
"""
    data = _minimal_yaml(text)
    assert data["top_level"] == 7
    assert data["slots"]["uncensored"]["repo"] == "myorg/my-gguf"
    assert data["slots"]["uncensored"]["port"] == 8900
    assert data["slots"]["coding"]["port"] == 8901


def test_minimal_yaml_ignores_comments_and_blanks():
    assert _minimal_yaml("# only a comment\n\n   \n") == {}


def test_load_overrides_missing_file(tmp_path):
    assert load_overrides(tmp_path / "nope.yaml") == {}


def test_load_overrides_empty_commented_file(tmp_path):
    # mirrors the shipped fleet.yaml (all comments) -> no overrides
    p = tmp_path / "fleet.yaml"
    p.write_text("# just comments\n# slots:\n", encoding="utf-8")
    assert load_overrides(p) == {}


def test_load_overrides_returns_slot_mapping(tmp_path):
    p = tmp_path / "fleet.yaml"
    p.write_text("slots:\n  coding:\n    port: 8888\n", encoding="utf-8")
    ov = load_overrides(p)
    assert ov == {"coding": {"port": 8888}}


def test_load_overrides_wires_into_resolve(tmp_path):
    p = tmp_path / "fleet.yaml"
    p.write_text("slots:\n  uncensored:\n    port: 8899\n    ctx: 4096\n", encoding="utf-8")
    merged = resolve(load_overrides(p))
    assert merged["uncensored"]["port"] == 8899
    assert merged["uncensored"]["ctx"] == 4096
    # non-overridden fields preserved
    assert merged["uncensored"]["repo"] == resolve()["uncensored"]["repo"]


def test_load_overrides_skips_non_dict_slot_values(tmp_path):
    p = tmp_path / "fleet.yaml"
    p.write_text("slots:\n  bogus: 5\n  coding:\n    port: 1\n", encoding="utf-8")
    ov = load_overrides(p)
    assert "bogus" not in ov and ov["coding"]["port"] == 1


def test_config_path_env_override(monkeypatch, tmp_path):
    target = tmp_path / "custom.yaml"
    monkeypatch.setenv("FLEET_CONFIG", str(target))
    assert config.config_path() == target


def test_load_overrides_honors_env(monkeypatch, tmp_path):
    p = tmp_path / "env.yaml"
    p.write_text("slots:\n  math:\n    port: 7000\n", encoding="utf-8")
    monkeypatch.setenv("FLEET_CONFIG", str(p))
    assert load_overrides() == {"math": {"port": 7000}}
