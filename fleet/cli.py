"""uncensored-fleet CLI — download, serve, and drive a local LLM fleet.

The CLI is a thin dispatcher over the package modules:

* :mod:`fleet.models`  — slot registry / override resolution
* :mod:`fleet.config`  — ``fleet.yaml`` override loading
* :mod:`fleet.download`— GGUF fetching
* :mod:`fleet.serve`   — llama.cpp process management
* :mod:`fleet.harness` — the agent loop
* :mod:`fleet.doctor`  — environment diagnostics

Every subcommand honors slot overrides from ``fleet.yaml`` (see
:func:`fleet.config.load_overrides`), so a local config file transparently
re-points ports, repos, or context sizes.
"""
from __future__ import annotations
import argparse, json, sys
from fleet import __version__
from fleet.models import resolve
from fleet.config import load_overrides
from fleet import download, serve, harness, doctor

BANNER = "  uncensored-fleet — local multi-model LLM fleet + harness (engram-integrated)"


def _print_models(overrides, as_json: bool) -> None:
    slots = resolve(overrides)
    if as_json:
        print(json.dumps(slots, indent=2))
        return
    for slot, s in slots.items():
        print(f"  {slot:12} :{s['port']}  {s['vram_gb']}GB  {s['repo']}  — {s['role']}")


def _print_status(overrides, as_json: bool) -> None:
    rows = serve.status(overrides)
    if as_json:
        print(json.dumps(
            [{"slot": s, "port": p, "state": st, "role": r} for s, p, st, r in rows],
            indent=2))
        return
    for slot, port, state, role in rows:
        print(f"  {slot:12} :{port}  {state:4}  {role}")


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser (exposed for tests and documentation)."""
    ap = argparse.ArgumentParser(prog="fleet", description=BANNER)
    ap.add_argument("--version", action="version", version=f"uncensored-fleet {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("models", help="list fleet slots"); p.add_argument("--json", action="store_true", help="emit JSON")
    p = sub.add_parser("pull", help="download a slot's model (or 'all')"); p.add_argument("slot")
    p = sub.add_parser("up", help="start a slot (or 'all')"); p.add_argument("slot")
    p = sub.add_parser("down", help="stop a slot (or all)"); p.add_argument("slot", nargs="?")
    p = sub.add_parser("status", help="show fleet status"); p.add_argument("--json", action="store_true", help="emit JSON")
    sub.add_parser("setup", help="install llama.cpp + pull all models")
    p = sub.add_parser("doctor", help="diagnose the local environment"); p.add_argument("--json", action="store_true", help="emit JSON")
    p = sub.add_parser("run", help="one-shot prompt to a slot"); p.add_argument("slot"); p.add_argument("prompt")
    p = sub.add_parser("agent", help="run the agent harness on a task"); p.add_argument("task"); p.add_argument("--slot", default="uncensored")
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    overrides = load_overrides()

    if args.cmd == "models":
        _print_models(overrides, getattr(args, "json", False))
    elif args.cmd == "pull":
        slots = list(resolve(overrides)) if args.slot == "all" else [args.slot]
        for s in slots: download.pull(s, overrides)
    elif args.cmd == "up":
        slots = list(resolve(overrides)) if args.slot == "all" else [args.slot]
        for s in slots: serve.up(s, overrides)
    elif args.cmd == "down":
        serve.down(args.slot)
    elif args.cmd == "status":
        _print_status(overrides, getattr(args, "json", False))
    elif args.cmd == "setup":
        print("Run scripts/setup-linux.sh (or setup-macos.sh / setup-windows.ps1) to build llama.cpp, then:")
        print("  fleet pull all && fleet up uncensored")
    elif args.cmd == "doctor":
        report = doctor.diagnose(overrides)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            print(doctor.format_report(report))
        return 0 if report["ok"] else 1
    elif args.cmd == "run":
        print(harness.chat(args.slot, [{"role": "user", "content": args.prompt}], overrides))
    elif args.cmd == "agent":
        print(harness.agent(args.task, slot=args.slot, overrides=overrides))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
