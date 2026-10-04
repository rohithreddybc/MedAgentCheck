"""Item definitions (items.yaml), retrieval queries (queries.yaml), perturbation texts."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PKG = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Item:
    id: str
    module: str
    source: str
    construct: str | None
    title: str
    item_text: str
    anchors: str
    na_clause: str | None
    n_elements: int

    @property
    def na_allowed(self) -> bool:
        return self.na_clause is not None


@lru_cache(maxsize=None)
def _items_doc(path: str | None = None) -> dict:
    p = Path(path) if path else PKG / "items.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_items(path: str | None = None) -> dict[str, Item]:
    doc = _items_doc(path)
    out = {}
    for d in doc["items"]:
        out[d["id"]] = Item(d["id"], d["module"], d["source"], d.get("construct"), d["title"],
                            d["item_text"], d["anchors"], d.get("na_clause"), d.get("n_elements", 0))
    return out


ITEM_ORDER = [f"C{i}" for i in range(1, 15)] + [f"A{i}" for i in range(1, 12)]


def global_rules(path: str | None = None) -> str:
    return _items_doc(path)["global_rules"]


def scale_text(path: str | None = None) -> str:
    return _items_doc(path)["scale"]


@lru_cache(maxsize=None)
def load_queries(path: str | None = None) -> dict:
    p = Path(path) if path else PKG / "queries.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_perturbation_specs(path: str | None = None) -> dict:
    p = Path(path) if path else PKG / "perturbations.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))["items"]


def na_clause_text(item_id: str, items: dict[str, Item]) -> str | None:
    """NA clause for the prompt. 'NA as for A5' also carries A5's clause."""
    it = items[item_id]
    if it.na_clause is None:
        return None
    import re

    m = re.match(r"^NA as for (A\d+)\.?$", it.na_clause)
    if m and m.group(1) in items and items[m.group(1)].na_clause:
        return f"{it.na_clause} ({m.group(1)}: {items[m.group(1)].na_clause})"
    return it.na_clause


def parse_item_list(spec: str | None) -> list[str]:
    if not spec or spec.lower() == "all":
        return list(ITEM_ORDER)
    ids = [s.strip().upper() for s in spec.split(",") if s.strip()]
    bad = [i for i in ids if i not in ITEM_ORDER]
    if bad:
        raise ValueError(f"unknown items: {bad}")
    return ids
