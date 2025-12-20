"""Launch/stop llama.cpp servers for fleet slots and track them."""
from __future__ import annotations
import json, os, shutil, signal, socket, subprocess, time
from pathlib import Path
from fleet.models import resolve, SLOT_CONFLICTS
from fleet.download import model_path

STATE = Path(os.environ.get("FLEET_STATE", Path.home() / ".cognis-fleet" / "state.json"))
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", "llama-server")

def _load():
    return json.loads(STATE.read_text()) if STATE.exists() else {"running": {}}
def _save(s):
    STATE.parent.mkdir(parents=True, exist_ok=True); STATE.write_text(json.dumps(s, indent=2))

def _port_up(port):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0

def up(slot, overrides=None):
    if not shutil.which(LLAMA_SERVER):
        raise SystemExit(f"{LLAMA_SERVER} not found. Run `fleet setup` or set $LLAMA_SERVER.")
    spec = resolve(overrides)[slot]
    st = _load()
    # evict conflicts
    for c in SLOT_CONFLICTS.get(slot, []):
        if c in st["running"]:
            down(c)
            st = _load()
    mp = model_path(slot, overrides)
    if not mp.exists():
        raise SystemExit(f"model for '{slot}' not downloaded. Run `fleet pull {slot}`.")
    cmd = [LLAMA_SERVER, "-m", str(mp), "--port", str(spec["port"]),
           "-c", str(spec["ctx"]), "-ngl", str(spec["ngl"]), "--host", "127.0.0.1"]
    if spec.get("mmproj"):
        cmd += ["--mmproj", str(mp.parent / spec["mmproj"])]
    log = STATE.parent / f"{slot}.log"; STATE.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(cmd, stdout=open(log, "w"), stderr=subprocess.STDOUT)
    st["running"][slot] = {"pid": p.pid, "port": spec["port"]}
    _save(st)
    print(f"  [{slot}] starting on :{spec['port']} (pid {p.pid}) — log {log}")
    for _ in range(60):
        if _port_up(spec["port"]):
            print(f"  [{slot}] ready"); return
        time.sleep(1)
    print(f"  [{slot}] still loading (check {log})")

def down(slot=None):
    st = _load()
    targets = [slot] if slot else list(st["running"].keys())
    for s in targets:
        info = st["running"].get(s)
        if not info: continue
        try: os.kill(info["pid"], signal.SIGTERM)
        except Exception: pass
        st["running"].pop(s, None)
        print(f"  [{s}] stopped")
    _save(st)

def status(overrides=None):
    spec = resolve(overrides); st = _load()
    rows = []
    for slot, s in spec.items():
        rows.append((slot, s["port"], "UP" if _port_up(s["port"]) else "down", s["role"]))
    return rows
