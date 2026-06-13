"""arXiv search tool (keyless; respects the ~3s rate-limit etiquette)."""

from __future__ import annotations

from ._common import clamp

# Relevant arXiv categories for game/anime generative AI — scopes searches to cut
# cross-domain noise (physics/math/bio "color"/"motion" papers, etc.).
DEFAULT_CATS = ["cs.CV", "cs.GR", "cs.LG", "cs.AI", "cs.MM", "cs.SD", "cs.CL", "cs.HC", "eess.AS", "eess.IV"]

SCHEMA = {
    "name": "search_arxiv",
    "description": "Search arXiv (auto-scoped to relevant CS/EESS categories). Quote phrases for precision "
                   "(e.g. 'abs:\"line art colorization\"'); use sort='relevance' to find established/SOTA work "
                   "or 'recent' for the newest. Returns title, arxiv_id, authors, year, abstract, links.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "e.g. 'abs:\"text to 3d\" AND diffusion'."},
            "max_results": {"type": "integer", "description": "1-20 (default 10)."},
            "sort": {"type": "string", "enum": ["relevance", "recent"],
                     "description": "'relevance' (best for known work) or 'recent' (newest, default)."},
            "categories": {"type": "array", "items": {"type": "string"},
                           "description": "Override the category scope, e.g. ['cs.SD','eess.AS'] for audio, "
                                          "['cs.CV','cs.GR'] for 3D. Omit to use the default CS/EESS set."},
        },
        "required": ["query"],
    },
}


def _scope(query: str, categories) -> str:
    if "cat:" in query.lower():  # LLM already scoped it
        return query
    if isinstance(categories, str):
        categories = [c.strip() for c in categories.split(",") if c.strip()]
    cats = categories or DEFAULT_CATS
    cat_clause = " OR ".join(f"cat:{c}" for c in cats)
    return f"({query}) AND ({cat_clause})"


def search(query: str, max_results: int = 10, sort: str = "recent", categories=None, **_) -> list[dict] | dict:
    import arxiv

    n = clamp(max_results, 1, 20, 10)
    crit = (arxiv.SortCriterion.Relevance if str(sort).lower().startswith("rel")
            else arxiv.SortCriterion.SubmittedDate)
    try:
        client = arxiv.Client(page_size=n, delay_seconds=3.0, num_retries=3)
        search_q = arxiv.Search(
            query=_scope(query, categories),
            max_results=n,
            sort_by=crit,
            sort_order=arxiv.SortOrder.Descending,
        )
        out = []
        for r in client.results(search_q):
            out.append(
                {
                    "title": r.title,
                    "arxiv_id": r.get_short_id().split("v")[0],
                    "authors": [a.name for a in r.authors][:8],
                    "year": r.published.year if r.published else None,
                    "summary": (r.summary or "").replace("\n", " ")[:500],
                    "abs_url": r.entry_id,
                    "pdf_url": r.pdf_url,
                }
            )
        return out
    except Exception as e:  # noqa: BLE001 - tools must never crash the loop
        return {"error": f"arxiv search failed: {e}"[:300]}
