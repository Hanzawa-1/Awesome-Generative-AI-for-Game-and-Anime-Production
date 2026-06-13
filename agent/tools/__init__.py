"""Discovery tools exposed to the LLM agent + the registry builder.

Each discovery tool module exposes a ``SCHEMA`` (OpenAI function schema) and a callable.
``build_tools(settings)`` returns the ``tools`` array for the chat API plus a name->callable
map. ``submit_entries`` is the terminal tool — it has a schema (so the model can call it) but
no callable here; ``run_agent`` validates its arguments with pydantic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import (
    arxiv_tool,
    civitai_tool,
    ddg_tool,
    fetch_tool,
    github_tool,
    hf_tool,
    pwc_tool,
    semantic_scholar,
)

# Flat, provider-portable schema for the forced structured submission.
SUBMIT_NAME = "submit_entries"
_LINKS = {
    "type": "object",
    "properties": {k: {"type": "string"} for k in ("arxiv", "github", "project", "hf", "paper", "website")},
}
_ENTRY = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "area": {"type": "string", "description": "An area id from the taxonomy."},
        "task": {"type": "string", "description": "A task id within that area."},
        "kind": {"type": "string", "enum": ["oss", "proprietary"]},
        "links": _LINKS,
        "authors": {"type": "array", "items": {"type": "string"}},
        "year": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string", "description": "Neutral 1-3 sentence description in English (20-600 chars)."},
        "summary_ja": {"type": "string", "description": "Japanese translation of the summary (1-3 sentences)."},
        "arxiv_id": {"type": "string", "description": "e.g. 2401.01234 (no version)."},
        "repo": {"type": "string", "description": "owner/name for the primary GitHub repo."},
    },
    "required": ["title", "area", "task", "kind", "links", "summary"],
}
SUBMIT_SCHEMA = {
    "name": SUBMIT_NAME,
    "description": "Submit the final list of NEW catalog entries you discovered this run. Call EXACTLY "
                   "ONCE, at the end. Submitting an empty list is acceptable if nothing new was found.",
    "parameters": {
        "type": "object",
        "properties": {
            "entries": {"type": "array", "items": _ENTRY},
            "notes": {"type": "string", "description": "Optional rationale (not stored)."},
        },
        "required": ["entries"],
    },
}


@dataclass
class ToolSpec:
    name: str
    schema: dict
    fn: Callable


def build_tools(settings) -> tuple[list[dict], dict[str, Callable]]:
    specs = [
        ToolSpec("search_arxiv", arxiv_tool.SCHEMA, arxiv_tool.search),
        ToolSpec("search_web", ddg_tool.SCHEMA, ddg_tool.search),
        ToolSpec("hf_daily_papers", hf_tool.DAILY_SCHEMA, hf_tool.daily_papers),
        ToolSpec("hf_search_models", hf_tool.MODELS_SCHEMA, hf_tool.search_models),
        ToolSpec("search_github", github_tool.SCHEMA, github_tool.search),
        ToolSpec("semantic_scholar", semantic_scholar.SCHEMA, semantic_scholar.search),
        ToolSpec("fetch_url", fetch_tool.SCHEMA, fetch_tool.fetch),
    ]
    if getattr(settings, "enable_civitai", False):
        specs.append(ToolSpec("civitai", civitai_tool.SCHEMA, civitai_tool.search))
    if getattr(settings, "enable_pwc", False):
        specs.append(ToolSpec("pwc_co", pwc_tool.SCHEMA, pwc_tool.search))

    tools_json = [{"type": "function", "function": s.schema} for s in specs]
    tools_json.append({"type": "function", "function": SUBMIT_SCHEMA})
    fn_map = {s.name: s.fn for s in specs}
    return tools_json, fn_map
