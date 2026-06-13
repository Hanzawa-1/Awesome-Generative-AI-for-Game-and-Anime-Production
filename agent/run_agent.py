"""The weekly research agent: an OpenAI-compatible tool-calling loop that discovers and
enriches candidate entries, then is forced to emit a single ``submit_entries`` call. Output
is a validated, de-duplicated, link-checked ``staged.json`` — the agent never writes the DB.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import Settings, load_settings  # noqa: E402
from agent.llm_client import LLMClient, MissingAPIKey  # noqa: E402
from agent.prompts import SYSTEM_PROMPT, build_task_prompt  # noqa: E402
from agent.schema import Entry  # noqa: E402
from agent.taxonomy import load_taxonomy  # noqa: E402
from agent.tools import SUBMIT_NAME, build_tools  # noqa: E402
from agent.tools._common import http_get  # noqa: E402
from pipeline import db  # noqa: E402

MAX_TOOL_RESULT_CHARS = 6000


# --------------------------------------------------------------------- helpers
def weekly_focus(area_ids: list[str], n: int = 3, week: int | None = None) -> list[str]:
    if not area_ids:
        return []
    if week is None:
        week = _dt.date.today().isocalendar()[1]
    L = len(area_ids)
    start = (week * n) % L
    return [area_ids[(start + i) % L] for i in range(min(n, L))]


def _tool_msg(call_id: str, payload) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": json.dumps(payload, default=str)[:MAX_TOOL_RESULT_CHARS]}


def _link_status(url: str) -> str:
    try:
        r = http_get(url, allow_redirects=True, timeout=10)
        return "dead" if r.status_code in (404, 410, 451) else "alive"
    except requests.exceptions.Timeout:
        return "unknown"
    except Exception:
        return "dead"


def _links_ok(e: Entry) -> bool:
    """Keep unless EVERY link is definitively dead (drops fabricated/DNS-fail URLs)."""
    urls = [str(getattr(e.links, f)) for f in ("arxiv", "github", "project", "hf", "paper", "website")
            if getattr(e.links, f)]
    statuses = [_link_status(u) for u in urls]
    return any(s in ("alive", "unknown") for s in statuses)


def _parse_submission(raw_args: str) -> tuple[list[Entry], int, bool]:
    """Validate submitted entries one-by-one, salvaging the valid ones.

    Returns (valid_entries, invalid_count, parsed_ok). parsed_ok is False only when the
    top-level JSON itself is unparseable (the caller can then ask the model to resubmit)."""
    try:
        data = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return [], 0, False
    raw_entries = data.get("entries", []) if isinstance(data, dict) else []
    valid, invalid = [], 0
    for r in raw_entries:
        try:
            valid.append(Entry.model_validate(r))
        except ValidationError:
            invalid += 1
    return valid, invalid, True


def verify_and_stage(
    entries: list[Entry], existing_keys: set[str], max_new: int, max_per_task: int
) -> list[Entry]:
    staged: list[Entry] = []
    seen = set(existing_keys)
    per_task: dict[tuple[str, str], int] = defaultdict(int)
    for e in entries:
        if len(staged) >= max_new:
            break
        if e.key in seen:
            continue
        if per_task[(e.area, e.task)] >= max_per_task:  # even coverage / quality cap
            continue
        if not _links_ok(e):
            continue
        seen.add(e.key)
        per_task[(e.area, e.task)] += 1
        staged.append(e)
    return staged


# --------------------------------------------------------------------- loop
def run(
    client: LLMClient,
    settings: Settings,
    max_iters: int,
    focus: list[str] | None,
    tasks: list[str] | None = None,
) -> tuple[list[Entry], str]:
    tax = load_taxonomy()
    existing = db.load_all()
    existing_keys = {e.key for e in existing}
    tools_json, fn_map = build_tools(settings)

    if tasks:  # explicit task slice (sweep mode / single-task test)
        task_prompt = build_task_prompt(tax, sorted(existing_keys), [], settings.max_per_task, target_tasks=tasks)
        scope = f"tasks={tasks}"
    else:
        focus_ids = focus or weekly_focus(tax.area_ids())
        task_prompt = build_task_prompt(tax, sorted(existing_keys), focus_ids, settings.max_per_task)
        scope = f"focus={focus_ids}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_prompt},
    ]
    print(f"[agent] provider={client.provider} model={client.model} {scope} "
          f"existing={len(existing_keys)} max_iters={max_iters} cap/task={settings.max_per_task}")

    staged: list[Entry] = []
    notes = ""
    submitted = False
    tool_calls_made = 0
    submit_retries = 0
    MAX_SUBMIT_RETRIES = 2
    tokens = 0
    start = time.monotonic()

    for i in range(max_iters):
        over_budget = (
            tokens >= settings.max_tokens
            or tool_calls_made >= settings.max_tool_calls
            or (time.monotonic() - start) >= settings.wall_clock_seconds
        )
        force = (max_iters - i <= 1) or over_budget
        tool_choice = {"type": "function", "function": {"name": SUBMIT_NAME}} if force else "auto"

        try:
            resp = client.chat(messages, tools=tools_json, tool_choice=tool_choice)
        except Exception as e:  # noqa: BLE001
            print(f"[agent] chat error on iter {i}: {e}")
            break

        usage = getattr(resp, "usage", None)
        if usage and getattr(usage, "total_tokens", None):
            tokens += usage.total_tokens
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        calls = msg.tool_calls or []
        if not calls:
            if force:
                break
            messages.append({"role": "user",
                             "content": "Use the tools to find candidates, then call submit_entries exactly once."})
            continue

        finalize = False
        for call in calls:
            name = call.function.name
            raw_args = call.function.arguments or "{}"
            if name == SUBMIT_NAME:
                valid, invalid, parsed = _parse_submission(raw_args)
                if not parsed and not force and submit_retries < MAX_SUBMIT_RETRIES:
                    # Don't lose the run on a malformed submission — ask for a clean resubmit.
                    submit_retries += 1
                    messages.append(_tool_msg(call.id, {
                        "error": "submit_entries arguments were not valid JSON. Resubmit ONE valid JSON "
                                 "object with an 'entries' array — do not truncate; reduce the entry count "
                                 "if needed."}))
                    continue
                staged = verify_and_stage(valid, existing_keys, settings.max_new_entries, settings.max_per_task)
                try:
                    notes = (json.loads(raw_args) or {}).get("notes", "") or ""
                except Exception:  # noqa: BLE001
                    notes = ""
                messages.append(_tool_msg(call.id, {"accepted": len(staged), "rejected": invalid + (len(valid) - len(staged))}))
                submitted = True
                finalize = True
            else:
                fn = fn_map.get(name)
                if not fn:
                    messages.append(_tool_msg(call.id, {"error": f"unknown tool {name}"}))
                    continue
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                    result = fn(**args) if isinstance(args, dict) else {"error": "arguments must be an object"}
                except Exception as e:  # noqa: BLE001
                    result = {"error": f"tool {name} failed: {e}"[:200]}
                tool_calls_made += 1
                print(f"[agent] iter {i}: {name}({str(args)[:80]}) -> "
                      f"{len(result) if isinstance(result, list) else 'dict'}")
                messages.append(_tool_msg(call.id, result))

        if finalize:
            break

    if not submitted:
        # One final forced submission attempt.
        try:
            messages.append({"role": "user", "content": "Now call submit_entries with your final list (an empty list is fine)."})
            resp = client.chat(messages, tools=tools_json,
                               tool_choice={"type": "function", "function": {"name": SUBMIT_NAME}})
            for call in (resp.choices[0].message.tool_calls or []):
                if call.function.name == SUBMIT_NAME:
                    valid, _, _ = _parse_submission(call.function.arguments or "{}")
                    staged = verify_and_stage(valid, existing_keys, settings.max_new_entries, settings.max_per_task)
        except Exception as e:  # noqa: BLE001
            print(f"[agent] final submit attempt failed: {e}")

    print(f"[agent] tokens~{tokens} tool_calls={tool_calls_made} staged={len(staged)}")
    return staged, notes


# --------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the weekly research agent -> staged.json")
    ap.add_argument("--out", default="staged.json")
    ap.add_argument("--max-iters", type=int, default=None)
    ap.add_argument("--focus", nargs="*", default=None, help="Override the weekly focus area ids.")
    ap.add_argument("--tasks", nargs="*", default=None,
                    help="Restrict the run to specific task ids (sweep slice / single-task test).")
    args = ap.parse_args(argv)

    settings = load_settings()
    max_iters = args.max_iters or settings.max_iters

    try:
        client = LLMClient(settings.provider, settings.model)
    except (MissingAPIKey, ValueError) as e:
        print(f"[agent] {e} — writing an empty staged set (no changes).")
        Path(args.out).write_text(json.dumps({"entries": [], "notes": ""}), encoding="utf-8")
        return 0

    staged, notes = run(client, settings, max_iters, args.focus, tasks=args.tasks)
    payload = {"entries": [e.model_dump(mode="json") for e in staged], "notes": notes}
    Path(args.out).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[agent] wrote {len(staged)} entries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
