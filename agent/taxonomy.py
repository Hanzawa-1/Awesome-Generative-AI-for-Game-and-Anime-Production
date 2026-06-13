"""Load and query the Area -> Task taxonomy (``taxonomy.yml``).

Single source of truth for the catalog structure. Schema validation, the generated nav,
and every catalog page derive from what this module returns.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _taxonomy_path() -> Path:
    return Path(os.environ.get("TAXONOMY_PATH") or (REPO_ROOT / "taxonomy.yml"))


class Task:
    __slots__ = ("area_id", "id", "name", "name_ja", "desc", "keywords")

    def __init__(self, area_id: str, d: dict):
        self.area_id = area_id
        self.id = d["id"]
        self.name = d["name"]
        self.name_ja = d.get("name_ja") or d["name"]
        self.desc = d.get("desc") or d.get("description")
        self.keywords = list(d.get("keywords") or [])

    def display_name(self, locale: str = "en") -> str:
        return self.name_ja if locale == "ja" else self.name

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Task({self.area_id}/{self.id})"


class Area:
    __slots__ = ("id", "name", "name_ja", "description", "description_ja", "tasks")

    def __init__(self, d: dict):
        self.id = d["id"]
        self.name = d["name"]
        self.name_ja = d.get("name_ja") or d["name"]
        self.description = d.get("description")
        self.description_ja = d.get("description_ja") or d.get("description")
        self.tasks = [Task(self.id, t) for t in (d.get("tasks") or [])]

    @property
    def task_ids(self) -> list[str]:
        return [t.id for t in self.tasks]

    def display_name(self, locale: str = "en") -> str:
        return self.name_ja if locale == "ja" else self.name

    def display_description(self, locale: str = "en") -> str | None:
        return self.description_ja if locale == "ja" else self.description

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Area({self.id}, {len(self.tasks)} tasks)"


class Taxonomy:
    def __init__(self, areas: list[Area]):
        self.areas = areas
        self._area_by_id: dict[str, Area] = {}
        self._pairs: set[tuple[str, str]] = set()
        seen_tasks: set[str] = set()
        for a in areas:
            if a.id in self._area_by_id:
                raise ValueError(f"duplicate area id: {a.id}")
            self._area_by_id[a.id] = a
            for t in a.tasks:
                if t.id in seen_tasks:
                    raise ValueError(f"duplicate task id: {t.id}")
                seen_tasks.add(t.id)
                self._pairs.add((a.id, t.id))

    # --- queries ---
    def area(self, area_id: str) -> Area | None:
        return self._area_by_id.get(area_id)

    def task(self, area_id: str, task_id: str) -> Task | None:
        a = self._area_by_id.get(area_id)
        if not a:
            return None
        return next((t for t in a.tasks if t.id == task_id), None)

    def is_valid(self, area_id: str, task_id: str) -> bool:
        return (area_id, task_id) in self._pairs

    def area_ids(self) -> list[str]:
        return [a.id for a in self.areas]

    def all_pairs(self) -> list[tuple[str, str]]:
        return sorted(self._pairs)

    def __len__(self) -> int:
        return len(self._pairs)


def build_taxonomy(raw: dict) -> Taxonomy:
    """Build a Taxonomy from an already-parsed mapping (used in tests)."""
    return Taxonomy([Area(a) for a in raw["areas"]])


@lru_cache(maxsize=1)
def load_taxonomy() -> Taxonomy:
    """Load the project taxonomy (cached). Call ``load_taxonomy.cache_clear()`` to force a reload."""
    raw = yaml.safe_load(_taxonomy_path().read_text(encoding="utf-8"))
    return build_taxonomy(raw)


def is_valid_area_task(area_id: str, task_id: str) -> bool:
    """True iff ``area_id``/``task_id`` is a valid pair in the loaded taxonomy."""
    return load_taxonomy().is_valid(area_id, task_id)
