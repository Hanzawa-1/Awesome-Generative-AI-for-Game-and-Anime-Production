"""Daily catalog sweep: research today's slice of the task list (the slice auto-divides the
WHOLE taxonomy across the week, so it adapts as tasks are added/removed), merge each task into
the DB, and resolve thumbnail URLs. The daily GitHub Actions job runs this; the workflow owns the
git branch + weekly PR. The agent only proposes — merge validates/dedupes before anything lands.

    uv run python scripts/daily_sweep.py            # today's slice (Mon=0..Sun=6 by date)
    uv run python scripts/daily_sweep.py --day 0    # force Monday's slice (for testing)
    uv run python scripts/daily_sweep.py --day 3 --max-iters 6 --no-thumbnails
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent  # noqa: E402
from agent.config import load_settings  # noqa: E402
from agent.llm_client import LLMClient, MissingAPIKey  # noqa: E402
from agent.run_agent import daily_sweep_tasks  # noqa: E402
from agent.taxonomy import load_taxonomy  # noqa: E402
from pipeline import db, thumbnails  # noqa: E402
from pipeline.merge import merge  # noqa: E402


def _write_pr_body(path: Path, day: int, days: int, slice_tasks: list[str],
                   added_by_task: dict[str, int]) -> None:
    total = sum(added_by_task.values())
    lines = [
        "## Automated catalog sweep",
        "",
        f"Day {day % days + 1} of {days} — researched {len(slice_tasks)} task(s), "
        f"**+{total}** new {'entry' if total == 1 else 'entries'}.",
        "",
    ]
    if added_by_task:
        lines.append("New this run:")
        lines += [f"- `{t}`: +{n}" for t, n in sorted(added_by_task.items())]
    else:
        lines.append("No new entries this run.")
    lines += ["", "_Proposed by the research agent. Review before merging — summaries are "
              "machine-generated and may contain mistakes._"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one day's slice of the weekly task sweep.")
    ap.add_argument("--day", type=int, default=None,
                    help="0-based day index in the week (default: today; Mon=0..Sun=6).")
    ap.add_argument("--days", type=int, default=7, help="Days to spread the full sweep across.")
    ap.add_argument("--max-iters", type=int, default=None, help="Agent iterations per task.")
    ap.add_argument("--pr-body", default="pr_body.md", help="Where to write the changelog.")
    ap.add_argument("--no-thumbnails", action="store_true", help="Skip thumbnail URL resolution.")
    args = ap.parse_args()

    tax = load_taxonomy()
    day = args.day if args.day is not None else (_dt.date.today().isoweekday() - 1)
    slice_tasks = daily_sweep_tasks(tax, day, args.days)
    print(f"[sweep] day {day % args.days}/{args.days} -> {len(slice_tasks)} of {len(tax)} tasks: "
          f"{slice_tasks}")
    if not slice_tasks:
        _write_pr_body(Path(args.pr_body), day, args.days, [], {})
        return 0

    settings = load_settings()
    if args.max_iters:
        settings.max_iters = args.max_iters

    try:
        client = LLMClient(settings.provider, settings.model)
    except (MissingAPIKey, ValueError) as e:
        print(f"[sweep] {e} — set LLM_PROVIDER/LLM_MODEL + key (env or .env).")
        return 1

    added_by_task: dict[str, int] = {}
    for i, task in enumerate(slice_tasks, 1):
        print(f"\n[sweep] ({i}/{len(slice_tasks)}) task={task}")
        try:
            staged, _ = run_agent.run(client, settings, settings.max_iters, None, tasks=[task])
        except Exception as e:  # noqa: BLE001 - one bad task must not abort the whole sweep
            print(f"[sweep] run failed for {task}: {e}")
            continue
        if not staged:
            print(f"[sweep] {task}: no new entries")
            continue
        # task -> merge -> next (merging after each task grows the dedup set for later tasks)
        merged, report = merge(staged, db.load_all())
        db.save_split(merged)
        if report.added:
            added_by_task[task] = len(report.added)
        print(f"[sweep] {task}: +{len(report.added)} added (catalog now {len(merged)})")

    if added_by_task and not args.no_thumbnails:
        thumbnails.main()

    _write_pr_body(Path(args.pr_body), day, args.days, slice_tasks, added_by_task)
    total = sum(added_by_task.values())
    print(f"\n[sweep] done: +{total} new entries across {len(added_by_task)} task(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
