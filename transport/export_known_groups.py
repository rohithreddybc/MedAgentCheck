"""Export the audit prompts for the 31 gold packets of the known-groups addendum (protocol/addendum-known-groups.md).

The prompt is the unchanged audit prompt: coder "sonnet", groups=1 (all 25 items C1..C14, A1..A11), frozen 150,000-token
cap and drop rule, rendered by export_prompts.render / write_prompt_dir (same part splitting, same meta.json fields).
Run dir audit/known_groups/ holds byte copies of the 22 BetterBench packets (audit/gold_bb/gold-betterbench/packets) and
the 9 ABC packets (audit/gold_abc/gold-abc/packets); only the packets/ layer is needed to render. Nothing under
scorer/agentaudit is edited.

Output: audit/transport/prompts_known_groups/<bench>/{system.txt, user_partNN.txt, meta.json}
Usage:  python export_known_groups.py [--run DIR] [--bench NAME ...] [--out DIR] [--prepare]
        --prepare re-copies the gold packets into the run dir when a packet directory is missing (never overwrites).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_prompts import AUDIT, CODER, GROUPS, SCHEMA, render, write_prompt_dir  # noqa: E402  (puts scorer/ on sys.path)

RUN = AUDIT / "known_groups"
SOURCES = {"betterbench": AUDIT / "gold_bb" / "gold-betterbench" / "packets", "abc": AUDIT / "gold_abc" / "gold-abc" / "packets"}
OUT = HERE / "prompts_known_groups"


def prepare(run: Path) -> int:
    """Copy any missing gold packet into run/packets (copy, not move; bench directory names kept)."""
    n = 0
    for src in SOURCES.values():
        for d in sorted(p for p in src.iterdir() if (p / "chunks.jsonl").exists()):
            dst = run / "packets" / d.name
            if not dst.exists():
                shutil.copytree(d, dst)
                n += 1
    return n


def export_bench(run: Path, bench: str, out: Path) -> dict:
    r = render(run, bench)
    return write_prompt_dir(out / bench, r["system"], r["prompt"], r["sel"]["kept"], {
        "mode": "known_groups", "bench": bench, "coder": CODER, "groups": GROUPS, "items": r["group"],
        "cap_tokens": r["cap"], "tokens_before_cap": r["sel"]["tokens_before"], "tokens_sent": r["sel"]["tokens"],
        "over_cap": r["sel"]["over_cap"], "n_dropped_chunks": len(r["sel"]["dropped"]),
        "expected_output_schema": SCHEMA,
        "response_path": f"audit/transport/responses_known_groups/{bench}.json",
        "response_path_codex": f"audit/transport/responses_known_groups_codex/{bench}.json"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(RUN))
    ap.add_argument("--bench", action="append")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()
    run, out = Path(a.run), Path(a.out)
    if a.prepare:
        print(f"copied {prepare(run)} missing packets")
    benches = a.bench or sorted(p.name for p in (run / "packets").iterdir() if (p / "chunks.jsonl").exists())
    for b in benches:
        m = export_bench(run, b, out)
        print(f"{b}: {m['n_parts']} parts, ~{m['prompt_tokens_est']} tokens, over_cap={m['over_cap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
