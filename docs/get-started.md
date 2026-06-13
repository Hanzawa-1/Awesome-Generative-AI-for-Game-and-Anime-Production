# Get started

How to run this project locally — preview the site, run the agent, and deploy. For *what the
site is*, see [About](about.md).

## Setup

Uses [`uv`](https://docs.astral.sh/uv/) for environment + dependency management
(`pyproject.toml` + `uv.lock`).

```bash
uv sync                       # create .venv and install all deps (incl. dev group)
cp .env.example .env          # then add your LLM key
```

`.env` (only the key for your chosen provider is required):

```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash
GEMINI_API_KEY=<your key>
# optional: GITHUB_TOKEN=<PAT>   (raises the GitHub search rate limit)
```

## Everyday commands

**Windows (PowerShell)** — the task runner (no `make` needed):

```powershell
.\tasks.ps1 serve             # preview the site at http://127.0.0.1:8000
.\tasks.ps1 ci                # validate + tests + strict build
.\tasks.ps1 run-local -Iters 3  # agent -> merge -> thumbnails (needs an LLM key)
```

**macOS / Linux** — `make serve`, `make ci`, `make run-local ITERS=3`.

Either runner just wraps `uv run …`, so you can call those directly:

```bash
uv run mkdocs serve
uv run pytest
uv run python scripts/validate.py
```

## Running the agent

```bash
# preview what the tools surface for a task (no LLM key needed):
uv run python scripts/harvest_preview.py lineart-colorization

# run the agent on specific tasks -> staged.json (needs an LLM key):
uv run python -m agent.run_agent --tasks facial-lipsync --out staged.json
uv run python -m pipeline.merge --staged staged.json
uv run python -m pipeline.thumbnails

# backfill every task below an entry threshold (task -> merge -> thumbnail -> next; resumable):
uv run python scripts/backfill.py --below 1
```

The agent only **proposes**; `pipeline/merge` validates, de-duplicates, and writes the YAML.
`data/entries.yml` / `data/services.yml` are the source of truth — the catalog pages are
generated from them by `scripts/gen_catalog.py` before each build.

## One-time GitHub setup

1. **Settings → Pages → Source → GitHub Actions**.
2. **Settings → Actions → General → Workflow permissions → “Allow GitHub Actions to create and approve pull requests”**.
3. **Settings → Secrets and variables → Actions**
   - *Secrets:* `GEMINI_API_KEY` (and/or `OPENROUTER_API_KEY`); optional `HF_TOKEN`.
   - *Variables:* `LLM_PROVIDER` (`gemini` | `openrouter`), optional `LLM_MODEL`.

`GITHUB_TOKEN` is provided automatically by Actions.

## Workflows

- **Deploy site** — on push to `main`: validate → generate catalog → `mkdocs build --strict` → publish to Pages.
- **Weekly update** — cron + manual: run the agent → merge → thumbnails → open/refresh a PR on
  `bot/weekly-update`. Trigger it manually with **`dry_run = true`** first to test without opening a PR.

Run a workflow locally with [`act`](https://github.com/nektos/act) (build job only — Pages
deploy and PR creation need real GitHub):

```bash
act -W .github/workflows/deploy.yml
```

## Contributing

Add or correct an entry by editing `data/entries.yml` (open source) or `data/services.yml`
(proprietary) — see the schema in `agent/schema.py` — then run `.\tasks.ps1 validate`. The
agent's merge fills only empty fields and never overwrites human-edited values.
