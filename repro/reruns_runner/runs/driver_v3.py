#!/usr/bin/env python
"""Resumable full-run driver, plan-v1.md "Run design v3": AgentClinic, RadABench, synthetic_hospital.

  python runs/driver_v3.py [--bench AgentClinic RadABench synthetic_hospital] [--limit-episodes N]

Design: first 10 of each benchmark's seeded sample (random.Random(20261004).sample(pool, 15)[:10]),
  conditions A = agent at benchmark temperature (AgentClinic 0.05; others 0), B = agent at 0.7,
  5 repeats  -> 100 episodes per benchmark. Agent qwen3-4b-ctx16k; simulator/judge llama3.1-8b-ctx16k T=0
  (runs/v3_config.json, serves both runner config formats).
Pools: AgentClinic = MedQA ids 0..106 ("MedQA:<i>"); RadABench = every (case, QA chain) in the shipped
  110-case subset; synthetic_hospital = patient_diagnosis gt_ids with split=public.
Order: benchmark -> task -> condition -> repeat. Each finished episode is appended to
  runs/v3/<bench>/episodes.jsonl (runner result + driver fields); a restart skips keys already present
  (key = task|condition|repeat). Failed/timed-out episodes are appended with driver_status "failed" and are
  NOT retried automatically (delete the line to retry). Per-episode wall-clock cap 90 min.
GPU lock: runs/gpu.lock, created atomically and held for the whole run; waits while a live pid holds it.
Probe: before each benchmark the agent model gets one tool-call request (capability.json); synthetic_hospital
  needs tool calls (its conditions are skipped if the probe fails); AgentClinic and RadABench use text-format
  actions, so the probe result is recorded but does not gate them.
"""
import argparse, glob, json, os, random, sqlite3, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXEC = HERE.parent
RUNNERS = EXEC / "runners"
SEED = 20261004
CFG = HERE / "v3_config.json"
AGENT = json.load(open(CFG, encoding="utf-8"))["profiles"]["local"]["agent"]["model"]
N_TASKS = 10
REPEATS = 5
CAP_S = 90 * 60
LOCK = HERE / "gpu.lock"
# bench -> (script, venv, tool calls required, condition A temperature)
BENCH = {
    "AgentClinic": ("AgentClinic_runner.py", "AgentClinic", False, 0.05),
    "RadABench": ("RadABench_runner.py", "RadABench", False, 0.0),
    "synthetic_hospital": ("synthetic_hospital_runner.py", "synthetic_hospital", True, 0.0),
}
COND_B_TEMP = 0.7


def pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True).stdout
        return str(pid) in out
    except Exception:
        return True


def acquire():
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "t": time.time(), "driver": "v3"}).encode())
            os.close(fd)
            return
        except FileExistsError:
            try:
                info = json.load(open(LOCK))
                if not pid_alive(info.get("pid")):
                    os.remove(LOCK); continue
            except Exception:
                pass
            time.sleep(60)


def release():
    try:
        if json.load(open(LOCK)).get("pid") == os.getpid():
            os.remove(LOCK)
    except Exception:
        pass


def tasks(bench):
    r = random.Random(SEED)
    if bench == "AgentClinic":
        n = sum(1 for l in open(EXEC / "repos/AgentClinic/agentclinic_medqa.jsonl", encoding="utf-8") if l.strip())
        pool = [f"MedQA:{i}" for i in range(n)]
    elif bench == "RadABench":
        d = json.load(open(EXEC / "repos/RadABench/EvalPlat/Data/combined_casesV3_qa_Subset.json", encoding="utf-8"))
        pool = [f"{k}:{q}" for k, v in d.items() for q in v["QA"]]
    else:
        c = sqlite3.connect(f"file:{(EXEC / 'repos/synthetic_hospital/benchmark_v1.3.db').as_posix()}?mode=ro", uri=True)
        pool = [f"patient_diagnosis:{g}" for (g,) in c.execute(
            "select gt_id from benchmark_ground_truth where task='patient_diagnosis' and split='public' order by gt_id")]
    return r.sample(pool, 15)[:N_TASKS]


def probe_tools(model):
    body = {"model": model, "temperature": 0, "max_tokens": 400,
            "messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}],
            "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Get weather",
                       "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]}
    req = urllib.request.Request("http://localhost:11434/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=1800))
        return bool(d["choices"][0]["message"].get("tool_calls"))
    except Exception as e:
        return f"probe error: {e}"


def ensure_sh_stack():
    def up():
        try:
            return b"ok" in urllib.request.urlopen("http://localhost:58000/health", timeout=5).read()
        except Exception:
            return False
    if not up():
        env = dict(os.environ, APP_PORT="58000", POSTGRES_PORT="55432", REDIS_PORT="56379")
        subprocess.run(["docker", "compose", "up", "-d"], cwd=EXEC / "repos/synthetic_hospital", env=env)
        for _ in range(60):
            if up(): break
            time.sleep(10)


def command(bench, script, py, task, temp, rep, epdir):
    base = [str(py), str(RUNNERS / script)]
    if bench == "AgentClinic":
        return base + ["--task", task, "--config", str(CFG), "--temperature", str(temp),
                       "--repeat", str(rep), "--out", str(epdir)]
    return base + ["--task-id", task, "--profile", "local", "--agent-role", "agent", "--roles-config", str(CFG),
                   "--temperature", str(temp), "--repeat", str(rep), "--out-dir", str(epdir)]


def run_bench(bench, root, limit):
    script, venv, needs_tools, tempA = BENCH[bench]
    conds = [("A", tempA), ("B", COND_B_TEMP)]
    out = root / bench
    out.mkdir(parents=True, exist_ok=True)
    ep_file = out / "episodes.jsonl"
    done = set()
    if ep_file.exists():
        for line in open(ep_file, encoding="utf-8"):
            try:
                done.add(json.loads(line)["_key"])
            except Exception:
                pass
    cap_file = out / "capability.json"
    if cap_file.exists():
        cap = json.load(open(cap_file))
    else:
        cap = {AGENT: probe_tools(AGENT), "tool_calls_required": needs_tools, "probed_at": time.strftime("%F %T")}
        json.dump(cap, open(cap_file, "w"), indent=1)
    if bench == "synthetic_hospital":
        ensure_sh_stack()
    py = EXEC / "envs" / venv / "Scripts" / "python.exe"
    n_run = 0
    for task in tasks(bench):
        for cname, temp in conds:
            if needs_tools and cap.get(AGENT) is not True:
                continue   # cannot emit tool calls: skipped, recorded in capability.json
            for rep in range(REPEATS):
                key = f"{task}|{cname}|{rep}"
                if key in done:
                    continue
                if limit is not None and n_run >= limit:
                    return
                epdir = out / "episodes" / cname / f"{task.replace(':', '_')}_r{rep}"
                cmd = command(bench, script, py, task, temp, rep, epdir)
                t0 = time.time()
                rec = {"_key": key, "bench": bench, "condition_name": cname, "driver_start": t0}
                try:
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=CAP_S,
                                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                    files = [f for f in glob.glob(str(epdir / "*.json")) if Path(f).name != "calls.json"]
                    res = json.load(open(files[0], encoding="utf-8")) if len(files) == 1 else None
                    if p.returncode != 0 or res is None:
                        rec.update(driver_status="failed", returncode=p.returncode, stderr_tail=p.stderr[-1500:])
                    else:
                        rec.update(res); rec["driver_status"] = "ok"
                        if res.get("error"):
                            rec["episode_error"] = res["error"]
                except subprocess.TimeoutExpired:
                    rec.update(driver_status="failed", stderr_tail="timeout 90 min")
                rec["wall_s"] = round(time.time() - t0, 1)
                with open(ep_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")
                done.add(key)
                n_run += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", nargs="+", default=list(BENCH))
    ap.add_argument("--root", default=str(HERE / "v3"))
    ap.add_argument("--limit-episodes", type=int, default=None, help="per benchmark, for smoke runs")
    a = ap.parse_args()
    acquire()
    try:
        for b in a.bench:
            run_bench(b, Path(a.root), a.limit_episodes)
    finally:
        release()


if __name__ == "__main__":
    main()
