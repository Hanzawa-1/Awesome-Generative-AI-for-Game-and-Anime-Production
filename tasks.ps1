#!/usr/bin/env pwsh
# Windows-friendly task runner (the Makefile equivalent). Usage:
#   .\tasks.ps1 serve
#   .\tasks.ps1 run-local -Iters 3
#   .\tasks.ps1 ci
param(
    [Parameter(Position = 0)][string]$Task = "help",
    [int]$Iters = 12
)

$env:DISABLE_MKDOCS_2_WARNING = "true"

function Stop-OnError { if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }

switch ($Task) {
    "sync"      { uv sync }
    "test"      { uv run pytest }
    "lint"      { uv run ruff check . }
    "validate"  { uv run python scripts/validate.py }
    "seed"      { uv run python scripts/seed.py }
    "agent"     { uv run python -m agent.run_agent --out staged.json --max-iters $Iters }
    "merge"     { uv run python -m pipeline.merge --staged staged.json --pr-body pr_body.md }
    "thumbs"    { uv run python -m pipeline.thumbnails }
    "run-local" { uv run python scripts/run_local.py --max-iters $Iters }
    "catalog"   { uv run python scripts/gen_catalog.py }
    "site"      { uv run python scripts/gen_catalog.py; Stop-OnError; uv run mkdocs build --strict }
    "serve"     { uv run python scripts/gen_catalog.py; Stop-OnError; uv run mkdocs serve }
    "ci" {
        uv run python scripts/validate.py; Stop-OnError
        uv run pytest; Stop-OnError
        uv run python scripts/gen_catalog.py; Stop-OnError
        uv run mkdocs build --strict; Stop-OnError
    }
    "clean" {
        Remove-Item -Recurse -Force site, staged.json, pr_body.md, .pytest_cache, .ruff_cache -ErrorAction SilentlyContinue
    }
    default {
        @"
Tasks (run as: .\tasks.ps1 <task> [-Iters N]):
  sync        uv sync (create/refresh .venv from uv.lock)
  test        run pytest
  lint        ruff check
  validate    validate data vs schema + taxonomy
  seed        regenerate the seed catalog
  agent       run the research agent  -> staged.json   (needs an LLM key in .env)
  merge       merge staged.json into the DB
  thumbs      extract thumbnails
  run-local   agent -> merge -> thumbnails
  catalog     generate bilingual catalog pages + nav (docs/catalog, SUMMARY*)
  site        generate catalog + mkdocs build --strict
  serve       generate catalog + mkdocs serve (preview at http://127.0.0.1:8000)
  ci          validate + test + generate catalog + strict build
  clean       remove build/temp artifacts
"@
    }
}
