.PHONY: sync test lint validate agent merge thumbs run-local site serve ci clean

# Silence the promotional MkDocs-2.0/properdocs banner injected by a transitive dep.
export DISABLE_MKDOCS_2_WARNING := true

# Create/refresh the environment from pyproject.toml + uv.lock (includes dev group)
sync:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

validate:
	uv run python scripts/validate.py

# Run the research agent (override iterations: make agent ITERS=2)
ITERS ?= 12
agent:
	uv run python -m agent.run_agent --out staged.json --max-iters $(ITERS)

merge:
	uv run python -m pipeline.merge --staged staged.json

thumbs:
	uv run python -m pipeline.thumbnails

# Full local pipeline: agent -> merge -> thumbnails (mirrors update.yml)
run-local:
	uv run python scripts/run_local.py --max-iters $(ITERS)

# Generate the bilingual catalog pages + nav (must run before build/serve)
catalog:
	uv run python scripts/gen_catalog.py

site: catalog
	uv run mkdocs build --strict

serve: catalog
	uv run mkdocs serve

# What CI runs (minus the GitHub-only PR/Pages steps)
ci: validate test site

clean:
	rm -rf site staged.json pr_body.md .pytest_cache .ruff_cache
