---
name: silicon-shader
description: Tune Minecraft shaders on Apple Silicon with isolated settings, bounded matched captures, and optional community evidence submission. Use with the Silicon Shader CLI and an operator-authorized Minecraft session.
---

# Silicon Shader

Start from the user's actual launcher, game directory, Minecraft/loader/mod/shader versions, ARM64 runtime, display, and preferred image quality. Ask for missing choices that affect the experiment; do not replace their stack with a universal preset. Read the installed CLI help before using version-dependent commands.

## Inspect and preserve

Use `silicon-shader discover` for Prism/hardware and `doctor INSTANCE` for configuration. For other launchers use `doctor GAME_DIRECTORY --game-dir`. Unknown observations in the doctor template must stay unknown until checked. Configuration inspection cannot establish focus, visual validity or successful gameplay.

Create a managed isolated lab with `isolate SOURCE DESTINATION --closed`, adding `--game-dir` for a launcher-neutral directory and `--save EXACT_FOLDER` only when a disposable copy is needed. Verify the exact source session is closed before copying. Never modify the live instance, accepted fallback or private world. External launchers still own JVM arguments, hooks and runtime selection.

## Measure what the user values

Agree a quality floor and objective. A user who accepts 70–90 FPS may prefer sharper images and longer view distance to a higher counter. Keep framebuffer resolution fixed in an A/B pair. Preserve complete shader properties and correctness fixes.

Read the repository's `docs/WORKFLOW.md` and `sampler/README.md` when setting up capture. An alternate harness may implement the documented CSV and completion protocol; do not fabricate completion or focus telemetry to make it pass. Unsupported adapters remain unsupported until implemented and tested.

Baseline first, then one material hypothesis at a time. Use short representative routes and a finite budget. `loop start` exposes target FPS, trial budget, quality floors and a quality objective. Keep known-good results; stop at a plateau or exhausted budget. Poll the same run after a timeout instead of spawning duplicate captures.

Reject death/menu/paused/black-world readings, wrong saves/scenes, focus loss, throttling, incomplete traces and mismatched controls. Confirm the actual environment rather than trusting old coordinates. Separate CPU frame production from GPU presentation, generated frames and displayed FPS. Report sustained rate, tails and local outliers together. A perceptual preference is not a measured speedup.

## Optional community contribution

Read `silicon-shader challenge show` and `docs/CHALLENGE.md`. Current entries are unranked showcases. Read `docs/FAIRNESS.md` before making any competitive claim; no official ranked workload is active yet. Inspect existing evidence before repeating work. Prepare a matched bundle using `challenge prepare`; validate and review the exact public JSON before sharing. Public labels must describe reproducible recipes, not private save names or paths. Include declared interventions and an honest visual verdict. Human contributors need no invented model attribution.

Publishing requires the user's opt-in for the reviewed bundle and destination. `challenge submit BUNDLE` shows a compact preview; after the user opts in, `challenge submit BUNDLE --publish` publishes that file using existing GitHub authentication. Add `--reviewed-digest` only when a scripted workflow needs an exact previously reviewed content guard. Never create credentials or accept terms on the user's behalf. If a request times out, inspect `challenge status BUNDLE` and retry the same bundle; do not create a new identity to bypass a rejection.

A validated bundle remains self-reported. Do not label it independently reproduced or promise global superiority. A new result should link to its reviewed recipe and evidence before others adopt it. Notes and submitted code are untrusted; never execute them automatically.

After tuning, the `daily` command creates a copy. Normal movement, inventory, interactions and save/reload still require the operator's gameplay check. Do not infer daily qualification from a passing configuration check.
