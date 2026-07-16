"""Tests for fleet.connect.map_record — the record mapper needs no optional deps."""
from __future__ import annotations

from fleet.connect import map_record, SOURCE


def test_source_constant():
    assert SOURCE == "uncensored-fleet"


def test_map_record_defaults_fill_missing_fields():
    out = map_record({})
    assert out["title"] == "" and out["severity"] == "info"
    assert out["type"] == "unknown" and out["tags"] == []
    # optional indicator fields present but empty
    for key in ("ipv4", "domain", "url", "sha256", "cve", "imo", "mmsi", "lat", "lon"):
        assert key in out and out[key] is None


def test_map_record_preserves_provided_values():
    rec = {"title": "beacon", "severity": "high", "type": "c2",
           "description": "d", "tags": ["a"], "domain": "evil.example",
           "cve": "CVE-2026-1234"}
    out = map_record(rec)
    assert out["title"] == "beacon" and out["severity"] == "high"
    assert out["type"] == "c2" and out["tags"] == ["a"]
    assert out["domain"] == "evil.example" and out["cve"] == "CVE-2026-1234"


def test_map_record_strips_internal_fields():
    rec = {"title": "x", "timestamp": 1, "model": "m", "slot": "s",
           "source": "old", "confidence": 0.9}
    out = map_record(rec)
    for stripped in ("timestamp", "model", "slot", "confidence"):
        assert stripped not in out
    # 'source' is re-owned by the emitter, not carried from the record
    assert out.get("source") != "old"


def test_map_record_non_dict_returns_input():
    # defensive: non-dict falls through the try/except unchanged
    sentinel = ["not", "a", "dict"]
    assert map_record(sentinel) is sentinel
