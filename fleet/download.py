"""Download GGUF model files for fleet slots.

Order of preference: huggingface_hub -> `huggingface-cli` -> direct HTTPS via urllib.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from fleet.models import resolve

MODELS_DIR = Path(os.environ.get("FLEET_MODELS_DIR", Path.home() / ".cognis-fleet" / "models"))

# Timeout (seconds) for direct HTTPS model downloads.
_DOWNLOAD_TIMEOUT = int(os.environ.get("FLEET_DOWNLOAD_TIMEOUT", "3600"))


def _hf_lib(repo: str, fname: str, dest: Path) -> bool:
    try:
        from huggingface_hub import hf_hub_download  # type: ignore[import]
    except Exception:  # noqa: BLE001
        return False
    try:
        p = hf_hub_download(repo_id=repo, filename=fname, local_dir=str(dest))
        return bool(p)
    except Exception:  # noqa: BLE001
        return False


def _hf_cli(repo: str, fname: str, dest: Path) -> bool:
    if not shutil.which("huggingface-cli"):
        return False
    r = subprocess.run(
        ["huggingface-cli", "download", repo, fname, "--local-dir", str(dest)]
    )
    return r.returncode == 0


def _direct(repo: str, fname: str, dest: Path) -> bool:
    url = f"https://huggingface.co/{repo}/resolve/main/{fname}?download=true"
    out = dest / fname
    print(f"  direct download {url}")
    try:
        with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    except urllib.error.URLError as exc:
        print(f"  download failed: {exc}")
        return False
    return out.exists()


def pull(slot: str, overrides=None) -> Path:
    slots = resolve(overrides)
    if slot not in slots:
        raise SystemExit(
            f"error: unknown slot '{slot}'. Known slots: {', '.join(slots)}"
        )
    spec = slots[slot]
    dest = MODELS_DIR / slot
    dest.mkdir(parents=True, exist_ok=True)
    files = [spec["file"]] + ([spec["mmproj"]] if spec.get("mmproj") else [])
    for fname in files:
        if (dest / fname).exists():
            print(f"  [{slot}] {fname} already present")
            continue
        print(f"  [{slot}] fetching {fname} from {spec['repo']}")
        ok = _hf_lib(spec["repo"], fname, dest) or _hf_cli(spec["repo"], fname, dest) or _direct(spec["repo"], fname, dest)
        if not ok:
            raise SystemExit(f"failed to download {fname}; install huggingface_hub or huggingface-cli")
    return dest / spec["file"]


def model_path(slot: str, overrides=None) -> Path:
    slots = resolve(overrides)
    if slot not in slots:
        raise SystemExit(
            f"error: unknown slot '{slot}'. Known slots: {', '.join(slots)}"
        )
    spec = slots[slot]
    return MODELS_DIR / slot / spec["file"]
