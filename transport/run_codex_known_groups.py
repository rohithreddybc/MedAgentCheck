"""Run the exported known-groups prompts (audit/transport/prompts_known_groups/<bench>/) through the frozen package's
CodexHeadlessBackend (coder "codex" of audit/coders_codex55.yaml: gpt-5.5, read-only sandbox, empty temporary cwd; the same
spec as the audit's OpenAI coder) and store the answers for import_known_groups.py.

System text and user prompt are read back from the exported files and checked against the hashes in meta.json, so the model
receives exactly the text the Claude subagents are given. Nothing under scorer/agentaudit is edited.

Output per bench, in audit/transport/responses_known_groups_codex/:
  <bench>.json       the model's final message, byte for byte
  <bench>.meta.json  model id, timestamp, prompt/system hash, source "codex exec", backend meta
Benches that already have a response with the current prompt hash are skipped (--force overrides). A failure is logged and
the bench is left unanswered (the backend keeps the package default retries, as in the main audit; rerun the script to try again). A
usage-limit or authentication message stops the whole run immediately (exit 3) and is recorded in the log.

Usage: python run_codex_known_groups.py [--bench NAME ...] [--limit N] [--workers N] [--force]
Log: audit/codex_known_groups_transport.log. The Codex binary directory is prepended to PATH here.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AUDIT.parent / "scorer"))

from agentaudit.backends import BackendAuthError, BackendError, CodexHeadlessBackend  # noqa: E402
from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.prompts import prompt_hash  # noqa: E402

CODERS_FILE = AUDIT / "coders_codex55.yaml"
PROMPTS = HERE / "prompts_known_groups"
OUT = HERE / "responses_known_groups_codex"
LOG = AUDIT / "codex_known_groups_transport.log"
CODEX_DIR = r"C:\Users\rohit\AppData\Local\OpenAI\Codex\bin"
LIMIT_MARKERS = ("usage limit", "hit your usage", "rate limit reached", "quota exceeded", "try again at",
                 "usage_limit_reached", "insufficient_quota")

_lock = threading.Lock()
stop = threading.Event()
state: dict = {"limit": None}


class UsageLimit(Exception):
    """Raised from the subprocess wrapper so the backend does not retry after a usage-limit message."""


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    with _lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class LoggingRunner:
    """subprocess.run wrapper: logs the stderr tail of every `codex exec` call and stops the run on a usage limit."""

    def __init__(self, bench: str):
        self.bench = bench

    def __call__(self, cmd, **kw):
        p = subprocess.run(cmd, **kw)
        if "exec" in cmd and "--help" not in cmd:
            err = p.stderr or ""
            log(f"[{self.bench}] codex exit {p.returncode}; stderr tail:\n{err[-1500:]}")
            blob = (err + (p.stdout or "")).lower()
            if p.returncode != 0 and any(m in blob for m in LIMIT_MARKERS):
                state["limit"] = {"bench": self.bench, "text": (err + (p.stdout or ""))[-600:]}
                stop.set()
                raise UsageLimit(state["limit"]["text"])
        return p


def read_prompt(d: Path) -> tuple[str, str, dict]:
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    system = (d / "system.txt").read_bytes().decode("utf-8")
    prompt = "".join((d / n).read_bytes().decode("utf-8") for n in meta["parts"])
    assert prompt_hash(system) == meta["system_sha256"], f"{d.name}: system hash mismatch"
    assert prompt_hash(prompt) == meta["prompt_sha256"], f"{d.name}: prompt hash mismatch"
    return system, prompt, meta


def answered(bench: str, meta: dict) -> bool:
    mp = OUT / f"{bench}.meta.json"
    return (mp.exists() and (OUT / f"{bench}.json").exists()
            and json.loads(mp.read_text(encoding="utf-8")).get("prompt_sha256") == meta["prompt_sha256"])


def save(bench: str, meta: dict, text: str, model_id: str, bmeta: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{bench}.json").write_text(text, encoding="utf-8", newline="")
    (OUT / f"{bench}.meta.json").write_text(json.dumps({
        "bench": bench, "coder": "codex", "model_id": model_id, "timestamp": utcnow(),
        "prompt_sha256": meta["prompt_sha256"], "system_sha256": meta["system_sha256"],
        "sha256_full_prompt": meta["sha256_full_prompt"], "source": "codex exec", "backend_meta": bmeta}, indent=2),
        encoding="utf-8")


def run_one(bench: str, spec: dict) -> tuple[str, str]:
    if stop.is_set():
        return bench, "not_started (usage limit)"
    system, prompt, meta = read_prompt(PROMPTS / bench)
    backend = CodexHeadlessBackend(spec.get("model"), runner=LoggingRunner(bench))
    t0 = time.time()
    try:
        log(f"[{bench}] calling codex ({meta.get('prompt_tokens_est')} est. tokens)")
        resp = backend.complete(system, prompt)
    except UsageLimit:
        log(f"[{bench}] USAGE LIMIT; run stopped")
        return bench, "usage limit"
    except BackendAuthError as e:  # its detector also fires on stderr noise containing "401"
        log(f"[{bench}] BackendAuthError: {e}")
        stop.set()
        state["limit"] = state["limit"] or {"bench": bench, "text": f"authentication: {str(e)[:300]}"}
        return bench, "auth failure"
    except BackendError as e:
        log(f"[{bench}] {type(e).__name__}: {e}")
        return bench, f"failed: {type(e).__name__}: {str(e)[:200]}"
    except Exception as e:  # noqa: BLE001  per-bench resilience
        log(f"[{bench}] unexpected {type(e).__name__}: {e}")
        return bench, f"failed: {type(e).__name__}: {e}"
    save(bench, meta, resp.text, resp.model_id, resp.meta)
    log(f"[{bench}] done in {time.time() - t0:.0f}s, model {resp.model_id}, {len(resp.text)} chars")
    return bench, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", action="append")
    ap.add_argument("--limit", type=int, help="send at most N unanswered benches in this invocation")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--force", action="store_true", help="resend benches that already have a current response")
    ap.add_argument("--model", default="gpt-5.5",
                    help="model id; anything other than gpt-5.5 is a disclosed substitute written to its own directory")
    ap.add_argument("--codex-dir", default=CODEX_DIR, help="directory holding the codex executable")
    a = ap.parse_args()
    global OUT
    os.environ["PATH"] = a.codex_dir + os.pathsep + os.environ.get("PATH", "")
    spec = load_coders(str(CODERS_FILE))["codex"]
    assert spec["backend"] == "codex" and spec["model"] == "gpt-5.5", spec
    if a.model != "gpt-5.5":
        spec = {**spec, "model": a.model}
        OUT = HERE / f"responses_known_groups_codex_{a.model}"
    benches = sorted(p.name for p in PROMPTS.iterdir() if (p / "meta.json").exists())
    if a.bench:
        benches = [b for b in benches if b in a.bench]
    todo = []
    for b in benches:
        meta = json.loads((PROMPTS / b / "meta.json").read_text(encoding="utf-8"))
        if answered(b, meta) and not a.force:
            continue
        todo.append(b)
    skipped = len(benches) - len(todo)
    if a.limit is not None:
        todo = todo[:a.limit]
    log(f"start: {len(todo)} to send, {skipped} already answered, spec {spec}, workers {a.workers}")
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        for b, st in ex.map(lambda b: run_one(b, spec), todo):
            results[b] = st
    summ: dict[str, int] = {}
    for st in results.values():
        k = st.split(":")[0]
        summ[k] = summ.get(k, 0) + 1
    log(f"finished: {summ}")
    for b, st in results.items():
        if st != "ok":
            log(f"  {b}: {st}")
    if state["limit"]:
        log(f"STOPPED at {state['limit']['bench']}: {state['limit']['text']}")
        return 3
    return 0 if all(s == "ok" for s in results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
