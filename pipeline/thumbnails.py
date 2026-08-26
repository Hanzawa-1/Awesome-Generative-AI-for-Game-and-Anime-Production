"""Resolve remote thumbnail URLs for catalog entries — no images are generated or stored.

For each entry lacking a resolved URL, try in order:
  A. Open Graph / Twitter / link-rel image from the project / website / hf page. These are
     the images those sites publish specifically for link previews, so referencing them
     from a card is their intended use.
  B. The GitHub social-preview card for the entry's repo, served by
     opengraph.githubassets.com for every public repository.
  C. The paper page's og:image (publisher preview) as a last resort. links.arxiv is
     deliberately skipped — arXiv abs pages serve one generic logo as og:image, which
     would make every paper card identical.

Every candidate is verified to actually respond with an image content-type before being
kept, so the data never records a dead or HTML-serving URL. Entries that resolve to
nothing keep ``thumbnail: null`` and the site renders a pure-CSS pastel initials tile
instead (see gen_catalog.py + extra.css), so every card still has a preview without a
single PNG existing in the repo, the CI cache, or the build.

Resolution is network-bound, so it fans out over a thread pool; failures never raise —
this step is best-effort and must not block the pipeline.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from pipeline import db

TIMEOUT = 15
MAX_WORKERS = 16

# A browser-like header set — many marketing sites block bare bot user-agents.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
}


def _http_get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        return r if r.status_code == 200 else None
    except Exception:
        return None


def _is_image_url(url: str) -> bool:
    """True if ``url`` responds 200 with an image content-type (body is not downloaded)."""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS, stream=True)
        try:
            return r.status_code == 200 and r.headers.get("Content-Type", "").lower().startswith("image/")
        finally:
            r.close()
    except Exception:
        return False


def _meta_image(soup: BeautifulSoup, base: str) -> str | None:
    for prop in ("og:image", "og:image:secure_url", "og:image:url", "twitter:image", "twitter:image:src"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return urljoin(base, tag["content"])
    link = soup.find("link", attrs={"rel": "image_src"})
    if link and link.get("href"):
        return urljoin(base, link["href"])
    # apple-touch-icon is usually 180px+ and served as a static asset (often un-blocked)
    for rel in ("apple-touch-icon", "apple-touch-icon-precomposed"):
        icon = soup.find("link", attrs={"rel": rel})
        if icon and icon.get("href"):
            return urljoin(base, icon["href"])
    return None


def og_image_url(page_url: str) -> str | None:
    """The verified preview-image URL a page advertises, or None."""
    r = _http_get(page_url)
    if not r:
        return None
    if r.headers.get("Content-Type", "").lower().startswith("image/"):
        return page_url  # the link IS an image
    try:
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None
    img_url = _meta_image(soup, r.url)
    if not img_url:
        return None
    # An http:// image would be mixed-content-blocked on the https site — prefer the
    # https variant whenever it actually serves.
    if img_url.startswith("http://"):
        https = "https://" + img_url[len("http://"):]
        if _is_image_url(https):
            return https
    if _is_image_url(img_url):
        return img_url
    return None


def github_card_url(repo: str) -> str:
    """GitHub's social-preview card for ``owner/name`` (the og:image every repo page serves)."""
    return f"https://opengraph.githubassets.com/1/{repo}"


def resolve_thumbnail_url(entry) -> str | None:
    for field in ("project", "website", "hf"):
        u = getattr(entry.links, field)
        if u:
            img = og_image_url(str(u))
            if img:
                return img
    if entry.repo:
        card = github_card_url(entry.repo)
        if _is_image_url(card):  # 404s for deleted/renamed repos
            return card
    if entry.links.paper:
        return og_image_url(str(entry.links.paper))
    return None


def _is_resolved(e) -> bool:
    return bool(e.thumbnail) and e.thumbnail.startswith(("http://", "https://"))


def main() -> int:
    entries = db.load_all()
    # Also picks up legacy local-path values ("assets/thumbnails/...") and re-resolves them.
    todo = [e for e in entries if not _is_resolved(e)]
    resolved = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for e, url in zip(todo, ex.map(resolve_thumbnail_url, todo), strict=True):
            e.thumbnail = url  # None -> field dropped on save; site falls back to the CSS tile
            resolved += bool(url)
    if todo:
        db.save_split(entries)
    print(f"thumbnails: resolved={resolved} unresolved={len(todo) - resolved} "
          f"checked={len(todo)} total={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
