# M4 Clear Water 24

A one-setting visual variant of the [M4 wide-view recipe](../m4-wide24/README.md). Start from its pinned Minecraft, Fabric, mod, shader, scaler, texture, and display setup. In the MakeUp Ultra Fast 9.5f shader options, change only `REFLECTION_SLIDER` from `1` to `2`; keep its exposure and CAS patches and every other listed setting unchanged.

This favors the stronger water reflections in the fixed Overworld showcase. It is a visual tradeoff, not a performance upgrade. In one same-machine pair on the standard 420-tick flight-and-turn route, the base setting averaged 101.78 FPS with a worst-five-second rate of 94.54 FPS; reflection level 2 averaged 99.76 FPS with a worst-five-second rate of 90.32 FPS. Neither trace contained a frame interval above 33 ms. These are short CPU frame-production measurements, not displayed-FPS or long-session guarantees.

The comparison changed only the reflection setting. To reproduce it, apply the base recipe first, warm the pinned workload, then run its baseline and candidate captures with the same controls. The candidate uses reflection level 2; do not change the render distance, scale, texture filtering, cap, route, or world.

This recipe has not been qualified as a normal daily profile. Check it in your own worlds before adopting it.

Power source and the exact background application mix were not recorded; both contexts passed the recorded CPU-idle/no-swap preflight. To revert this variant, restore `REFLECTION_SLIDER=1` or your saved base profile. Keep the accepted daily instance as fallback.

![Candidate at the fixed front-facing shoreline view](../../workloads/overworld-v1/showcase.png)
