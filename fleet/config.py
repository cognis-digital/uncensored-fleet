"""Load fleet configuration overrides from ``fleet.yaml``.

The README documents overriding any slot in ``fleet.yaml``; this module makes
that real. It is **dependency-free**: if PyYAML is installed it is used, otherwise
a small built-in parser handles the documented subset (a top-level ``slots:``
mapping of ``slot -> {key: value}`` with scalar values, plus simple top-level
scalars). Values are coerced to ``int``/``float``/``bool``/``None`` where they
look numeric or boolean so overrides like ``port: 8801`` behave correctly.

Nothing here changes existing behavior when no config file is present: the loader
returns an empty dict, so ``resolve(load_overrides())`` is identical to
``resolve()`` on a fresh checkout.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    """Return the path to the active fleet config file.

    Honors ``$FLEET_CONFIG``; otherwise ``fleet.yaml`` in the current directory.
    """
    return Path(os.environ.get("FLEET_CONFIG", "fleet.yaml"))


def _coerce(value: str) -> Any:
    """Coerce a scalar string to int/float/bool/None where it clearly is one."""
    v = value.strip()
    if (len(v) >= 2) and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]  # quoted string — keep verbatim
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _minimal_yaml(text: str) -> dict:
    """Parse the documented subset of YAML without a dependency.

    Supports two indentation levels under a top-level ``slots:`` mapping plus
    plain top-level ``key: value`` scalars. Comments (``#``) and blank lines are
    ignored. This is intentionally small; install PyYAML for full YAML.
    """
    root: dict[str, Any] = {}
    cur_section: dict[str, Any] | None = None
    cur_slot: dict[str, Any] | None = None
    section_indent: int | None = None  # indent of keys directly under a section
    for raw in text.splitlines():
        # strip trailing comments (the documented subset never quotes ``#``) and
        # skip blank / comment-only lines
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, val = line.strip().partition(":")
        if not sep:
            continue
        key = key.strip()
        val = val.strip()
        if indent == 0:
            if val == "":
                cur_section = {}
                root[key] = cur_section
                cur_slot = None
                section_indent = None
            else:
                root[key] = _coerce(val)
                cur_section = None
                cur_slot = None
                section_indent = None
        elif cur_section is not None:
            if section_indent is None:
                section_indent = indent  # first indented line fixes the level
            if indent <= section_indent:
                # a key directly under the section (a slot, or a section scalar)
                if val == "":
                    cur_slot = {}
                    cur_section[key] = cur_slot
                else:
                    cur_section[key] = _coerce(val)
                    cur_slot = None
            elif cur_slot is not None:
                # deeper than the section level -> a property of the current slot
                cur_slot[key] = _coerce(val)
    return root


def parse_config(text: str) -> dict:
    """Parse config text into a dict, preferring PyYAML when available."""
    try:
        import yaml  # type: ignore
    except Exception:
        return _minimal_yaml(text)
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def load_overrides(path: str | os.PathLike | None = None) -> dict:
    """Return the slot-override mapping from the config file (``{}`` if absent).

    The returned dict is suitable to pass straight to
    :func:`fleet.models.resolve`. Missing file, empty file, or a file without a
    ``slots:`` section all yield ``{}`` so callers never need to special-case.
    """
    p = Path(path) if path is not None else config_path()
    if not p.exists():
        return {}
    try:
        data = parse_config(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    slots = data.get("slots")
    if isinstance(slots, dict):
        return {k: v for k, v in slots.items() if isinstance(v, dict)}
    return {}
