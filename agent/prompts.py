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

SEARCH STRATEGY — work like a human researcher (WEB-FIRST: the web is semantic, arXiv search is
keyword-brittle, so don't query arXiv blind):
1. DISCOVER with search_web first — issue 2-3 varied phrasings per task (e.g. the task name + "open
   source" / "github" / "state of the art" / "generative model" / "anime" or "game"). Open the most
   promising results with fetch_url (awesome-lists, project pages, leaderboards, roundups) and harvest
   the model NAMES and their real arXiv / GitHub / Hugging Face links.
2. CONFIRM & ENRICH using the names you found: search_arxiv (sort='relevance', quoted phrase like
   'abs:"talking head"') for the paper + id, search_github for the repo + stars, hf for model pages,
   semantic_scholar to resolve arXiv ids. For image / anime / illustration / checkpoint tasks, also
   check civitai for community models and LoRAs.
3. ALSO find PROPRIETARY / commercial tools that game/anime studios use for this task (these populate
   the catalog's "Proprietary / Industry Tools" section). Web-search phrasings like
   '<task> commercial tool', 'best <task> app / SaaS / API', '<task> studio software'. Submit each as
   kind="proprietary" with a "website" link (no arXiv/repo needed).
4. If web search is sparse or rate-limited, fall back to querying arXiv / HF / GitHub directly.

Then call submit_entries ONCE with every new, valid entry. For each: the correct area/task id, a neutral
English summary + a Japanese summary_ja, and 2-4 short lowercase tags. Open-source entries (kind="oss")
need an arxiv_id OR a github repo; proprietary tools (kind="proprietary") need a website link.
A few good entries beats none — never return an empty list if you found real work.
"""
