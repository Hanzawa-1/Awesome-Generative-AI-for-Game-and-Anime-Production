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


def _render_target_tasks(tax: Taxonomy, task_ids: list[str]) -> str:
    wanted = set(task_ids)
    lines = []
    for area in tax.areas:
        for t in area.tasks:
            if t.id in wanted:
                kw = f"  [{', '.join(t.keywords)}]" if t.keywords else ""
                lines.append(f"- {area.id}/{t.id} ({t.name}){kw}")
    return "\n".join(lines) or "(no valid task ids given)"


def build_task_prompt(
    tax: Taxonomy,
    existing_keys: list[str],
    focus_area_ids: list[str],
    max_per_task: int,
    target_tasks: list[str] | None = None,
) -> str:
    keys_block = "\n".join(sorted(existing_keys)[:800]) or "(none yet)"
    if target_tasks:
        scope = ("TARGET TASKS THIS RUN — find entries ONLY for these specific tasks "
                 "(cover every one of them):\n" + _render_target_tasks(tax, target_tasks))
    else:
        focus = ", ".join(focus_area_ids) if focus_area_ids else "any area"
        scope = f"THIS WEEK'S FOCUS AREAS (spend most effort here, but other areas are allowed): {focus}"
    return f"""\
TAXONOMY (area id — name; then task id (name) [keywords]):
{render_taxonomy(tax)}

{scope}

EXISTING ENTRIES — dedup keys already in the catalog. Do NOT resubmit any of these
(a key looks like "arxiv:2401.01234", "repo:owner/name", or "title:normalizedtitle"):
{keys_block}

Find NEW entries that are not in the existing set. Submit AT MOST {max_per_task} entries per task —
choose the most notable / state-of-the-art ones; never pad to hit the limit.

SEARCH STRATEGY (important — recall matters): generative-model naming is diverse, so a single query
misses most of the field. For EACH task, issue SEVERAL varied queries before concluding:
- vary the phrasing: the task name, its keywords, common technique terms (diffusion, GAN,
  autoregressive, transformer, NeRF, gaussian-splatting), and likely model-name patterns;
- use search_arxiv with sort='relevance' and quoted phrases (e.g. 'abs:"text to 3d"') to find the
  established/SOTA work, and sort='recent' to catch the newest;
- cross-check Hugging Face (papers + models), GitHub (topic/stars), and the web.
Prioritise notable papers with code, trending model releases, and proprietary tools studios actually use.

Verify a candidate's primary link with fetch_url if unsure it is real. When done, call
submit_entries exactly once.
"""
