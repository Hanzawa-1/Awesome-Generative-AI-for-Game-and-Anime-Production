import responses

from agent.schema import Entry
from pipeline import thumbnails as th

PNG_BYTES = b"\x89PNG\r\n\x1a\n fake image body"


def _entry(**kw):
    base = dict(
        title="Some Tool",
        area="gen-3d",
        task="image-to-3d",
        kind="proprietary",
        links={"website": "https://example.com/tool"},
        summary="A neutral one to three sentence description used purely for thumbnail tests here.",
    )
    base.update(kw)
    return Entry(**base)


@responses.activate
def test_og_image_url_parses_meta_and_verifies():
    page = '<html><head><meta property="og:image" content="/img/preview.png"></head></html>'
    responses.add(responses.GET, "https://example.com/tool", body=page,
                  content_type="text/html", status=200)
    responses.add(responses.GET, "https://example.com/img/preview.png", body=PNG_BYTES,
                  content_type="image/png", status=200)
    assert th.og_image_url("https://example.com/tool") == "https://example.com/img/preview.png"


@responses.activate
def test_og_image_url_direct_image_content_type():
    responses.add(responses.GET, "https://cdn.example.com/a.png", body=PNG_BYTES,
                  content_type="image/png", status=200)
    assert th.og_image_url("https://cdn.example.com/a.png") == "https://cdn.example.com/a.png"


@responses.activate
def test_og_image_url_upgrades_http_to_https():
    page = '<html><head><meta property="og:image" content="http://example.com/p.jpg"></head></html>'
    responses.add(responses.GET, "https://example.com/tool", body=page,
                  content_type="text/html", status=200)
    responses.add(responses.GET, "https://example.com/p.jpg", body=PNG_BYTES,
                  content_type="image/jpeg", status=200)
    assert th.og_image_url("https://example.com/tool") == "https://example.com/p.jpg"


@responses.activate
def test_og_image_url_rejects_dead_or_non_image_target():
    page = '<html><head><meta property="og:image" content="/gone.png"></head></html>'
    responses.add(responses.GET, "https://example.com/tool", body=page,
                  content_type="text/html", status=200)
    responses.add(responses.GET, "https://example.com/gone.png",
                  body="<html>404</html>", content_type="text/html", status=404)
    assert th.og_image_url("https://example.com/tool") is None


@responses.activate
def test_og_image_url_none_when_page_has_no_meta():
    responses.add(responses.GET, "https://example.com/tool",
                  body="<html><head></head></html>", content_type="text/html", status=200)
    assert th.og_image_url("https://example.com/tool") is None


@responses.activate
def test_resolve_prefers_page_og_image_over_github_card():
    page = '<html><head><meta property="og:image" content="https://example.com/p.jpg"></head></html>'
    responses.add(responses.GET, "https://example.com/tool", body=page,
                  content_type="text/html", status=200)
    responses.add(responses.GET, "https://example.com/p.jpg", body=PNG_BYTES,
                  content_type="image/jpeg", status=200)
    e = _entry(kind="oss", links={"project": "https://example.com/tool",
                                  "github": "https://github.com/acme/tool"})
    assert th.resolve_thumbnail_url(e) == "https://example.com/p.jpg"


@responses.activate
def test_resolve_falls_back_to_github_social_card():
    # No project/website/hf pages at all -> the constructed GitHub card (verified live).
    card = "https://opengraph.githubassets.com/1/acme/tool"
    responses.add(responses.GET, card, body=PNG_BYTES, content_type="image/png", status=200)
    e = _entry(kind="oss", links={"github": "https://github.com/acme/tool"})
    assert th.resolve_thumbnail_url(e) == card


@responses.activate
def test_resolve_none_when_nothing_resolves():
    responses.add(responses.GET, "https://example.com/tool",
                  body="<html><head></head></html>", content_type="text/html", status=200)
    assert th.resolve_thumbnail_url(_entry()) is None
