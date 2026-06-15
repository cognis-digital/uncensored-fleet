"""Launch/stop llama.cpp servers for fleet slots and track them."""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path

from fleet.download import model_path
from fleet.models import resolve, SLOT_CONFLICTS

STATE = Path(os.environ.get("FLEET_STATE", Path.home() / ".cognis-fleet" / "state.json"))
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", "llama-server")


def _load() -> dict:
    if not STATE.exists():
        return {"running": {}}
    try:
        data = json.loads(STATE.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable state file — start fresh rather than crash.
        return {"running": {}}
    if not isinstance(data, dict) or "running" not in data:
        return {"running": {}}
    return data


def _save(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def _port_up(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def up(slot: str, overrides=None) -> None:
    if not shutil.which(LLAMA_SERVER):
        raise SystemExit(f"{LLAMA_SERVER} not found. Run `fleet setup` or set $LLAMA_SERVER.")
    slots = resolve(overrides)
    if slot not in slots:
        raise SystemExit(f"error: unknown slot '{slot}'. Known slots: {', '.join(slots)}")
    spec = slots[slot]
    st = _load()
    # evict conflicts
    for c in SLOT_CONFLICTS.get(slot, []):
        if c in st["running"]:
            down(c)
            st = _load()
    mp = model_path(slot, overrides)
    if not mp.exists():
        raise SystemExit(f"model for '{slot}' not downloaded. Run `fleet pull {slot}`.")
    cmd = [
        LLAMA_SERVER, "-m", str(mp),
        "--port", str(spec["port"]),
        "-c", str(spec["ctx"]),
        "-ngl", str(spec["ngl"]),
        "--host", "127.0.0.1",
    ]
    if spec.get("mmproj"):
        cmd += ["--mmproj", str(mp.parent / spec["mmproj"])]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    log = STATE.parent / f"{slot}.log"
    log_fh = open(log, "w")  # noqa: WPS515 — kept open intentionally for Popen lifetime
    p = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
    st["running"][slot] = {"pid": p.pid, "port": spec["port"]}
    _save(st)
    print(f"  [{slot}] starting on :{spec['port']} (pid {p.pid}) — log {log}")
    for _ in range(60):
        if _port_up(spec["port"]):
            print(f"  [{slot}] ready")
            return
        time.sleep(1)
    print(f"  [{slot}] still loading (check {log})")


def down(slot=None) -> None:
    st = _load()
    targets = [slot] if slot else list(st["running"].keys())
    for s in targets:
        info = st["running"].get(s)
        if not info:
            continue
        try:
            os.kill(info["pid"], signal.SIGTERM)
        except Exception:  # noqa: BLE001
            pass
        st["running"].pop(s, None)
        print(f"  [{s}] stopped")
    _save(st)


def status(overrides=None) -> list:
    spec = resolve(overrides)
    rows = []
    for slot, s in spec.items():
        rows.append((slot, s["port"], "UP" if _port_up(s["port"]) else "down", s["role"]))
    return rows
