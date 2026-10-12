#!/usr/bin/env python
"""Episode runner adapter for RadA-BenchPlat (synthetic layer, multihop general pipeline).

Usage (from any cwd, with the benchmark venv):
  envs/RadABench/Scripts/python runners/RadABench_runner.py \
      --task-id 0:012 --model openai/gpt-oss-20b --temperature 0 --repeat 0 \
      --out-dir smoke/RadABench

One episode = one (case, QA type) pair, e.g. task_id "0:012" = case key "0", QA chain "012".
Agent role  : routed by runners/roles.json (--profile local|groq, --agent-role agent|agent_replication);
              default local = ollama gpt-oss-20b-ctx32k (gpt-oss:20b weights, num_ctx 32768). There is no simulator or judge LLM in this benchmark: tools are
              simulated in local code and scoring is lexical (BLEU/ROUGE/F1) plus chain matching.

Output JSON: {task_id, condition:{model,temperature}, repeat, model_ids, timestamps, actions,
              final_state, verdict, raw_log_path, usage, calls, env_seed, error}

CANONICALISATION of actions
  Source: each agent step output is parsed by the benchmark's own extract_call_content() into
  {'Purpose','Tool','Input'}. One action = one step's tool call:
      "<Tool>" + json.dumps({"Input": sorted(Input list)}, sort_keys=True, separators=(",", ":"))
  e.g.  TOOL3{"Input":["$Image$","$Information$"]}
  Input is the list of reserved variables ($Image$, $OrganMask$, ...) the benchmark extracted from
  the agent's <Input> text, sorted. The free-text <Purpose> is a rationale, not an argument, and is
  excluded from the canonical string (kept in raw log). Every executed step, including the one
  tagged <EndCall>, is one action. Steps that fail to parse or name an unknown tool abort the
  episode and are recorded as "ERROR:<ExceptionType>".

Environment control: the simulated toolset is built with python's `random` at construction
  (random.sample of supported organs etc.), so the runner seeds `random` from a stable hash of
  task_id ONLY (not condition or repeat). Environment is therefore identical across repeats and
  conditions for a task. env_seed is recorded.

Verdict: the benchmark has no native pass/fail. verdict = the metrics returned by the benchmark's
  own analyze_output() (EvalMetrics/multihop_performance.py): win_rate, milestone (bool), f1, bleu,
  rouge, has_error. verdict["pass"] is OUR derived binary = milestone and not has_error; record it
  as a deviation / derived field in the paper.

final_state: the benchmark's final memory bank (value_dict / score_dict after the last tool call),
  parsed from the saved log.
"""
import argparse, ast, hashlib, json, os, random, re, sys, time, datetime, threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
REPO = EXEC / "repos" / "RadABench"
EVAL = REPO / "EvalPlat"

MAX_CHAT_CALLS = 60   # hard cap; pipelinerun recurses forever on KeyError otherwise
TPM_BUDGET = 6500     # throttle below Groq 8000 tokens/min/model


class CallCapExceeded(BaseException):
    pass


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


def canon(tool, inputs):
    return tool + json.dumps({"Input": sorted(inputs)}, sort_keys=True, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--profile", default="local", help="roles.json profile: local (default) | groq")
    ap.add_argument("--agent-role", default="agent", help="agent | agent_replication")
    ap.add_argument("--roles-config", default=str(HERE / "roles.json"))
    ap.add_argument("--model", default=None, help="override the model name from roles.json")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--repeat", type=int, default=0)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--strategies", default="")
    a = ap.parse_args()

    out_dir = Path(a.out_dir).resolve()  # resolve before chdir
    os.chdir(EVAL)
    sys.path.insert(0, str(EVAL))
    import Utils.llm_client as L  # noqa
    import EvalPipeline_multihop_general as P
    from EvalMetrics import multihop_performance as M

    case_key, qa_type = a.task_id.split(":")

    env_seed = int(hashlib.sha256(a.task_id.encode()).hexdigest()[:8], 16)
    random.seed(env_seed)

    t_start = now()
    # per-role routing from roles.json, injected into the benchmark's own registry in memory
    # (no repo file patched for this); the benchmark's LLMClient then builds its OpenAI client from it.
    role = json.load(open(a.roles_config, encoding="utf-8"))["profiles"][a.profile][a.agent_role]
    a.model = a.model or role["model"]
    ep_name = f"{case_key}_{qa_type}__{a.profile}_{a.model.replace('/', '_')}__T{a.temperature}__r{a.repeat}"
    raw_dir = out_dir / "raw" / ep_name
    raw_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RUNNER_ROLE_KEY"] = os.environ.get(role["api_key_env"], "") if role["api_key_env"] else "ollama"
    reg = L._registry()
    reg["models"]["runner-role"] = {"backend": "openai_compatible", "model_id": a.model,
                                    "base_url": role["base_url"], "api_key_env": "RUNNER_ROLE_KEY", "paper_ref": []}
    is_groq = "groq" in role["base_url"]
    if not is_groq:   # local ollama queues requests; the benchmark's default 120 s timeout would abort them
        reg["defaults"] = dict(reg.get("defaults", {}), timeout=3600)
    chatbot = P.My_Chatbot(model="runner-role", output_root=str(raw_dir / "bench_out"),
                           strategies=a.strategies)
    llm = chatbot.llm
    llm.defaults = dict(llm.defaults)
    llm.defaults["temperature"] = a.temperature
    if not is_groq:
        llm._client = llm._client.with_options(max_retries=0, timeout=3600)

    calls, window, rate_waits = [], [], [0]
    orig_create = llm._client.chat.completions.create

    def logged_create(**kw):
        if len(calls) >= MAX_CHAT_CALLS:
            raise CallCapExceeded()
        cutoff = time.time() - 60
        while is_groq:
            window[:] = [(t, n) for t, n in window if t > cutoff]
            if sum(n for _, n in window) < TPM_BUDGET:
                break
            time.sleep(3); cutoff = time.time() - 60
        rec = {"t_request": now(), "request": {k: v for k, v in kw.items()}}
        t0 = time.time()
        while True:
            try:
                resp = orig_create(**kw)
                break
            except Exception as e:  # logged then re-raised for the benchmark's own retry loop
                w = rate_limit_wait_s(e)
                if w is not None and rate_waits[0] < 12:   # wait out Groq 429s (TPD) instead of aborting
                    rate_waits[0] += 1
                    calls.append({"t_request": rec["t_request"], "error": f"{type(e).__name__}: {str(e)[:300]}",
                                  "rate_limit_wait_s": w})
                    time.sleep(w); rec["t_request"] = now(); t0 = time.time(); continue
                rec.update(error=f"{type(e).__name__}: {e}", latency_s=time.time() - t0)
                calls.append(rec)
                raise
        d = resp.model_dump()
        rec.update(t_response=now(), latency_s=round(time.time() - t0, 3), response=d)
        calls.append(rec)
        window.append((time.time(), (d.get("usage") or {}).get("total_tokens", 0)))
        return resp

    llm._client.chat.completions.create = logged_create

    qa_path = EVAL / "Data" / "combined_casesV3_qa_Subset.json"
    cases = json.load(open(qa_path, encoding="utf-8"))
    keys = list(cases)
    i = keys.index(case_key)
    j = list(cases[case_key]["QA"].keys()).index(qa_type)

    error = None
    try:
        chatbot.pipelinerun(i, j, cases, chatbot.base_path)
    except CallCapExceeded:
        error = "CallCapExceeded"
    except Exception as e:  # noqa
        error = f"{type(e).__name__}: {e}"
    t_end = now()

    # ---- gather benchmark's own saved artefacts
    logf = Path(chatbot.base_path) / "logouts" / str(i) / f"{qa_type}.txt"
    infof = Path(chatbot.base_path) / "info" / str(i) / f"{qa_type}.json"
    text = logf.read_text(encoding="utf-8") if logf.exists() else ""
    if "An error occurred:" in text and not error:
        error = "benchmark-logged: " + text.split("Error Type:")[-1].split("\n")[1:2][0] if "Error Type:" in text else "benchmark-logged error"

    # actions: from the benchmark's own parser applied to each logged step output
    actions = []
    for m in re.finditer(r"Call Dict: (\{.*?\})\n", text, re.DOTALL):
        try:
            cd = ast.literal_eval(m.group(1))
            actions.append(canon(cd["Tool"], cd["Input"]))
        except Exception:
            actions.append("ERROR:UnparsableCallDict")
    if error and not actions:
        actions.append("ERROR:" + error.split(":")[0])

    verdict = None
    final_state = None
    if text and infof.exists():
        TOOLINFO = json.load(open(infof))["TOOLINFO"]
        max_tool_dict = {"012": ["TOOL3", "TOOL4", "TOOL5"], "013": ["TOOL5", "TOOL6", "TOOL7"],
                         "014": ["TOOL9", "TOOL11", "TOOL7", "TOOL8", "TOOL10"],
                         "0123": ["TOOL3", "TOOL4", "TOOL5"], "0126": ["TOOL10", "TOOL11"],
                         "0136": ["TOOL11", "TOOL12"], "01235": ["TOOL7", "TOOL8", "TOOL10", "TOOL9", "TOOL11"],
                         "01348": ["TOOL5", "TOOL6", "TOOL7"], "0123568": ["TOOL7", "TOOL8", "TOOL10", "TOOL9", "TOOL11"],
                         "01235678": ["TOOL12", "TOOL14", "TOOL13", "TOOL15"],
                         "012356789": ["TOOL12", "TOOL14", "TOOL13", "TOOL15"]}  # copied from multihop_performance.main()
        key_map = {"012": "Organ Segmentor", "013": "Anomaly Detector", "014": "Disease Diagnoser",
                   "0123": "Organ Segmentor", "01235": "Disease Inferencer", "0126": "Biomarker Quantifier",
                   "0136": "Biomarker Quantifier", "01348": "Anomaly Detector", "0123568": "Disease Diagnoser",
                   "01235678": "Indicator Evaluator", "012356789": "Indicator Evaluator"}
        verdict = M.analyze_output(text, cases[case_key], qa_type, max_tool_dict, key_map, TOOLINFO)
        verdict["pass"] = bool(verdict["milestone"] and not verdict["has_error"])
        verdict["reference_answer"] = cases[case_key]["QA"][qa_type]["A"]
        verdict["conclusion"] = M.extract_conclusion(text)
        banks = re.findall(r"Memory bank: (\{.*?\}) \nScore bank: (\{.*?\}) \nFixed bank", text, re.DOTALL)
        if banks:
            final_state = {"value_dict_last": banks[-1][0][:4000], "score_dict_last": banks[-1][1]}
    if verdict is None:
        verdict = {"pass": False, "has_error": True}

    ok = [c for c in calls if "response" in c]
    usage = {k: sum((c["response"].get("usage") or {}).get(k, 0) for c in ok)
             for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    fps = sorted({c["response"].get("system_fingerprint") for c in ok} - {None})
    (raw_dir / "calls.json").write_text(json.dumps(calls, indent=1, default=str), encoding="utf-8")

    result = {
        "task_id": a.task_id,
        "condition": {"model": a.model, "temperature": a.temperature},
        "repeat": a.repeat,
        "model_ids": {"agent": a.model, "agent_response_model": sorted({c["response"].get("model") for c in ok}),
                      "system_fingerprint": fps, "simulator": None, "judge": None,
                      "profile": a.profile, "agent_role": a.agent_role,
                      "digest": json.load(open(a.roles_config, encoding="utf-8"))["digests"].get(a.model)},
        "timestamps": {"start": t_start, "end": t_end},
        "actions": actions,
        "final_state": final_state,
        "verdict": verdict,
        "raw_log_path": str(raw_dir),
        "usage": usage,
        "calls": {"total": len(calls), "ok": len(ok), "errors": len(calls) - len(ok)},
        "env_seed": env_seed,
        "error": error,
    }
    (out_dir / f"{ep_name}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("task_id", "actions", "usage", "calls", "error")}, indent=1))
    print("verdict:", {k: v for k, v in verdict.items() if k not in ("reference_answer", "conclusion")})


if __name__ == "__main__":
    main()
