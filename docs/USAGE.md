# Usage

A task-oriented tour of the `fleet` CLI and the Python API. Every command honors
`fleet.yaml` overrides (see [Configuration](#configuration)).

## Install

```bash
pip install -e ".[dev]"          # from a clone, with the test extras
# or, without cloning:
pip install "git+https://github.com/cognis-digital/uncensored-fleet.git"
```

## First run

```bash
fleet doctor          # check python / llama-server / disk / slots before pulling models
fleet models          # list the slots, ports, VRAM, and default repos
```

`fleet doctor` is read-only and safe to run anytime.

## Downloading models

```bash
fleet pull coding      # one slot
fleet pull all         # every slot in the registry
```

GGUFs land under `$FLEET_MODELS_DIR` (default `~/.cognis-fleet/models/<slot>/`). The downloader
tries `huggingface_hub`, then the `huggingface-cli`, then a direct HTTPS GET — the first that works
wins. Install the `hf` extra for the fastest path:

```bash
pip install "cognis-uncensored-fleet[hf]"
```

## Serving

```bash
fleet up coding        # start one slot's llama-server
fleet up all           # start the whole fleet (VRAM conflicts auto-evict)
fleet status           # human-readable table of every slot's port + state
fleet status --json    # same, as JSON
fleet down coding      # stop one slot
fleet down             # stop everything
```

Starting a slot that VRAM-conflicts with a running one (e.g. `uncensored` vs `reasoning`) stops the
other automatically. Override the ports in `fleet.yaml` to co-locate them.

## Prompting a slot

```bash
fleet run coding "write a python LRU cache with unit tests"
```

`run` sends a single chat turn and prints the completion.

## The agent harness

```bash
fleet agent "audit ./repo for hardcoded secrets and write FINDINGS.md" --slot uncensored
```

The harness loops: the model may emit tool calls and a final answer using a plain-text protocol.

```
TOOL::run_bash <cmd>
TOOL::read_file <path>
TOOL::write_file <path>|||<content>
FINAL:: <answer>
```

Each `TOOL::` line runs a safe built-in tool and feeds the result back; `FINAL::` ends the run and
the outcome is stored in memory for next time. If the model never emits `FINAL::` within `max_steps`
(default 8), the harness returns `"(max steps reached)"`.

## Configuration

Drop a `fleet.yaml` in the working directory (or set `$FLEET_CONFIG`):

```yaml
slots:
  uncensored:
    repo: your-org/your-abliterated-gguf
    file: model-Q5_K_M.gguf
    port: 8774
    ctx: 32768
  coding:
    port: 8801
```

Overrides merge over the defaults, so you list only what changes. PyYAML is used if installed;
otherwise a built-in parser handles this documented subset with no extra dependency.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `FLEET_CONFIG` | `fleet.yaml` | override-file path |
| `FLEET_MODELS_DIR` | `~/.cognis-fleet/models` | GGUF storage |
| `FLEET_STATE` | `~/.cognis-fleet/state.json` | running-process state |
| `FLEET_MEMORY` | `~/.cognis-fleet/memory.sqlite` | fallback memory store |
| `LLAMA_SERVER` | `llama-server` | llama.cpp binary / path |

## Python API

Every CLI action is a plain function call:

```python
from fleet.models import resolve
from fleet.config import load_overrides
from fleet import download, serve, harness, doctor

overrides = load_overrides()                 # {} if no fleet.yaml
slots = resolve(overrides)                    # merged registry

report = doctor.diagnose(overrides)           # {'ok': ..., 'checks': [...]}
download.pull("coding", overrides)            # fetch a GGUF
serve.up("coding", overrides)                 # launch llama-server
answer = harness.agent("summarize ./notes", slot="uncensored", overrides=overrides)
serve.down("coding")
```

## Forwarding findings

If the fleet emits JSON findings, pipe them to any SIEM/threat-intel platform via the optional
`cognis-connect` integration:

```bash
pip install "cognis-uncensored-fleet[connect]"
cat findings.json | uncensored-fleet-emit --to stix
cat findings.json | uncensored-fleet-emit --to slack --url "$WEBHOOK" --dry-run
```
