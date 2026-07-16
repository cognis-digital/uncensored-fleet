"""Tests for the slot registry and override resolution (fleet.models)."""
from __future__ import annotations

from fleet.models import resolve, SLOTS, SLOT_CONFLICTS


def test_all_expected_slots_present():
    assert set(SLOTS) == {"reasoning", "math", "coding", "vision", "uncensored"}


def test_every_slot_has_required_fields():
    for slot, spec in SLOTS.items():
        for field in ("repo", "file", "port", "ctx", "ngl", "vram_gb", "role"):
            assert field in spec, f"{slot} missing {field}"
        assert isinstance(spec["port"], int)
        assert isinstance(spec["ctx"], int) and spec["ctx"] > 0
        assert spec["repo"] and spec["file"] and spec["role"]


def test_ports_are_unique():
    ports = [s["port"] for s in SLOTS.values()]
    assert len(ports) == len(set(ports))


def test_only_vision_has_mmproj():
    assert "mmproj" in SLOTS["vision"]
    for slot, spec in SLOTS.items():
        if slot != "vision":
            assert "mmproj" not in spec


def test_resolve_returns_deep_copy():
    a = resolve()
    a["coding"]["port"] = 1
    # mutation must not leak into the module-level registry
    assert SLOTS["coding"]["port"] != 1
    assert resolve()["coding"]["port"] != 1


def test_resolve_merges_override_onto_existing_slot():
    out = resolve({"coding": {"port": 9999}})
    assert out["coding"]["port"] == 9999
    # untouched keys survive the merge
    assert out["coding"]["repo"] == SLOTS["coding"]["repo"]


def test_resolve_adds_new_slot():
    out = resolve({"custom": {"port": 8801, "repo": "x/y", "file": "z.gguf",
                              "role": "r", "ctx": 4096, "ngl": 99, "vram_gb": 4}})
    assert "custom" in out and out["custom"]["port"] == 8801
    # original slots still there
    assert "uncensored" in out


def test_resolve_none_equivalent_to_empty():
    assert resolve() == resolve({})


def test_conflicts_are_symmetric():
    for a, others in SLOT_CONFLICTS.items():
        for b in others:
            assert a in SLOT_CONFLICTS.get(b, []), f"{a}<->{b} not symmetric"


def test_conflict_slots_exist_in_registry():
    for a, others in SLOT_CONFLICTS.items():
        assert a in SLOTS
        for b in others:
            assert b in SLOTS
