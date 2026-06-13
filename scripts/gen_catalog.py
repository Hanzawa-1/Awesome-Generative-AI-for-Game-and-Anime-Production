"""Pre-build generator: taxonomy.yml + data/*.yml -> real bilingual catalog pages + nav.

Writes actual files under ``docs/`` (not via mkdocs-gen-files) because mkdocs-static-i18n
handles on-disk suffix files (``.ja.md``) reliably, whereas it chokes on plugin-generated
virtual files. Run this BEFORE ``mkdocs build`` / ``mkdocs serve`` (the Makefile, tasks.ps1,
and CI all do).

For each locale it emits, under docs/:
  * catalog/index{sfx}.md
  * catalog/<area>/index{sfx}.md
  * catalog/<area>/<task>{sfx}.md
  * SUMMARY{sfx}.md            (consumed by mkdocs-literate-nav, localized by i18n)
where sfx is "" (en) or ".ja" (ja).
"""

from __future__ import annotations

import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.taxonomy import load_taxonomy  # noqa: E402
from pipeline import db  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CATALOG = DOCS / "catalog"
PLACEHOLDER = "assets/thumbnails/placeholder.svg"

LOCALES = (("en", ""), ("ja", ".ja"))

UI = {
    "en": {
        "catalog": "Catalog",
        "catalog_intro": "Generative-AI tasks for game & anime production, grouped by area. Each task "
                         "lists open-source models & papers plus proprietary tools in active use.",
        "oss": "Open Source",
        "prop": "Proprietary / Industry Tools",
        "home": "Home",
        "about": "About",
        "stub": "No entries yet — contributions welcome. The weekly research agent will populate this "
                "task as it finds work.",
        "entries": lambda n: f"{n} entr{'y' if n == 1 else 'ies'}",
        "area_meta": lambda e, t: f"{e} entries · {t} tasks",
        "new": "NEW",
        "ai": "Discovered by AI",
        "getstarted": "Get started",
        "links": {"project": "Project", "github": "GitHub", "arxiv": "arXiv",
                  "hf": "Hugging Face", "paper": "Paper", "website": "Website"},
    },
    "ja": {
        "catalog": "カタログ",
        "catalog_intro": "ゲーム・アニメ制作向けの生成AIタスクを領域別に整理。各タスクにはオープンソースの"
                         "モデル・論文と、実際に使われている商用ツールを掲載しています。",
        "oss": "オープンソース",
        "prop": "商用・業界ツール",
        "home": "ホーム",
        "about": "概要",
        "stub": "まだ項目がありません。貢献を歓迎します。週次のリサーチエージェントが見つけ次第追加します。",
        "entries": lambda n: f"{n} 件",
        "area_meta": lambda e, t: f"{e} 件 · {t} タスク",
        "new": "新着",
        "ai": "AIが発見",
        "getstarted": "はじめに",
        "links": {"project": "プロジェクト", "github": "GitHub", "arxiv": "arXiv",
                  "hf": "Hugging Face", "paper": "論文", "website": "公式サイト"},
    },
}


def _rel_prefix(page_path: str) -> str:
    return "../" * page_path.count("/")


def _esc(text: str) -> str:
    return text.replace("[", r"\[").replace("]", r"\]")


def _summary(e, loc: str) -> str:
    if loc == "ja" and getattr(e, "summary_ja", None):
        return e.summary_ja
    return e.summary


def _link_row(links, loc: str) -> list[str]:
    # Show EVERY source link present (do not hide the primary), so each card
    # consistently surfaces its arXiv / GitHub / project / HF / paper / website links.
    bits = []
    for field, label in UI[loc]["links"].items():
        url = getattr(links, field)
        if url:
            bits.append(f"[{label}]({url})")
    return bits


def _thumb(e) -> str:
    """Prefer the entry's thumbnail field; else an on-disk PNG by id; else the placeholder.
    The on-disk fallback keeps previews working even if a re-seed cleared the thumbnail field."""
    if e.thumbnail:
        return e.thumbnail
    if (DOCS / "assets" / "thumbnails" / f"{e.id}.png").exists():
        return f"assets/thumbnails/{e.id}.png"
    return PLACEHOLDER


def _card(e, prefix: str, loc: str, new_ids: set[str]) -> str:
    thumb = _thumb(e)
    primary = e.links.primary() or "#"
    lines = [f"-   [![]({prefix}{thumb}){{ .card-thumb }}]({primary})", ""]
    # Badges live in the title paragraph but CSS pins them to fixed card corners, so their
    # position is identical on every card regardless of title length.
    title = f"**[{_esc(e.title)}]({primary})**"
    if e.id in new_ids:
        title += f' <span class="card-new">{UI[loc]["new"]}</span>'
    if e.source == "agent":  # human-added (seed/manual) entries carry no badge
        title += f' <span class="card-src">{UI[loc]["ai"]}</span>'
    lines.append(f"    {title}")
    # Year in the link/accent colour, bold. Author names are intentionally not shown.
    if e.year:
        lines += ["", f'    <span class="card-year">{e.year}</span>']
    # Tag the summary so CSS can absorb free space below it (margin-bottom:auto),
    # pushing the tags + links to the card bottom WITHOUT adding a wrapper element
    # (a nested block element would break Material's grid-cards <ul>).
    lines += ["", f"    {_summary(e, loc)}", "    {: .card-summary }"]
    if e.tags:
        lines += ["", "    " + " ".join(f"`{t}`" for t in e.tags)]
    row = _link_row(e.links, loc)
    if row:
        lines += ["", "    " + " · ".join(row)]
    lines.append("")
    return "\n".join(lines)


def _grid(entries, prefix: str, loc: str, new_ids: set[str]) -> str:
    if not entries:
        return ""
    inner = "\n".join(_card(e, prefix, loc, new_ids) for e in entries)
    return f'<div class="grid cards" markdown>\n\n{inner}\n</div>\n'


def _newest_first(entries):
    return sorted(entries, key=lambda e: (-(e.year or 0), e.title.lower()))


def _write(relpath: str, text: str) -> None:
    p = DOCS / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def build_locale(loc: str, sfx: str, tax, by_area, by_task, new_ids: set[str]) -> None:
    ui = UI[loc]
    summary = [f"- [{ui['home']}](index.md)", f"- [{ui['catalog']}](catalog/index.md)"]

    # catalog overview
    out = [f"# {ui['catalog']}\n", ui["catalog_intro"] + "\n", '<div class="grid cards" markdown>\n']
    for area in tax.areas:
        n = len(by_area.get(area.id, []))
        out.append(f"-   **[{area.display_name(loc)}]({area.id}/index.md)**\n\n"
                   f"    {area.display_description(loc) or ''}\n\n"
                   f"    <span class=\"card-meta\">{ui['area_meta'](n, len(area.tasks))}</span>\n")
    out.append("</div>\n")
    _write(f"catalog/index{sfx}.md", "\n".join(out))

    for area in tax.areas:
        summary.append(f"    - [{area.display_name(loc)}](catalog/{area.id}/index.md)")
        # area index
        out = [f"# {area.display_name(loc)}\n"]
        if area.display_description(loc):
            out.append(f"{area.display_description(loc)}\n")
        out.append('<div class="grid cards" markdown>\n')
        for t in area.tasks:
            n = len(by_task.get((area.id, t.id), []))
            out.append(f"-   **[{t.display_name(loc)}]({t.id}.md)**\n\n"
                       f"    <span class=\"card-meta\">{ui['entries'](n)}</span>\n")
        out.append("</div>\n")
        _write(f"catalog/{area.id}/index{sfx}.md", "\n".join(out))

        for t in area.tasks:
            summary.append(f"        - [{t.display_name(loc)}](catalog/{area.id}/{t.id}.md)")
            page = f"catalog/{area.id}/{t.id}{sfx}.md"
            prefix = _rel_prefix(f"catalog/{area.id}/{t.id}.md")
            items = by_task.get((area.id, t.id), [])
            oss = _newest_first([e for e in items if e.kind == "oss"])
            prop = _newest_first([e for e in items if e.kind == "proprietary"])
            out = [f"# {t.display_name(loc)}\n", f"<small>{area.display_name(loc)}</small>\n"]
            if not items:
                out.append(f"> {ui['stub']}\n")
            else:
                if oss:
                    out += [f"## {ui['oss']}\n", _grid(oss, prefix, loc, new_ids)]
                if prop:
                    out += [f"## {ui['prop']}\n", _grid(prop, prefix, loc, new_ids)]
            _write(page, "\n".join(out))

    summary.append(f"- [{ui['about']}](about.md)")
    summary.append(f"- [{ui['getstarted']}](get-started.md)")
    _write(f"SUMMARY{sfx}.md", "\n".join(summary) + "\n")


def _compute_new_ids(entries) -> set[str]:
    """Flag entries from the most recent update batch (within 10 days of the newest
    date_added). Returns empty when all entries share one date (the day-one seed),
    so the initial catalog isn't blanketed with NEW badges.

    Preview: set CATALOG_PREVIEW_NEW=<n> to force-flag the n most-recently-dated entries
    (purely for previewing the badge locally; does not change any data)."""
    preview = os.environ.get("CATALOG_PREVIEW_NEW")
    if preview and preview.isdigit() and int(preview) > 0:
        ordered = sorted(entries, key=lambda e: (e.date_added, e.id), reverse=True)
        return {e.id for e in ordered[: int(preview)]}

    dates = {e.date_added for e in entries}
    if len(dates) <= 1:
        return set()
    latest = max(dates)
    return {e.id for e in entries if (latest - e.date_added).days <= 10}


def main() -> int:
    if CATALOG.exists():
        shutil.rmtree(CATALOG)
    tax = load_taxonomy()
    entries = db.load_all()
    new_ids = _compute_new_ids(entries)
    by_task: dict[tuple[str, str], list] = defaultdict(list)
    by_area: dict[str, list] = defaultdict(list)
    for e in entries:
        by_task[(e.area, e.task)].append(e)
        by_area[e.area].append(e)
    for loc, sfx in LOCALES:
        build_locale(loc, sfx, tax, by_area, by_task, new_ids)
    print(f"generated catalog for {len(LOCALES)} locales "
          f"({len(entries)} entries, {len(new_ids)} flagged new)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
