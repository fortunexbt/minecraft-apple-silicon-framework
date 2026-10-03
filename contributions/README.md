# Community experiments

Reviewed data-only submissions appear here as `<content_digest>.json`. Use `silicon-shader challenge prepare`, inspect the bundle, then opt in with `challenge submit`. New entries contain a public GitHub handle, validated timing bundle, and `presentation` with title, gameplay screenshot URL and Markdown recipe URL. Use `challenge submit BUNDLE --presentation setup.json` to preview; add `--publish` when ready. They remain **self-reported** after review; merging does not certify independent reproduction.

Maintainers must verify the author matches the submitting GitHub account, open the screenshot and recipe links, inspect reproducibility and quality claims, and review the exact data before merging. The automated gate validates with the base branch's code and never executes contributor code. Changes to the validator belong in a separate code PR. See [the rules](../docs/CHALLENGE.md).
