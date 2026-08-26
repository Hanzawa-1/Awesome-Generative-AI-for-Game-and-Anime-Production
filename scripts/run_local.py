"""Local driver: run the agent, merge into the DB, then resolve thumbnail URLs.

Mirrors the weekly CI pipeline (minus the PR step). Needs an LLM key in .env to do anything;
without one the agent stages nothing and merge/thumbnails are no-ops.

    uv run python scripts/run_local.py --max-iters 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent  # noqa: E402
from pipeline import merge, thumbnails  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iters", type=int, default=6)
    ap.add_argument("--out", default="staged.json")
    ap.add_argument("--skip-thumbnails", action="store_true")
    args = ap.parse_args()

    print("=== 1/3 agent ===")
    run_agent.main(["--out", args.out, "--max-iters", str(args.max_iters)])
    print("=== 2/3 merge ===")
    merge.main(["--staged", args.out, "--pr-body", "pr_body.md"])
    if not args.skip_thumbnails:
        print("=== 3/3 thumbnails ===")
        thumbnails.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
