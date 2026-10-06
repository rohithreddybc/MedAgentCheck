"""Run the exported perturbation prompts (audit/transport/prompts_perturb/<variant>/) through the frozen package's
CodexHeadlessBackend (coder "codex" of audit/coders_codex55.yaml: gpt-5.5, read-only sandbox, empty temporary cwd) and
store the answers for import_validation.py --mode perturb --coder codex.

The system text and the user prompt are read back from the exported files and checked against the hashes in meta.json
(system_sha256, prompt_sha256), so the model receives exactly the text the Claude subagents were given. Nothing under
scorer/agentaudit is edited.

Output per variant, in audit/transport/responses_perturb_codex/:
  <variant>.json       the model's final message, byte for byte
  <variant>.meta.json  model id, timestamp, prompt/system hash, source ("codex exec", or "cli_run" for an answer taken from
                       audit/perturb/<variant>/codex.json when that record has the same prompt hash and a single attempt)

Usage: python run_codex_prompts.py [--variant v01 ...] [--workers N] [--force] [--no-reuse]
The Codex binary directory is prepended to PATH here. Stops cleanly on a usage-limit message.
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
PROMPTS = HERE / "prompts_perturb"
OUT = HERE / "responses_perturb_codex"
LOG = AUDIT / "codex_perturb_transport.log"
CLI_RUN = AUDIT / "perturb"
CODEX_DIR = r"<local-path>"
LIMIT_MARKERS = ("usage limit", "hit your usage", "rate limit reached", "quota exceeded", "try again at",
                 "usage_limit_reached", "insufficient_quota")

_lock = threading.Lock()
stop = threading.Event()
state: dict = {"limit": None}


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    with _lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class LoggingRunner:
    """subprocess.run wrapper that logs the stderr tail of every `codex exec` call and watches for a usage limit."""

    def __init__(self, variant: str):
        self.variant = variant

    def __call__(self, cmd, **kw):
        p = subprocess.run(cmd, **kw)
        if "exec" in cmd and "--help" not in cmd:
            err = p.stderr or ""
            blob = (err + (p.stdout or "")).lower()
            log(f"[{self.variant}] codex exit {p.returncode}; stderr tail:\n{err[-1500:]}")
            if p.returncode != 0 and any(m in blob for m in LIMIT_MARKERS):
                state["limit"] = {"variant": self.variant, "text": (err + (p.stdout or ""))[-600:]}
                stop.set()
        return p


def read_prompt(d: Path) -> tuple[str, str, dict]:
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    system = (d / "system.txt").read_bytes().decode("utf-8")
    prompt = "".join((d / n).read_bytes().decode("utf-8") for n in meta["parts"])
    assert prompt_hash(system) == meta["system_sha256"], f"{d.name}: system hash mismatch"
    assert prompt_hash(prompt) == meta["prompt_sha256"], f"{d.name}: prompt hash mismatch"
    return system, prompt, meta


def reusable_cli_answer(variant: str, meta: dict) -> dict | None:
    p = CLI_RUN / variant / "codex.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text(encoding="utf-8"))
    att = r.get("attempts") or []
    if (r.get("status") == "ok" and len(att) == 1 and (r.get("prompt_sha256") or {}).get("1") == meta["prompt_sha256"]
            and att[0].get("raw_response")):
        return {"text": att[0]["raw_response"], "model_id": att[0]["model_id"], "timestamp": att[0]["timestamp"],
                "meta": att[0].get("meta") or {}}
    return None


def save(variant: str, meta: dict, text: str, model_id: str, timestamp: str, source: str, bmeta: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{variant}.json").write_text(text, encoding="utf-8", newline="")
    (OUT / f"{variant}.meta.json").write_text(json.dumps({
        "variant": variant, "coder": "codex", "model_id": model_id, "timestamp": timestamp,
        "prompt_sha256": meta["prompt_sha256"], "system_sha256": meta["system_sha256"],
        "sha256_full_prompt": meta["sha256_full_prompt"], "source": source, "backend_meta": bmeta}, indent=2),
        encoding="utf-8")


def run_one(variant: str, spec: dict, force: bool, reuse: bool) -> tuple[str, str]:
    if stop.is_set():
        return variant, "not_started (usage limit)"
    system, prompt, meta = read_prompt(PROMPTS / variant)
    mp = OUT / f"{variant}.meta.json"
    if mp.exists() and (OUT / f"{variant}.json").exists() and not force:
        if json.loads(mp.read_text(encoding="utf-8")).get("prompt_sha256") == meta["prompt_sha256"]:
            return variant, "already_done"
    if reuse:
        old = reusable_cli_answer(variant, meta)
        if old:
            save(variant, meta, old["text"], old["model_id"], old["timestamp"], "cli_run", old["meta"])
            log(f"[{variant}] reused CLI-run answer (same prompt hash {meta['prompt_sha256'][:12]}, model {old['model_id']})")
            return variant, "reused"
    backend = CodexHeadlessBackend(spec.get("model"), runner=LoggingRunner(variant))
    t0 = time.time()
    try:
        log(f"[{variant}] calling codex ({meta.get('prompt_tokens_est')} est. tokens)")
        resp = backend.complete(system, prompt)
    except BackendError as e:  # includes BackendAuthError (its detector also fires on stderr noise containing "401")
        log(f"[{variant}] {type(e).__name__}: {e}")
        return variant, "usage limit" if stop.is_set() else f"failed: {type(e).__name__}: {str(e)[:200]}"
    except Exception as e:  # noqa: BLE001  per-variant resilience
        log(f"[{variant}] unexpected {type(e).__name__}: {e}")
        return variant, f"failed: {type(e).__name__}: {e}"
    save(variant, meta, resp.text, resp.model_id, utcnow(), "codex exec", resp.meta)
    log(f"[{variant}] done in {time.time() - t0:.0f}s, model {resp.model_id}, {len(resp.text)} chars")
    return variant, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", action="append")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-reuse", action="store_true")
    a = ap.parse_args()
    os.environ["PATH"] = CODEX_DIR + os.pathsep + os.environ.get("PATH", "")
    spec = load_coders(str(CODERS_FILE))["codex"]
    assert spec["backend"] == "codex" and spec["model"] == "gpt-5.5", spec
    variants = sorted(p.name for p in PROMPTS.iterdir() if (p / "meta.json").exists())
    if a.variant:
        variants = [v for v in variants if v in a.variant]
    log(f"start: {len(variants)} variants, spec {spec}, workers {a.workers}")
    results = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for v, st in ex.map(lambda v: run_one(v, spec, a.force, not a.no_reuse), variants):
            results[v] = st
    summ: dict[str, int] = {}
    for st in results.values():
        k = st.split(":")[0]
        summ[k] = summ.get(k, 0) + 1
    log(f"finished: {summ}")
    for v, st in results.items():
        if st not in ("ok", "reused", "already_done"):
            log(f"  {v}: {st}")
    if state["limit"]:
        log(f"USAGE LIMIT reached at {state['limit']['variant']}: {state['limit']['text']}")
        return 3
    return 0 if all(s in ("ok", "reused", "already_done") for s in results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
