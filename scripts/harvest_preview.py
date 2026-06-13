"""Preview what the agent's discovery tools surface for a task — NO LLM key needed.

Runs the deterministic half of the agent (arXiv / GitHub / Hugging Face searches built
from the task's taxonomy keywords) and prints the candidates. Useful for sanity-checking a
task before running the full agent.

    uv run python scripts/harvest_preview.py lineart-colorization
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.taxonomy import load_taxonomy  # noqa: E402
from agent.tools import arxiv_tool, github_tool, hf_tool  # noqa: E402


def _find(tax, task_id):
    for a in tax.areas:
        for t in a.tasks:
            if t.id == task_id:
                return a, t
    return None, None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: harvest_preview.py <task_id>")
        return 1
    task_id = sys.argv[1]
    tax = load_taxonomy()
    area, task = _find(tax, task_id)
    if not task:
        print(f"unknown task id '{task_id}'")
        return 1

    # Concise phrase from the task name (the real agent's LLM crafts queries like this).
    phrase = re.sub(r"[^a-z0-9 ]", " ", task.name.lower())
    phrase = re.sub(r"\s+", " ", phrase).strip()
    arxiv_q = f'abs:"{phrase}"'  # phrase-match the abstract; relevance-sorted below
    print(f"# {area.name} / {task.name}")
    print(f"  arxiv query: {arxiv_q!r} (sort=relevance)\n  web/github query: {phrase!r}\n")

    print("## arXiv (relevance)")
    for r in arxiv_tool.search(arxiv_q, max_results=6, sort="relevance") or []:
        if isinstance(r, dict) and r.get("title"):
            print(f"  [{r.get('arxiv_id')}] {r['title']} ({r.get('year')})")

    print("\n## GitHub (by stars)")
    for r in github_tool.search(phrase, sort="stars", limit=6) or []:
        if isinstance(r, dict) and r.get("repo"):
            print(f"  ({r.get('stars')}*) {r['repo']} — {(r.get('description') or '')[:70]}")

    print("\n## Hugging Face models")
    for r in hf_tool.search_models(phrase, limit=5) or []:
        if isinstance(r, dict) and r.get("model_id"):
            print(f"  ({r.get('downloads')} dl) {r['model_id']}")

    print("\nNote: this is a NAIVE preview query. The full agent uses the LLM to craft "
          "targeted queries per task, then selects/dedupes/summarizes. Run it with an LLM key:\n"
          f"  uv run python -m agent.run_agent --tasks {task_id} --out staged.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
