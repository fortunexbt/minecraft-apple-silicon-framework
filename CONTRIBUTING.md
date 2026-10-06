# Contributing

- **Share a setup:** follow [docs/CHALLENGE.md](docs/CHALLENGE.md). Evidence submissions are data only and merge automatically after the checks pass.
- **Recipes, tools and docs:** open a normal pull request. Read [AGENTS.md](AGENTS.md) first and keep the project a small CLI and agent pack.
- **Before you push:** `python -m unittest discover -s tests`, then `ruff check silicon_shader tests --select F` and `ruff format silicon_shader tests --check`.
- **Lessons from measuring:** add durable findings to [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) so the next agent does not repeat them.
- **Reports:** a misleading entry or a broken link can be reported as an issue. Maintainers can correct or remove it.
