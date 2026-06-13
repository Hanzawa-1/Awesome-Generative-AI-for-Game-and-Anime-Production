"""Pydantic schema for catalog entries + deterministic id / dedup helpers.

The agent may *propose* entries, but the deterministic pipeline recomputes the stable
``id`` and ``dedup_key`` here and validates ``area``/``task`` against the taxonomy — the
LLM's claims are never trusted as-is.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from agent.taxonomy import is_valid_area_task

Kind = Literal["oss", "proprietary"]
Source = Literal["agent", "seed", "manual"]

ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{2,80}$")
_ARXIV_RE = re.compile(r"(\d{4}\.\d{4,5})")
_GITHUB_RE = re.compile(r"github\.com[:/]+([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)


# --------------------------------------------------------------------------- helpers
def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)[:60].strip("-")
    return s or "entry"


def normalized_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def normalize_arxiv_id(value: object) -> str | None:
    if not value:
        return None
    m = _ARXIV_RE.search(str(value))
    return m.group(1) if m else None


def normalize_repo(value: object) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    m = _GITHUB_RE.search(s)
    if m:
        owner, name = m.group(1), m.group(2)
    elif "/" in s and "://" not in s:
        parts = [p for p in s.split("/") if p]
        if len(parts) < 2:
            return None
        owner, name = parts[0], parts[1]
    else:
        return None
    name = re.sub(r"\.git$", "", name)
    return f"{owner}/{name}".lower()


def dedup_key(arxiv_id: str | None, repo: str | None, title: str) -> str:
    """Strong dedup key. Precedence: arxiv_id > repo > normalized title."""
    if arxiv_id:
        return f"arxiv:{arxiv_id}"
    if repo:
        return f"repo:{repo.lower()}"
    return f"title:{normalized_title(title)}"


def derive_id(title: str, arxiv_id: str | None, repo: str | None) -> str:
    """Human-readable, collision-resistant stable id: ``<title-slug>-<6 hex of dedup_key>``."""
    h = hashlib.sha1(dedup_key(arxiv_id, repo, title).encode("utf-8")).hexdigest()[:6]
    return f"{slugify(title)}-{h}"


# --------------------------------------------------------------------------- models
class Links(BaseModel):
    arxiv: HttpUrl | None = None
    github: HttpUrl | None = None
    project: HttpUrl | None = None
    hf: HttpUrl | None = None
    paper: HttpUrl | None = None
    website: HttpUrl | None = None

    @model_validator(mode="after")
    def at_least_one(self):
        if not any(getattr(self, f) for f in ("arxiv", "github", "project", "hf", "paper", "website")):
            raise ValueError("entry must have at least one link")
        return self

    # Ordered preference for the card's primary link.
    def primary(self) -> str | None:
        for f in ("project", "github", "arxiv", "hf", "paper", "website"):
            v = getattr(self, f)
            if v:
                return str(v)
        return None


class Entry(BaseModel):
    id: str = ""  # canonicalized in the validator below; merge recomputes for new entries
    title: str = Field(..., min_length=3, max_length=300)
    area: str
    task: str
    kind: Kind = "oss"
    links: Links
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(None, ge=1990, le=2100)
    tags: list[str] = Field(default_factory=list)
    summary: str = Field(..., min_length=20, max_length=600)
    summary_ja: str | None = Field(None, max_length=800)  # Japanese summary (optional)
    thumbnail: str | None = None
    date_added: _dt.date = Field(default_factory=_dt.date.today)
    source: Source = "agent"
    arxiv_id: str | None = None
    repo: str | None = None

    @field_validator("tags", mode="after")
    @classmethod
    def _norm_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t and t.strip()})

    @field_validator("authors", mode="after")
    @classmethod
    def _clean_authors(cls, v: list[str]) -> list[str]:
        return [a.strip() for a in v if a and a.strip()]

    @field_validator("arxiv_id", mode="before")
    @classmethod
    def _norm_arxiv(cls, v):
        return normalize_arxiv_id(v)

    @field_validator("repo", mode="before")
    @classmethod
    def _norm_repo(cls, v):
        return normalize_repo(v)

    @model_validator(mode="after")
    def _backfill_and_validate(self):
        # Backfill dedup keys from links when the LLM didn't set them explicitly.
        if not self.arxiv_id and self.links.arxiv:
            self.arxiv_id = normalize_arxiv_id(self.links.arxiv)
        if not self.repo and self.links.github:
            self.repo = normalize_repo(self.links.github)
        # OSS entries must be anchored to a paper or a repo.
        if self.kind == "oss" and not (self.arxiv_id or self.repo):
            raise ValueError("oss entry requires an arxiv_id or a github repo")
        # Taxonomy must be valid.
        if not is_valid_area_task(self.area, self.task):
            raise ValueError(f"invalid area/task: {self.area}/{self.task}")
        # Canonicalize id (keep a valid provided id; otherwise derive).
        if not ID_RE.match(self.id or ""):
            self.id = derive_id(self.title, self.arxiv_id, self.repo)
        return self

    @property
    def key(self) -> str:
        return dedup_key(self.arxiv_id, self.repo, self.title)

    def canonical_id(self) -> str:
        return derive_id(self.title, self.arxiv_id, self.repo)


class SubmitEntries(BaseModel):
    """The ONLY structured output the LLM is allowed to emit (function-call args)."""

    entries: list[Entry] = Field(default_factory=list, max_length=40)
    notes: str | None = None
