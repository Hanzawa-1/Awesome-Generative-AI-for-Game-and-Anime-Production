"""Layered thumbnail extraction for catalog entries.

For each entry lacking a committed thumbnail, try in order:
  A. arXiv PDF — an embedded raster figure on pages 1-2, else render page 1 to PNG
     (arXiv figures are frequently *vector*, so the render fallback is essential).
  B. Open Graph / Twitter / link-rel image from the project / website / github / hf page,
     then apple-touch-icon as a smaller fallback.
  C. A generated pastel "brand tile" with the entry's initials — so EVERY card has a
     preview (no bland "no preview" gaps).

Network failures never raise; this step is best-effort and must not block the pipeline.
Output PNGs are committed under ``docs/assets/thumbnails/<id>.png``.
"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

from pipeline import db

REPO_ROOT = Path(__file__).resolve().parents[1]
THUMB_DIR = REPO_ROOT / "docs" / "assets" / "thumbnails"
MAX_EDGE = 1280
TIMEOUT = 20

# A browser-like header set — many marketing sites block bare bot user-agents.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
}

# Soft watercolor-pastel pairs for generated brand tiles (microsoft.ai-ish).
PASTELS = [
    ((244, 178, 196), (170, 201, 240)),
    ((248, 216, 155), (170, 225, 197)),
    ((244, 178, 196), (248, 216, 155)),
    ((170, 225, 197), (170, 201, 240)),
    ((216, 191, 240), (248, 216, 155)),
    ((170, 201, 240), (244, 178, 196)),
]


def _http_get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        return r if r.status_code == 200 else None
    except Exception:
        return None


def save_image(data: bytes, out_path: Path, max_edge: int = MAX_EDGE) -> bool:
    """Decode bytes, downscale to ``max_edge`` longest side, write an optimized PNG."""
    try:
        img = Image.open(BytesIO(data)).convert("RGB")
    except Exception:
        return False
    if min(img.size) < 64:  # icons / tracking pixels too small to be a useful preview
        return False
    img.thumbnail((max_edge, max_edge))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return True


def from_arxiv_pdf(arxiv_id: str, out_path: Path) -> bool:
    import fitz  # PyMuPDF; imported lazily so non-thumbnail code paths don't need it

    # Many arXiv PDFs carry Screen/multimedia annotations MuPDF can't build appearance streams
    # for; it prints "MuPDF error: ..." to stderr per annotation but still renders fine. Silence
    # that chatter so build logs stay readable (real failures are still caught below).
    fitz.TOOLS.mupdf_display_errors(False)

    r = _http_get(f"https://arxiv.org/pdf/{arxiv_id}")
    if not r:
        return False
    try:
        doc = fitz.open(stream=r.content, filetype="pdf")
    except Exception:
        return False
    try:
        for page in doc[:2]:
            for img in page.get_images(full=True):
                try:
                    pix = fitz.Pixmap(doc, img[0])
                    if pix.n - pix.alpha >= 4:  # CMYK/other -> RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    if pix.width >= 256 and pix.height >= 128 and save_image(pix.tobytes("png"), out_path):
                        return True
                except Exception:
                    continue
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
        return save_image(pix.tobytes("png"), out_path)
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


def from_og_image(url: str, out_path: Path) -> bool:
    r = _http_get(url)
    if not r:
        return False
    if r.headers.get("Content-Type", "").startswith("image/"):
        return save_image(r.content, out_path)
    try:
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return False
    img_url = _meta_image(soup, r.url)
    if not img_url:
        return False
    ir = _http_get(img_url)
    return bool(ir) and save_image(ir.content, out_path)


def _initials(title: str) -> str:
    toks = re.findall(r"[A-Za-z0-9]+", title)
    if not toks:
        return "?"
    if len(toks) >= 2:
        return (toks[0][0] + toks[1][0]).upper()
    return toks[0][:2].upper()


def generate_brand_tile(entry, out_path: Path, w: int = 640, h: int = 360) -> bool:
    """Deterministic pastel-gradient tile with the entry's initials — always succeeds."""
    idx = int(hashlib.sha1(entry.id.encode()).hexdigest(), 16) % len(PASTELS)
    c0, c1 = PASTELS[idx]
    grad = Image.new("RGB", (1, 2))
    grad.putpixel((0, 0), c0)
    grad.putpixel((0, 1), c1)
    img = grad.resize((w, h), Image.BILINEAR)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=150)
    except TypeError:  # very old Pillow without sizable default
        font = ImageFont.load_default()
    draw.text((w / 2, h / 2), _initials(entry.title), fill=(46, 40, 32), font=font, anchor="mm")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return True


def ensure_thumbnail(entry, thumb_dir: Path = THUMB_DIR) -> str:
    """Produce a thumbnail for ``entry`` (always succeeds); return its repo-relative path."""
    out = thumb_dir / f"{entry.id}.png"
    rel = f"assets/thumbnails/{entry.id}.png"
    if out.exists():
        return rel
    if entry.arxiv_id and from_arxiv_pdf(entry.arxiv_id, out):
        return rel
    for field in ("project", "website", "github", "hf", "paper"):
        u = getattr(entry.links, field)
        if u and from_og_image(str(u), out):
            return rel
    generate_brand_tile(entry, out)
    return rel


def main() -> int:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    entries = db.load_all()
    produced = 0
    updated = 0
    for e in entries:
        rel = f"assets/thumbnails/{e.id}.png"
        if (THUMB_DIR / f"{e.id}.png").exists():
            if e.thumbnail != rel:
                e.thumbnail = rel
                updated += 1
            continue
        e.thumbnail = ensure_thumbnail(e)
        produced += 1
        updated += 1
    if updated:
        db.save_split(entries)
    print(f"thumbnails: produced={produced} updated={updated} total={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
