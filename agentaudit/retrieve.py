"""Stage 2: deterministic item-targeted retrieval (BM25 plus always-include rules)."""
from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .items import load_queries
from .packet import load_chunks, packet_dir
from .util import read_json, sha256_text, write_json

_TOK = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOK.findall(text.lower())


def retrieve_chunks(chunks: list[Chunk], item_id: str, queries: dict | None = None) -> dict:
    """Return the retrieval record for one item. Pure and deterministic."""
    queries = queries or load_queries()
    params = queries["params"]
    spec = queries["items"][item_id]
    cap = int(params["token_cap"])
    k = int(params["k"])
    always_budget = int(cap * float(params.get("always_fraction", 0.5)))
    qtok = tokenize(spec["query"])
    ordered = sorted(chunks, key=lambda c: c.id)
    if not ordered:
        scores: list[float] = []
    else:
        bm25 = BM25Okapi([tokenize(c.text) for c in ordered])
        scores = [round(float(s), 9) for s in bm25.get_scores(qtok)]
    ranked = sorted(zip(ordered, scores), key=lambda cs: (-cs[1], cs[0].id))
    selected: list[dict] = []
    seen: set[str] = set()
    used = 0

    always = spec.get("always_include") or {}
    if always.get("s5"):
        a_used = 0
        for c, s in ranked:
            if not c.s5 or len(selected) >= k:
                continue
            if a_used + c.tokens > always_budget:
                continue
            selected.append({"id": c.id, "score": s, "reason": "always:s5", "tokens": c.tokens})
            seen.add(c.id)
            a_used += c.tokens
        used = a_used
    for c, s in ranked:
        if len(selected) >= k:
            break
        if c.id in seen or s <= 0:
            continue
        if used + c.tokens > cap:
            continue
        selected.append({"id": c.id, "score": s, "reason": "bm25", "tokens": c.tokens})
        seen.add(c.id)
        used += c.tokens
    for rank, e in enumerate(selected, 1):
        e["rank"] = rank
    return {
        "item": item_id,
        "query": spec["query"],
        "always_include": always,
        "params": {"k": k, "token_cap": cap, "always_fraction": params.get("always_fraction", 0.5),
                   "bm25": "BM25Okapi k1=1.5 b=0.75", "tokenizer": "[a-z0-9]+ lowercase"},
        "n_packet_chunks": len(chunks),
        "total_tokens": used,
        "chunks": selected,
    }


def retrieval_path(run: Path, bench: str, item_id: str) -> Path:
    return Path(run) / "retrieval" / bench / f"{item_id}.json"


def run_retrieval(run: Path, bench: str, items: list[str], queries: dict | None = None) -> dict[str, dict]:
    chunks = load_chunks(run, bench)
    man = read_json(packet_dir(run, bench) / "manifest.json")
    out = {}
    for it in items:
        rec = retrieve_chunks(chunks, it, queries)
        rec["bench"] = bench
        rec["packet_sha256"] = man["packet_sha256"]
        rec["retrieval_sha256"] = sha256_text("|".join(c["id"] for c in rec["chunks"]))
        write_json(retrieval_path(run, bench, it), rec)
        out[it] = rec
    return out


def load_retrieval(run: Path, bench: str, item_id: str) -> dict:
    return read_json(retrieval_path(run, bench, item_id))
