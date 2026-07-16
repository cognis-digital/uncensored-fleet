"""Download GGUF model files for fleet slots.

Order of preference: huggingface_hub -> `huggingface-cli` -> direct HTTPS via urllib.
"""
from __future__ import annotations
import os, shutil, subprocess, urllib.request
from pathlib import Path
from fleet.models import resolve

MODELS_DIR = Path(os.environ.get("FLEET_MODELS_DIR", Path.home() / ".cognis-fleet" / "models"))

def _hf_lib(repo, fname, dest):
    try:
        from huggingface_hub import hf_hub_download
    except Exception:
        return False
    p = hf_hub_download(repo_id=repo, filename=fname, local_dir=str(dest))
    return bool(p)

def _hf_cli(repo, fname, dest):
    if not shutil.which("huggingface-cli"):
        return False
    r = subprocess.run(["huggingface-cli", "download", repo, fname, "--local-dir", str(dest)])
    return r.returncode == 0

def _direct(repo, fname, dest):
    url = f"https://huggingface.co/{repo}/resolve/main/{fname}?download=true"
    out = dest / fname
    print(f"  direct download {url}")
    with urllib.request.urlopen(url) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f)
    return out.exists()

def pull(slot: str, overrides=None) -> Path:
    spec = resolve(overrides)[slot]
    dest = MODELS_DIR / slot
    dest.mkdir(parents=True, exist_ok=True)
    files = [spec["file"]] + ([spec["mmproj"]] if spec.get("mmproj") else [])
    for fname in files:
        if (dest / fname).exists():
            print(f"  [{slot}] {fname} already present"); continue
        print(f"  [{slot}] fetching {fname} from {spec['repo']}")
        ok = _hf_lib(spec["repo"], fname, dest) or _hf_cli(spec["repo"], fname, dest) or _direct(spec["repo"], fname, dest)
        if not ok:
            raise SystemExit(f"failed to download {fname}; install huggingface_hub or huggingface-cli")
    return dest / spec["file"]

def model_path(slot, overrides=None) -> Path:
    spec = resolve(overrides)[slot]
    return MODELS_DIR / slot / spec["file"]
