# The shared challenge run

Every new challenge submission runs **Overworld flight v1**. A fast result from a superflat world, another seed, a stationary camera or a different route does not qualify.

Use `silicon-shader challenge workload` for the versioned definition. The reference adapter and setup instructions live in [workloads/overworld-v1](../workloads/overworld-v1/). The benchmark is one short route, not a test suite.

## Time budget

A repeat comparison is **one baseline and one candidate, about 21 seconds each**, with a 30-second stationary warm-up before each capture. Aim for about eight minutes including the configuration change (two launches, three flights each with the first discarded). Stop the session at ten minutes if the world, sampler or route cannot become ready; diagnose the failure rather than retry indefinitely. Do not add more candidates automatically.

First-time Minecraft/mod downloads and generation of the reference world are separate setup work and may take longer. Report that clearly before starting. Reuse the prepared benchmark world for subsequent comparisons. Trying an existing recipe does not require benchmarking unless the user requests measurements or publication.

## Fixed for everyone

- Minecraft Java **26.3**, vanilla/default Overworld generation, seed **20260929**, structures on, bonus chest off. No custom datapacks or world-generation changes.
- A separate disposable reference world, with the same prepared terrain. Never turn a personal save into the benchmark world.
- Creative flight from the pinned position, a scripted camera turn and default flying speed. No sprinting, manual steering or other manual movement during the measured run.
- FOV **70**, FOV effects **0**, noon and clear weather, normal simulation, focused fullscreen game.
- The same 420-tick, approximately 21-second flight-and-turn trajectory for both configurations, with observed poses compared to the calibrated reference path.

The adapter checks the loaded world's actual seed, generator, noise/biome preset and datapacks. A label in a manifest is not enough. It also records flight state, camera pose and movement on the frame sampler's clock. Wrong terrain setup, stationary/obstructed runs, unscripted camera changes, focus loss and incomplete output are rejected.

The same 420 movement ticks are required even when frames stall. Captures retain the final frame interval and may take up to 30 seconds; a timeout is an incomplete run, not a smooth result. Slow intermediate frames are kept in the statistics.

Terrain is generated before the timed run. Flying still exercises chunk loading and rendering; this is not a fresh-world-generation benchmark.

Hardware and the shader/configuration being tested can differ. Keep resolution and non-intervention settings matched within a baseline/candidate pair; compare those settings across cards before interpreting FPS. A shared path does not make different image quality or hardware equivalent.

## What the player sees

| Stage | In-game behavior | Screenshots |
| --- | --- | --- |
| Prepare | Agent explains the chosen setting, checks the isolated reference world and resets the view | Only a diagnostic image if needed for visual review |
| Warm up | Chat announces the baseline/candidate, 30-second warm-up and upcoming flight | None required |
| Measure | The same automatic flight and turn for about 21 seconds; new chat messages are withheld to keep the workload clean | None |
| Compare | Chat reports completion; the agent reads actual timing files and explains the candidate change/result | None required |
| Portrait | Fixed front-facing view; the agent presses F2 once and checks the saved PNG | One final candidate image for publication |
| Finish | Restore the view, report the actual FPS/pacing and keep or revert the candidate | Stats, seed and submission ID appear on the website card |

Never invent an FPS readout while testing. The agent may announce a result in Minecraft chat only after reading the completed metrics. Do not open the chat input, take screenshots or fast-forward movement during timed frames. Setup and diagnostic screenshots are local; they are not automatically uploaded.

## Flight protocol and invalid runs

Run three flights per launch and discard the first. It runs about 2.4 FPS slower with worse lows because JIT, shader compile and meshing are still warming, which the 30 second stationary warm-up does not remove. Report the same later flight for both sides and say which one in the recipe. A pair with the first flight discarded takes about 8 minutes, not counting first time setup. Differences under about 5 FPS between launches are noise.

A run is invalid, whatever its FPS, when any of these is true.

- The picture shows no shaders. FPS pinned at the cap with a vanilla looking frame means the pack did not draw. Set `preferredGraphicsBackend` to `opengl` for Iris packs, because a leftover Vulkan setting makes Iris draw nothing.
- Window mode, graphics backend, resolution or cap differ between baseline and candidate.
- The route receipt, seed or focus check fails.

Use the same window mode for both sides. Borderless fullscreen is recommended and measured about 4% faster than exclusive on the reference Mac. The public schema cannot record window mode or backend, so name both in the recipe. Candidate `scale` must be between 0.5 and 1.0 to be submittable.

## Supported automatic path

Use Minecraft 26.3, ARM64 Java 25, the version-matched Fabric/Minescript 5/Pyjinn stack and [reference FrameAgent setup](../workloads/overworld-v1/README.md). These are installed in the isolated lab, not the daily instance. The agent must already have working game controls: launch its lab, send Minecraft chat commands, press native F2, inspect the resulting image and restore the view. Codex/computer-control, another coding agent’s native controls, or an existing local game harness can provide that boundary. Shell access alone is insufficient; this repository does not install a system-wide input driver.

If those controls or the pinned version are unavailable, finish the compatible recipe/setup work and report performance as unmeasured. Do not turn one prompt into a new harness-porting project, steal a playing user’s screen, or run a second GPU client. First-time world creation and terrain preparation happen once; reuse them.

## Agent workflow

1. Inspect the Mac and existing game; prepare the isolated reference instance once.
2. Apply the baseline, reset the route and run the shipped adapter. Let it warm up, move and finish without human input.
3. Apply one material candidate and repeat that same run. Keep the baseline if the change is not useful.
4. After measurement, capture the [standard front-facing portrait](../workloads/overworld-v1/README.md#submission-screenshot) with the candidate settings. This short, separate step shows the player’s skin without changing the timed camera. Review the saved image and recorded results, export the observed route receipts, then prepare the submission with both receipts:

```sh
silicon-shader challenge route-receipt CONTROL BASELINE_RUN --out baseline-route.json
silicon-shader challenge route-receipt CONTROL CANDIDATE_RUN --out candidate-route.json
silicon-shader challenge prepare baseline.json candidate.json \
  baseline.csv candidate.csv metadata.json \
  --baseline-route baseline-route.json --candidate-route candidate-route.json \
  --out experiment.json
```

The metadata and capture templates contain illustrative values: replace hardware, versions and settings with observations. The public workload labels must be `scene: overworld-flight`, `route: silicon-shader-overworld-v1`, and `terrain: vanilla-seed-20260929`, with Minecraft `26.3`.

Before the final `challenge prepare` (run from the repository checkout, since the importer script lives there), import each real completion with an operator manifest built from observed context:

```sh
python3 recipes/m4-wide24/sampler/import_capture.py CONTROL BASELINE_RUN baseline-manifest.json baseline.json
python3 recipes/m4-wide24/sampler/import_capture.py CONTROL CANDIDATE_RUN candidate-manifest.json candidate.json
```

The importer accepts the current flight’s text receipt and also retains the historical pan format for old evidence. Never manufacture an old `route.json` or a modern sampler status file to get past it.

Preparation validates the versioned workload and ties each route receipt to its actual frame CSV. Publication requires these checks too. Do not hand-write a passing receipt or copy one from another capture.

## What this establishes

The shared script and receipts catch invalid workloads and accidental interference. They are local, self-reported evidence—not tamper-proof remote attestation. We do not collect transcripts or install anti-cheat software. Reviewers can reproduce a recipe using the same route.

Previous submissions remain available under **Earlier routes**. Their configurations may be useful, but their FPS does not enter the current challenge comparison. They need fresh standard-route captures to qualify; editing a label cannot upgrade them.

Normal movement, inventory, interactions and save/reload are separate daily-use checks. Passing a flight benchmark does not prove all-day gameplay smoothness.
