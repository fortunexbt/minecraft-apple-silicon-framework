# Benchmark and tune a setup

## 1. Discover and isolate

`silicon-shader discover` reads hardware and Prism metadata; it does not launch games. `--prism /path/to/PrismLauncher` supports portable/custom installations. Output may contain local paths: keep discovery output private.

Close the exact source instance and use `isolate SOURCE DEST --closed --save SAVE_FOLDER`. `--closed` is your acknowledgment; the CLI also rejects a visible Java command referencing that path. A launcher or wrapper may conceal its working directory, so process scanning cannot replace your check. The destination must be new. Symlinks in copied content are refused. Back up valuable worlds separately. The tool copies mods, shader/resource packs and configs locally, not to any server.

Starting from scratch? `silicon-shader setup DEST --minecraft 26.3 --fabric 0.19.5` writes Prism metadata only. Confirm compatibility in Prism, select the appropriate ARM64 Java and install mods/shaders through their original channels. Unknown Minecraft versions must be created through Prism first. Java 25 is the 26.1–26.3 baseline; older games need their own runtime. No automatic mod installer guesses a compatible release. Verify your explicit Java selection with `silicon-shader runtime /path/to/java --minecraft 26.3`; it reports the actual Java major and ARM64 architecture without launching Minecraft.

Launch the lab normally once, choose a disposable world, set your preferred shaders and fullscreen native output, and close it before backend changes. The Python CLI never takes the foreground, launches the game, teleports you, or issues simulated inputs.

## 2. Establish the baseline

Start with your existing good visuals. RenderScale support expects `config/renderscale.json5` containing JSON, as produced by the reference version. Other scaling implementations require a new adapter. The CLI refuses unknown syntax rather than rewriting it incorrectly.

```sh
silicon-shader profile show "$LAB"
silicon-shader loop start session.json "$LAB" \
  --scenes loaded water village nether end --target-fps 85 --max-trials 4
```

`$LAB` is your new instance's absolute path. Choose a target you actually care about; 70–90 FPS travel can be a good tradeoff. The loop is conservative: a complete baseline already above the chosen worst-five-second target, with no >50 ms intervals, ends the search. Visual quality is an independent gate, not an FPS score.

Build the optional [sampler](../../sampler/README.md), attach it **only to the lab** through Prism's per-instance Java arguments, and configure the exact version's frame-return hook. Do not inherit this agent into your daily setup. Unknown mappings fail closed. Successful synthetic testing is not proof the hook works on your Minecraft version.

Create a private control folder and a capture manifest from [the template](../../examples/capture-manifest.json). Fill `expected` before measurement; independently fill `observed` from the actual game and runtime, not by copying expectations. Screenshots/visual inspection or an independently verified runtime adapter are needed. `native_framebuffer` means verified native output pixels, not window points. `versions` identifies the complete mod set; `shader` identifies the pack/version/fix; `terrain` names an identical generated terrain snapshot for A/B. Use a separate `fresh` scene when intentionally testing chunk generation.

```sh
silicon-shader capture request "$CONTROL" baseline-water --seconds 20 --delay 5
# Return focus to the game during the five-second delay. Play the selected short route, remaining focused.
silicon-shader capture status "$CONTROL" baseline-water --wait 25
# After visual review and observed-state completion:
silicon-shader capture import "$CONTROL" baseline-water water-manifest.json \
  --profile baseline --out baseline-water.json
silicon-shader loop submit session.json baseline-water.json
```

Repeat once for each required scene with unique short IDs. Explicit states are **starting → recording → done**, or **error**. If a wait expires, the state remains starting/recording; never assume it stopped. Diagnose that request before creating another. If you have independently confirmed the JVM exited but left a stale nonterminal status, preserve that folder as abandoned evidence and configure a new control folder on the next lab launch; never forge a `done` file. Imports reject absent completion, wrong frame counts, non-monotonic timestamps, invalid duration, focus failures, mismatched identity and visual artifacts. Two invalid submissions stop a session for inspection instead of causing endless retries.

The manifest records an operator's observations; the CLI does not magically detect wrong worlds, black images or fabricated attestations. Do not claim independent visual verification from JSON alone.

## 3. Try one material change

Close the lab before changing disk settings:

```sh
silicon-shader loop propose session.json "$LAB" --closed
```

Scaler controls are preserved with the baseline; the optimizer requires static mode and matching game/Iris scales before starting. This saves the exact baseline profile, applies the next material proposal and returns its ID and rollback receipt. Simulation distance, excess view distance and small static-scale steps are the initial candidate set. Later proposals start from the retained winner. No proposed value is a measured gain.

Open the lab, confirm the actual settings, play the same short scenes, and import/submit captures with `--profile trial-1` (then the returned ID for subsequent trials). Keep instance, save, route, terrain, dimension, hardware/runtime/mods, weather/time, power, focus, cap and framebuffer matched. A new generated area is not a valid A/B control for an already generated one.

Promotion requires at least 5% improvement in the worst scene's worst-five-second rate, no scene losing more than 3% on that measure, no material p95 regression, and no increase in absolute or local outlier counts. The visual reviewer must explicitly set `acceptable_quality: true` as well as accept the absence of artifacts. Captures must also have matched durations within one second. This is an inexpensive selection rule, not statistical proof of a universal improvement; investigate a suspicious small gain with a matched repeat before relying on it.

If no candidate improves, retain the baseline. Stop after the finite budget or two failed candidates. You can stop early with `silicon-shader loop stop session.json --reason "Visual tradeoff already good"` once a complete winner suite exists. No additional JVM matrix or arbitrary frame quota is required.

Inspect `loop status session.json`. Before another candidate or the daily copy, close the lab and restore retained settings:

```sh
silicon-shader loop sync session.json "$LAB" --closed
```

The example `quality75.json` and `wide20.json` files set distance, cap and scaling only; they do not install or select shaders, textures or correctness patches. Select those through Prism/Iris first.

You can also use `profile apply LAB profile.json --closed` and `profile rollback LAB RECEIPT_ID --closed` outside the search. Rollback refuses to overwrite later changes. Shader edits require the entire current property set under `shader_properties`; partial resets invalidate comparisons.

## 4. Leave the benchmark behind

```sh
silicon-shader daily "$LAB" "$DAILY" --closed \
  --save "My World" --session session.json
```

The daily destination must be new. This removes Java arguments/agents and launch hooks, omits sampler/control/log directories, removes Minescript (including a renamed Fabric mod), and keeps other mods and shader fixes. It does not delete the lab or any fallback. The session gate requires a stopped session with a complete winner and matching retained settings.

The resulting status is **clean copy, unverified gameplay**. To call it ready to play, do one brief normal launch and check movement/look/jump, inventory, block interaction, shader appearance and save/reload persistence. Check a varied scene rather than a long stationary benchmark. Release inputs and return to the title screen. Record that check separately; neither an average FPS nor copied files proves it happened.

## Reading results correctly

`average_fps` is intervals per measured CPU time, including the frame limiter. It is not GPU presentation, display refresh, generated frames or input latency. The sampler does not implement frame generation.

For >33/50/100 ms, `time_ms` sums **whole interval durations** crossing the threshold. It is not time in excess of that threshold. `local_outliers` separately counts intervals over twice the neighboring 60-frame median and over 8 ms above it. This heuristic helps distinguish abrupt stalls from sustained gradual slowdowns. Review the source intervals before attributing a cause.

The included reference ledger is prior campaign evidence on one M4. A new Mac, renderer, shader, game version or terrain cohort requires its own valid baseline. Do not pool invalid captures, pristine scenes and fresh-generation stress into one impressive number.

## Adapt to the player

Run `doctor INSTANCE` before tuning, or `doctor GAME_DIRECTORY --game-dir` for another launcher. The JSON result includes detected config and a manifest template with unknown live observations. Do not turn those placeholders into claims without measurement. `isolate --game-dir` copies supported game files into a managed lab while preserving the original. Runtime choice and external launcher arguments remain manual. Configuration adapters currently target Iris and the supported scaling mod; an unsupported stack can supply evidence through the capture protocol without pretending those settings are writable.

Choose explicit floors with `loop start SESSION INSTANCE --min-scale 0.75 --min-render-distance 20`. The default objective seeks performance while preserving those floors. For higher visual quality with verified headroom, use `--objective quality --max-scale 1 --max-render-distance 24`. If a minimum exceeds the default maximum, pass a matching higher maximum. Quality mode can retain a lower-FPS candidate when scale/view distance improves and the chosen pacing target still passes. It does not automatically search arbitrary shaders or mods.

New capture manifests require `game_state=playing`, `player_alive=true`, and the actual `game_mode` in both expected and observed context. Legacy captures without this evidence are not automatically upgraded. Menus and death screens can produce misleadingly high counters. Nearest filtering is a preference unless a matched run shows a speed difference; old world coordinates are not proof of the intended scene.
