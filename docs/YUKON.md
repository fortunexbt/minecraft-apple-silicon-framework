# Yukon challenge research

Studied 3 October 2026 from the live ECDSA.fail interface, public challenge repository, installed Yukon CLI source and bundled skill. This is a design reference for Silicon Shader, not a claim of affiliation or access to Yukon's private backend.

## The participation loop

ECDSA.fail's Participate dialog offers CLI installation, API-key login, clone, local run and submit. Installation also provides an agent skill. The current Yukon CLI generalizes this into benchmark discovery, multi-track selection, setup, local scoring, submission, result inspection, public notes, and synchronization with promoted work. Its skill teaches agents to check the frontier before spending effort, preserve local changes before synchronization, and describe reproducible experiments. The interface links submissions back to commits and credits the solver and model. [Live challenge](https://ecdsa.fail/)

The installed CLI packages only manifest-authorized paths, limits compressed archives to 25 MiB, and supplies a submission idempotency key. Submission and promotion are distinct states. Schema 2 assigns separate editable paths to tracks sharing one repository. A successful track promotion preserves other tracks. Local runs are useful feedback; server evaluation decides acceptance. These implementation observations are version-specific, not a promise about every deployment. Do not copy the CLI's account setup or transcript collection into this project: local tuning should need no account, and publishing evidence must be optional.

## Model and agent credits

The installed `yukon submit --help` requires separate `--model` and `--harness` labels. The model is the underlying version; the harness is the coding agent (Codex, Claude Code, OpenCode, etc.). The model appears on the leaderboard and the harness on the solver profile. Silicon Shader records both in `presentation.agent`, separately from its Minecraft capture harness. Missing historical attribution stays unknown; no transcripts are required.

## The trusted boundary

The ECDSA manifest defines the metric direction, editable directory, setup command, benchmark command, score path and runner. Its workflow independently checks the submission diff before setup, uses read-only credentials, pins actions and prevents submission branches from saving shared caches. [Manifest](https://github.com/Layr-Labs/ecdsafail-challenge/blob/main/benchmark.json), [workflow](https://github.com/Layr-Labs/ecdsafail-challenge/blob/main/.github/workflows/benchmark.yml)

The benchmark separates untrusted circuit construction from trusted evaluation. It removes stale outputs, confines construction, requires a new output artifact and evaluates that artifact with a separate verifier. The public script explicitly distinguishes its local unconfined fallback from official sandbox scoring. The transferable principle is that contributors cannot replace the verifier or supply the authoritative score. [Benchmark script](https://github.com/Layr-Labs/ecdsafail-challenge/blob/main/benchmark.sh)

The MLX challenge is especially relevant: its official score pairs a reference and candidate on the same organizer M5 machine. Local estimates do not enter the ranked result directly. Its score combines prefill and decode improvements with defined weights. This is stronger evidence than comparing unrelated users' machines. [MLX challenge](https://www.yukon.org/mlxfast)

## The visible product

ECDSA.fail uses an ivory page, forest-green chart panel, large outcome, compact explanation and participation dialogs, a frontier chart with alternate views, and a detailed results table. Selecting a result exposes its metrics, time, note and commit. Historical contributions remain inspectable even when superseded. Silicon Shader should preserve this immediate route from result to evidence, with its own identity and labels.

One inspected public note contained conflicting contributor-authored correctness limits. Such notes are research leads, not authoritative rules. A Minecraft challenge must pin its eligibility and quality requirements in the versioned contract; silently weakening quality must never manufacture progress.

## Decisions for Silicon Shader

- Ship a portable agent skill with the CLI workflow and machine-readable challenge contract. Adapt to the existing launcher, versions, hardware, harness and user's image-quality floor.
- Keep local optimization account-free. Package explicit same-machine baseline/candidate evidence, then publish only the reviewed bundle through an optional command.
- Use the existing public GitHub repository for review and provenance, and a hosted leaderboard for participation and discovery. No separate API-key service is necessary for this first version.
- Recompute timings with trusted code. Structural validation means self-reported evidence; it cannot establish that gameplay occurred or that an image is acceptable. Independent reproduction needs a separately reviewed experiment.
- Compare compatible cohorts and expose pacing, visual tradeoffs and raw relative traces. Never rank all Apple Silicon machines by raw FPS or turn visual quality into an invented scalar.
- Treat reusable configs, reproducible negative results, adapter improvements and independent reproductions as useful contributions. A short capture does not qualify a daily setup.

The hosted site and CLI must state their actual implementation status. A static leaderboard backed by reviewed data is not a remote GPU evaluation service.
