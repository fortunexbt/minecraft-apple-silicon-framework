# Apple Silicon Mac inventory

Checked **3 October 2026**. The [machine-readable inventory](hardware.json) records released Mac models with their chip tier, CPU/GPU core counts, permitted unified-memory options and Apple source links. It includes older Macs people already own. Storage, colour and regional ordering codes do not create separate gaming configurations.

Coverage: **M1–M6**, the released Pro/Max/Ultra variants, and **A18 Pro MacBook Neo**; MacBook Air, MacBook Pro, iMac, Mac mini, Mac Studio and Mac Pro (tower/rack). iPhones and iPads are outside this Java/macOS framework.

Apple lists the [M6 Mac mini as available from 22 September 2026](https://www.apple.com/newsroom/2026/08/apple-unveils-a-more-powerful-mac-mini-featuring-the-all-new-m6-and-m5-pro/). The [M5 Ultra Mac Studio's 512 GB option](https://www.apple.com/newsroom/2026/09/the-new-mac-mini-and-mac-studio-are-available-today/) is announced for late October and is excluded from this released inventory.

This is a hardware reference, not a promise that every Minecraft version, mod or harness works on every Mac. `discover` reads the actual machine; submission validation accepts new M/A chip families without waiting for a catalogue update. It never publishes serial numbers or hardware UUIDs.

Use `challenge find --this-mac --minecraft VERSION --loader LOADER`. Exact hardware matches come first. When none exist, similar hardware is clearly labelled; compare the screenshot, resolution, view distance, versions and recipe before trying it. A faster result on a different Mac is not a prediction for yours.

To maintain the inventory, update the dated JSON from Apple specifications, keeping memory options attached to the CPU/GPU/model combinations that actually support them. Do not generate the Cartesian product of every option in a product family.
