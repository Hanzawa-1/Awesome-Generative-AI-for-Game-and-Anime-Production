import json

from agent import run_agent as ra
from agent.config import load_settings
from agent.tools import build_tools


def test_weekly_focus_is_deterministic_and_in_range():
    areas = ["a", "b", "c", "d", "e", "f", "g", "h"]
    f1 = ra.weekly_focus(areas, n=3, week=10)
    f2 = ra.weekly_focus(areas, n=3, week=10)
    assert f1 == f2
    assert len(f1) == 3
    assert all(x in areas for x in f1)
    # different weeks generally shift the window
    assert ra.weekly_focus(areas, n=3, week=11) != f1


def test_parse_submission_salvages_valid_entries():
    payload = json.dumps({
        "entries": [
            {  # valid oss
                "title": "DreamFusion", "area": "gen-3d", "task": "text-to-3d", "kind": "oss",
                "links": {"arxiv": "https://arxiv.org/abs/2209.14988"},
                "summary": "A neutral description of the work that is comfortably long enough to pass.",
            },
            {  # invalid: bad area/task
                "title": "Bad", "area": "nope", "task": "nope", "kind": "oss",
                "links": {"arxiv": "https://arxiv.org/abs/2209.14988"},
                "summary": "Another sufficiently long neutral description string for testing here.",
            },
            {  # invalid: oss with no paper/repo
                "title": "AlsoBad", "area": "gen-3d", "task": "text-to-3d", "kind": "oss",
                "links": {"project": "https://example.com/"},
                "summary": "Yet another sufficiently long neutral description string for testing here.",
            },
        ]
    })
    valid, invalid = ra._parse_submission(payload)
    assert len(valid) == 1
    assert invalid == 2


def test_parse_submission_handles_garbage():
    assert ra._parse_submission("not json") == ([], 0)


def test_verify_and_stage_dedupes_and_caps(monkeypatch):
    monkeypatch.setattr(ra, "_links_ok", lambda e: True)
    from agent.schema import Entry

    def mk(title):
        return Entry(title=title, area="gen-3d", task="text-to-3d", kind="oss",
                     links={"github": f"https://github.com/x/{title.lower()}"},
                     summary="A neutral description long enough to satisfy the schema validator here.")

    a, b, c = mk("Alpha"), mk("Beta"), mk("Gamma")
    existing = {a.key}
    staged = ra.verify_and_stage([a, b, c], existing, max_new=1, max_per_task=5)
    assert len(staged) == 1  # 'a' is a dup; capped at 1 -> only 'b'
    assert staged[0].title == "Beta"


def test_verify_and_stage_caps_per_task(monkeypatch):
    monkeypatch.setattr(ra, "_links_ok", lambda e: True)
    from agent.schema import Entry

    def mk(title):
        return Entry(title=title, area="gen-3d", task="text-to-3d", kind="oss",
                     links={"github": f"https://github.com/x/{title.lower()}"},
                     summary="A neutral description long enough to satisfy the schema validator here.")

    entries = [mk(t) for t in ("Cand1", "Cand2", "Cand3", "Cand4")]
    staged = ra.verify_and_stage(entries, set(), max_new=100, max_per_task=2)
    assert len(staged) == 2  # same task -> capped at 2


def test_verify_and_stage_drops_dead_links(monkeypatch):
    monkeypatch.setattr(ra, "_links_ok", lambda e: False)
    from agent.schema import Entry

    e = Entry(title="Ghost", area="gen-3d", task="text-to-3d", kind="oss",
              links={"github": "https://github.com/x/ghost"},
              summary="A neutral description long enough to satisfy the schema validator here.")
    assert ra.verify_and_stage([e], set(), max_new=10, max_per_task=5) == []


def test_build_tools_respects_optional_flags():
    settings = load_settings()
    settings.enable_civitai = True
    settings.enable_pwc = False
    tools_json, fn_map = build_tools(settings)
    names = {t["function"]["name"] for t in tools_json}
    assert "search_arxiv" in names and "submit_entries" in names
    assert "civitai" in names
    assert "pwc_co" not in names
    assert "submit_entries" not in fn_map  # terminal tool has no callable
