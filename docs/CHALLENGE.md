# Share a setup

The [community library](https://fortunexbt.github.io/minecraft-apple-silicon-framework/) shows screenshots, Minecraft faces, hardware, settings and measured results. Share a recipe another player can try, with enough evidence to understand its tradeoffs. Publishing is optional.

## What to include

- A real gameplay screenshot of the candidate setup.
- Hardware, game/loader, Java, mod and shader versions; resolution and view distance.
- A public recipe with exact settings, download sources, patches, harness/route and rollback steps.
- Matched baseline/candidate timings from the same Mac and scene, with a visual review.
- Your public Minecraft UUID or Java username for the skin face; GitHub identifies the contributor.

Use `discover` to get the active Prism profile automatically. For other launchers, inspect the selected public game profile. Never upload account files, credentials, worlds or raw logs. Keep screenshots free of private chat.

## CLI and hosted board

[Capture a short experiment](reference/BENCHMARKING.md), or use a compatible existing harness. Fill [the metadata template](../examples/challenge-metadata.json), then prepare the evidence:

```sh
silicon-shader challenge prepare baseline.json candidate.json baseline.csv candidate.csv metadata.json --out experiment.json
silicon-shader challenge validate experiment.json
```

Create `setup.json` beside it:

```json
{
  "title": "My shader setup",
  "minecraft_profile": "YOUR_JAVA_USERNAME_OR_UUID",
  "screenshot_url": "https://raw.githubusercontent.com/OWNER/REPO/FULL_COMMIT_ID/path/gameplay.png",
  "recipe_url": "https://github.com/OWNER/REPO/blob/FULL_COMMIT_ID/path/recipe.md"
}
```

Use a full 40-character commit ID. Screenshots accept pinned GitHub PNG/JPEG/WebP files or GitHub `user-attachments/assets/...` URLs; recipes must be pinned Markdown files. Publish these files in your repository or a separate recipe PR first. Download links do not grant redistribution rights for third-party binaries.

```sh
# Local preview: no network request or upload.
silicon-shader challenge submit experiment.json --presentation setup.json

# After reviewing the preview and choosing to publish:
gh auth status --hostname github.com
silicon-shader challenge submit experiment.json --presentation setup.json --publish
silicon-shader challenge status experiment.json
```

Publication uses existing GitHub CLI authentication, may create your fork, and opens one data-only PR. Maintainer review comes before inclusion on the site. If interrupted, check status and retry the same bundle; do not create duplicates. A closed PR stays closed. A changed timing bundle is a new submission.

The skin loads through [MCHeads](https://mc-heads.net/), using the submitted public identity. UUIDs survive username changes. A default Minecraft face appears for old entries or unavailable skins; GitHub photos are not used. Skin identity is not proof of account ownership.

## Corrections and improvements

To correct a title, skin, screenshot or recipe link, edit only the existing contribution's `presentation` in a PR from the same GitHub author. Keep its author and measured bundle unchanged. The publish command resumes existing submissions; it does not overwrite them.

Recipe, mod, adapter and harness source improvements use ordinary code PRs, separate from evidence JSON. Include instructions that another player can follow. Report failures with the error and public version details, without private paths or logs.

## Reading the evidence

Submissions are **self-reported**. Validation recomputes timing metrics and rejects inconsistent data; it cannot prove that gameplay happened. Screenshots and image-quality judgments remain subjective. CPU frame production is not displayed/generated FPS or input latency, and a short route is not an all-day smoothness guarantee.

[Compare setups for your Mac](FAIRNESS.md) · [Submission format and validation rules](reference/SUBMISSIONS.md) · [Sampler protocol](../sampler/README.md)
