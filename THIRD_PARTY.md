# Third-party components and credits

The framework source is MIT-licensed by the repository's top-level `LICENSE`. The campaign below tested separate projects. This repository does not bundle Minecraft, Prism Launcher, Java, Fabric, mods, shader packs, resource packs, or world saves. Setup links users to each publisher's own project or release page. “Tested version” records the campaign version, not a claim that it is current today. Project metadata and primary license pages were checked on 2026-10-03; missing values are marked instead of guessed.

The selected visual sample is a campaign screenshot of Minecraft rendered with MakeUp Ultra Fast 9.5f and Faithful 32x. Faithful requires clear credit and a visible link; the image note and this table provide both. The main README includes Mojang's required non-affiliation wording because a Minecraft screenshot is included.

## Game, launcher, loader, and selected stack

| Component | Campaign version | License / rights | Official source |
|---|---|---|---|
| Minecraft: Java Edition | 26.3 | Mojang/Microsoft proprietary game; no game files redistributed | [Minecraft](https://www.minecraft.net/); [official version manifest](https://piston-meta.mojang.com/mc/game/version_manifest_v2.json) |
| Prism Launcher | 11.1.1 | GPL-3.0-only; launcher not bundled | [Project and license](https://github.com/PrismLauncher/PrismLauncher) |
| Fabric Loader | 0.19.5 | Apache-2.0; loader not bundled | [Fabric Loader](https://github.com/FabricMC/fabric-loader) |
| Fabric API | 0.161.0+26.3 | Apache-2.0; API not bundled | [Fabric API](https://github.com/FabricMC/fabric-api) |
| Sodium | 0.9.2+26.3 | PolyForm Shield 1.0.0; no Sodium code or binary is included or modified here | [Source and license](https://github.com/CaffeineMC/sodium/blob/dev/LICENSE.md) |
| Iris | 1.11.6+26.3 | LGPL-3.0-only; campaign used a locally patched copy described under `patches/` | [Source and license](https://github.com/IrisShaders/Iris) |
| Lithium | 0.26.2+26.3 | LGPL-3.0-only; not bundled | [Source and license](https://github.com/CaffeineMC/lithium) |
| Entity Culling | 1.11.2 | tr7zw Protective License; not bundled or modified | [Source and license](https://github.com/tr7zw/EntityCulling/blob/main/LICENSE-EntityCulling) |
| FerriteCore | 9.0.0 | MIT; not bundled | [Source](https://github.com/malte0811/FerriteCore) |
| Sodium Extra | 0.9.4+26.3 | LGPL-3.0-only; not bundled | [Source and license](https://github.com/FlashyReese/sodium-extra) |
| Reese's Sodium Options | 2.2.5+26.3 | MIT; not bundled | [Source and license](https://github.com/FlashyReese/reeses-sodium-options) |
| MakeUp Ultra Fast | 9.5f | LGPL-3.0-only; patch recipe is under `patches/`; shader archive not bundled | [Project and source](https://github.com/javiergcim/MakeUpUltraFast), [Modrinth version](https://modrinth.com/shader/makeup-ultra-fast-shaders/version/IUFkxmHz), [license](https://raw.githubusercontent.com/javiergcim/MakeUpUltraFast/master/LICENSE) |
| Faithful 32x | 26.3 September 2026 | Faithful License v4; screenshot credit and website link required | [Pack](https://modrinth.com/resourcepack/faithful-32x/version/lDYpMiqk), [license](https://faithfulpack.net/license), [source](https://github.com/Faithful-Resource-Pack/Faithful-Java-32x) |

## Other tested or screened projects

These entries appeared in the campaign ledger or its experiment summaries. They are not required by the selected stack and are not distributed here.

| Component | Tested version | License / rights | Official source |
|---|---|---|---|
| BSL Shaders | 10.1.8 | All Rights Reserved per project metadata; no pack included | [Project](https://modrinth.com/shader/bsl-shaders) |
| Complementary Reimagined | r5.9.3 | Custom Complementary License; no pack included | [Project and license](https://github.com/ComplementaryDevelopment/ComplementaryReimagined) |
| Complementary Unbound | r5.9.3 | Custom Complementary License; no pack included | [Project and license](https://github.com/ComplementaryDevelopment/ComplementaryShadersV4) |
| Bliss Shaders | 2.1.2 | All Rights Reserved; no pack included | [Project and license](https://github.com/X0nk/Bliss-Shader) |
| Sildur's Vibrant Shaders | 2.02 | All Rights Reserved per project metadata; no pack included | [Project](https://modrinth.com/shader/sildurs-vibrant-shaders) |
| Solas Shader | 3.7b | All Rights Reserved per project metadata; no pack included | [Project](https://github.com/Septonious/Solas-Shader) |
| C2ME | 0.4.2-alpha.0.88+26.3 | MIT for the main repository; an OpenCL subproject is proprietary; no binary included | [Source and license](https://github.com/RelativityMC/C2ME-fabric) |
| Distant Horizons | 3.3.4-26.3 | LGPL-3.0-only; no binary included | [Source](https://gitlab.com/distant-horizons-team/distant-horizons) |
| ImmediatelyFast | 1.17.1+26.3 | LGPL-3.0-or-later; no binary included | [Source](https://github.com/RaphiMC/ImmediatelyFast) |
| Bad Optimizations | 2.4.1 | MIT; no binary included | [Source](https://github.com/ItsThosea/BadOpitmizations) |
| Cloth Config | 26.3.159 | LGPL-3.0-only; no binary included | [Source](https://github.com/shedaniel/ClothConfig) |
| Dynamic FPS | 3.11.10 | MIT; no binary included | [Source](https://github.com/juliand665/Dynamic-FPS) |
| Mod Menu | 21.0.0 | MIT; no binary included | [Source](https://github.com/TerraformersMC/ModMenu) |
| YetAnotherConfigLib | 3.9.7+26.3 | LGPL-3.0-or-later; no binary included | [Source](https://github.com/isXander/YetAnotherConfigLib) |
| More Culling | 1.9.0-beta.1 | GPL-3.0-only; no binary included | [Source](https://github.com/FxMorin/MoreCulling) |
| Minescript | 5.0 Fabric 26.3 | GPL-3.0-only; benchmark helper was removed from the clean profile and is not bundled | [Source](https://github.com/maxuser0/minescript) |
| RenderScale (upstream stock) | 1.4.0-alpha.6 Fabric 26.3 | MIT; the framework workflow supports it as a user-installed scale-setting dependency. | [Project](https://github.com/Zolo101/RenderScale), [Modrinth version](https://modrinth.com/mod/renderscale/version/Qr4y3YLK) |
| MetalMC | Tested source at commit `8304347e5acf251238303dc8404e5f2c79384e98` | MIT in the current upstream `LICENSE`; no binary or source included | [Pinned campaign commit](https://github.com/XaviFortes/MetalMC/commit/8304347e5acf251238303dc8404e5f2c79384e98), [license](https://github.com/XaviFortes/MetalMC/blob/main/LICENSE) |
| MetalUpscaler | 0.4.0+mc26.2 | License/source URL not verified in the campaign record; no binary included | [Campaign measurement index](evidence/ledger.json) |
| Complemetal | 0.4.1+mc26.2, source commit `81defd5285bc84e0022d25221d82e8541dec5655` | Apache-2.0; no binary or source included | [Release](https://github.com/daniiarkg/complemetal-mc/releases/tag/v0.4.1%2Bmc26.2), [pinned commit](https://github.com/daniiarkg/complemetal-mc/commit/81defd5285bc84e0022d25221d82e8541dec5655), [license](https://github.com/daniiarkg/complemetal-mc/blob/main/LICENSE) |
| Prisma renderer preview | 26.3 preview 3 hotfix | License not verified in the inspected project metadata; preview was only screened and is not bundled | [Project](https://github.com/ahlansantos/Prisma), [campaign project docs](https://github.com/ahlansantos/Prisma-docs) |
| Rockstar Shaders | 1.0.0, release commit `42c7e4c` | Proprietary, closed-source license; no binary or shader source included | [Release](https://github.com/ryleighnewman/RockstarShaders/releases/tag/v1.0.0), [license](https://github.com/ryleighnewman/RockstarShaders/blob/main/LICENSE.md) |
| ASM | 9.9.1, patch build dependency | BSD-3-Clause; downloaded by a user when building the optional Iris recipe, not vendored | [ASM project](https://asm.ow2.io/), [Maven Central](https://repo.maven.apache.org/maven2/org/ow2/asm/asm/9.9.1/) |

## Mojang Java runtime requirements

The CLI prefers `javaVersion` metadata in the selected instance and installed game patch JSON when present. Its offline version-family fallback uses the values below, which were cross-checked against Mojang's official version manifest on 2026-10-03.

| Minecraft versions | Required Java major |
|---|---:|
| 26.1, 26.2, 26.3 | 25 |
| 1.20.5 through 1.21.x | 21 |
| 1.18 through 1.20.4 | 17 |
| 1.17 | 16 |

This table describes Mojang's game metadata, not a recommendation to use a particular Java vendor. Fabric mods may impose additional requirements.

### Campaign-local RenderScale variants

The campaign's stock-version receipt records RenderScale 1.4.0-alpha.6. A later lab-only JAR changed `RenderScale.class` to force the forward dynamic-update `viewChanged` argument; its SHA-256 was `9fc93fd74c979124bd483f1b2b736b3caf084fc5e8e0001044df8619b4600b04`. A separate quantized-factor JAR (SHA-256 `8337af211bef89572bf57a2fe5aeeb0e4ab231beda1ac35f450bb1e9901e07e3`) was subsequently verified installed in the October 3 wide-view lab. Its dynamic extensions remain dormant at targetFrameRate 0; static 60% was used for the paired wide-view experiment. Reproducible source-only transforms are in [the wide-view recipe](recipes/m4-wide24/). Neither variant is an upstream release or included here. Dynamic scaling was not promoted; the accepted profile used static 75% scaling. The setup workflow preserves existing instance mods and does not replace a user's locally modified JAR with upstream stock.

## Screenshot and project disclaimer

Minecraft screenshots are Mojang/Microsoft assets covered by the [Minecraft Usage Guidelines](https://www.minecraft.net/en-us/usage-guidelines). This project is unaffiliated and includes the required wording in the main README: **NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.** The screenshot is unmodified and is used as an example of a local visual comparison; it is not a product-performance claim.
