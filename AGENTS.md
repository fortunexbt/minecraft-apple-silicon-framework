# Working on Silicon Shader

Keep this a small CLI and agent pack. No GUI, daemon, telemetry or launcher replacement unless it solves a demonstrated setup problem.

- Work in this repository or explicit disposable fixtures. Never mutate a user's live Prism instance, save, options, runtime or accepted fallback. Close the exact instance before copying or changing it; a stale PID or timed-out command is not proof it stopped.
- Run `python3 -m unittest discover -s tests -v`. Sampler changes also run its synthetic smoke. No actual game/GPU benchmark is part of CI or ordinary implementation verification.
- Configuration edits require a managed isolated instance and receipt. Preserve full shader properties and correctness fixes. Never silently replace mod/shader versions or launch hooks.
- Captures must verify instance, actual save folder, dimension, scene, framebuffer, scaling, foreground focus, throttle state, route and visual validity. CPU frame production is not GPU presentation, displayed or generated FPS.
- `time_ms` in threshold summaries means whole durations of intervals above the threshold. Report absolute >33/50/100 ms separately from local abrupt outliers. Do not sell normal gradual FPS changes as hitches.
- Baseline first; reuse valid matched evidence. Short representative segments, material settings changes and a finite stopping condition. No arbitrary frame quotas or JVM matrices.
- A clean copy is not a tested daily setup. Normal gameplay, inventory, block interaction and save/reload require an explicit operator check. Do not mark them complete from config inspection.
- Public files must contain no private paths, account details, tokens, worlds, raw logs, runtimes or third-party binaries. Use attributed download manifests/patch recipes and verify licenses. Never infer a redistribution license from a download link.
- Keep public performance claims scoped to the actual machine, scene, version and metric. Unknown hardware or game mappings remain unverified.
- Do not create credentials, accept terms, submit promotional posts or publish new releases without direct user authority.
