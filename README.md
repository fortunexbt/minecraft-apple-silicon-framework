# Silicon Shader

![Minecraft shaders. Made for your Mac.](site/assets/social-card.jpg)

Pick a Minecraft Java shader look that your Apple Silicon Mac can run well. Browse screenshots and measured results from real Macs, then let your coding agent adapt a setup to your launcher and mods without touching your current game.

**[Browse setups](https://fortunexbt.github.io/minecraft-apple-silicon-framework/) · [Give your agent the prompt](agents/START.md) · [Share a setup](docs/CHALLENGE.md)**

## Who it is for

Mac players of Minecraft Java (26.x) who use Prism or another launcher with Fabric, Sodium and Iris shaders, and who would rather ask an agent than tune settings by hand. It does not cover Bedrock, Intel Macs, iPhone or iPad, or Windows.

## Current results

All results are from a base M4 MacBook Pro (10 CPU cores, 10 GPU cores, 24 GiB) on the [shared seeded flight](docs/WORKLOAD.md), at 3024 pixel wide output. Each row is one matched pair against a wide view baseline. These are short CPU frame production measurements, not displayed FPS.

| Setup | Look | Average FPS | Worst five seconds | Notes |
| --- | --- | --- | --- | --- |
| [M4 Far Horizon](recipes/m4-far-horizon/README.md) | Sildur's Vibrant, shaded terrain out to 256 chunks | 98.4 | 92.8 | 10 real chunks plus Distant Horizons |
| [M4 Vibrant 16](recipes/m4-vibrant16/README.md) | Sildur's Vibrant, richest sky and water | 99.8 | 90.3 | 16 chunks, 60% scale |
| [M4 Max 32](recipes/m4-max32/README.md) | MakeUp Ultra Fast, full 32 chunks | 98.5 | 88.9 | 50% scale, softer image |
| [M4 Clear Water 24](recipes/m4-clear-water24/README.md) | MakeUp with stronger water reflections | 99.8 | 90.3 | Exclusive fullscreen, 3024x1964 |

Run to run noise is about 1 to 3 FPS once the first flight is discarded, so treat gaps under about 5 FPS between cards as ties. The [M4 Wide View](recipes/m4-wide24/README.md) card was measured on an earlier route and is shown separately on the site. Only the base M4 has current results. The [hardware inventory](docs/HARDWARE.md) lists every released Apple Silicon Mac, and an entry there does not mean it was benchmarked.

## What the library is

The site is a filterable library, not a global ranking. Each card has a screenshot with the player's skin, hardware, versions, resolution, view distance, FPS and frame pacing, and a recipe. Filter for a Mac like yours and sort by pacing, FPS or distance. A higher FPS can simply mean a lower resolution or a shorter view distance, so compare the picture before choosing. Entries are self reported, not certified.

## Quick start

Give [the starter prompt](agents/START.md) to Codex, Claude Code or another coding agent with shell access. It detects your Mac and game, compares suitable recipes and tries changes in a separate copy with rollback. Your worlds, current settings and any game in use are left alone, and your current image quality is the starting point. Sharing is optional.

You need

- An Apple Silicon Mac. The reference machine runs macOS 26. Older versions are untested.
- Your own Minecraft Java installation, ideally in Prism, with ARM64 Java 25 for Minecraft 26.x.
- Python 3.10 or later. There are no runtime dependencies or API keys.
- For automatic performance runs only, an agent with real game control (chat commands, F2, window focus) and macOS Accessibility permission for that agent. Shell access alone cannot drive Minecraft. Without it you still get the setup, reported as unmeasured.

Prefer the CLI? Clone outside Desktop and Documents, because iCloud syncing corrupts `.git`.

```sh
git clone https://github.com/fortunexbt/minecraft-apple-silicon-framework.git
cd minecraft-apple-silicon-framework
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
silicon-shader discover
silicon-shader challenge find --this-mac
```

Continue with [try a setup](docs/WORKFLOW.md). Prism has the most direct integration and other launchers use an explicit game directory. The [agent skill](silicon_shader/skills/silicon-shader/SKILL.md) ships with the CLI and can be read directly. Installing it into your agent is optional.

## How a comparison works

New submissions use [one shared seeded world and scripted flight](docs/WORKLOAD.md). The agent runs a baseline and a candidate, discards the first flight of each launch, and checks that the picture really shows shaders. A separate short launch takes one fixed front facing portrait. Earlier route recipes stay separate. Plan on about 8 minutes for a pair, not counting first time setup.

## What the toolkit does

| Task | Command or guide |
| --- | --- |
| Inspect the Mac, active player and game | `discover`, `doctor`, `runtime` |
| Find a community recipe | `challenge find --this-mac` |
| Try settings and roll back | `isolate`, `profile` and the [workflow](docs/WORKFLOW.md) |
| Measure one fair comparison | [Shared flight and portrait](docs/WORKLOAD.md) |
| Make a clean daily copy | `daily` |
| Preview and publish evidence | `challenge submit`, `challenge status` and the [submission guide](docs/CHALLENGE.md) |
| Learn from earlier tuning | [What the campaign measured](docs/EXPERIMENTS.md) |

Configuration writes require an isolated managed copy. The CLI does not launch Minecraft, install arbitrary mods, or upload anything during tuning. External launchers retain control of Java and launch arguments. Unsupported settings need explicit adaptation.

Measurements use **CPU frame production**, not displayed or generated FPS. The optional sampler needs a confirmed hook for the Minecraft version. A copied setup is only gameplay-checked after a normal launch. [How to compare results](docs/FAIRNESS.md).

## Work on the project

- `silicon_shader/` — CLI, configuration adapters and bundled agent skill.
- `recipes/` — reproducible shared setups; `contributions/` — accepted measurement bundles.
- `site/` — static community library; `sampler/` — optional Java capture agent.
- `docs/` — player guides; `docs/reference/` — capture and submission contracts.
- `examples/`, `patches/`, `evidence/` — input templates, correctness fixes and historical research.

Campaign lessons live in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md). Read [AGENTS.md](AGENTS.md) before editing. Run `python3 -m unittest discover -s tests -v`; sampler changes also run `./sampler/smoke.sh`. Keep recipe/code improvements separate from evidence submissions. Preserve existing worlds and configurations.

The repository is the source of the website and accepted submissions. The index is generated, not edited by hand. Preview or host it anywhere:

```sh
python3 -m silicon_shader.registry contributions site/data.json
python3 -m http.server 8000 --directory site
```

Validated current-workload data-only submissions merge and publish automatically; recipe/tool changes still need review. Entries remain self-reported, not certified performance. No database or private backend is required. Historical campaign notes remain in [the experiment digest](docs/EXPERIMENTS.md) and `evidence/`.

Original code is [MIT licensed](LICENSE). See [third-party attribution](THIRD_PARTY.md) for mods, shaders and textures. Independent community project; not affiliated with Apple or Prism.

**NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.**
