"""Stage 8: per-benchmark score card (markdown and JSON), resolved table, contradiction flags."""
from __future__ import annotations

from pathlib import Path

from .items import ITEM_ORDER, load_items
from .packet import packet_dir
from .util import read_json, write_json

DISCLAIMER = ("A documentary 0 means the property is absent from every surface checked; it never means the "
              "benchmark lacks the practice. Contradiction flags are candidates only until verified against the "
              "benchmark's own documentation and offered for right of reply.")


def build_card(run: Path, bench: str) -> dict:
    items = load_items()
    run = Path(run)
    man = read_json(packet_dir(run, bench) / "manifest.json")
    res = read_json(run / "resolved" / f"{bench}.json")["cells"]
    card: dict = {
        "bench": bench,
        "pin": {"arxiv": man.get("arxiv"), "repo": man.get("repo"), "packet_sha256": man["packet_sha256"],
                "packet_built_utc": man.get("built_utc")},
        "packet": {"files": man["n_files"], "chunks": man["n_chunks"], "chunk_tokens": man["total_chunk_tokens"]},
        "cells": [], "contradiction_candidates": [],
    }
    for iid in ITEM_ORDER:
        if iid not in res:
            continue
        c = res[iid]
        coders = {}
        best_quote = None
        vdir = run / "verified" / bench / iid
        for f in sorted(vdir.glob("*.json")) if vdir.exists() else []:
            v = read_json(f)
            coders[f.stem] = {"raw": v["score_raw"], "effective": v["effective"], "n_verified": v["n_verified"],
                              "flags": v["flags"], "contradicted": v["contradicted"],
                              "contradiction_verified": v["contradiction_verified"]}
            if best_quote is None and f.stem in c["supporters"]:
                for q in v["quotes"]:
                    if q["verified"]:
                        best_quote = {"coder": f.stem, "chunk_id": q["chunk_id"], "text": q["text"]}
                        break
            if v["contradiction_verified"]:
                card["contradiction_candidates"].append({
                    "item": iid, "coder": f.stem,
                    "reported_quotes": [q for q in v["quotes"] if q["verified"]],
                    "contradicting_quotes": [q for q in v["contradiction_quotes"] if q["verified"]],
                    "status": "candidate: verify against the benchmark's own documentation and offer right of reply"})
        card["cells"].append({"item": iid, "title": items[iid].title, "final": c["final"], "status": c["status"],
                              "fallback": c["fallback"], "majority_final": c["majority_final"],
                              "coders": coders, "quote": best_quote})
    n = len(card["cells"])
    fb = sum(1 for c in card["cells"] if c["fallback"])
    card["summary"] = {"cells": n, "fallback_cells": fb, "fallback_share": fb / n if n else None,
                       "mean_final_level": (sum(c["final"] for c in card["cells"] if c["final"] != "NA") /
                                            max(1, sum(1 for c in card["cells"] if c["final"] != "NA"))) if n else None}
    return card


def card_markdown(card: dict) -> str:
    L = [f"# Score card: {card['bench']}", ""]
    pin = card["pin"]
    ax, rp = pin.get("arxiv") or {}, pin.get("repo") or {}
    L.append(f"Pinned: arXiv {ax.get('id', '-')}{ax.get('version', '')} ({ax.get('format', '-')}); repo "
             f"{rp.get('url', '-')} at {rp.get('commit', '-')}; accessed {rp.get('access_date_utc', pin.get('packet_built_utc'))}; "
             f"packet sha256 {pin['packet_sha256'][:16]}.")
    p = card["packet"]
    L.append(f"Packet: {p['files']} files, {p['chunks']} chunks, {p['chunk_tokens']} tokens (4 characters per token).")
    s = card["summary"]
    L.append(f"Cells: {s['cells']}; not established (fallback to 0): {s['fallback_cells']}.")
    L += ["", DISCLAIMER, "", "| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |", "|---|---|---|---|---|---|"]
    for c in card["cells"]:
        cod = "; ".join(f"{k} {v['raw']}/{v['effective']}" for k, v in c["coders"].items())
        q = c["quote"]
        ev = f"[{q['chunk_id']}] \"{q['text']}\"" if q else ""
        L.append(f"| {c['item']} {c['title']} | {c['final']} | {c['status']} | {c['majority_final']} | {cod} | {ev} |")
    L += ["", "## Contradiction flags (candidates only)"]
    if not card["contradiction_candidates"]:
        L.append("None with a verified contradicting quote.")
    for k in card["contradiction_candidates"]:
        L.append(f"- {k['item']} ({k['coder']}): " + " / ".join(f"[{q['chunk_id']}] \"{q['text']}\""
                                                                for q in k["reported_quotes"] + k["contradicting_quotes"]))
    return "\n".join(L) + "\n"


def run_report(run: Path, benches: list[str]) -> list[Path]:
    out = []
    for b in benches:
        card = build_card(run, b)
        write_json(Path(run) / "report" / f"{b}.json", card)
        md = Path(run) / "report" / f"{b}.md"
        md.write_text(card_markdown(card), encoding="utf-8")
        out.append(md)
    return out
