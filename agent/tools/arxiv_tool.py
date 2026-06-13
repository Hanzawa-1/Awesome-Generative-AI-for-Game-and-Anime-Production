"""arXiv search tool (keyless; respects the ~3s rate-limit etiquette)."""

from __future__ import annotations

from ._common import clamp

SCHEMA = {
    "name": "search_arxiv",
    "description": "Search arXiv. Quote phrases for precision (e.g. 'abs:\"line art colorization\"') and "
                   "use sort='relevance' to find the most on-topic papers, or 'recent' for the newest. "
                   "Returns title, arxiv_id, authors, year, abstract snippet, and links.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "e.g. 'abs:\"text to 3d\" AND diffusion' or 'cat:cs.CV AND inbetweening'."},
            "max_results": {"type": "integer", "description": "1-20 (default 10)."},
            "sort": {"type": "string", "enum": ["relevance", "recent"],
                     "description": "'relevance' = most on-topic (best for finding known work); 'recent' = newest first (default)."},
        },
        "required": ["query"],
    },
}


def search(query: str, max_results: int = 10, sort: str = "recent", **_) -> list[dict] | dict:
    import arxiv

    n = clamp(max_results, 1, 20, 10)
    crit = (arxiv.SortCriterion.Relevance if str(sort).lower().startswith("rel")
            else arxiv.SortCriterion.SubmittedDate)
    try:
        client = arxiv.Client(page_size=n, delay_seconds=3.0, num_retries=3)
        search_q = arxiv.Search(
            query=query,
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
