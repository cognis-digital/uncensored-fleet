"""Tests for the fleet CLI dispatcher (fleet.cli)."""
from __future__ import annotations

import json

import pytest

import fleet.cli as cli
from fleet import __version__


def test_version_flag_exits_zero_with_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help(capsys):
    rc = cli.main([])
    assert rc == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_models_human_output(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    rc = cli.main(["models"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "uncensored" in out and ":8774" in out


def test_models_json_output(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    cli.main(["models", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["coding"]["port"] == 8773


def test_models_applies_overrides(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {"coding": {"port": 9100}})
    cli.main(["models", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["coding"]["port"] == 9100


def test_status_json_output(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    monkeypatch.setattr(cli.serve, "status",
                        lambda ov=None: [("coding", 8773, "down", "code gen+edits")])
    cli.main(["status", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data[0]["slot"] == "coding" and data[0]["state"] == "down"


def test_pull_all_threads_overrides(monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {"coding": {"port": 1}})
    seen = []
    monkeypatch.setattr(cli.download, "pull", lambda slot, ov: seen.append((slot, ov)))
    cli.main(["pull", "all"])
    assert len(seen) == len(cli.resolve({"coding": {"port": 1}}))
    assert all(ov == {"coding": {"port": 1}} for _, ov in seen)


def test_up_single_slot(monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    started = []
    monkeypatch.setattr(cli.serve, "up", lambda slot, ov: started.append(slot))
    cli.main(["up", "coding"])
    assert started == ["coding"]


def test_down_dispatches(monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    stopped = []
    monkeypatch.setattr(cli.serve, "down", lambda slot: stopped.append(slot))
    cli.main(["down", "coding"])
    assert stopped == ["coding"]


def test_run_calls_chat(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    monkeypatch.setattr(cli.harness, "chat", lambda slot, msgs, ov: "ANSWER")
    cli.main(["run", "coding", "hello"])
    assert "ANSWER" in capsys.readouterr().out


def test_agent_calls_harness(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    monkeypatch.setattr(cli.harness, "agent",
                        lambda task, slot, overrides: f"did:{task}:{slot}")
    cli.main(["agent", "scan repo", "--slot", "coding"])
    assert "did:scan repo:coding" in capsys.readouterr().out


def test_doctor_returns_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    monkeypatch.setattr(cli.doctor, "diagnose",
                        lambda ov: {"ok": True, "version": "0.3.0",
                                    "models_dir": "/m", "checks": []})
    rc = cli.main(["doctor"])
    assert rc == 0
    assert "environment check" in capsys.readouterr().out


def test_doctor_json_and_failure_exit(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    monkeypatch.setattr(cli.doctor, "diagnose",
                        lambda ov: {"ok": False, "version": "0.3.0",
                                    "models_dir": "/m", "checks": []})
    rc = cli.main(["doctor", "--json"])
    assert rc == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_setup_prints_instructions(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_overrides", lambda: {})
    cli.main(["setup"])
    assert "llama.cpp" in capsys.readouterr().out


def test_build_parser_exposes_subcommands():
    ap = cli.build_parser()
    # subparser choices should include the new commands
    actions = [a for a in ap._actions if getattr(a, "choices", None)]
    names = set()
    for a in actions:
        if a.choices:
            names |= set(a.choices)
    assert {"models", "doctor", "status", "agent"} <= names
