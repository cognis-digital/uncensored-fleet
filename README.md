<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:6b46c1,100:111111&height=170&section=header&text=uncensored-fleet&fontSize=46&fontColor=ffffff&fontAlignY=42" width="100%" alt="uncensored-fleet"/>

# uncensored-fleet

### Deploy a local multi-model LLM fleet in one command — llama.cpp slots, an agent harness, and [engram](https://github.com/cognis-digital/engram) memory.

[![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) ![Local](https://img.shields.io/badge/runs-100%25%20local-111111) ![llama.cpp](https://img.shields.io/badge/engine-llama.cpp-6b46c1) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital/cognis-neural-suite)

*Your hardware. Your models. No API keys, no rate limits, nothing leaves the box.*

</div>

```bash
pip install cognis-uncensored-fleet
bash scripts/build-llamacpp.sh     # build the engine (CUDA/Metal/Vulkan auto)
fleet pull all                     # download the model fleet
fleet up uncensored                # start the commander slot
fleet agent "summarize ./notes and propose next steps"
```


<!-- cognis:example:start -->
## 🔎 Example output

Real, reproducible output from the tool — runs offline:

```console
$ uncensored-fleet-emit --version
uncensored-fleet 0.3.0
```

```console
$ uncensored-fleet-emit --help
usage: fleet [-h] [--version] {models,pull,up,down,status,setup,run,agent} ...

uncensored-fleet — local multi-model LLM fleet + harness (engram-integrated)

positional arguments:
  {models,pull,up,down,status,setup,run,agent}
    models              list fleet slots
    pull                download a slot's model (or 'all')
    up                  start a slot (or 'all')
    down                stop a slot (or all)
    status              show fleet status
    setup               install llama.cpp + pull all models
    run                 one-shot prompt to a slot
    agent               run the agent harness on a task

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

```console
$ uncensored-fleet-emit status
reasoning    :8771  down  planning, analysis, chain-of-thought
  math         :8772  down  math, SymPy-verifiable problems
  coding       :8773  down  code generation + edits
  vision       :8775  down  image understanding / OCR
  uncensored   :8774  UP    lead/commander, unrestricted local reasoning
```

> Blocks above are real `uncensored-fleet` output — reproduce them from a clone.

<!-- cognis:example:end -->

## Usage — step by step

1. **Install** the `fleet` command, then build llama.cpp + pull models (`setup` prints the platform script to run first):
   ```bash
   pip install -e .
   fleet setup
   ```
2. **List the slots** to see each model, its port, VRAM and role:
   ```bash
   fleet models
   ```
3. **Pull and start** a slot (use `all` for the whole fleet), then check it's serving:
   ```bash
   fleet pull all
   fleet up uncensored
   fleet status
   ```
4. **Use the fleet** — send a one-shot prompt to a slot, or run the agent harness on a task (`--slot` defaults to `uncensored`):
   ```bash
   fleet run uncensored "summarize this repo"
   fleet agent "scaffold a fizzbuzz module with tests" --slot coding
   ```
5. **Tear down** when finished (omit the slot to stop all):
   ```bash
   fleet down
   ```

## Contents
- [Why](#why) · [The fleet](#the-fleet) · [Quick start](#quick-start) · [The harness](#the-harness) · [Engram memory](#engram-memory) · [Explore the suite](#explore-the-suite)

<a name="why"></a>
## Why

Cloud LLMs gate you on price, rate limits, and content policy. `uncensored-fleet` stands up a **fleet of
local models** — reasoning, math, coding, vision, and an **abliterated "commander"** — each served by
llama.cpp on your own GPU, and gives you a **model-agnostic agent harness** to drive them. It is the
deployment layer for a private, unrestricted, self-improving local AI stack.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="the-fleet"></a>
## The fleet

| Slot | Role | Default model | Port |
|---|---|---|---|
| `reasoning` | planning / analysis | DeepSeek-R1-Distill-Qwen-7B | 8771 |
| `math` | SymPy-verifiable problems | Qwen2.5-Math-7B | 8772 |
| `coding` | code gen + edits | Qwen2.5-Coder-7B | 8773 |
| `vision` | image / OCR | Qwen2-VL-7B | 8775 |
| `uncensored` | **commander**, unrestricted | Josiefied-Qwen3-8B-abliterated | 8774 |

VRAM-aware: conflicting slots auto-evict. Override any slot in `fleet.yaml`.

<a name="quick-start"></a>
## Quick start

```bash
fleet models                 # list slots
fleet pull all               # download GGUFs (huggingface_hub / hf-cli / direct)
fleet up all                 # start servers (or: fleet up coding)
fleet status                 # see what's live
fleet run coding "write a python LRU cache"
fleet agent "audit ./repo for secrets and write FINDINGS.md" --slot uncensored
fleet down                   # stop everything
```

<a name="the-harness"></a>
## The harness

A tiny, dependency-free agent loop (`fleet/harness.py`) talks to any slot over the llama.cpp
OpenAI-compatible endpoint and supports safe tools (`run_bash`, `read_file`, `write_file`) via a simple
`TOOL::` / `FINAL::` text protocol — model-agnostic, so it works with whatever you load.

<a name="engram-memory"></a>
## Engram memory

The harness remembers. It uses the Cognis **[engram](https://github.com/cognis-digital/engram)** fork for
portable, model-agnostic long-term memory when installed (`pip install "cognis-uncensored-fleet[engram]"`),
and falls back to a local SQLite store otherwise. Every task's outcome is recalled on the next related run.

<a name="explore-the-suite"></a>
## Explore the Cognis Neural Suite

`uncensored-fleet` is the local-AI backbone of the **[Cognis Neural Suite](https://github.com/cognis-digital/cognis-neural-suite)** (170+ tools). Pair it with:

- 🧠 **[engram](https://github.com/cognis-digital/engram)** — model-agnostic agent memory
- 🛠️ **[skills](https://github.com/cognis-digital/skills)** — agent skill registry the harness can load
- 🤖 **[agentsmith](https://github.com/cognis-digital/agentsmith)** · **[evalbench](https://github.com/cognis-digital/evalbench)** · **[modelroute](https://github.com/cognis-digital/modelroute)** — orchestrate, evaluate, route
- 📚 **[awesome-cognis](https://github.com/cognis-digital/awesome-cognis)** · **[cognis-sources](https://github.com/cognis-digital/cognis-sources)** — the full index

## Responsible use
Local, unrestricted models are powerful. Use them lawfully and ethically; you are responsible for what you generate and run.

## How it fits

```mermaid
flowchart LR
  U[You / CI / Agent] --> R[uncensored-fleet]
  R --> O[Outputs & artifacts]
  R --> M[MCP / JSON]
  M --> AI[AI agents]
  R --> S[Cognis Neural Suite]
```

**Explore the suite →** [🗂️ all tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources)

## Interoperability

`uncensored-fleet` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## Integrations

Forward `uncensored-fleet`'s findings to STIX/MISP/Sigma/Splunk/Elastic/Slack/webhooks via
[`cognis-connect`](https://github.com/cognis-digital/cognis-connect). See **[INTEGRATIONS.md](INTEGRATIONS.md)**.

## License
Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — see [LICENSE](LICENSE). Commercial use: licensing@cognis.digital.

---
<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · part of the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
