# Architecture

`uncensored-fleet` is a thin, dependency-free control plane over [llama.cpp](https://github.com/ggml-org/llama.cpp).
It downloads GGUF models, launches one `llama-server` process per **slot**, tracks them, and drives
them through an OpenAI-compatible `/v1` endpoint with a small agent loop. Everything is standard
library — the optional extras (`hf`, `engram`, `connect`) only add convenience.

## Component map

```
          fleet (CLI)                fleet/cli.py        argument parsing + dispatch
               │
   ┌───────────┼───────────────────────────────┐
   │           │                                │
config      models                          harness
(fleet/     (fleet/                         (fleet/
 config.py)  models.py)                      harness.py)
   │           │                                │
 fleet.yaml  SLOTS registry                 chat() ──HTTP──▶ llama-server /v1
 overrides   + resolve(overrides)           agent() loop (TOOL:: / FINAL::)
               │                                │
        ┌──────┴──────┐                     memory (fleet/memory.py)
     download        serve                  engram fork ─or─ sqlite fallback
   (fleet/          (fleet/
    download.py)     serve.py)
   GGUF fetch       Popen(llama-server)
   hf_hub → cli     state.json tracking
   → direct HTTPS   port health + conflicts

     doctor (fleet/doctor.py)   read-only environment diagnostics
     connect (fleet/connect.py) map findings → cognis-connect emitters
```

## Modules

| Module | Responsibility | Key entry points |
|---|---|---|
| `fleet/cli.py` | Parse args, load config, dispatch to modules. | `build_parser()`, `main()` |
| `fleet/config.py` | Load `fleet.yaml` overrides (PyYAML or built-in parser). | `load_overrides()`, `parse_config()` |
| `fleet/models.py` | Static slot registry + override merge. | `SLOTS`, `SLOT_CONFLICTS`, `resolve()` |
| `fleet/download.py` | Fetch GGUFs with a 3-tier fallback chain. | `pull()`, `model_path()` |
| `fleet/serve.py` | Start/stop `llama-server`, track PIDs, evict VRAM conflicts. | `up()`, `down()`, `status()` |
| `fleet/harness.py` | Talk to a slot; run the tool-using agent loop. | `chat()`, `agent()`, `_run_tool()` |
| `fleet/memory.py` | Long-term memory (engram fork or sqlite). | `get_memory()` |
| `fleet/doctor.py` | Read-only environment health check. | `diagnose()`, `format_report()` |
| `fleet/connect.py` | Map fleet JSON findings into `cognis-connect`. | `map_record()`, `emit_main()` |

## Data flow: `fleet up <slot>`

1. `cli.main()` loads `fleet.yaml` overrides via `config.load_overrides()`.
2. `serve.up(slot, overrides)` resolves the merged spec with `models.resolve(overrides)`.
3. It checks `LLAMA_SERVER` is on `PATH` and the model file exists (`download.model_path`).
4. Any VRAM-conflicting slot in `SLOT_CONFLICTS` is stopped first.
5. `llama-server` is launched with `-m <model> --port <port> -c <ctx> -ngl <ngl>`; the PID and
   port are written to `state.json`.
6. The launcher polls the port until it accepts connections (or times out to "still loading").

## Data flow: `fleet agent "<task>"`

1. `harness.agent()` calls `memory.recall(task)` and seeds a system prompt with the tool protocol
   and any recalled context.
2. Each step, `chat()` POSTs the running transcript to `http://127.0.0.1:<port>/v1/chat/completions`.
3. The reply is scanned for `FINAL:: <answer>` (done → remembered) or `TOOL:: <verb> <args>`
   (executed by `_run_tool`, result appended, loop continues).
4. After `max_steps` with no `FINAL::`, the loop returns `"(max steps reached)"`.

## Override resolution

`resolve(overrides)` deep-copies the static `SLOTS` and shallow-merges each slot override on top,
so callers never mutate the module registry and untouched fields survive. `config.load_overrides()`
produces the `overrides` dict from `fleet.yaml`; with no file present it returns `{}`, making the
configured path byte-for-byte equivalent to the default path.

## Design principles

- **Standard library first.** The core imports nothing outside the stdlib; extras are optional.
- **Local only.** All servers bind `127.0.0.1`; the sole outbound call is the model download.
- **Model-agnostic.** The harness uses a plain text `TOOL::`/`FINAL::` protocol, so any chat model works.
- **Additive & overridable.** Defaults live in code; `fleet.yaml` re-points anything without edits.
