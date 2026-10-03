# Overworld flight v1

The standard challenge is one 420-tick creative flight with a smooth north-to-west turn. Minecraft 26.3 and Minescript 5/Pyjinn are required. The [packaged workload](../../silicon_shader/workloads/overworld-v1.json), also printed by `silicon-shader challenge workload`, defines the seed, poses and tolerances.

## Prepare once

Use an isolated instance. Create a disposable **Silicon Shader Overworld v1** world: default Overworld, seed **20260929**, creative, commands enabled, structures on, bonus chest off. Do not use a personal world or world-generation mods. Generate the corridor before timing: at render distance 32, visit the start `-121.3 100 438.7`, midpoint `-121.3 100 346.2` and end `-233.3 100 320.7`, allowing terrain to finish loading. Restore the profile's render distance afterward. First-time downloads and world preparation are separate from the repeat benchmark budget.

Use the existing [FrameAgent source and build script](../../recipes/m4-wide24/sampler/), following the sampler setup in the [working recipe](../../recipes/m4-wide24/README.md). This is the 26.3 adapter; the generic sampler has a different completion format. Set `MCBENCH_EVIDENCE` to the same output directory passed to FrameAgent when launching the instance. The default is `minescript/bench-output` if both tools use it. Keep the sampler's inactivity policy at MINIMIZED.

Copy `reference_flight.pyj` into the instance's `minescript/` directory. Keep the game focused, with debug charts closed. The agent can invoke the script through its existing game harness; it must not steer during capture.

## Run

From Minecraft chat, invoke:

```text
\reference_flight
```

An optional unique run ID may follow the command. The runner checks the named world and actual generation settings, sets FOV 70/effects 0 and frozen clear noon, enables native flight if needed, teleports to the start and settles before measurement. It then records 30 seconds of stationary warmup and about 21 seconds of scripted flight. Capture ends after all 420 movement ticks, retaining the next frame so the final slow interval is included. A 30-second safety limit bounds a stalled route. Each attempt has a 65-second deadline and releases movement keys on completion or a caught error.

The runner records actual world settings, terrain probes, camera poses, flight state, focus, dimensions and timing, alongside the real FrameAgent files. It never creates sampler completion evidence. Normalize each finished run:

```sh
silicon-shader challenge route-receipt CONTROL RUN_ID --out route.json
```

Only this validation establishes that the observations match the standard. A script finishing does not establish acceptance. Use one baseline and one candidate; follow the [submission workflow](../../docs/WORKLOAD.md). Aim for under five minutes per repeat comparison. Stop and diagnose instead of starting an automatic retry loop.

## Verified on hardware

A fresh default world on the base M4 produced the pinned terrain probes. Runs `owv1cal8` and `owv1cal9` took 30.045/30.004 seconds of warmup and 20.996/21.004 seconds of flight. All 22 recorded positions and yaw samples matched exactly. The second run exercised automatic preparation. Both sampler completions had no focus loss or sink errors. The final sampler-stop implementation was then exercised in `owv1stop1`: 30.055 seconds of warmup, 21.035 seconds of captured frames, and the closing frame retained after the route ended at 21.025 seconds relative to frame zero. That run passed the CLI route validator; the built sampler matched the shipped sources.

The source records `calibration_required` for a completed capture: raw output always needs independent validation. Frame and route timestamps come from the same JVM clock, with a small allowed startup offset. These are self-reported development observations, not remote anti-cheat proof or a new performance submission. Prepared terrain keeps world generation out of the timed comparison. This short flight does not establish all-day gameplay stability.
