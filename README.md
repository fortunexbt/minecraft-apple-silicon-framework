<p align="center"><img src="docs/banner.svg" alt="Silicon Shader — keep the atmosphere, lose the guesswork" width="900"></p>

<p align="center"><strong>A small, open-source workbench for better Minecraft shaders on Apple Silicon.</strong><br>Discover → isolate → measure → keep the winner → play.</p>

Silicon Shader gives you a Python CLI, a short agent prompt, and an optional Java frame sampler. It helps you find a good visual/performance tradeoff in a handful of useful experiments, then leave the benchmark behind.

Settings and worlds stay in separate Prism instances. Every configuration change has a rollback receipt. Install third-party components from their publishers; the repository distributes original tools, patch recipes and compact evidence.

### Start here

Requires **Python 3.10+**, [Prism Launcher](https://prismlauncher.org/download/), and your own Minecraft installation. No Python runtime dependencies.

```sh
git clone https://github.com/fortunexbt/minecraft-apple-silicon-framework.git
cd minecraft-apple-silicon-framework
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
silicon-shader discover
```

Then give your coding agent **[this entry prompt](agents/START.md)**, or follow the **[manual guide](docs/WORKFLOW.md)**. The CLI works without an agent or an API key.

To make a lab copy, close the source instance first:

```sh
silicon-shader isolate \
  "$HOME/Library/Application Support/PrismLauncher/instances/My Minecraft" \
  "$HOME/Library/Application Support/PrismLauncher/instances/Shader Lab" \
  --closed --save "My World"
```

Use the exact **save folder**, not its display name. Omit `--save` to create a fresh disposable world yourself. Existing instances are never overwritten; accounts, logs and launcher hooks are not copied.

### What you get

| Tool | Purpose |
| --- | --- |
| `discover` / `setup` / `runtime` | Inspect hardware, Prism, game version and Java needs; create new instance metadata |
| `isolate` | Copy only selected game/configuration content into a new lab |
| `profile` | Apply reversible settings; preserve the complete shader property set |
| `capture` | Request 20–30 seconds, inspect explicit status, reject partial or invalid output |
| `loop` | Validate a baseline, propose material changes, retain measured winners, stop |
| `daily` | Create a separate copy without Java agents, launch hooks or Minescript |

The search has **at most four trials by default** (hard limit six), stops after two failed improvements, and stops immediately when the baseline meets your chosen tradeoff. It keeps view distance at least 12 in its generated proposals and avoids scaling below 65%. These are tuning guardrails, not hardware performance claims. Crispness and atmosphere still need your eyes.

### Evidence, without the hype

The reference campaign used a **base M4, 10 CPU/GPU cores, 24 GB**. Quality 75% used native 3024×1898 output, nearest scaling, R12/S8, MakeUp 9.5f and Faithful 32×. Short accepted scene captures averaged **84–119 CPU-produced frames/s**, including the limiter. The largest interval in that narrow set was **30.16 ms**. That is not GPU presentation, input latency, an all-day guarantee, or performance verified on another Mac.

Wide View 20 traded internal resolution for R20/S6. Brief ordinary movement showed approximately **91–105 F3 FPS**; a separate percentile readout was **69 FPS**. It was not locked at 120. The [experiment digest](docs/EXPERIMENTS.md) and [indexed ledger](evidence/) include losses, invalid runs, and unmeasured ideas as well as winners.

Discovery is designed for M1–M5 families, including Pro/Max/Ultra and MacBooks, iMacs and minis. **Only the named M4 campaign has gameplay evidence.** Start from your own baseline on every other machine. Static scaling is the default; native Metal and dynamic resolution are research paths, not promised upgrades.

![MakeUp and Faithful village, historical visual reference](evidence/images/makeup-faithful-village.png)

<sub>Historical 52.5% nearest-scale visual reference, not the final 75% benchmark. MakeUp Ultra Fast by [javiergcim](https://github.com/javiergcim/MakeUpUltraFast); textures by [Faithful](https://faithfulpack.net/).</sub>

### Scope and status

**0.1 research release.** The CLI is verified on disposable fixtures; the sampler has a synthetic Java smoke test. This repository build did not launch Minecraft or touch the source campaign’s instances. The live sampler hook is version-specific, must be explicitly configured, and has not been newly gameplay-qualified in this release. Unknown mappings fail closed.

- [Manual workflow and capture contract](docs/WORKFLOW.md)
- [Sampler build and hook setup](sampler/README.md)
- [Experiment digest](docs/EXPERIMENTS.md)
- [Attribution, licenses and download sources](THIRD_PARTY.md)
- [Correctness patch recipes](patches/)

Original framework code is [MIT licensed](LICENSE). Third-party components retain their own licenses. This project is independent of Apple, Prism and the mod/shader authors.

**NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.**

## Open community challenge

[Explore the hosted challenge](https://fortunexbt.github.io/minecraft-apple-silicon-framework/) · [Agent skill](silicon_shader/skills/silicon-shader/SKILL.md) · [Rules and optional submission](docs/CHALLENGE.md) · [What we learned from Yukon](docs/YUKON.md)

Version 0.2 adds launcher-neutral game-directory isolation, a read-only setup doctor, user-selected quality floors and an optional quality-first search. Community contributions pair a baseline and candidate, export bounded relative timing evidence, and use an explicit reviewed-digest publication command. The hosted board separates cohorts and labels all initial results self-reported. No community measurements are fabricated to populate it.

```sh
silicon-shader doctor /path/to/game --game-dir
silicon-shader isolate /path/to/game /path/to/new-lab --game-dir --closed
silicon-shader challenge show
silicon-shader install-skill --destination ~/.agents/skills/silicon-shader
```

Generic game directories preserve the existing mod/shader stack. Automatic settings edits still require a supported adapter; launcher JVM arguments/hooks remain the operator's responsibility. Any harness can implement the documented [capture protocol](sampler/README.md), but missing focus/completion evidence cannot be invented.
