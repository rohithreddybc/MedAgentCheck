"""Runner adapter for AgentClinic (repo SamuelSchmidgall/AgentClinic, patched for model routing only).

Run with the benchmark's own venv:
    envs/AgentClinic/Scripts/python runners/AgentClinic_runner.py \
        --task MedQA:0 --model openai/gpt-oss-20b --temperature 0.05 --repeat 0 --out smoke/AgentClinic/ep0

Task id  : "<dataset>:<index>", dataset in {MedQA, MedQA_Ext}; index is the 0-based line of the shipped jsonl.
Condition: {"model", "backend", "temperature", "replication"}; all optional, defaults from runners/runner_config.json.
Roles    : doctor = config role "agent"; patient and measurement = role "simulator"; moderator (judge) = role "judge".
           Defaults (Run design v2, all local ollama): agent gpt-oss:20b, simulator and judge llama3.1:8b-instruct-q4_K_M at
           temperature 0, served through derived tags with num_ctx 16384. Agent temperature defaults to the benchmark's 0.05.
           Groq routing (backend "groq", env GROQ_API_KEY) is still supported and was used for the first smoke episode.
The benchmark's own main() loop runs unmodified; the only monkeypatch here maps scenario id 0 to the requested task id
and adds a token-per-minute throttle for Groq calls. Per-call request/response/usage are written by the patch to calls.jsonl.

CANONICALISATION (function `canonicalise`)
    Applied to each doctor utterance in order, with the benchmark's own precedence ("DIAGNOSIS READY" before "REQUEST TEST"):
      * contains "DIAGNOSIS READY"  -> "DIAGNOSIS:<d>", d = text after "DIAGNOSIS READY:", lowercased, punctuation removed,
                                       whitespace collapsed to single underscores, first 12 tokens kept.
      * contains "REQUEST TEST"     -> "REQUEST_TEST:<t>", t = text after "REQUEST TEST:" up to the first sentence terminator
                                       [.?!], lowercased, non-alphanumerics to "_", repeated "_" collapsed, stripped.
      * otherwise                   -> "ASK" (free-text question; arguments are not compared at the coarse level).
    `actions`        = coarse list as above (typed actions; what the divergence metric uses by default).
    `actions_strict` = same, but ASK carries the normalised utterance: "ASK:<first 12 normalised tokens>" (sensitivity analysis).
    Utterance "Maximum inferences reached" is not an action and is dropped. Raw utterances stay in calls.jsonl.
"""
import argparse
import contextlib
import datetime as dt
import io
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
REPO = EXEC / "repos" / "AgentClinic"

sys.path.insert(0, str(HERE))
import runner_common as rc  # noqa: E402

TPM_LIMIT = 7000  # Groq free tier is 8000 TPM per model; keep headroom


def _norm_tokens(text, n=12):
    t = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return "_".join(t[:n])


def canonicalise(utterance, strict=False):
    """Map one doctor utterance to a canonical action string (see module docstring). Returns None if not an action."""
    u = re.sub(r"\s+", " ", utterance or "").strip()
    if not u or u.startswith("Maximum inferences reached"):
        return None
    if "DIAGNOSIS READY" in u:
        d = u.split("DIAGNOSIS READY", 1)[1].lstrip(" :")
        return "DIAGNOSIS:" + _norm_tokens(d)
    if "REQUEST TEST" in u:
        t = u.split("REQUEST TEST", 1)[1].lstrip(" :")
        t = re.split(r"[.?!]", t, 1)[0]
        t = re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")
        return "REQUEST_TEST:" + t
    return ("ASK:" + _norm_tokens(u)) if strict else "ASK"


def _role_of(system_prompt):
    s = system_prompt or ""
    if s.startswith("You are a doctor"):
        return "doctor"
    if s.startswith("You are a patient"):
        return "patient"
    if s.startswith("You are an measurement reader"):
        return "measurement"
    if s.startswith("You are responsible for determining"):
        return "moderator"
    return "unknown"


def run_episode(task_id, condition, repeat, out_dir, config_path=None):
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    stdout_path = out_dir / "stdout.log"
    if calls_path.exists():
        calls_path.unlink()
    os.environ["AC_CALL_LOG"] = str(calls_path)
    cfg = rc.load_config(config_path)
    roles = rc.resolve_roles(cfg, "AgentClinic", condition.get("model"), condition.get("backend"),
                             condition.get("temperature"), condition.get("replication", False))
    if any(r["backend"] == "groq" for r in roles.values()) and "GROQ_API_KEY" not in os.environ:
        raise SystemExit("GROQ_API_KEY not set")
    ms = {k: "%s|%s|%s" % (r["backend"], r["model"], r["temperature"]) for k, r in roles.items()}
    condition = {"model": roles["agent"]["model"], "backend": roles["agent"]["backend"],
                 "temperature": roles["agent"]["temperature"]}
    role_desc = rc.describe(roles, rc.ollama_digests())
    dataset, idx = task_id.split(":")
    idx = int(idx)

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))
    import agentclinic as ac  # patched copy

    # map scenario id 0 -> requested task index (benchmark main() always starts at 0)
    loader_cls = {"MedQA": ac.ScenarioLoaderMedQA, "MedQA_Ext": ac.ScenarioLoaderMedQAExtended}[dataset]
    orig_get = loader_cls.get_scenario
    loader_cls.get_scenario = lambda self, id: orig_get(self, idx)

    # Groq tokens-per-minute throttle (estimate prompt tokens as chars/3.5 + 500 for completion incl. reasoning)
    window = {}  # model -> list[(t, tokens)]
    orig_routed = ac._routed_query

    def throttled(model_str, prompt, system_prompt):
        backend, mid, _ = model_str.split("|")
        if backend == "groq":
            est = int((len(prompt) + len(system_prompt)) / 3.5) + 500
            while True:
                now = time.time()
                w = [x for x in window.setdefault(mid, []) if now - x[0] < 60]
                window[mid] = w
                if sum(x[1] for x in w) + est <= TPM_LIMIT or not w:
                    break
                time.sleep(max(1.0, 60 - (now - w[0][0]) + 0.5))
            window[mid].append((time.time(), est))
        return orig_routed(model_str, prompt, system_prompt)

    ac._routed_query = throttled

    t_start = dt.datetime.now(dt.timezone.utc)
    buf = io.StringIO()
    err = None
    try:
        with contextlib.redirect_stdout(buf):
            ac.main(api_key="unused", replicate_api_key=None, inf_type="llm", doctor_bias="None", patient_bias="None",
                    doctor_llm=ms["agent"], patient_llm=ms["simulator"], measurement_llm=ms["simulator"],
                    moderator_llm=ms["judge"], num_scenarios=1, dataset=dataset, img_request=False, total_inferences=20)
    except BaseException as e:  # noqa: BLE001
        err = repr(e)
    t_end = dt.datetime.now(dt.timezone.utc)
    stdout_path.write_text(buf.getvalue(), encoding="utf-8")

    calls = []
    if calls_path.exists():
        calls = [json.loads(l) for l in calls_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [c for c in calls if "error" not in c]
    for c in ok:
        c["role"] = _role_of(c["messages"][0]["content"])
    doctor_utts = [c["response"] for c in ok if c["role"] == "doctor"]
    actions = [a for a in (canonicalise(u) for u in doctor_utts) if a]
    actions_strict = [a for a in (canonicalise(u, True) for u in doctor_utts) if a]
    mod = [c for c in ok if c["role"] == "moderator"]
    if err:
        verdict = "error"
    elif mod:
        verdict = "correct" if mod[-1]["response"].strip().lower() == "yes" else "incorrect"
    else:
        verdict = "no_diagnosis"
    usage = {}
    for c in ok:
        k = "%s/%s" % (c["backend"], c["model"])
        u = usage.setdefault(k, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
        u["calls"] += 1
        u["prompt_tokens"] += (c.get("usage") or {}).get("prompt_tokens", 0)
        u["completion_tokens"] += (c.get("usage") or {}).get("completion_tokens", 0)
    result = {
        "task_id": task_id,
        "condition": condition,
        "repeat": repeat,
        "model_ids": {"doctor": roles["agent"]["backend"] + "/" + roles["agent"]["model"],
                      "patient": roles["simulator"]["backend"] + "/" + roles["simulator"]["model"],
                      "measurement": roles["simulator"]["backend"] + "/" + roles["simulator"]["model"],
                      "moderator": roles["judge"]["backend"] + "/" + roles["judge"]["model"]},
        "role_config": role_desc,
        "system_fingerprints": sorted({str(c.get("system_fingerprint")) for c in ok}),
        "timestamps": {"start": t_start.isoformat(), "end": t_end.isoformat(),
                       "wall_s": (t_end - t_start).total_seconds()},
        "actions": actions,
        "actions_strict": actions_strict,
        "final_state": None,  # AgentClinic has no observable environment state; grader reads the transcript only
        "verdict": verdict,
        "correct_diagnosis": (re.search(r"Correct answer: (.*)", buf.getvalue()) or [None, None])[1],
        "n_calls": len(ok),
        "n_error_calls": len(calls) - len(ok),
        "usage": usage,
        "error": err,
        "raw_log_path": str(calls_path),
        "stdout_path": str(stdout_path),
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--config", default=None, help="role config json (default runners/runner_config.json)")
    ap.add_argument("--model", default=None, help="override agent model tag")
    ap.add_argument("--backend", default=None, help="override agent backend (ollama|groq)")
    ap.add_argument("--replication", action="store_true", help="use the replication agent from the config")
    ap.add_argument("--temperature", type=float, default=None, help="agent temperature (default: benchmark spec, 0.05)")
    ap.add_argument("--repeat", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = run_episode(a.task, {"model": a.model, "backend": a.backend, "temperature": a.temperature,
                             "replication": a.replication}, a.repeat, a.out, a.config)
    print(json.dumps({k: r[k] for k in ("task_id", "verdict", "actions", "n_calls", "usage", "error")}, indent=1))
