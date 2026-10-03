# The shared challenge run

Every new challenge submission runs **Overworld flight v1**. A fast result from a superflat world, another seed, a stationary camera or a different route does not qualify.

Use `silicon-shader challenge workload` for the versioned definition. The reference adapter and setup instructions live in [workloads/overworld-v1](../workloads/overworld-v1/). The benchmark is one short route, not a test suite.

## Time budget

A repeat comparison is **one baseline and one candidate, about 21 seconds each**, with a 30-second stationary warm-up before each capture. Aim for under five minutes including the configuration change. Stop the session at five minutes if the world, sampler or route cannot become ready; diagnose the failure rather than retry indefinitely. Do not add more candidates automatically.

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

Preparation validates the versioned workload and ties each route receipt to its actual frame CSV. Publication requires these checks too. Do not hand-write a passing receipt or copy one from another capture.

## What this establishes

The shared script and receipts catch invalid workloads and accidental interference. They are local, self-reported evidence—not tamper-proof remote attestation. We do not collect transcripts or install anti-cheat software. Reviewers can reproduce a recipe using the same route.

Previous submissions remain available under **Earlier routes**. Their configurations may be useful, but their FPS does not enter the current challenge comparison. They need fresh standard-route captures to qualify; editing a label cannot upgrade them.

Normal movement, inventory, interactions and save/reload are separate daily-use checks. Passing a flight benchmark does not prove all-day gameplay smoothness.
