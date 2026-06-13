"""Backfill: run the agent on every task with fewer than N entries, with high (effectively
uncapped) limits — one agent run per task, merging into the DB after each (resumable).

    uv run python scripts/backfill.py --below 10

Needs an LLM key in .env. This is a LARGE run: dozens of tasks x many iterations each. On a
free tier (e.g. Gemini's ~250 req/day) you WILL hit rate limits partway — that's fine, progress
is saved after every task, so just re-run later and it resumes (filled tasks drop below the
threshold and are skipped). Use --below / --per-task / --max-iters to scope it.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent  # noqa: E402
from agent.config import load_settings  # noqa: E402
from agent.llm_client import LLMClient, MissingAPIKey  # noqa: E402
from agent.taxonomy import load_taxonomy  # noqa: E402
from pipeline import db, thumbnails  # noqa: E402
from pipeline.merge import merge  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill tasks below an entry-count threshold.")
    ap.add_argument("--below", type=int, default=10, help="Target tasks with fewer than this many entries.")
    ap.add_argument("--per-task", type=int, default=10, help="Max new entries per task (0 = unlimited).")
    ap.add_argument("--max-iters", type=int, default=18,
                    help="Agent iterations per task. Higher = more thorough but much slower on rate-limited "
                         "free tiers (each throttled call backs off up to ~60s).")
    ap.add_argument("--no-thumbnails", action="store_true", help="Skip thumbnail extraction at the end.")
    args = ap.parse_args()

    settings = load_settings()
    settings.max_per_task = args.per_task if args.per_task > 0 else 9999
    settings.max_iters = args.max_iters
    settings.max_new_entries = max(settings.max_new_entries, settings.max_per_task * 3, 300)
    settings.max_tool_calls = max(settings.max_tool_calls, 200)
    settings.max_tokens = max(settings.max_tokens, 2_000_000)
    settings.wall_clock_seconds = max(settings.wall_clock_seconds, 3600)

    try:
        client = LLMClient(settings.provider, settings.model)
    except (MissingAPIKey, ValueError) as e:
        print(f"[backfill] {e} — set LLM_PROVIDER/LLM_MODEL + key in .env.")
        return 1

    tax = load_taxonomy()
    counts = Counter((e.area, e.task) for e in db.load_all())
    todo = [t.id for a in tax.areas for t in a.tasks if counts.get((a.id, t.id), 0) < args.below]
    print(f"[backfill] {len(todo)} tasks below {args.below} entries; per_task={settings.max_per_task} "
          f"iters={settings.max_iters}\n           {todo}")

    total_added = 0
    for i, task in enumerate(todo, 1):
        print(f"\n[backfill] ({i}/{len(todo)}) task={task}")
        try:
            staged, _ = run_agent.run(client, settings, settings.max_iters, None, tasks=[task])
        except Exception as e:  # noqa: BLE001 - one bad task shouldn't abort the whole backfill
            print(f"[backfill] run failed for {task}: {e}")
            continue
        if not staged:
            print(f"[backfill] {task}: no new entries")
            continue
        # task -> merge -> thumbnails, then move to the next task (each task fully done; resumable)
        merged, report = merge(staged, db.load_all())
        db.save_split(merged)
        total_added += len(report.added)
        print(f"[backfill] {task}: +{len(report.added)} added (catalog now {len(merged)})")
        if not args.no_thumbnails:
            thumbnails.main()

    print(f"\n[backfill] done: +{total_added} new entries. Preview with:  .\\tasks.ps1 serve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
