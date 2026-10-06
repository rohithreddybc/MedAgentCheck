"""Per-benchmark score cards (markdown) and one long CSV, generated from the released results/ folder.

Post-freeze script; the frozen scorer's own `agentaudit report` needs the evidence packets, which are not redistributed.
This script uses only results/resolved/*.json (resolved cells, coder votes, verified quotes, flags) and
results/packet_manifests/*.json (hashes and counts), so it runs on a clean checkout:

    python analysis/make_scorecards.py            # writes results/scorecards/

Output: results/scorecards/<bench>.md, results/scorecards/scorecards.csv (one row per benchmark and item) and
results/scorecards/benchmarks.csv (one row per benchmark).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402

RES = ROOT / "results"
OUT = RES / "scorecards"
DISCLAIMER = ("A documentary 0 means the property is absent from every surface checked; it never means the "
              "benchmark lacks the practice. Contradiction flags are candidates only until verified against the "
              "benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied "
              "from the cited source for verification; they remain the work of its authors.")


def load(bench: str) -> tuple[dict, dict]:
    res = json.loads((RES / "resolved" / f"{bench}.json").read_text(encoding="utf-8"))
    pm = RES / "packet_manifests" / f"{bench}.json"
    man = json.loads(pm.read_text(encoding="utf-8")) if pm.exists() else {}
    return res, man


def best_quote(cell: dict) -> dict | None:
    for coder in cell.get("supporters", []):
        v = cell["coders"].get(coder)
        for q in (v or {}).get("quotes", []):
            if q.get("verified"):
                return {"coder": coder, **q}
    return None


def main() -> None:
    items = load_items()
    OUT.mkdir(parents=True, exist_ok=True)
    benches = sorted(p.stem for p in (RES / "resolved").glob("*.json") if p.stem != "summary")
    long_rows, bench_rows = [], []
    for b in benches:
        res, man = load(b)
        cells = res["cells"]
        L = [f"# Score card: {b}", ""]
        ax, rp = man.get("arxiv") or {}, man.get("repo") or {}
        L.append(f"Pinned: arXiv {ax.get('id', '-')}{ax.get('version', '')}; repo {rp.get('url', '-')} at "
                 f"{rp.get('commit', '-')}; accessed {rp.get('access_date_utc', man.get('built_utc', '-'))}; "
                 f"packet sha256 {str(man.get('packet_sha256', '-'))[:16]}.")
        if not cells:
            L += ["", "No resolved cells: this benchmark was not scored (its evidence packet exceeds the coders' "
                      "frozen context cap after the drop rule; see results/coder_responses/base/).", ""]
            (OUT / f"{b}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
            bench_rows.append({"bench": b, "cells": 0})
            continue
        fb = sum(1 for c in cells.values() if c["fallback"])
        finals = [c["final"] for c in cells.values() if c["final"] != "NA"]
        mean = sum(finals) / len(finals) if finals else ""
        L.append(f"Cells: {len(cells)}; not established (fallback to 0): {fb}; mean final level: "
                 f"{mean:.2f}." if finals else f"Cells: {len(cells)}.")
        L += ["", DISCLAIMER, "",
              "| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |", "|---|---|---|---|---|---|"]
        flags = []
        for iid in ITEM_ORDER:
            if iid not in cells:
                continue
            c = cells[iid]
            cod = "; ".join(f"{k} {v['score_raw']}/{v['effective']}" for k, v in c["coders"].items())
            q = best_quote(c)
            ev = f"[{q['chunk_id']}] \"{q['text']}\"".replace("|", "/") if q else ""
            L.append(f"| {iid} {items[iid].title} | {c['final']} | {c['status']} | {c['majority_final']} | {cod} | {ev} |")
            for k, v in c["coders"].items():
                if v.get("contradiction_verified"):
                    flags.append((iid, k, v))
            long_rows.append({"bench": b, "item": iid, "module": items[iid].module, "final": c["final"],
                              "status": c["status"], "fallback": c["fallback"], "majority_final": c["majority_final"],
                              "supporters": ";".join(c["supporters"]),
                              **{f"raw_{k}": v["score_raw"] for k, v in c["coders"].items()},
                              **{f"eff_{k}": v["effective"] for k, v in c["coders"].items()},
                              "contradiction_flag": any(v.get("contradiction_verified") for v in c["coders"].values()),
                              "evidence_chunk": q["chunk_id"] if q else "", "evidence_quote": q["text"] if q else ""})
        L += ["", "## Contradiction flags (candidates only)"]
        if not flags:
            L.append("None with a verified contradicting quote.")
        for iid, k, v in flags:
            qs = [q for q in v["quotes"] if q.get("verified")] + [q for q in v["contradiction_quotes"] if q.get("verified")]
            L.append(f"- {iid} ({k}): " + " / ".join(f"[{q['chunk_id']}] \"{q['text']}\"" for q in qs))
        (OUT / f"{b}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        bench_rows.append({"bench": b, "cells": len(cells), "fallback_cells": fb, "mean_final_level": mean,
                           "n_contradiction_flag_cells": len({(i, ) for i, _, _ in flags}),
                           "packet_sha256": man.get("packet_sha256", ""), "arxiv": f"{ax.get('id', '')}{ax.get('version', '')}",
                           "repo_commit": rp.get("commit", "")})
    cols = sorted({k for r in long_rows for k in r}, key=lambda k: (k not in ("bench", "item", "module", "final", "status"), k))
    with open(OUT / "scorecards.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(long_rows)
    bc = ["bench", "cells", "fallback_cells", "mean_final_level", "n_contradiction_flag_cells", "arxiv", "repo_commit", "packet_sha256"]
    with open(OUT / "benchmarks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=bc)
        w.writeheader()
        w.writerows(bench_rows)
    print(f"{len(benches)} benchmarks, {len(long_rows)} cells -> {OUT}")


if __name__ == "__main__":
    main()
