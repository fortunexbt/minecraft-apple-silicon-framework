# Initial release verification snapshot

This historical snapshot records the initial framework build. Current checks are in [GitHub Actions](https://github.com/fortunexbt/minecraft-apple-silicon-framework/actions). It is not a current hardware-qualification matrix.

That release was built without launching Minecraft, using the foreground, altering source Prism instances, or running GPU workloads.

- Python fixture suite exercises the public CLI from isolation through baseline intake, finite stopping, retained settings and clean daily copy. It also checks rollback drift, source preservation, symlink refusal, capture completion/CSV integrity, outlier semantics and version-specific Java requirements.
- Local Python 3.11 and 3.14 runs passed. The package installed into a fresh virtual environment and its installed command ran.
- Ruff's undefined/unused-code checks and formatting check passed.
- Read-only discovery identified the reference base M4 (10 CPU/GPU cores, 24 GB) and 19 Prism instances. An explicit Java probe verified ARM64 Java 25 for the 26.3 reference runtime. Local discovery output is not published.
- The optional sampler passed `./sampler/smoke.sh` after rebuilding current source: bootstrap injection, explicit lifecycle, two sequential captures, CSV consistency, restart non-replay, missing hook and unknown focus. This tests injection and the file protocol, not real Minecraft compatibility.

The historical gameplay evidence in `evidence/` predates this framework release. No new live gameplay was performed. M1/M2/M3/M5, Pro/Max/Ultra variants and other Macs have no performance qualification here. A clean daily copy created by the CLI remains gameplay-unverified until the operator performs the normal-launch checklist.
