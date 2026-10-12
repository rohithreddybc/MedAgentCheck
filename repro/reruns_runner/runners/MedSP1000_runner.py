"""Runner adapter for MedSP1000 (repo MAGIC-AI4Med/MedSP1000, patched for model routing only).

Run with the benchmark's own venv:
    envs/MedSP1000/Scripts/python runners/MedSP1000_runner.py \
        --task mededportal_10009/scenario1 --model openai/gpt-oss-20b --temperature 0 --repeat 0 --out smoke/MedSP1000/ep0

Task id  : "<case_id>/<scenario>", an entry of repos/MedSP1000/subset.json (100-scenario quality-controlled subset).
Condition: {"model", "backend", "temperature", "replication"}; all optional, defaults from runners/runner_config.json.
Roles    : examinee = config role "agent"; sp and environment = role "simulator"; evaluator (judge, frozen ACGME rubric) = role "judge".
           Defaults (Run design v2, all local ollama): agent gpt-oss:20b, simulator and judge llama3.1:8b-instruct-q4_K_M at
           temperature 0, served through derived tags with num_ctx 16384. Groq routing (backend "groq") was used for the first
           smoke episodes.
The benchmark's SimulationController runs unmodified (max_total_turns 12 as shipped). Routing is via model strings parsed by the
patched LLMClient; every call (request/response/usage) is appended to calls.jsonl by the patch.

CANONICALISATION (function `canonicalise_actions`)
    The examinee emits free-text action strings per turn (examination, investigation, medication, management) plus an `eos` flag.
    The benchmark's environment controller maps each raw action to an `interpreted_action` id from the scenario's own action
    catalogue (temperature 0 here). Canonical action string, in emission order:
      * "<canonical_id>"            when the environment assigned one and status != "unsupported"
      * "UNSUPPORTED:<norm(raw)>"   otherwise; norm = lowercase, non-alphanumerics -> "_", collapsed, first 12 tokens
      * "EOS"                       appended after the actions of a turn whose examinee output had eos=true
    Speech (`speak`) is not an action. `actions_raw_norm` gives norm(raw) for every raw action (+ EOS) with no environment mapping,
    for a sensitivity analysis independent of the simulator's mapping.
    Verdict: the frozen-rubric evaluator returns true/false per rubric item; verdict = {score, items_true, items_total}.
    No pass/fail threshold is defined by the benchmark; a binary pass for pass^k must be fixed before the full run.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
REPO = EXEC / "repos" / "MedSP1000"
BASE_CONFIG = EXEC / "patches" / "MedSP1000_config.yaml"
sys.path.insert(0, str(HERE))
import runner_common as rc  # noqa: E402
TPM_LIMIT = 7000


def _norm(text, n=12):
    t = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).split()
    return "_".join(t[:n])


def canonicalise_actions(execution_log, action_history):
    """Return (actions, actions_raw_norm) per the module docstring."""
    actions, raw_norm = [], []
    hist = list(action_history)
    pos = 0
    for ev in execution_log:
        if ev.get("event_type") != "agent_output_examinee":
            continue
        p = ev["payload"]
        for _ in p.get("actions", []):
            h = hist[pos] if pos < len(hist) else {"raw": _, "canonical_id": None, "status": "unsupported"}
            pos += 1
            if h.get("canonical_id") and h.get("status") != "unsupported":
                actions.append(str(h["canonical_id"]))
            else:
                actions.append("UNSUPPORTED:" + _norm(h.get("raw", "")))
            raw_norm.append(_norm(h.get("raw", "")))
        if p.get("eos"):
            actions.append("EOS")
            raw_norm.append("EOS")
    return actions, raw_norm


def run_episode(task_id, condition, repeat, out_dir, config_path=None):
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    if calls_path.exists():
        calls_path.unlink()
    os.environ["MEDSP_CALL_LOG"] = str(calls_path)
    os.environ.setdefault("OPENAI_API_KEY", "unused")  # default client is never used for routed models
    rcfg = rc.load_config(config_path)
    roles = rc.resolve_roles(rcfg, "MedSP1000", condition.get("model"), condition.get("backend"),
                             condition.get("temperature"), condition.get("replication", False))
    if any(r["backend"] == "groq" for r in roles.values()) and "GROQ_API_KEY" not in os.environ:
        raise SystemExit("GROQ_API_KEY not set")
    ms = {k: "%s:%s@%s" % (r["backend"], r["model"], r["temperature"]) for k, r in roles.items()}
    condition = {"model": roles["agent"]["model"], "backend": roles["agent"]["backend"],
                 "temperature": roles["agent"]["temperature"]}
    role_desc = rc.describe(roles, rc.ollama_digests())

    cfg = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    cfg["agents"]["examinee"]["model"] = ms["agent"]
    cfg["agents"]["sp"]["model"] = ms["simulator"]
    cfg["agents"]["environment"]["model"] = ms["simulator"]
    cfg["agents"]["evaluator"]["model"] = ms["judge"]
    cfg["api"]["model"] = ms["agent"]
    cfg["simulation"]["output_root"] = str(out_dir / "run")
    cfg_path = out_dir / "config.effective.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    sys.path.insert(0, str(REPO / "src"))
    from simulate.api import LLMClient, load_config
    from simulate.case_loader import load_case
    from simulate.controller import SimulationController, _count_evaluation_items

    window = []
    orig_chat = LLMClient.chat

    def throttled(self, messages, **kw):
        m = kw.get("model") or ""
        if m.startswith("groq:"):
            msgs = list(messages)
            est = int(sum(len(str(x.get("content", ""))) for x in msgs) / 3.5) + 800
            while True:
                now = time.time()
                w = [x for x in window if now - x[0] < 60 and x[2] == m]
                window[:] = [x for x in window if now - x[0] < 60]
                if sum(x[1] for x in w) + est <= TPM_LIMIT or not w:
                    break
                time.sleep(max(1.0, 60 - (now - w[0][0]) + 0.5))
            window.append((time.time(), est, m))
            return orig_chat(self, msgs, **kw)
        return orig_chat(self, messages, **kw)

    LLMClient.chat = throttled

    case_root = REPO / "data" / "MedSP1000" / task_id
    t_start = dt.datetime.now(dt.timezone.utc)
    err, result, ctrl = None, None, None
    try:
        config = load_config(str(cfg_path))
        case = load_case(case_root=str(case_root), examinee_dir=None, sp_dir=None, environment_dir=None, evaluator_dir=None)
        ctrl = SimulationController(case, config, output_dir=str(out_dir / "run"))
        result = ctrl.run()
    except BaseException as e:  # noqa: BLE001
        err = repr(e)
    t_end = dt.datetime.now(dt.timezone.utc)

    calls = []
    if calls_path.exists():
        calls = [json.loads(l) for l in calls_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    usage = {}
    for c in calls:
        k = c["model"]
        u = usage.setdefault(k, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
        u["calls"] += 1
        u["prompt_tokens"] += (c.get("usage") or {}).get("prompt_tokens", 0)
        u["completion_tokens"] += (c.get("usage") or {}).get("completion_tokens", 0)

    actions, raw_norm, final_state, verdict = [], [], None, None
    if ctrl is not None:
        actions, raw_norm = canonicalise_actions(ctrl.execution_log, ctrl.state.action_history)
        st = ctrl.state
        final_state = {"progress_index": st.progress_index, "state_label": st.current_phase_id,
                       "patient_status": st.patient_status, "completion_reason": st.completion_reason,
                       "phase_history": st.phase_history, "total_turns": st.total_turns,
                       "minutes_since_encounter": st.minutes_since_encounter}
    if result and not result.get("skipped"):
        done, total = _count_evaluation_items(result["evaluation"])
        verdict = {"score": (done / total) if total else None, "items_true": done, "items_total": total}
    out = {
        "task_id": task_id,
        "condition": condition,
        "repeat": repeat,
        "model_ids": {"examinee": roles["agent"]["backend"] + "/" + roles["agent"]["model"],
                      "sp": roles["simulator"]["backend"] + "/" + roles["simulator"]["model"],
                      "environment": roles["simulator"]["backend"] + "/" + roles["simulator"]["model"],
                      "evaluator": roles["judge"]["backend"] + "/" + roles["judge"]["model"]},
        "role_config": role_desc,
        "system_fingerprints": sorted({str(c.get("system_fingerprint")) for c in calls}),
        "timestamps": {"start": t_start.isoformat(), "end": t_end.isoformat(), "wall_s": (t_end - t_start).total_seconds()},
        "actions": actions,
        "actions_raw_norm": raw_norm,
        "final_state": final_state,
        "verdict": verdict,
        "n_calls": len(calls),
        "usage": usage,
        "error": err,
        "raw_log_path": str(calls_path),
        "run_dir": str(out_dir / "run"),
    }
    (out_dir / "result.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--config", default=None, help="role config json (default runners/runner_config.json)")
    ap.add_argument("--model", default=None, help="override agent model tag")
    ap.add_argument("--backend", default=None, help="override agent backend (ollama|groq)")
    ap.add_argument("--replication", action="store_true", help="use the replication agent from the config")
    ap.add_argument("--temperature", type=float, default=None, help="agent temperature (default: 0)")
    ap.add_argument("--repeat", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = run_episode(a.task, {"model": a.model, "backend": a.backend, "temperature": a.temperature,
                             "replication": a.replication}, a.repeat, a.out, a.config)
    print(json.dumps({k: r[k] for k in ("task_id", "verdict", "actions", "n_calls", "usage", "error")}, indent=1))
