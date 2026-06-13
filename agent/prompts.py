"""System + task prompt construction for the research agent."""

from __future__ import annotations

from agent.taxonomy import Taxonomy

SYSTEM_PROMPT = """\
You are the research librarian for "Awesome Generative AI for Game & Anime Production", a curated
catalog of generative-AI / ML *tasks* (organized Area -> Task) that GAME and ANIME studios actually
use in production. Your job each run: discover NEW, real, high-quality models, papers, and tools that
are not already in the catalog, and submit them as structured entries.

Hard rules (a deterministic validator enforces these — violations are dropped):
1. Use ONLY URLs returned by your tools. NEVER invent or guess a URL.
2. Every open-source (kind="oss") entry MUST have a real arXiv id OR a real GitHub repo.
   Proprietary tools (kind="proprietary") use a "website" link.
3. Classify each entry into a VALID area id + task id from the taxonomy you are given.
4. Write neutral, factual 1-3 sentence summaries (20-600 chars). No marketing language, no hype.
5. ALSO provide a concise Japanese translation of the summary in `summary_ja` (the site is bilingual).
6. Prefer open-source models/papers (they are the bulk of the catalog), but ALSO include notable
   proprietary/industry tools that studios actively use.
7. Do NOT resubmit anything whose dedup key is already in the provided "existing" set.
8. Favor production-relevant, well-known, or state-of-the-art work over obscure one-offs.

Workflow: call the search/fetch tools to find and verify candidates, then call `submit_entries`
EXACTLY ONCE with your final list. If you found nothing genuinely new, submit an empty list — never
fabricate entries to fill a quota.
"""


def render_taxonomy(tax: Taxonomy) -> str:
    lines = []
    for area in tax.areas:
        lines.append(f"- {area.id} — {area.name}: {area.description or ''}")
        for t in area.tasks:
            kw = f"  [{', '.join(t.keywords)}]" if t.keywords else ""
            lines.append(f"    - {t.id} ({t.name}){kw}")
    return "\n".join(lines)


def build_task_prompt(
    tax: Taxonomy,
    existing_keys: list[str],
    focus_area_ids: list[str],
    max_new: int,
) -> str:
    focus = ", ".join(focus_area_ids) if focus_area_ids else "any area"
    keys_block = "\n".join(sorted(existing_keys)[:600]) or "(none yet)"
    return f"""\
TAXONOMY (area id — name; then task id (name) [keywords]):
{render_taxonomy(tax)}

THIS WEEK'S FOCUS AREAS (spend most effort here, but other areas are allowed): {focus}

EXISTING ENTRIES — dedup keys already in the catalog. Do NOT resubmit any of these
(a key looks like "arxiv:2401.01234", "repo:owner/name", or "title:normalizedtitle"):
{keys_block}

Find up to {max_new} NEW entries that are not in the existing set. Prioritise:
- recent arXiv / Hugging Face papers and trending model releases,
- new or actively-maintained GitHub repositories,
- proprietary tools that game/anime studios are actively adopting.

Verify a candidate's primary link with fetch_url if unsure it is real. When done, call
submit_entries exactly once.
"""
