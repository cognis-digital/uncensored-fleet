"""``fleet doctor`` — diagnose the local environment before you deploy a fleet.

This is a read-only, side-effect-free health check. It inspects the things that
commonly block a first run — the Python version, whether the ``llama-server``
binary is on ``PATH``, where models live and which slots are already downloaded,
free disk space on the models volume, and which slot ports are currently live —
and returns a structured report. Nothing here starts or stops a process.

Use it programmatically::

    from fleet import doctor
    report = doctor.diagnose()
    print(report["ok"], [c["name"] for c in report["checks"] if not c["ok"]])

or from the CLI::

    fleet doctor          # human-readable table, exit 0 if healthy
    fleet doctor --json    # machine-readable report
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from fleet import __version__
from fleet.models import resolve
from fleet.download import MODELS_DIR, model_path
from fleet.serve import LLAMA_SERVER, _port_up

MIN_PYTHON = (3, 10)
#: recommended free space (GB) on the models volume for a full 5-slot fleet
RECOMMENDED_FREE_GB = 40


def _check(name: str, ok: bool, detail: str, *, warn: bool = False) -> dict[str, Any]:
    """Build one check record. ``warn`` marks a soft failure (advisory only)."""
    return {"name": name, "ok": ok, "warn": warn and not ok, "detail": detail}


def _free_gb(path: Path) -> float | None:
    """Return free space in GiB on the volume containing ``path`` (or ``None``)."""
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        return round(shutil.disk_usage(probe).free / (1024 ** 3), 1)
    except OSError:
        return None


def python_check() -> dict[str, Any]:
    """Verify the interpreter meets the minimum supported version."""
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    need = ".".join(map(str, MIN_PYTHON))
    return _check("python", ok, f"{v.major}.{v.minor}.{v.micro} (need >= {need})")


def llama_server_check() -> dict[str, Any]:
    """Check whether the llama.cpp server binary is discoverable on ``PATH``."""
    found = shutil.which(LLAMA_SERVER)
    return _check("llama-server", bool(found),
                  found or f"'{LLAMA_SERVER}' not on PATH — run scripts/build-llamacpp.sh",
                  warn=True)


def disk_check(models_dir: Path = MODELS_DIR) -> dict[str, Any]:
    """Check free space on the models volume against :data:`RECOMMENDED_FREE_GB`."""
    free = _free_gb(models_dir)
    if free is None:
        return _check("disk", False, "could not determine free space", warn=True)
    ok = free >= RECOMMENDED_FREE_GB
    return _check("disk", ok, f"{free} GB free at {models_dir} (recommend >= {RECOMMENDED_FREE_GB} GB)",
                  warn=True)


def slots_check(overrides: dict | None = None) -> dict[str, Any]:
    """Report which slots have their GGUF present and which ports are live."""
    spec = resolve(overrides)
    downloaded: list[str] = []
    live: list[str] = []
    for slot, s in spec.items():
        if model_path(slot, overrides).exists():
            downloaded.append(slot)
        if _port_up(s["port"]):
            live.append(slot)
    ok = bool(downloaded)
    detail = (f"{len(downloaded)}/{len(spec)} downloaded ({', '.join(downloaded) or 'none'}); "
              f"live: {', '.join(live) or 'none'}")
    check = _check("slots", ok, detail, warn=True)
    check["downloaded"] = downloaded
    check["live"] = live
    return check


def diagnose(overrides: dict | None = None) -> dict[str, Any]:
    """Run all checks and return a report ``{ok, version, models_dir, checks}``.

    ``ok`` is ``True`` when every *hard* check passes. Soft checks (``warn``)
    never fail the overall report — they are advisories (missing binary, low
    disk, no models yet) that are expected on a fresh machine.
    """
    checks = [
        python_check(),
        llama_server_check(),
        disk_check(MODELS_DIR),
        slots_check(overrides),
    ]
    hard_ok = all(c["ok"] for c in checks if not c["warn"])
    return {
        "ok": hard_ok,
        "version": __version__,
        "models_dir": str(MODELS_DIR),
        "checks": checks,
    }


def format_report(report: dict[str, Any]) -> str:
    """Render a diagnose() report as a compact human-readable table."""
    lines = [f"uncensored-fleet {report['version']} — environment check",
             f"models dir: {report['models_dir']}", ""]
    for c in report["checks"]:
        mark = "ok  " if c["ok"] else ("warn" if c["warn"] else "FAIL")
        lines.append(f"  [{mark}] {c['name']:14} {c['detail']}")
    lines.append("")
    lines.append("healthy" if report["ok"] else "issues found (see FAIL rows above)")
    return "\n".join(lines)
