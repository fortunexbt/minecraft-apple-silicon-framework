# Community A/B challenge evidence

This optional protocol packages a small same-machine experiment for another person to reproduce. It can accompany a launcher setup, mod change, shader setting, or alternate harness that emits the documented capture and CSV formats. It neither launches Minecraft nor executes submitted code, downloads mods, uploads evidence, or contacts a service. The optional CLI publication flow is documented below.

`silicon_shader.challenge.prepare(baseline_capture_path, candidate_capture_path, baseline_csv_path, candidate_csv_path, metadata_path)` returns a JSON-compatible dictionary and raises `ValueError` for rejected input. It reads files without modifying them. `validate_bundle(bundle)` returns a list of errors; an empty list means structurally valid **self-reported** evidence. See `examples/challenge-metadata.json` for the exact metadata shape. These preparation and validation functions do not submit anything.

## Capture an experiment

Use an isolated managed setup and a representative 20–30 second living-player gameplay route. Capture baseline first, then candidate on the same machine with the same scene, actual save, terrain, route, runtime, display, game mode, focus, fullscreen, and environmental controls. Keep the two durations within one second. A completion overrun up to 31 seconds is accepted. Do not record a menu, death screen, paused state, or black world. Both captures must pass the existing capture validator, including explicit visual approval and a successful sampler completion receipt.

The local importer verifies each original CSV SHA-256 against capture provenance and recomputes every metric. Missing provenance is rejected. Timestamps must be monotonic, indexes consecutive, and intervals consistent with timestamps. Input files and exported bundles are capped at 8 MB, interval arrays at 30,000 entries, and numbers must be finite. This is a short experiment protocol, not a long unattended benchmark or an arbitrary frame quota.

The supported metric is **CPU frame production**. It is not GPU presentation, displayed FPS, generated FPS, or input latency. Threshold `time_ms` measures the full duration of intervals exceeding 33/50/100 ms, separately from local abrupt outliers.

## Public metadata contract

Unknown keys are rejected throughout public metadata. Required fields are:

- `hardware`: `family` M1–M5, `tier` base/pro/max/ultra, integer `cpu_cores`, `gpu_cores`, and `memory_gib` (1–512).
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

## CLI and hosted board

The [hosted challenge](https://fortunexbt.github.io/minecraft-apple-silicon-framework/) reads a generated index of reviewed repository contributions. It offers cohort selection, paired pacing/improvement plots and full evidence details. The first version has no remote Minecraft runner or automatic independent-reproduction certification. It starts empty; historical campaign claims are not silently converted into community submissions.

```sh
silicon-shader challenge show
silicon-shader challenge prepare baseline.json candidate.json baseline.csv candidate.csv metadata.json --out experiment.json
silicon-shader challenge validate experiment.json
silicon-shader challenge submit experiment.json
```

The final command above is a local preview and makes no network requests. Inspect its bundle, destination and content digest. When you choose to publish:

```sh
silicon-shader challenge submit experiment.json --publish --reviewed-digest FULL_SHA256_FROM_PREVIEW
silicon-shader challenge status FULL_SHA256_FROM_PREVIEW
```

Publication uses an existing authenticated `gh` installation. It publishes your GitHub handle and bundle, may create your fork, creates a deterministic branch and opens one data-only PR. No credential creation, login, automatic telemetry or transcript upload occurs. A fork may take time to become available. After an interrupted or failed request, inspect status and retry the **same bundle and digest**. The command resumes an existing file/PR and refuses to overwrite different content. A closed PR is returned as closed rather than resubmitted. Content changes require a new reviewed digest. No local Git checkout is reset or modified.

The PR check reads the JSON blob using trusted base-branch code, verifies author identity and recomputes metrics and hashes. Maintainer review is required before merge. The site rebuilds on main; merging self-reported evidence does not upgrade its status. Do not include executable code, archives or private configs. Code/adapter improvements use a separate ordinary PR with tests. A named shader profile or route must point to an available public recipe that a reviewer can actually reproduce; unsupported or private recipes should not be merged.

Install the portable skill into your agent's supported skill directory explicitly:

```sh
silicon-shader skill
silicon-shader install-skill --destination ~/.agents/skills/silicon-shader
```

The installer refuses to overwrite an existing different skill or follow a symlink. Other harnesses can read the same SKILL.md directly. Installing the CLI does not silently modify agent configuration.
