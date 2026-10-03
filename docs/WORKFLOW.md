# Try a shader setup

Use [the agent prompt](../agents/START.md) for the guided path. These are the same steps by hand. Install the CLI using the [README](../README.md#get-started).

## Inspect and choose

```sh
silicon-shader discover
silicon-shader doctor "/path/to/Prism/instances/My Minecraft"
silicon-shader challenge find --this-mac
```

For another launcher, use `doctor /path/to/game --game-dir`. Add known `--minecraft VERSION` and `--loader LOADER` filters to the search. Compare the screenshot, shader/mod versions, resolution and view distance with your current setup. Missing hardware fields and similar-machine results are identified in the output.

Discovery includes public player names/UUIDs and local paths. Keep its complete output private. It does not launch the game or measure FPS.

## Make a reversible trial

Close the exact source instance. Set `SOURCE` and `LAB` to its path and a **new** destination:

```sh
SOURCE="/path/to/Prism/instances/My Minecraft"
LAB="/path/to/Prism/instances/Shader Lab"
silicon-shader isolate "$SOURCE" "$LAB" --closed
silicon-shader profile show "$LAB"
```

For other launchers add `--game-dir` to `isolate`; configure that launcher to use the new directory. Add `--save "Exact Save Folder"` only to copy a chosen world while closed, or create a disposable world in the lab. Existing destinations and symlinked content are refused. Accounts, logs and launcher hooks are not copied.

Read the chosen recipe before installing anything. Use compatible publisher downloads and preserve its complete shader properties. The built-in writer handles supported game/Iris/scaler settings; it does not install or select shader packs, port mods, or configure another launcher's Java arguments.

```sh
silicon-shader profile apply "$LAB" compatible-profile.json --closed
# To undo that application while the lab is closed:
silicon-shader profile rollback "$LAB" RECEIPT_ID --closed
```

Use the receipt ID returned by `apply`. A profile must describe the chosen compatible settings; the example profiles are limited presets, not complete shader installations. Rollback refuses to overwrite later edits.

## Play, then keep or revert

Launch the lab normally and check the actual image, movement, inventory, interactions and save/reload. Keep the original instance as your fallback. A visually useful trial can finish here; without a compatible capture, report performance as unmeasured.

If the lab contains measurement tools, `daily LAB NEW_DEST --closed` makes a clean copy; use `--save` for the exact save to retain. It strips agents/hooks and Minescript. Launch that copy once before calling it ready to play.

## Measure or contribute

Use an existing harness when available. The [benchmarking guide](reference/BENCHMARKING.md) covers the optional sampler, capture manifests, finite tuning loop and quality floors. Start with one baseline and one material candidate; do not require a sampler-porting project just to try a recipe.

[Share a setup](CHALLENGE.md) when you have the screenshot, reproducible recipe and matched measurements. Recipe or harness source improvements can also be ordinary code PRs.
