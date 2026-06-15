"""uncensored-fleet CLI — download, serve, and drive a local LLM fleet."""
from __future__ import annotations

import argparse
import sys

from fleet import __version__
from fleet import download, harness, serve
from fleet.models import resolve

BANNER = "  uncensored-fleet — local multi-model LLM fleet + harness (engram-integrated)"


def _valid_slot(slot: str) -> None:
    """Raise SystemExit with a clear message when *slot* is not in the registry."""
    known = list(resolve())
    if slot not in known:
        sys.exit(
            f"error: unknown slot '{slot}'. Known slots: {', '.join(known)}"
        )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fleet", description=BANNER)
    ap.add_argument("--version", action="version", version=f"uncensored-fleet {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("models", help="list fleet slots")
    p = sub.add_parser("pull", help="download a slot's model (or 'all')")
    p.add_argument("slot")
    p = sub.add_parser("up", help="start a slot (or 'all')")
    p.add_argument("slot")
    p = sub.add_parser("down", help="stop a slot (or all)")
    p.add_argument("slot", nargs="?")
    sub.add_parser("status", help="show fleet status")
    sub.add_parser("setup", help="install llama.cpp + pull all models")
    p = sub.add_parser("run", help="one-shot prompt to a slot")
    p.add_argument("slot")
    p.add_argument("prompt")
    p = sub.add_parser("agent", help="run the agent harness on a task")
    p.add_argument("task")
    p.add_argument("--slot", default="uncensored")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "models":
            for slot, s in resolve().items():
                print(f"  {slot:12} :{s['port']}  {s['vram_gb']}GB  {s['repo']}  — {s['role']}")
        elif args.cmd == "pull":
            slots = list(resolve()) if args.slot == "all" else [args.slot]
            for s in slots:
                if s != "all":
                    _valid_slot(s)
                download.pull(s)
        elif args.cmd == "up":
            slots = list(resolve()) if args.slot == "all" else [args.slot]
            for s in slots:
                if s != "all":
                    _valid_slot(s)
                serve.up(s)
        elif args.cmd == "down":
            if args.slot is not None and args.slot not in list(resolve()):
                # allow None (stop all) but validate named slots
                _valid_slot(args.slot)
            serve.down(args.slot)
        elif args.cmd == "status":
            for slot, port, state, role in serve.status():
                print(f"  {slot:12} :{port}  {state:4}  {role}")
        elif args.cmd == "setup":
            print("Run scripts/setup-linux.sh (or setup-macos.sh / setup-windows.ps1) to build llama.cpp, then:")
            print("  fleet pull all && fleet up uncensored")
        elif args.cmd == "run":
            _valid_slot(args.slot)
            if not args.prompt or not args.prompt.strip():
                sys.exit("error: prompt must not be empty")
            print(harness.chat(args.slot, [{"role": "user", "content": args.prompt}]))
        elif args.cmd == "agent":
            _valid_slot(args.slot)
            if not args.task or not args.task.strip():
                sys.exit("error: task must not be empty")
            print(harness.agent(args.task, slot=args.slot))
        else:
            ap.print_help()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
