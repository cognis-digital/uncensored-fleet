"""Memory bridge — uses the Cognis `engram` fork if installed, else a tiny sqlite fallback.

    pip install cognis-engram   # the fork: https://github.com/cognis-digital/engram
"""
from __future__ import annotations
import os, sqlite3, time
from pathlib import Path

class _Fallback:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS mem(ts REAL, key TEXT, val TEXT)")
    def remember(self, key, val):
        self.db.execute("INSERT INTO mem VALUES(?,?,?)", (time.time(), key, val)); self.db.commit()
    def recall(self, query, k=5):
        cur = self.db.execute("SELECT key,val FROM mem WHERE val LIKE ? OR key LIKE ? ORDER BY ts DESC LIMIT ?",
                              (f"%{query}%", f"%{query}%", k))
        return [{"key": r[0], "value": r[1]} for r in cur.fetchall()]

def get_memory():
    try:
        import engram  # the Cognis fork
        return engram.Memory()  # type: ignore
    except Exception:
        p = Path(os.environ.get("FLEET_MEMORY", Path.home() / ".cognis-fleet" / "memory.sqlite"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return _Fallback(str(p))
