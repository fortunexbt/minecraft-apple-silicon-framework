# Submission data format

For the participation steps, read [Share a setup](../CHALLENGE.md). This reference is for agents and harness authors preparing timing evidence.

## Capture an experiment

Use an isolated managed setup and a representative 20–30 second living-player gameplay route. Capture baseline first, then candidate on the same machine with the same scene, actual save, terrain, route, runtime, display, game mode, focus, fullscreen, and environmental controls. Keep the two durations within one second. A completion overrun up to 31 seconds is accepted. Do not record a menu, death screen, paused state, or black world. Both captures must pass the existing capture validator, including explicit visual approval and a successful sampler completion receipt.

The local importer verifies each original CSV SHA-256 against capture provenance and recomputes every metric. Missing provenance is rejected. Timestamps must be monotonic, indexes consecutive, and intervals consistent with timestamps. Input files and exported bundles are capped at 8 MB, interval arrays at 30,000 entries, and numbers must be finite. This is a short experiment protocol, not a long unattended benchmark or an arbitrary frame quota.

The supported metric is **CPU frame production**. It is not GPU presentation, displayed FPS, generated FPS, or input latency. Threshold `time_ms` measures the full duration of intervals exceeding 33/50/100 ms, separately from local abrupt outliers.

## Public metadata contract

Unknown keys are rejected throughout public metadata. Required fields are:

- `hardware`: observed `family` such as M1–M6 or A18, `tier` base/pro/max/ultra, integer `cpu_cores`, `gpu_cores`, and `memory_gib` (1–2048). Optional `model` (e.g. MacBook Pro) and `model_identifier` (e.g. Mac16,1) preserve chassis context without serial numbers. The hardware reference is not an admission whitelist.
- `minecraft`, `launcher`, `harness`, `runtime`: short product/version labels. `loader` has `name` and `version`.
- `workload`: generic public `scene`, `route`, and `terrain` recipe labels, matching capture context exactly. Use reproducible recipe names, never a private world name. Runtime must also match the capture.
- `baseline` and `candidate`: each has `mods` (1–200 name-to-version entries), `shader` (`name`, `version`), and `settings`.
- `settings`: output `resolution` (two integers, 320–16384), `scale` (0.5–1), integer `render_distance` and `simulation_distance` (2–64), integer `cap` (0–1000; zero denotes uncapped), `filter` (nearest/linear/off/fsr), and `visual_properties` (up to 100 safe property/value entries, or a named profile). Resolution and all scalar settings are checked against capture context. Shader name must also match the capture.
- `interventions`: exactly the changed fields from scale/render_distance/simulation_distance/cap/filter/visual_properties/shader/mods. Output resolution is fixed. Changes to shader or mod versions are supported. All undeclared configuration fields must match.
- `quality_review`: `reviewed`, `baseline_acceptable`, and `candidate_acceptable` must be true; `artifacts` false; `outcome` is improved/equivalent/tradeoff. This is an explicit operator judgment, not a metric-derived quality score.

The capture format has an opaque `versions` context rather than a structured mod inventory. A declared mods intervention permits this context to differ; public structured mod versions, Minecraft/loader versions, chip details, shader version, and visual properties remain operator declarations, not independently detected facts. Keep Minecraft and loader unchanged. Reproduction needs a human audit of the recipe and actual installed versions. A profile label must identify a reproducible public preset; no config file, archive, or executable is embedded.

Labels allow only short ASCII product-style words, dots, plus signs, spaces, underscores and hyphens. Paths, URLs, emails, long opaque token-like strings and recognizable secret labels are rejected. This is a narrow input vocabulary, **not anonymization** or a guarantee that user-entered text cannot contain personal information. Use generic public labels and inspect the exported JSON before sharing. Custom/private dimension identifiers are not accepted.

## Bundle and integrity

Schema version 1 contains `schema_version`, `status`, `metric`, `metadata`, `controls`, `runs`, `cohort_hash`, and `content_digest`. The only allowed status is `self_reported`. Each run contains relative `intervals_ms`, recomputed `metrics`, and original `csv_sha256`. Absolute nanotimes, source paths, capture IDs, reviewer identities, account data, instance names, and save folder identifiers are never exported. Public recipe labels are exported deliberately. Private instance/save context is compared locally and then discarded.

`cohort_hash` covers public workload/hardware/software context, safe gameplay controls, and configuration fields that are not interventions. It does not identify a private world or establish physical machine identity. `content_digest` is SHA-256 over sorted compact JSON of the complete bundle excluding the digest itself. Validation recomputes all metrics, cohort hash, and content digest; it does not mutate the bundle. Reordered JSON object keys preserve the digest. Array order and numeric JSON representation are part of the content identity.

Digests detect inconsistent edits; they are not signatures or proof against fabricated traces. An author can invent raw intervals and recompute hashes. CSV provenance is checked during local preparation, but the public relative trace cannot independently prove the original absolute CSV. Successful validation must never be labeled externally reproduced or verified. Independent reproduction requires a separately recorded same-machine A/B experiment and human assessment; that workflow is not implemented here.

## Compare outcomes

Compare each candidate to its matched baseline. Discuss visual quality, sustained frame production, frame-time tails and abrupt stalls together. A sharper or richer candidate with equal or lower FPS can be a useful quality tradeoff; there is no higher-FPS-only gate. Never build a global raw-FPS ranking across different machines, scenes or software stacks from these bundles. A short accepted segment does not qualify a complete daily gameplay setup.


## Python API

`silicon_shader.challenge.prepare(baseline_capture_path, candidate_capture_path, baseline_csv_path, candidate_csv_path, metadata_path)` reads files and returns a bundle, or raises `ValueError`. `validate_bundle(bundle)` returns a list of errors; an empty list means structurally consistent self-reported evidence. Neither function publishes anything.

`challenge submit --reviewed-digest DIGEST` optionally checks that the timing bundle matches a prior preview. It does not cover the separate presentation file; inspect its links and public Minecraft identity before publishing. See the submission guide for retry and presentation-correction behavior.
