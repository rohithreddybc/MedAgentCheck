#!/usr/bin/env python
"""Episode runner adapter for Synthetic Hospital (sparkcpark/synthetic_hospital) via its /env API.

Usage (compose stack must be up, see setup_tools.md; ports 58000/55432/56379):
  envs/synthetic_hospital/Scripts/python runners/synthetic_hospital_runner.py \
      --task-id patient_diagnosis:<gt_id> --model openai/gpt-oss-20b --temperature 0 --repeat 0 \
      --out-dir smoke/synthetic_hospital

task_id = "<task>:<gt_id>" (gt_id = benchmark_ground_truth.gt_id; task in patient_diagnosis,
context_summarization, evidence_retrieval, imaging_indication).

Why /env and not eval.cli: the repo README says the paper's agentic harness (eval/agents) leaves the
problem list visible, which leaks the patient_diagnosis labels; the /env endpoints enforce hidden
outcome, budget and server-side scoring. The repo ships no model-driven policy loop for /env (only
scripts/env_demo.py with a scripted policy), so this runner supplies the loop: system prompt =
obs.instructions, first user message = obs.intro, tools = obs.tools, all taken verbatim from the
server. No repo file is patched.

Roles: agent routed by runners/roles.json (--profile local (default) = ollama gpt-oss-20b-ctx32k;
groq = Groq openai/gpt-oss-20b via env GROQ_API_KEY; --agent-role agent_replication = qwen3 4b). There is no
simulator LLM and no judge LLM: the scorer is lexical/ontology-based and runs server-side.
The harness holds the scorer token (read from the environment; local server only); the
model only ever sees observation_text, never the reward.

CANONICALISATION of actions
  One action per tool call the model emits, in the order emitted (a response with several parallel
  tool_calls yields several actions in listed order), including the submit tool and calls the server
  rejected (they still cost a step).
  action = tool_name + json.dumps(norm(args), sort_keys=True, separators=(",",":"), ensure_ascii=False)
  norm: strings stripped and whitespace-collapsed; ICD-10 strings upper-cased and stripped; for
  submit_diagnosis the lists active_diagnoses / chronic_conditions are sorted by their canonical
  JSON (they are sets); all other lists keep their order (rankings are ordered).
  Arguments are not otherwise altered (extra/unknown keys are kept).

final_state (server-side, observable): GET /env/state/<episode_id> after the submit step (budget,
  steps, trace of every tool call with server-side observation, done/submitted, reward), plus the
  per-instance reference read directly from the shipped benchmark_v1.3.db (ground_truth JSON for the
  gt_id) so that a state-based re-check is possible; plus `state_check`: an independent exact-match
  comparison of the submission's ICD-10 codes against the reference ICD-10 codes (patient_diagnosis
  only), computed by this runner, not by the benchmark scorer. The grader's verdict is `verdict`
  (reward and metrics from the step response); RQ3c compares verdict against state_check.

verdict: reward in [0,1] and info["metrics"] from the server; verdict["pass"] is OUR derived binary
  (reward >= 0.5) and exists only for pass^k bookkeeping; keep the raw reward in analyses.
"""
import argparse, json, os, re, sqlite3, sys, time, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
REPO = EXEC / "repos" / "synthetic_hospital"
BASE = os.environ.get("SH_BASE_URL", "http://localhost:58000")
# Scorer token of the local Synthetic Hospital server. Not stored here: read from SYNTHETIC_HOSPITAL_TOKEN (or the
# upstream variable name EPIC_SIM_SCORER_TOKEN). The reruns used the upstream repository's default development token
# (see repro/README_REPRO.md, "Credentials"); set the variable to the value your local server was started with.
TOKEN = os.environ.get("SYNTHETIC_HOSPITAL_TOKEN") or os.environ.get("EPIC_SIM_SCORER_TOKEN")


def require_token() -> str:
    if not TOKEN:
        sys.exit("error: scorer token not set. Export SYNTHETIC_HOSPITAL_TOKEN (or EPIC_SIM_SCORER_TOKEN) with the value "
                 "your local Synthetic Hospital server uses; see repro/README_REPRO.md, section Credentials.")
    return TOKEN
TPM_BUDGET = 6500
GROQ = "https://api.groq.com/openai/v1"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def rate_limit_wait_s(err):
    """Seconds Groq says to wait ("try again in 1h2m3.4s"), else None. Only for 429s."""
    s = str(err)
    if "429" not in s and "rate_limit" not in s and "RateLimit" not in type(err).__name__:
        return None
    m = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", s)
    if not m or not any(m.groups()):
        return 30.0
    h, mi, sec = (float(x) if x else 0.0 for x in m.groups())
    return min(h * 3600 + mi * 60 + sec + 5, 3 * 3600)



def ws(s):
    return re.sub(r"\s+", " ", s).strip()


def norm(v, key=None):
    if isinstance(v, str):
        s = ws(v)
        return s.upper() if key in ("icd10", "icd10_code") else s
    if isinstance(v, list):
        return [norm(x, key) for x in v]
    if isinstance(v, dict):
        return {k: norm(x, k) for k, x in v.items()}
    return v


def canon(name, args):
    a = norm(args)
    if name == "submit_diagnosis" and isinstance(a, dict):
        for k in ("active_diagnoses", "chronic_conditions"):
            if isinstance(a.get(k), list):
                a[k] = sorted(a[k], key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    return name + json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--profile", default="local", help="roles.json profile: local (default) | groq")
    ap.add_argument("--agent-role", default="agent", help="agent | agent_replication")
    ap.add_argument("--roles-config", default=str(HERE / "roles.json"))
    ap.add_argument("--model", default=None, help="override the agent model name from roles.json")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--repeat", type=int, default=0)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--budget", type=int, default=None, help="server default 40")
    ap.add_argument("--max-tokens", type=int, default=4096)
    a = ap.parse_args()
    out_dir = Path(a.out_dir).resolve()
    task, gt_id = a.task_id.split(":"); gt_id = int(gt_id)

    sys.path.insert(0, str(REPO))
    from eval.env_client import SyntheticHospitalEnv
    from openai import OpenAI

    require_token()
    cfg = json.load(open(a.roles_config, encoding="utf-8"))
    ag = cfg["profiles"][a.profile][a.agent_role]
    a.model = a.model or ag["model"]
    is_groq = "groq" in ag["base_url"]
    ep_name = f"{task}_{gt_id}__{a.profile}_{a.model.replace('/', '_')}__T{a.temperature}__r{a.repeat}"
    raw_dir = out_dir / "raw" / ep_name
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI(base_url=ag["base_url"], api_key=os.environ[ag["api_key_env"]] if ag["api_key_env"] else "ollama",
                    max_retries=2, timeout=1800 if not is_groq else 120)

    calls, steps, actions, window, rl_waits = [], [], [], [], [0]
    t_start = now()
    env = SyntheticHospitalEnv(BASE, scorer_token=TOKEN, budget=a.budget)
    obs = env.reset(gt_id=gt_id)
    episode_id = obs.episode_id
    assert obs.task == task, f"task mismatch: {obs.task} vs {task}"
    messages = [{"role": "system", "content": obs.instructions}, {"role": "user", "content": obs.intro}]
    tools = obs.tools
    (raw_dir / "reset_observation.json").write_text(json.dumps(
        {k: v for k, v in vars(obs).items() if k != "agent_token"}, indent=1, default=str), encoding="utf-8")

    done, reward, last_info, error = False, None, {}, None
    max_turns = obs.budget + 6
    for turn in range(max_turns):
        while is_groq:  # throttle Groq tokens/min
            cut = time.time() - 60
            window[:] = [(t, n) for t, n in window if t > cut]
            if sum(n for _, n in window) < TPM_BUDGET: break
            time.sleep(3)
        req = {"model": a.model, "messages": messages, "tools": tools, "temperature": a.temperature,
               "max_tokens": a.max_tokens}
        rec = {"turn": turn, "t_request": now(), "request": req}
        t0 = time.time()
        try:
            resp = client.chat.completions.create(**req)
        except Exception as e:
            rec.update(error=f"{type(e).__name__}: {str(e)[:600]}", latency_s=round(time.time() - t0, 3))
            calls.append(rec)
            w = rate_limit_wait_s(e)
            if w is not None and "too large" not in str(e).lower() and rl_waits[0] < 12:
                rl_waits[0] += 1; rec["rate_limit_wait_s"] = w
                time.sleep(w); continue          # wait out Groq 429s (TPD/TPM); not an episode failure
            # one retry of the same request for transient provider errors (400 tool_use_failed is
            # deterministic and is NOT retried beyond this)
            if rec["error"].startswith("BadRequestError") or sum(1 for c in calls if "error" in c) > 6:
                error = rec["error"]; break
            time.sleep(5); continue
        d = resp.model_dump()
        rec.update(t_response=now(), latency_s=round(time.time() - t0, 3), response=d)
        calls.append(rec)
        window.append((time.time(), (d.get("usage") or {}).get("total_tokens", 0)))
        msg = d["choices"][0]["message"]
        am = {"role": "assistant", "content": msg.get("content")}
        tcs = msg.get("tool_calls") or []
        if tcs:
            am["tool_calls"] = [{"id": t["id"], "type": "function",
                                 "function": {"name": t["function"]["name"], "arguments": t["function"]["arguments"]}} for t in tcs]
        messages.append(am)
        if not tcs:
            # model answered in text without a tool call: nudge once per turn (harness-side, logged)
            messages.append({"role": "user", "content": "Continue by calling one of the available tools. When ready, call the submit tool."})
            if sum(1 for m in messages if m["role"] == "user") > 8:
                error = "model repeatedly produced no tool call"; break
            continue
        for t in tcs:
            name = t["function"]["name"]
            try:
                args = json.loads(t["function"]["arguments"] or "{}")
            except Exception:
                args = {"_unparsable": t["function"]["arguments"]}
            actions.append(canon(name, args))
            ts = now()
            try:
                o, r, done, info = env.step(name, args if isinstance(args, dict) else {})
                text = info.get("observation_text", json.dumps(o)[:8000])
                steps.append({"t": ts, "name": name, "args": args, "observation_text": text, "done": done,
                              "reward": r if done else None, "remaining": info.get("remaining"), "info": info if done else None})
                last_info = info
                if done: reward = r
            except Exception as e:
                text = f"error: {e}"
                steps.append({"t": ts, "name": name, "args": args, "harness_error": str(e)[:600]})
                error = f"step failed: {str(e)[:300]}"
                done = False
            messages.append({"role": "tool", "tool_call_id": t["id"], "content": text})
            if done: break
        if done or (error and error.startswith("step failed")):
            break
    t_end = now()

    # ---- server-side end state (observable) + independent reference
    state = None
    try:
        import httpx
        state = httpx.get(f"{BASE}/env/state/{episode_id}", headers={"X-Scorer-Token": TOKEN}, timeout=60).json()
    except Exception as e:
        state = {"error": str(e)}
    ref = None
    try:
        c = sqlite3.connect(f"file:{(REPO / 'benchmark_v1.3.db').as_posix()}?mode=ro", uri=True)
        row = c.execute("select task, split, patient_id, ground_truth from benchmark_ground_truth where gt_id=?", (gt_id,)).fetchone()
        ref = {"task": row[0], "split": row[1], "patient_id": row[2], "ground_truth": json.loads(row[3])}
    except Exception as e:
        ref = {"error": str(e)}
    submission = next((s["args"] for s in steps if s["name"].startswith("submit_")), None)
    state_check = None
    if task == "patient_diagnosis" and submission is not None and isinstance(ref.get("ground_truth"), dict):
        gt_txt = json.dumps(ref["ground_truth"])
        gt_codes = sorted(set(re.findall(r'"(?:icd10|icd10_code|icd_10|code)"\s*:\s*"([A-Za-z0-9.]+)"', gt_txt)))
        sub_codes = sorted({str(x.get("icd10", "")).upper() for k in ("active_diagnoses", "chronic_conditions")
                            for x in (submission.get(k) or []) if isinstance(x, dict) and x.get("icd10")})
        inter = set(gt_codes) & set(sub_codes)
        state_check = {"gt_codes": gt_codes, "submitted_codes": sub_codes, "exact_code_overlap": sorted(inter),
                       "exact_code_precision": len(inter) / len(sub_codes) if sub_codes else 0.0,
                       "exact_code_recall": len(inter) / len(gt_codes) if gt_codes else 0.0}

    ok = [c for c in calls if "response" in c]
    usage = {k: sum((c["response"].get("usage") or {}).get(k, 0) for c in ok) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    (raw_dir / "calls.json").write_text(json.dumps(calls, indent=1, default=str), encoding="utf-8")
    (raw_dir / "env_steps.json").write_text(json.dumps(steps, indent=1, default=str), encoding="utf-8")
    (raw_dir / "env_state.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
    metrics = (last_info or {}).get("metrics") if done else None
    result = {
        "task_id": a.task_id,
        "condition": {"model": a.model, "temperature": a.temperature},
        "repeat": a.repeat,
        "model_ids": {"agent": a.model, "agent_response_models": sorted({c["response"].get("model") for c in ok}),
                      "system_fingerprint": sorted({c["response"].get("system_fingerprint") or "" for c in ok}),
                      "simulator": None, "judge": None, "profile": a.profile, "agent_role": a.agent_role,
                      "digest": cfg["digests"].get(a.model)},
        "timestamps": {"start": t_start, "end": t_end},
        "actions": actions,
        "final_state": {"env_state": state, "reference": ref, "submission": submission, "state_check": state_check,
                        "episode_id": episode_id},
        "verdict": {"done": done, "reward": reward, "metric": (last_info or {}).get("reward_metric"),
                    "metrics": metrics, "pass": bool(done and reward is not None and reward >= 0.5)},
        "raw_log_path": str(raw_dir),
        "usage": usage,
        "calls": {"total": len(calls), "ok": len(ok), "errors": len(calls) - len(ok), "env_steps": len(steps)},
        "error": error,
    }
    (out_dir / f"{ep_name}.json").write_text(json.dumps(result, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("task_id", "actions", "usage", "calls", "error", "verdict")}, indent=1, default=str)[:4000])
    if not done:
        try: env.close()
        except Exception: pass


if __name__ == "__main__":
    main()
