"""RQ3 judge-only rerun for AgentClinic (design-review-1 T5; decision log 2026-10-05).

The end-to-end rerun varies the agent, the simulator and the judge at once. This script isolates the judge. For
each recorded AgentClinic transcript it takes the moderator call exactly as the benchmark made it (the recorded
system and user messages, which hold the correct diagnosis and the doctor's dialogue) and sends it again to the
v3 judge model, ``--repeats`` times (default 3), with the same decoding settings as the original run (temperature 0,
max_tokens 1500). The agent and the simulator are not run again, so any change in a verdict comes from the judge.

Requires a running ollama with the v3 judge tag (llama3.1-8b-ctx16k, digest recorded by the runner). The judge call
function is injectable, so the logic is tested without ollama (tests/test_judge_rerun.py).

Verdict rule, as in research/executed/runners/AgentClinic_runner.py: the answer ``yes`` (case-insensitive, after
trimming) is "correct"; anything else is "incorrect".

Output (analysis/out/):
  rq3_judge_rerun.jsonl    one record per transcript: ids, recorded verdict, the raw answers of the re-judgements
  rq3_judge_rerun.csv      the same, one row per transcript, with the agreement flags
  rq3_judge_rerun.json     summary: transcripts, re-judgements, share of transcripts whose re-judgements are not all
                           identical (judge-only instability), share that differ from the recorded verdict, Wilson CIs,
                           the model and digest used

Usage:  python analysis/judge_rerun.py --limit 2          (the test run: 2 transcripts, seeded order)
        python analysis/judge_rerun.py                    (all complete AgentClinic episodes)
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

from common import OUT, ROOT, SEED, write_csv

from agentaudit.sampling import rank_hash  # noqa: E402
from agentaudit.stats import wilson  # noqa: E402

RUN_DIR = ROOT / "research" / "executed" / "runs" / "v3" / "AgentClinic"
BASE_URL = "http://localhost:11434"
JUDGE_MODEL = "llama3.1-8b-ctx16k"  # v3 judge: llama3.1:8b-instruct-q4_K_M, num_ctx 16384 (runners/runner_config.json)
MODERATOR_PREFIX = "You are responsible for determining"  # the moderator's system prompt (AgentClinic_runner._role_of)
REPEATS = 3
MAX_TOKENS = 1500
TEMPERATURE = 0.0


# ------------------------------------------------------------------ loading
def verdict_of(answer: str) -> str:
    """AgentClinic's rule: 'yes' is correct, anything else incorrect."""
    return "correct" if (answer or "").strip().lower() == "yes" else "incorrect"


def moderator_call(calls_path: Path) -> dict | None:
    """The last moderator call in an episode's calls.jsonl (the one that produced the verdict), or None."""
    p = Path(calls_path)
    if not p.exists():
        return None
    last = None
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        if "error" in c or not c.get("messages"):
            continue
        if str(c["messages"][0].get("content", "")).startswith(MODERATOR_PREFIX):
            last = c
    return last


def _calls_path(ep: dict, run_dir: Path) -> Path:
    cand = Path(ep.get("raw_log_path") or "")
    if cand.exists():
        return cand
    rel = Path(run_dir) / "episodes" / str(ep.get("condition_name")) / (str(ep["task_id"]).replace(":", "_") +
                                                                       f"_r{ep.get('repeat')}") / "calls.jsonl"
    return rel


def load_transcripts(run_dir: Path = RUN_DIR) -> list[dict]:
    """One record per usable AgentClinic episode: {key, task_id, condition, repeat, recorded_verdict, messages,
    recorded_answer, calls_path}. Episodes with an error, no verdict or no moderator call are skipped."""
    out = []
    ep_file = Path(run_dir) / "episodes.jsonl"
    if not ep_file.exists():
        return out
    by_key: dict[str, dict] = {}
    for i, line in enumerate(ep_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        ep = json.loads(line)
        by_key[ep.get("_key") or f"{ep.get('task_id')}|{ep.get('condition_name')}|{ep.get('repeat')}|{i}"] = ep
    for key, ep in by_key.items():
        if ep.get("driver_status", "ok") != "ok" or ep.get("error") or ep.get("verdict") not in ("correct", "incorrect"):
            continue
        cp = _calls_path(ep, run_dir)
        mc = moderator_call(cp)
        if not mc:
            continue
        out.append({"key": key, "task_id": ep["task_id"], "condition": ep.get("condition_name"),
                    "repeat": ep.get("repeat"), "recorded_verdict": ep["verdict"], "messages": mc["messages"],
                    "recorded_answer": mc["response"], "recorded_judge_model": mc.get("model"),
                    "calls_path": str(cp)})
    return sorted(out, key=lambda r: r["key"])


def select_transcripts(transcripts: list[dict], limit: int | None, seed: int = SEED) -> list[dict]:
    """Seeded order (SHA-256 of seed|judge-rerun|key), so the 2-transcript test run is reproducible. When ``limit`` is
    set and both recorded verdicts occur, the first transcript of each verdict is taken before filling up."""
    ordered = sorted(transcripts, key=lambda t: rank_hash(seed, "judge-rerun", t["key"]))
    if not limit or limit >= len(ordered):
        return ordered
    picked: list[dict] = []
    for v in ("correct", "incorrect"):
        for t in ordered:
            if t["recorded_verdict"] == v and t not in picked:
                picked.append(t)
                break
        if len(picked) >= limit:
            break
    for t in ordered:
        if len(picked) >= limit:
            break
        if t not in picked:
            picked.append(t)
    return picked[:limit]


# ------------------------------------------------------------------ the judge
def ollama_judge(messages: list[dict], model: str = JUDGE_MODEL, base_url: str = BASE_URL, timeout: float = 600.0) -> str:
    """One chat completion from a local ollama (OpenAI-compatible endpoint), temperature 0, max_tokens 1500."""
    body = json.dumps({"model": model, "messages": messages, "temperature": TEMPERATURE,
                       "max_tokens": MAX_TOKENS}).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return re.sub(r"\s+", " ", d["choices"][0]["message"]["content"] or "")


def ollama_digest(model: str = JUDGE_MODEL, base_url: str = BASE_URL) -> str | None:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=10) as r:
            for m in json.load(r)["models"]:
                if m["name"].replace(":latest", "") == model:
                    return m["digest"]
    except Exception:  # noqa: BLE001
        pass
    return None


# ------------------------------------------------------------------ rerun and summary
def rejudge(t: dict, judge_fn, repeats: int = REPEATS) -> dict:
    """Re-judge one transcript ``repeats`` times. ``judge_fn(messages) -> answer string``."""
    answers, verdicts, secs = [], [], []
    for _ in range(repeats):
        t0 = time.time()
        a = judge_fn(t["messages"])
        secs.append(round(time.time() - t0, 2))
        answers.append(a)
        verdicts.append(verdict_of(a))
    return {"key": t["key"], "task_id": t["task_id"], "condition": t["condition"], "repeat": t["repeat"],
            "recorded_verdict": t["recorded_verdict"], "recorded_answer": t["recorded_answer"],
            "rejudge_answers": answers, "rejudge_verdicts": verdicts, "rejudge_seconds": secs,
            "all_identical": len(set(verdicts)) == 1,
            "all_match_recorded": all(v == t["recorded_verdict"] for v in verdicts),
            "any_differs_from_recorded": any(v != t["recorded_verdict"] for v in verdicts)}


def summarise(records: list[dict], model: str = JUDGE_MODEL, digest: str | None = None, repeats: int = REPEATS) -> dict:
    n = len(records)
    unstable = sum(not r["all_identical"] for r in records)
    differs = sum(r["any_differs_from_recorded"] for r in records)
    n_calls = sum(len(r["rejudge_verdicts"]) for r in records)
    flips = sum(sum(v != r["recorded_verdict"] for v in r["rejudge_verdicts"]) for r in records)

    def share(k):
        if not n:
            return {"k": k, "n": n, "share": None, "wilson95": None}
        ci = wilson(k, n)
        return {"k": k, "n": n, "share": k / n, "wilson95": [ci[0], ci[1]]}

    return {"benchmark": "AgentClinic", "judge_model": model, "judge_digest": digest, "repeats": repeats,
            "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS, "transcripts": n, "rejudgements": n_calls,
            "transcripts_with_unstable_rejudgements": share(unstable),
            "transcripts_where_any_rejudgement_differs_from_recorded": share(differs),
            "rejudgements_differing_from_recorded": {"k": flips, "n": n_calls,
                                                     "share": flips / n_calls if n_calls else None},
            "note": "agent and simulator were not rerun; the transcripts are the recorded ones, so any change is judge "
                    "variance. Ollama at temperature 0 is not guaranteed to be bit-deterministic."}


def run(run_dir: Path = RUN_DIR, out_dir: Path = OUT, limit: int | None = None, repeats: int = REPEATS,
        judge_fn=None, model: str = JUDGE_MODEL, base_url: str = BASE_URL, seed: int = SEED, digest: str | None = None,
        log=print) -> dict:
    out_dir = Path(out_dir)
    transcripts = select_transcripts(load_transcripts(run_dir), limit, seed)
    if judge_fn is None:
        judge_fn = lambda m: ollama_judge(m, model, base_url)  # noqa: E731
        digest = digest or ollama_digest(model, base_url)
    records = []
    for i, t in enumerate(transcripts, 1):
        r = rejudge(t, judge_fn, repeats)
        records.append(r)
        log(f"[{i}/{len(transcripts)}] {t['key']}: recorded {t['recorded_verdict']}, rejudged {r['rejudge_verdicts']}")
    summary = summarise(records, model, digest, repeats)
    summary["selected"] = [t["key"] for t in transcripts]
    summary["limit"] = limit
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rq3_judge_rerun.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
                                                   encoding="utf-8", newline="\n")
    write_csv(out_dir / "rq3_judge_rerun.csv",
              [{**{k: r[k] for k in ("key", "task_id", "condition", "repeat", "recorded_verdict", "all_identical",
                                     "all_match_recorded")},
                "rejudge_verdicts": ";".join(r["rejudge_verdicts"])} for r in records])
    (out_dir / "rq3_judge_rerun.json").write_text(json.dumps(summary, indent=2), encoding="utf-8", newline="\n")
    return summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-dir", type=Path, default=RUN_DIR)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--limit", type=int, help="re-judge only this many transcripts (seeded order); omit for all")
    ap.add_argument("--repeats", type=int, default=REPEATS)
    ap.add_argument("--model", default=JUDGE_MODEL)
    ap.add_argument("--base-url", default=BASE_URL)
    a = ap.parse_args(argv)
    s = run(a.run_dir, a.out, a.limit, a.repeats, model=a.model, base_url=a.base_url)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
