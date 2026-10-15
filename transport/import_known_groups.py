"""Import coder answers for the known-groups run (protocol/addendum-known-groups.md) and resolve them.

Inputs (per bench = packet directory name, 31 benches):
  responses_known_groups/<bench>.json              coder "sonnet" (Claude Code subagent, transport "subagent")
  responses_known_groups_codex/<bench>.json (+ .meta.json from run_codex_known_groups.py)   coder "codex" (gpt-5.5)
Run dir: audit/known_groups/. Output: scoring/<bench>/<coder>/, coding/, verified/ (inside the package's score_packet,
which parses with parse_packet_response and runs run_verify), then resolved/ (package run_resolve, both coders, frozen
cross-family rule) for every bench that has both coders verified.

The frozen package does all parsing, scoring, verification and resolution; a replay backend returns the stored answer where
the CLI backend would have returned its text (as import_responses.py / import_validation.py). Before scoring, the prompt
that the package renders from the run dir is compared with prompts_known_groups/<bench>/meta.json (prompt and system
sha256); a mismatch skips that bench/coder. Nothing under scorer/agentaudit is edited.

Usage: python import_known_groups.py [--dry-run] [--bench NAME ...] [--coder sonnet|codex ...] [--force] [--no-resolve]
                                      [--run DIR] [--prompts DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_known_groups import OUT as PROMPTS, RUN  # noqa: E402
from export_prompts import AUDIT, CODER, GROUPS, render  # noqa: E402  (puts scorer/ on sys.path)
from import_validation import MODEL_ID as SONNET_MODEL_ID, TRANSPORT as SONNET_TRANSPORT  # noqa: E402
from import_validation import HashReplayBackend, MetaReplayBackend  # noqa: E402
from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.packet_score import score_packet, scoring_dir  # noqa: E402
from agentaudit.prompts import prompt_hash  # noqa: E402
from agentaudit.resolve import run_resolve  # noqa: E402
from agentaudit.util import read_json, write_json  # noqa: E402

RESP = {"sonnet": HERE / "responses_known_groups", "codex": HERE / "responses_known_groups_codex"}
CODERS_FILE = AUDIT / "coders_codex55.yaml"
CODEX_TRANSPORT = "codex exec (frozen CodexHeadlessBackend, identical prompt)"


def spec_for(coder: str) -> dict:
    return load_coders()[CODER] if coder == "sonnet" else load_coders(str(CODERS_FILE))["codex"]


def exported(prompts: Path) -> list[str]:
    return sorted(p.name for p in prompts.iterdir() if (p / "meta.json").exists()) if prompts.exists() else []


def answer_for(coder: str, bench: str, meta: dict) -> tuple[str | None, dict | None, str]:
    """(answer text, codex meta or None, status). status 'ok' or the reason the response cannot be used."""
    rp = RESP[coder] / f"{bench}.json"
    if not rp.exists():
        return None, None, "no_response"
    text = rp.read_bytes().decode("utf-8")
    if coder == "sonnet":
        return text, None, "ok"
    mp = RESP[coder] / f"{bench}.meta.json"
    if not mp.exists():
        return (text, {"model_id": "codex-default (not reported)", "source": "no meta file", "backend_meta": {}},
                "ok_no_meta")
    m = read_json(mp)
    if m.get("prompt_sha256") != meta["prompt_sha256"]:
        return None, None, "stale_response (produced for a different prompt)"
    return text, m, "ok"


def stamp(path: Path, transport: str, response_file: str, full_sha: str) -> None:
    if path.exists():
        r = read_json(path)
        r["transport"] = transport
        r["response_file"] = response_file
        r["prompt_full_sha256"] = full_sha
        write_json(path, r)


def import_one(run: Path, prompts: Path, bench: str, coder: str, force: bool) -> dict:
    meta = read_json(prompts / bench / "meta.json")
    text, cm, st = answer_for(coder, bench, meta)
    if text is None:
        return {"bench": bench, "coder": coder, "status": st}
    r = render(run, bench)
    if prompt_hash(r["prompt"]) != meta["prompt_sha256"] or prompt_hash(r["system"]) != meta["system_sha256"]:
        return {"bench": bench, "coder": coder, "status": "stale_export (packet renders a different prompt than the exported one)"}
    if coder == "sonnet":
        backend = HashReplayBackend({meta["prompt_sha256"]: text})
        transport, rel = SONNET_TRANSPORT, f"transport/responses_known_groups/{bench}.json"
    else:
        backend = MetaReplayBackend({meta["prompt_sha256"]: (text, cm)})
        transport, rel = CODEX_TRANSPORT, f"transport/responses_known_groups_codex/{bench}.json"
    s = score_packet(run, bench, coder, spec_for(coder), backend, groups=GROUPS, force=force, log=lambda *_: None)
    s["import_status"] = st
    stamp(scoring_dir(run, bench, coder) / "group1.json", transport, rel, meta["sha256_full_prompt"])
    for iid in s.get("done", []):
        cp = run / "coding" / bench / iid / f"{coder}.json"
        if cp.exists():
            c = read_json(cp)
            c["transport"] = transport
            write_json(cp, c)
    return s


def complete_benches(run: Path, benches: list[str]) -> list[str]:
    """Benches with verified records of both coders."""
    return [b for b in benches if all(any((run / "verified" / b).glob(f"*/{c}.json")) for c in RESP)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(RUN))
    ap.add_argument("--prompts", default=str(PROMPTS))
    ap.add_argument("--bench", action="append")
    ap.add_argument("--coder", action="append", choices=list(RESP), help="default: both")
    ap.add_argument("--force", action="store_true", help="rescore an existing ok group1.json")
    ap.add_argument("--no-resolve", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="list which benches have responses; score nothing")
    a = ap.parse_args()
    run, prompts = Path(a.run), Path(a.prompts)
    benches = [b for b in exported(prompts) if not a.bench or b in a.bench]
    coders = a.coder or list(RESP)
    if a.dry_run:
        have = {c: [b for b in benches if (RESP[c] / f"{b}.json").exists()] for c in coders}
        for b in benches:
            print(f"{b}: " + ", ".join(f"{c}={'response' if b in have[c] else 'pending'}" for c in coders))
        print(f"{len(benches)} exported benches; " + "; ".join(f"{c}: {len(have[c])} responses, {len(benches) - len(have[c])} pending"
                                                               for c in coders))
        return 0
    rc = 0
    for b in benches:
        for c in coders:
            s = import_one(run, prompts, b, c, a.force)
            print(json.dumps(s, default=str))
            if s.get("status") not in ("no_response",) and (s.get("blocked") or s.get("failed") or "stale" in str(s.get("status"))):
                rc = 2
    if not a.no_resolve:
        done = complete_benches(run, exported(prompts))
        if done:
            summ = run_resolve(run, done)
            print(json.dumps({"resolved_benches": len(done), "total_cells": summ["total_cells"],
                              "fallback_cells": summ["fallback_cells"]}))
        else:
            print("resolve: no bench has both coders verified yet")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
