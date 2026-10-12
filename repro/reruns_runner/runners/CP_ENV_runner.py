#!/usr/bin/env python
"""Episode runner adapter for CP-Env (SPIRAL-MED/CP_ENV, DiagnosisArena test split).

Usage:
  envs/CP_ENV/Scripts/python runners/CP_ENV_runner.py --task-id <DiagnosisArena id> \
      --model openai/gpt-oss-20b --temperature 0 --repeat 0 --out-dir smoke/CP_ENV [--skip-judge]

One episode = run_pipeline() (registration -> diagnostic_test -> specialist_consultation ->
end_of_diagnosis) for one DiagnosisArena case, then the benchmark's own MedicalEvaluator scores it.
No repo file is patched. Routing is done entirely through the benchmark's CLI-equivalent arguments
and one runner-level hook (below).

Roles (runners/roles.json; --profile local (default) | groq; --agent-role agent | agent_replication)
  agent (doctor)      : local default = ollama gpt-oss-20b-ctx32k (gpt-oss:20b weights, num_ctx 32768);
                        groq profile = Groq openai/gpt-oss-20b, key from env GROQ_API_KEY
  simulator (patient, : local llama3.1-8b-q4km-ctx32k (llama3.1:8b-instruct-q4_K_M weights), temperature 0
   test results, tool    (groq profile: gpt-oss-20b-ctx16k)
   summariser, MDT)
  judge (evaluator)   : local llama3.1-8b-q4km-ctx32k, temperature 0 (groq profile: Groq gpt-oss-120b)
  Keys come from the environment only; no key in any repo file is read.

Runner hook: openai.resources.chat.completions.Completions.create is wrapped to (a) inject
  temperature (simulator 0; doctor = condition temperature; the benchmark passes none for these
  calls), (b) log every request/response/latency/usage, (c) throttle Groq to <= 6500 tokens/min per
  model. Wikipedia/PubMed tool fetches (WikipediaQueryRun.run, PubmedQueryRun.run) are wrapped to
  log the raw live-API payload (environment-drift record).

CANONICALISATION of actions
  Source: message.tool_calls of each doctor (agent-role) response, in call order and, within one
  response, in the order the model listed them. Attempted calls count even if executing them
  crashed the episode (context.tool_usages would omit those).
  action = tool_name + json.dumps(args, sort_keys=True, separators=(",",":"), ensure_ascii=False)
  after normalising args: strings stripped and whitespace-collapsed, list-valued args whose
  elements are strings (get_info.test_names) sorted, organize_mdt recruited_agents (list of
  [role, description] pairs) reduced to the sorted list of role names, and a JSON-string
  recruited_agents parsed first. Free-text query strings (search_wikipedia/search_pubmed) are kept
  verbatim after whitespace normalisation, so different phrasing = different action (strict).
  Non-tool decisions (department referrals) are in final_state.department_path, not in actions.

final_state: department_path (record["Recording Department"] sequence), patient_records (all),
  final_diagnosis (top 5) and treatment_plan, process_success, completed tests, number of dialogue
  encounters.
verdict: MedicalEvaluator scores dict (WC, DR, DR@3, DR@5, and the subjective ones), plus
  process_success from the pipeline; verdict["pass"] is OUR derived binary: process_success and
  scores["DR"] == 1.0 (Final Diagnosis Accuracy, exact match). The benchmark itself reports averaged
  scores, not a per-case pass.
"""
import argparse, json, os, re, sys, time, threading, datetime, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
REPO = EXEC / "repos" / "CP_ENV" / "codes"

TPM_BUDGET = 6500


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def ws(s):
    return re.sub(r"\s+", " ", s).strip()



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


def norm_args(name, args):
    a = dict(args)
    for k, v in list(a.items()):
        if isinstance(v, str):
            if name == "organize_mdt" and k == "recruited_agents":
                import ast
                try:
                    v = ast.literal_eval(v)
                except Exception:
                    pass
            else:
                a[k] = ws(v); continue
        if name == "organize_mdt" and k == "recruited_agents":
            roles = []
            for it in (v if isinstance(v, (list, tuple)) else [v]):
                roles.append(ws(str(it[0] if isinstance(it, (list, tuple)) and it else it)))
            a[k] = sorted(roles)
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            a[k] = sorted(ws(x) for x in v)
    return a


def canon(name, args):
    return name + json.dumps(norm_args(name, args), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
    ap.add_argument("--skip-judge", action="store_true")
    ap.add_argument("--wiki-user-agent",
                    default="BenchmarkReproducibilityStudy/0.1 (academic research; python-requests)")
    a = ap.parse_args()
    out_dir = Path(a.out_dir).resolve()
    cfg = json.load(open(a.roles_config, encoding="utf-8"))
    R = cfg["profiles"][a.profile]
    def key_of(r):  # keys come from the environment only, never from a repo file
        return os.environ[r["api_key_env"]] if r["api_key_env"] else "ollama"
    ag, sm, jd = R[a.agent_role], R["simulator"], R["judge"]
    a.model = a.model or ag["model"]
    a.sim_model, JUDGE_MODEL = sm["model"], jd["model"]

    os.chdir(REPO)
    sys.path.insert(0, str(REPO))
    import logging
    ep_name = f"{a.task_id}__{a.profile}_{a.model.replace('/', '_')}__T{a.temperature}__r{a.repeat}"
    raw_dir = out_dir / "raw" / ep_name
    raw_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, filename=str(raw_dir / "benchmark_logger.log"), filemode="w",
                        format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s")

    import openai.resources.chat.completions as occ
    calls, window, lock = [], {}, threading.Lock()
    orig_create = occ.Completions.create

    phase = ["pipeline"]

    def role_of(model):
        if phase[0] == "judge": return "judge"
        return "agent" if model == a.model else "simulator"

    def logged_create(self, *args, **kw):
        model = kw.get("model")
        role = role_of(model)
        groq = "groq" in str(self._client.base_url)
        if not groq:
            kw.setdefault("timeout", 3600)   # local ollama queues requests; SDK default would abort long waits
        if role in ("simulator", "judge"):
            kw["temperature"] = 0
        elif role == "agent":
            kw.setdefault("temperature", a.temperature)
        if groq:
            while True:
                with lock:
                    cut = time.time() - 60
                    w = [(t, n) for t, n in window.get(model, []) if t > cut]
                    window[model] = w
                    if sum(n for _, n in w) < TPM_BUDGET:
                        break
                time.sleep(3)
        rec = {"role": role, "base_url": str(self._client.base_url), "t_request": now(),
               "request": {k: v for k, v in kw.items() if k != "extra_headers"}}
        t0 = time.time()
        rl = 0
        while True:
            try:
                resp = orig_create(self, *args, **kw)
                break
            except Exception as e:
                w = rate_limit_wait_s(e) if groq else None
                if w is not None and rl < 12:   # wait out Groq 429s (TPD) instead of aborting the episode
                    rl += 1
                    with lock:
                        calls.append({"role": role, "t_request": rec["t_request"], "rate_limit_wait_s": w,
                                      "error": f"{type(e).__name__}: {str(e)[:300]}"})
                    time.sleep(w); rec["t_request"] = now(); t0 = time.time()
                    continue
                rec.update(error=f"{type(e).__name__}: {str(e)[:500]}", latency_s=round(time.time() - t0, 3))
                with lock:
                    calls.append(rec)
                raise
        d = resp.model_dump()
        rec.update(t_response=now(), latency_s=round(time.time() - t0, 3), response=d)
        with lock:
            calls.append(rec)
            if groq:
                window.setdefault(model, []).append((time.time(), (d.get("usage") or {}).get("total_tokens", 0)))
        return resp

    occ.Completions.create = logged_create

    # live-API capture (environment-drift record)
    web = []
    from langchain_community.tools import WikipediaQueryRun
    from langchain_community.tools.pubmed.tool import PubmedQueryRun
    for cls, nm in ((WikipediaQueryRun, "wikipedia"), (PubmedQueryRun, "pubmed")):
        def mk(orig, nm):
            def run(self, *args, **kw):
                t = now()
                try:
                    out = orig(self, *args, **kw)
                    err = None
                except Exception as e:
                    out, err = None, f"{type(e).__name__}: {e}"
                with lock:
                    web.append({"source": nm, "t": t, "query": args[0] if args else kw, "output": out, "error": err})
                if err: raise RuntimeError(err)
                return out
            return run
        cls.run = mk(cls.run, nm)

    # Wikimedia now answers 403 to the `wikipedia` package's default User-Agent, so the benchmark's
    # search_wikipedia tool crashes the episode. Set a descriptive UA (environment deviation, no
    # repo file touched). Recorded in the result JSON as env_deviations.
    import wikipedia.wikipedia as _w
    _w.USER_AGENT = a.wiki_user_agent

    import pandas as pd
    from huggingface_hub import hf_hub_download
    try:  # prefer the local cache (HF returns 429 on repeated unauthenticated HEADs)
        pq = hf_hub_download("SII-SPIRAL-MED/DiagnosisArena", "data/test-00000-of-00001.parquet",
                             repo_type="dataset", local_files_only=True)
    except Exception:
        pq = hf_hub_download("SII-SPIRAL-MED/DiagnosisArena", "data/test-00000-of-00001.parquet", repo_type="dataset")
    df = pd.read_parquet(pq)
    row = df[df["id"].astype(str) == str(a.task_id)]
    if len(row) != 1:
        sys.exit(f"task id {a.task_id} not found; ids look like {list(df['id'][:3])}")
    item = row.iloc[0].to_dict()
    for k, v in item.items():
        if hasattr(v, "tolist"): item[k] = v.tolist()

    from utils.run_context import RunContext
    from pipeline import run_pipeline
    args = types.SimpleNamespace(
        patient_model_name=sm["model"], patient_base_url=sm["base_url"], patient_api_key=key_of(sm),
        doctor_model_name=a.model, doctor_base_url=ag["base_url"], doctor_api_key=key_of(ag),
        doctor_responses_api=False, max_encounter_nums=8, max_talk_turns=5, max_query_nums=3,
        parallel_workers=1)

    t_start = now()
    out_jsonl = raw_dir / "episode.jsonl"
    ctx = RunContext(data_item=item, output_path=str(out_jsonl))
    error = None
    try:
        ctx = run_pipeline(args, ctx)
        if not hasattr(ctx, "process_success"):
            ctx.process_success = False
    except Exception as e:  # run_pipeline catches most itself
        error = f"{type(e).__name__}: {e}"
        ctx.process_success = False
    t_pipe_end = now()
    # benchmark's own output record (inference.py writes it only when run() reaches this line; it
    # does so regardless of process_success because `exit` there is a no-op)
    ctx.output_agent_results()
    rec = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[-1])

    # actions come from the agent's own responses (message.tool_calls), so an attempted call whose
    # execution crashed the episode is still recorded; context.tool_usages only lists completed calls.
    actions = []
    for c in calls:
        if c.get("role") == "agent" and "response" in c:
            for tc in (c["response"]["choices"][0]["message"].get("tool_calls") or []):
                try:
                    targs = json.loads(tc["function"]["arguments"])
                except Exception:
                    targs = {"_unparsable": tc["function"]["arguments"]}
                actions.append(canon(tc["function"]["name"], targs))
    recs = rec["patient_records"]
    last = recs[-1] if recs else {}
    final_state = {
        "department_path": [r.get("Recording Department") for r in recs],
        "final_diagnosis": last.get("final_diagnosis"),
        "treatment_plan": last.get("treatment_plan"),
        "process_success": rec["process_success"],
        "completed_tests": [d["test_name"] for d in rec["diagnosis_reports"]],
        "n_encounters": len(rec["doctor_patient_diaglogues"]),
        "reference_diagnosis": item["Final Diagnosis"],
        "patient_records": recs,
    }

    verdict = {"process_success": rec["process_success"], "scores": None, "pass": False}
    t_judge_start = now()
    if not a.skip_judge and rec["process_success"]:
        phase[0] = "judge"
        import evaluation as E
        ev = E.MedicalEvaluator(model=JUDGE_MODEL, base_url=jd["base_url"], api_key=key_of(jd), temperature=0.0)
        res = ev.process_single_case((1, rec))
        if res:
            verdict["scores"] = res["scores"]
            verdict["evaluation_result"] = res["evaluation_result"]
            verdict["pass"] = bool(rec["process_success"] and res["scores"].get("DR") == 1.0)
        else:
            verdict["judge_error"] = "MedicalEvaluator returned None"
    t_end = now()

    (raw_dir / "calls.json").write_text(json.dumps(calls, indent=1, default=str), encoding="utf-8")
    (raw_dir / "web_tool_payloads.json").write_text(json.dumps(web, indent=1, default=str), encoding="utf-8")
    ok = [c for c in calls if "response" in c]
    by_role = {}
    for c in ok:
        u = c["response"].get("usage") or {}
        r = by_role.setdefault(c["role"], {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        r["calls"] += 1
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            r[k] += u.get(k, 0)
    result = {
        "task_id": a.task_id,
        "condition": {"model": a.model, "temperature": a.temperature},
        "repeat": a.repeat,
        "model_ids": {"agent": a.model, "simulator": a.sim_model, "judge": JUDGE_MODEL,
                      "profile": a.profile, "agent_role": a.agent_role,
                      "digests": {m: cfg["digests"].get(m) for m in (a.model, a.sim_model, JUDGE_MODEL)},
                      "agent_response_models": sorted({c["response"].get("model") for c in ok if c["role"] == "agent"}),
                      "agent_system_fingerprint": sorted({c["response"].get("system_fingerprint") or "" for c in ok if c["role"] == "agent"}),
                      "judge_system_fingerprint": sorted({c["response"].get("system_fingerprint") or "" for c in ok if c["role"] == "judge"})},
        "timestamps": {"start": t_start, "pipeline_end": t_pipe_end, "judge_start": t_judge_start, "end": t_end},
        "actions": actions,
        "final_state": final_state,
        "verdict": verdict,
        "raw_log_path": str(raw_dir),
        "usage_by_role": by_role,
        "calls": {"total": len(calls), "ok": len(ok), "errors": len(calls) - len(ok)},
        "web_tool_fetches": [{"source": w["source"], "query": w["query"], "error": w["error"],
                              "chars": len(w["output"] or "")} for w in web],
        "error": error,
        "env_deviations": {"wikipedia_user_agent": a.wiki_user_agent,
                           "ollama_note": "*-ctx32k tags = pinned base tag + PARAMETER num_ctx 32768, same weights blob"},
    }
    (out_dir / f"{ep_name}.json").write_text(json.dumps(result, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("task_id", "actions", "usage_by_role", "calls", "error")}, indent=1))
    print("verdict:", verdict["process_success"], verdict.get("scores"), "pass=", verdict["pass"])


if __name__ == "__main__":
    main()
