"""Render the item prompt from prompts/item.txt, items.yaml and a retrieved chunk set."""
from __future__ import annotations

from pathlib import Path

from .chunking import Chunk
from .items import PKG, Item, global_rules, na_clause_text, scale_text
from .util import sha256_text

S5_ITEMS = ("A5", "A6", "A7")


def load_template(name: str = "item.txt") -> str:
    return (PKG / "prompts" / name).read_text(encoding="utf-8")


def system_prompt() -> str:
    return load_template("system.txt").strip()


def render_chunks(chunks: list[Chunk]) -> str:
    parts = []
    for c in chunks:
        tag = " agent_visible" if c.s5 else ""
        parts.append(f"### [{c.id}] surface={c.surface}{tag} path={c.path}\n{c.text}")
    return "\n\n".join(parts) if parts else "(no excerpts were retrieved for this item)"


def render_prompt(item: Item, items: dict[str, Item], chunks: list[Chunk]) -> str:
    t = load_template()
    na = na_clause_text(item.id, items)
    if item.module == "agent":
        elements_rule = ('"elements" is three booleans for elements (i), (ii), (iii) of this item, true when the '
                         "excerpts show that element on S1-S3.")
        shape = "[true | false, true | false, true | false]"
    else:
        elements_rule = '"elements" is [] for this item (core items have no element list).'
        shape = "[]"
    if na is None:
        na_text = "None. NA is not allowed for this item: \"not mentioned\" is 0, never NA (G7)."
        na_rule = 'Never answer "NA" for this item.'
    else:
        na_text = na
        na_rule = 'Answer "NA" only if the NA clause applies; "not mentioned" is 0, never NA (G7).'
    s5_rule = s5_field = ""
    if item.id in S5_ITEMS:
        s5_rule = ('- Also record whether the property in element (ii) reaches the agent-visible surface (S5): '
                   '"s5_reach" is true, false, or null when it cannot be told.\n')
        s5_field = ', "s5_reach": true | false | null'
    rep = {
        "{{SCALE}}": scale_text(),
        "{{GLOBAL_RULES}}": global_rules(),
        "{{ITEM_ID}}": item.id,
        "{{ITEM_TITLE}}": item.title,
        "{{ITEM_TEXT}}": item.item_text,
        "{{ANCHORS}}": item.anchors,
        "{{NA_CLAUSE}}": na_text,
        "{{ELEMENTS_RULE}}": elements_rule,
        "{{ELEMENTS_SHAPE}}": shape,
        "{{NA_RULE}}": na_rule,
        "{{S5_RULE}}": s5_rule,
        "{{S5_FIELD}}": s5_field,
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    t = t.replace("{{CHUNKS}}", render_chunks(chunks))  # last, so excerpt text is never re-expanded
    return t


def prompt_hash(prompt: str) -> str:
    return sha256_text(prompt)
