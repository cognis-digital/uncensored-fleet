"""Memory bridge — uses the Cognis `engram` fork if installed, else a tiny sqlite fallback.

    pip install cognis-engram   # the fork: https://github.com/cognis-digital/engram
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


class _Fallback:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS mem(ts REAL, key TEXT, val TEXT)")

    def remember(self, key: str, val: str) -> None:
        if not key:
            return
        self.db.execute("INSERT INTO mem VALUES(?,?,?)", (time.time(), str(key), str(val)))
        self.db.commit()

    def recall(self, query: str, k: int = 5) -> list:
        if not query:
            return []
        if k < 1:
            k = 1
        cur = self.db.execute(
            "SELECT key,val FROM mem WHERE val LIKE ? OR key LIKE ? ORDER BY ts DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", k),
        )
        return [{"key": r[0], "value": r[1]} for r in cur.fetchall()]


def get_memory():
    try:
        import engram  # the Cognis fork  # type: ignore[import]
        return engram.Memory()
    except Exception:  # noqa: BLE001
        p = Path(os.environ.get("FLEET_MEMORY", Path.home() / ".cognis-fleet" / "memory.sqlite"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return _Fallback(str(p))
