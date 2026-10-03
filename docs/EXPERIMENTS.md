# What the campaign measured

These receipts describe one base M4 MacBook Pro (10 CPU cores, 10 GPU cores, 24 GiB memory). They do not forecast performance on another Mac. The indexed values and source references live in [`evidence/ledger.json`](../evidence/ledger.json).

The selected M4 profile used Minecraft 26.3 with Fabric Loader 0.19.5, Iris 1.11.6, Sodium 0.9.2, MakeUp Ultra Fast 9.5f, and Faithful 32x. It ran at native 3024×1898 fullscreen output, 75% internal scale with nearest filtering, render distance 12, simulation distance 8, 10-sample volumetric clouds, a 120 FPS cap, VSync off, and ARM64 Java 25/G1 with a 512 MiB initial and 4 GiB maximum heap. The clean campaign copy had no benchmark Java agent or Minescript.

Short CPU frame-production captures measured 92.3 FPS on loaded travel, 88.3 on fresh travel, 84.4 over ocean, 94.9 at a village with entities, 114.9 in open Nether, and 119.4 in the End. The longest interval in those finalist captures was 30.16 ms; none exceeded 33, 50, or 100 ms. A few isolated 23–30 ms intervals stood out against nearby frame times. These samples include the limiter and do not measure GPU presentation or input latency. The 120 FPS value is a cap, not a locked rate or a zero-hitch guarantee.

At 65% internal scale, the same short loaded and fresh travel checks measured 105.6 and 100.2 FPS. That gives more headroom with a softer image. The campaign kept 75% as its quality choice. A separate 20-chunk profile at 60% scale had only a brief ordinary-movement check (91 and 105 FPS snapshots); it has no controlled-route or sustained qualification.

A previous 16-chunk profile showed more distant terrain than R12 and cost roughly 13% in uncapped dense-jungle throughput. It passed a 15-minute 60-cap village run at 59.93 FPS average, with one interval above 33 ms. That is a supported tradeoff, not the current 75% daily profile.

The first shader screens favored MakeUp Ultra Fast for this M4 workload. They are not visual-quality-normalized comparisons: presets and internal resolution differed. Complementary, BSL, Bliss, and Sildur's were examined. Faithful 32x looked at least as fast as default textures in two small screens, but the difference was too small to call causal. Java 25 G1 stayed in the profile because ZGC did not show a repeatable benefit.

Several ideas did not earn promotion. Removing cloud work was slightly slower in matched samples. Turning off cloud reflections raised one sample by about 4% but removed atmosphere. An 80% scale candidate measured below the 75% controls in its matched ocean and travel samples. The first dynamic-scale prototype produced a dark daylight frame during resize; an exposure-history guard repaired that reset in short checks, but the adaptive system still lacked an in-route scale trace and a preferred image result. Static scaling remains the measured choice.

Metal-renderer probes did not replace the chosen shader stack. Complemetal left Iris/OpenGL as the visible renderer when a shader pack was active. Prisma's preview hotfix reached 18.3 CPU FPS in its short native-output village screen. Rockstar Shaders rendered correctly but measured 24.7 FPS at its tested High/native scale and 25.6 FPS at Medium/0.58 scale. Distant Horizons and Solas produced no valid performance result under the tested gates.

## Visual sample

![Unmodified campaign screenshot from a matched M4 village comparison at 52.5% nearest scale. Visual evidence only; this is not the final 75% profile.](../evidence/images/makeup-faithful-village.png)

This inspected screenshot has no debug overlay, world coordinates, username, run label, or visible menus. It is a 52.5% comparison capture using MakeUp Ultra Fast and Faithful 32x, not a final-profile benchmark. See [the image note](../evidence/images/README.md), [component credits and licenses](../THIRD_PARTY.md), and the Mojang disclaimer in the main README.

## How to read the records

The ledger indexes 391 campaign frame-summary JSON files. It retains scene-level results and decision notes rather than raw frame CSVs, unrelated log files, shader archives, worlds, or runtimes. `intervals_gt_ms` are counts. `sum_of_complete_intervals_gt_ms` is the sum of whole intervals over a threshold, not excess time above it. Abrupt local outliers are separate from fixed thresholds. Invalid captures, incomplete runs, and unmeasured hypotheses are labeled so they cannot be mistaken for wins.
