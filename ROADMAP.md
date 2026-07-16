# Roadmap

Direction for `uncensored-fleet`. This is a living document — priorities shift with real usage.
Nothing here removes an existing command or breaks the standard-library-only core; every item is
additive and, where it touches behavior, opt-in.

## Guiding principles

- **Local-first, private by default** — servers stay on `127.0.0.1`; the only outbound call is the
  one-time model download.
- **Standard-library core** — heavy dependencies remain optional extras.
- **Model-agnostic** — the harness protocol works with whatever GGUF you load.
- **Additive & overridable** — new behavior arrives behind flags or `fleet.yaml`, never as a
  breaking default.

## Near-term (next few releases)

- **`fleet up --wait/--timeout`** — configurable readiness polling instead of the fixed 60s.
- **`fleet logs <slot>`** — tail the per-slot llama.cpp log without hunting in the state dir.
- **`fleet run --json` / streaming** — structured completions and token streaming from `run`.
- **Health endpoint probe** — `status`/`doctor` hit `/health` (not just the TCP port) to
  distinguish "port open" from "model loaded".
- **Config validation** — `fleet doctor` flags unknown slot keys and port collisions in `fleet.yaml`.
- **Coverage in CI** — publish a coverage report and enforce a floor.

## Mid-term

- **Router slot** — a `fleet route "<task>"` that picks a slot by role (reasoning/math/coding/vision)
  using lightweight heuristics, then dispatches through the harness.
- **Parallel fleet ops** — concurrent `pull all` / `up all` with progress, respecting VRAM conflicts.
- **Pluggable tools** — register additional harness tools (HTTP fetch, structured file edits) behind
  an allow-list, keeping the safe defaults.
- **Quantization awareness** — surface each GGUF's quant/VRAM estimate in `models` and let `doctor`
  warn when a slot won't fit available VRAM.
- **Metrics** — optional Prometheus-style counters (tokens, latency, tool calls) for the harness.

## Long-term

- **Multi-GPU / multi-host placement** — schedule slots across devices or machines with a shared
  registry, still local to your network.
- **Memory backends** — first-class adapters beyond the sqlite fallback and the engram fork
  (vector stores, on-disk KV) selected via config.
- **Evaluation loop** — integrate with the suite's evaluation tooling to score slot/model choices on
  repeatable task sets and feed the router.
- **Declarative fleets** — describe a whole fleet (slots, models, tools, memory) in one file and
  bring it `up` reproducibly.

## Non-goals

- Cloud-hosted inference or telemetry.
- Bundling model weights in the package.
- Turning the core into a heavyweight framework — orchestration lives in sibling suite tools.

## Contributing

Ideas and RFCs are welcome via GitHub Issues/Discussions. See
[CONTRIBUTING.md](CONTRIBUTING.md). Additive PRs with tests are the fastest path in.
