# How a fair winner is decided

**Open experiments are accepting submissions. Official ranking is not open yet.** The shared reference world, camera route and visual preset still need to be published and qualified. Current submissions are useful, self-reported showcases; their order on the site is not a ranking.

Visual taste does not determine the winner. The first ranked challenge will ask a narrower question: **can you render the agreed image more efficiently without changing what the player sees?** These are the proposed v1 rules. Freeze them together with the reference workload before accepting ranked entries; changes start a new rules version.

## One fixed workload per board

A ranked track must publish a downloadable, redistributable world or complete deterministic generation recipe, pre-generated terrain snapshot, fixed camera route, scene checkpoints, warm-up procedure, capture duration, reference screenshots, shader/settings preset, and exact Minecraft, loader, runtime and baseline mod versions. A private world name or a route label alone is insufficient.

Each board uses one specified evaluator hardware model, chip/core count, memory, macOS version, output resolution, power mode and thermal starting procedure. Participants may develop on any Mac, but the official baseline and candidate are replayed on the same evaluator machine. Different machines or workload versions get separate boards. An M4 Max does not beat a base M4 by being larger.

Output resolution, internal resolution, view and simulation distances, texture pack, required shader features, frame cap and VSync mode are fixed by the track. Dynamic resolution and frame generation are off. A throughput track must use an uncapped baseline/candidate rather than ranking limiter headroom. Correct output-preserving culling is allowed; missing visible geometry, delayed loading or disabled ambient occlusion/shadows/reflections are not optimizations of the same image. Changes to performance code or mods are allowed only with reproducible source and unchanged required rendering behavior. Link the separate reviewed code PR or immutable commit from the evidence PR; the data submission must not execute contributor code.

## A reproducible score

Run three matched baseline/candidate pairs for every required scene after warm-up, alternating order B→C, C→B, B→C. Restart or reset the track's prescribed state between runs. Retain all attempts and invalidate a pair for focus loss, background contention, incomplete loading, wrong game state or another declared environmental failure. Do not keep only the best run. No menus, death screens or stationary views substituted for the route.

For each pair, compute `baseline p95 frame time / candidate p95 frame time`. Take the median of the three ratios in each scene. The overall score is `100 × (lowest scene ratio − 1)`: the least-improved required scene determines the result. Higher is better. A score of 10 means the worst scene's p95 ratio is 1.10; it is **not** a claim of 10% more displayed FPS.

Before ranking, baseline p95 spread `(maximum − minimum) / median` must be at most 3% within each scene. Otherwise the batch is inconclusive and needs a clean rerun. A positive record needs at least 5% overall improvement, no scene's median worst-five-second rate more than 3% worse, no scene's median p99 more than 3% worse, and no increase in total >33/50/100 ms interval counts or local abrupt-outlier counts over equal-duration matched runs. These are declared engineering tolerances, not statistical confidence intervals.

Compare eligible results only within their board. Entries within 3 percentage points of the highest score share the lead; timestamps, contributor popularity and subjective appearance do not break that tie. A sole record requires a lead beyond that margin in an independent complete replay against the same reference. Smaller improvements remain worth sharing even when they do not establish a new record.

## Image correctness is an eligibility gate

Review the fixed scene checkpoints and the moving route against the reference: visible geometry, shadows, reflections, lighting, water, textures and temporal stability must remain intact. Matching screenshots alone cannot rule out flicker or missing work during movement. Any intended appearance change belongs in the showcase rather than the fixed-image track. A visual reviewer records what was checked and any uncertainty; “looks acceptable to me” alone cannot certify equivalence.

Automated image comparisons may help locate differences later, but are not a beauty score or currently implemented verifier. CPU frame-production timing remains the current capture metric; it does not establish GPU presentation, displayed FPS, generated FPS or input latency. The track must retain that label unless a separately qualified measurement backend is adopted.

## Who can declare a result ranked

The contributor supplies the recipe and raw evidence. The existing validator recomputes single-pair trace summaries, checks context consistency and keeps the submission self-reported. It does **not** implement the repeated-run scoring and official replay process described above, verify image equivalence, or promote a winner.

An independent evaluator must reproduce the complete fixed workload and publish the paired evidence, comparison and visual review before a maintainer can record an official result. Contributor-entered “verified” flags do not count. Until the reference workload and this process are operational, all submissions stay in the unranked showcase. This is a deliberate boundary, not a hidden judgment made by the website.

## Where other useful work belongs

Higher view distance, sharper scaling, different shaders and artistic preferences belong in the setup showcase, with their measured costs and tradeoffs visible. A future distance challenge could fix the visual preset and rank the highest **actually rendered** distance meeting a defined pacing floor. It would be a separate track, not a bonus blended into this score.

The first M4 setup is a reference contribution, not automatically a champion. The goal is to let other players reproduce and improve it.
