# Verification and operating limits

The release checks run in [GitHub Actions](https://github.com/fortunexbt/minecraft-apple-silicon-framework/actions). On October 4, finalization used existing recordings and remote CI only: the user was playing, so no Minecraft actions, local builds, tests or browser rendering were performed.

- The pinned flight and full-route stop were previously exercised on the base M4. A deliberate 319.7 ms late stall remained in the recorded trace and passed route validation.
- The front-facing shoreline composition has an inspected, unedited 1920×1080 reference image. A later sizing bug was traced to RenderScale’s virtual dimensions; the helper now queries the actual framebuffer. The complete corrected capture/restore cycle and new phase announcements have **not** been live-tested in this finalization. Every use still checks the saved PNG and actual image before publication.
- Other Macs, external-display scaling modes and alternative game-control harnesses are not a tested hardware matrix. The supported automatic path is documented in [WORKLOAD.md](WORKLOAD.md); unsupported setups stop without a fabricated measurement.
- Automated publication checks current-workload data, contributor identity and exact PR contents. It does not independently verify graphics, detect fabricated local evidence or promise that community recipes are safe to execute blindly.
- The static site and data live in GitHub. There is no private service to keep running. Code changes still need review, compatibility changes may need new adapters, and misleading submissions may need moderation. No honest local benchmark framework is maintenance-free forever.

## Initial release snapshot


This historical snapshot records the initial framework build. Current checks are in [GitHub Actions](https://github.com/fortunexbt/minecraft-apple-silicon-framework/actions). It is not a current hardware-qualification matrix.

That release was built without launching Minecraft, using the foreground, altering source Prism instances, or running GPU workloads.

- Python fixture suite exercises the public CLI from isolation through baseline intake, finite stopping, retained settings and clean daily copy. It also checks rollback drift, source preservation, symlink refusal, capture completion/CSV integrity, outlier semantics and version-specific Java requirements.
- Local Python 3.11 and 3.14 runs passed. The package installed into a fresh virtual environment and its installed command ran.
- Ruff's undefined/unused-code checks and formatting check passed.
- Read-only discovery identified the reference base M4 (10 CPU/GPU cores, 24 GB) and 19 Prism instances. An explicit Java probe verified ARM64 Java 25 for the 26.3 reference runtime. Local discovery output is not published.
- The optional sampler passed `./sampler/smoke.sh` after rebuilding current source: bootstrap injection, explicit lifecycle, two sequential captures, CSV consistency, restart non-replay, missing hook and unknown focus. This tests injection and the file protocol, not real Minecraft compatibility.

The historical gameplay evidence in `evidence/` predates this framework release. No new live gameplay was performed. M1/M2/M3/M5, Pro/Max/Ultra variants and other Macs have no performance qualification here. A clean daily copy created by the CLI remains gameplay-unverified until the operator performs the normal-launch checklist.
