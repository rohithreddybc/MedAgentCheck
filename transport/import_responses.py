"""Import a Claude Code subagent's answer as the stored response of coder "sonnet".

Reads audit/transport/responses/<bench>.json (the subagent's final JSON array, i.e. what `claude -p` would have
returned as the model's text) and runs the frozen package's own score_packet with a replay backend that returns
that text. Storage (scoring/<bench>/sonnet/group1.json, results.json, coding/<bench>/<item>/sonnet.json), JSON
parsing (parse_packet_response) and quote verification (run_verify) are therefore the package's own code paths.
The model id is recorded as "claude-sonnet-5-5 via Claude Code subagent" and the transport as "subagent".

Before importing, the prompt that score_packet will render is compared with prompts/<bench>/meta.json; a mismatch
(stale export, changed packet) aborts the import.

Usage: python import_responses.py [--run DIR] [--bench NAME ...] [--responses DIR] [--prompts DIR] [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_prompts import AUDIT, CODER, GROUPS, render  # noqa: E402  (also puts scorer/ on sys.path)
from agentaudit.backends import Response  # noqa: E402
from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.packet_score import score_packet, scoring_dir  # noqa: E402
from agentaudit.prompts import prompt_hash  # noqa: E402
from agentaudit.util import read_json, write_json  # noqa: E402

MODEL_ID = "claude-sonnet-5-5 via Claude Code subagent"
TRANSPORT = "subagent"


class ReplayBackend:
    """Returns a stored model answer where ClaudeHeadlessBackend would have returned the CLI's `result`."""

    def __init__(self, text: str, system: str, prompt: str):
        self.text, self.system, self.prompt = text, system, prompt

    def complete(self, system: str, prompt: str) -> Response:
        if system != self.system or prompt != self.prompt:
            raise RuntimeError("score_packet rendered a different prompt than the one that was checked")
        return Response(text=self.text, model_id=MODEL_ID, usage={}, raw=None,
                        meta={"transport": TRANSPORT, "attempts": 1})


def import_bench(run: Path, bench: str, responses: Path, prompts: Path, force: bool = False, log=print) -> dict:
    rp = responses / f"{bench}.json"
    if not rp.exists():
        raise FileNotFoundError(f"no response file {rp}")
    text = rp.read_text(encoding="utf-8")
    r = render(run, bench)
    meta = read_json(prompts / bench / "meta.json")
    if prompt_hash(r["prompt"]) != meta["prompt_sha256"] or prompt_hash(r["system"]) != meta["system_sha256"]:
        raise RuntimeError(f"{bench}: the packet now renders a different prompt than the exported one "
                           f"(meta.json is stale); re-export and re-run the subagent")
    spec = load_coders()[CODER]
    summary = score_packet(run, bench, CODER, spec, ReplayBackend(text, r["system"], r["prompt"]), groups=GROUPS,
                           force=force, log=log)
    sdir = scoring_dir(run, bench, CODER)
    gp = sdir / "group1.json"
    if gp.exists():
        g = read_json(gp)
        if any(a.get("model_id") == MODEL_ID for a in g.get("attempts", [])):
            g["transport"] = TRANSPORT
            g["response_file"] = f"transport/responses/{bench}.json"
            g["prompt_full_sha256"] = meta["sha256_full_prompt"]
            write_json(gp, g)
            for iid in summary.get("done", []):
                cp = run / "coding" / bench / iid / f"{CODER}.json"
                if cp.exists():
                    c = read_json(cp)
                    if c.get("model_id") == MODEL_ID:
                        c["transport"] = TRANSPORT
                        write_json(cp, c)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(AUDIT), help="run directory (default: audit/)")
    ap.add_argument("--bench", action="append", help="benchmark (repeatable); default: every file in responses/")
    ap.add_argument("--responses", default=str(HERE / "responses"))
    ap.add_argument("--prompts", default=str(HERE / "prompts"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing ok group1.json")
    a = ap.parse_args()
    run, responses, prompts = Path(a.run), Path(a.responses), Path(a.prompts)
    benches = a.bench or sorted(p.stem for p in responses.glob("*.json"))
    rc = 0
    for b in benches:
        s = import_bench(run, b, responses, prompts, a.force)
        print(json.dumps(s))
        if s["blocked"] or s["failed"]:
            rc = 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
