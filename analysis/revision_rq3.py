"""Revision (reviewer 1, M6): RQ3 re-analyses from the existing episodes. No new runs, no frozen result changed.

  python analysis/revision_rq3.py            (from the project root; seed 20261004)

Reads research/executed/runs/v3/<bench>/episodes.jsonl (and the runner/driver sources for item 6) and writes

  analysis/out/rev_rq3_design.csv        item 1  task design facts
  analysis/out/rev_rq3_validity.csv      item 2  episode validity and divergence/instability, all vs clean groups
  analysis/out/rev_rq3_passk_bayes.csv   item 3  pass^k: percentile bootstrap, Bayesian bootstrap, exact intervals
  analysis/out/rev_rq3_deff.csv          item 3  pooled pass^1 Clopper-Pearson and design effect
  analysis/out/rev_rq3_cutoff.csv        item 4  Synthetic Hospital reward cut-off sensitivity
  analysis/out/rev_rq3_decomp.csv        item 5  divergence decomposition
  analysis/out/rev_rq3_seed_facts.json   item 6  seed facts read from the sources
  paper/tables/rev_rq3_validity.tex      booktabs, bare tabular
  paper/tables/rev_passk_bayes.tex       booktabs, bare tabular
  analysis/out/RESULTS_SUMMARY.md        section "7. RQ3 revision analyses" appended (replaced when it exists)

Definitions (stated again in the summary section). Unit = task group of 5 reruns of one (benchmark, condition, task).

  invalid or missing tool inputs
      RadABench: the runner's ``error`` is "benchmark-logged: ... (Missing|Invalid) ... input" (the benchmark's own
      input validation rejected a tool call; verdict.has_error is True and verdict.pass False by the runner's rule).
      Synthetic Hospital: any trace step with a non-null ``error`` or ``malformed``, an unparsable tool-argument
      string, or a failed environment step ("step failed").
      AgentClinic (no tool inputs): the doctor output did not yield exactly one DIAGNOSIS action, or the verdict is
      "error" / "no_diagnosis".
  no tool call
      The episode has no executed action (empty list or only ERROR: markers), or the runner stopped with
      "model repeatedly produced no tool call" (Synthetic Hospital: more than 8 user turns without a tool call).
  runner error
      driver_status other than "ok" (no result file), or any other non-empty ``error`` (for example CallCapExceeded),
      or provider request errors (calls.errors, n_error_calls > 0).
  invalid episode = any of the above. A group is clean when none of its 5 episodes is invalid.
  divergent group = more than one distinct ``actions`` list among the 5 runs (as in rq3_reruns.py).
  unstable group = the 5 binary verdicts are not all equal.

Bayesian bootstrap: weights ~ Dirichlet(1, ..., 1) over the 10 tasks (Rubin 1981), statistic = weighted mean of the
per-task unbiased pass^k estimator, 20,000 draws, 95% equal-tailed interval. It cannot move outside the range of the
10 task values, so it is degenerate wherever all 10 task values are equal (for example all zero).
Clopper-Pearson (exact binomial, beta quantiles): pass^1 on the pooled 50 episodes (10 tasks x 5 reruns) treats the 50
episodes as independent and is too narrow when reruns of a task agree. Design effect DEFF = 1 + (m - 1) * ICC with
m = 5 and the one-way ANOVA ICC (clipped at 0 so DEFF >= 1); the adjusted interval is the Clopper-Pearson interval at
n_eff = 50 / DEFF with the same proportion (fractional beta parameters). pass^5 is a binary outcome per task (all five
reruns pass), so its exact interval is Clopper-Pearson on 10 tasks.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta

from common import OUT, ROOT, SEED, TABLES, booktabs, fnum, read_csv, tex_escape, write_csv
import rq3_reruns as R

BENCHES = R.BENCHES
DISPLAY = R.DISPLAY
REPEATS = R.REPEATS
KS = list(R.KS)
N_BAYES = 20000
CUTOFFS = [0.3, 0.4, 0.5, 0.6, 0.7]
SUMMARY = OUT / "RESULTS_SUMMARY.md"
EXEC = ROOT / "research" / "executed"
NO_TOOL_MSG = "model repeatedly produced no tool call"
INPUT_RE = re.compile(r"^benchmark-logged:.*(Missing|Invalid).*input")


# ------------------------------------------------------------------ loading
def load() -> dict:
    """bench -> {(cond, task): [episodes sorted by repeat]} over every episode record (all have driver_status ok)."""
    out = {}
    for b in BENCHES:
        eps = R.load_episodes(R.RUNS_ROOT / b / "episodes.jsonl")
        g: dict = {}
        for e in eps:
            g.setdefault((e["condition_name"], e["task_id"]), []).append(e)
        for k in g:
            g[k].sort(key=lambda e: int(e["repeat"]))
        out[b] = g
    return out


def conds_of(groups: dict) -> list[str]:
    return sorted({c for c, _ in groups})


def _acts(ep: dict) -> list[str]:
    a = ep.get("actions")
    return a if isinstance(a, list) else []


def episode_flags(bench: str, ep: dict) -> dict:
    err = ep.get("error")
    acts = _acts(ep)
    real = [a for a in acts if not str(a).startswith("ERROR:")]
    f = {"runner_failed": ep.get("driver_status", "ok") != "ok", "invalid_input": False, "no_tool_call": False,
         "other_error": False, "request_error": False}
    if bench == "RadABench":
        f["invalid_input"] = bool(err and INPUT_RE.match(str(err)))
        f["request_error"] = (ep.get("calls") or {}).get("errors", 0) > 0
    elif bench == "synthetic_hospital":
        fs = ep.get("final_state") if isinstance(ep.get("final_state"), dict) else {}
        trace = (fs.get("env_state") or {}).get("trace") or []
        f["invalid_input"] = (any(t.get("error") or t.get("malformed") for t in trace)
                              or any("_unparsable" in str(a) for a in acts)
                              or bool(err and str(err).startswith("step failed")))
        f["request_error"] = (ep.get("calls") or {}).get("errors", 0) > 0
    else:  # AgentClinic
        n_diag = sum(str(a).startswith("DIAGNOSIS") for a in acts)
        f["invalid_input"] = n_diag != 1 or ep.get("verdict") in ("error", "no_diagnosis")
        f["request_error"] = (ep.get("n_error_calls") or 0) > 0
    f["no_tool_call"] = (not real) or err == NO_TOOL_MSG
    explained = f["invalid_input"] or err == NO_TOOL_MSG
    f["other_error"] = bool(err) and not explained
    f["invalid"] = any(f[k] for k in ("runner_failed", "invalid_input", "no_tool_call", "other_error", "request_error"))
    return f


def group_div_unst(eps: list[dict]) -> tuple[bool, bool]:
    seqs = {R.seq_key(e["actions"]) for e in eps}
    verd = {bool(R.verdict_pass(e)) for e in eps}
    return len(seqs) > 1, len(verd) > 1


# ------------------------------------------------------------------ item 1
def item1(data: dict) -> tuple[list[dict], dict]:
    rows = []
    all_tasks, n_groups = set(), 0
    for b in BENCHES:
        g = data[b]
        ta = {t for c, t in g if c == "A"}
        tb = {t for c, t in g if c == "B"}
        sizes = Counter(len(v) for v in g.values())
        reps_ok = all(sorted(int(e["repeat"]) for e in v) == list(range(REPEATS)) for v in g.values())
        extra = ""
        if b == "RadABench":
            extra = f"{len({t.split(':')[0] for t in ta})} distinct cases, {len(ta)} (case, QA chain) tasks"
        if b == "synthetic_hospital":
            pids = {e["final_state"]["env_state"]["patient_id"] for v in g.values() for e in v
                    if isinstance(e.get("final_state"), dict)}
            extra = f"{len(pids)} distinct patients"
        rows.append({"bench": b, "tasks_A": len(ta), "tasks_B": len(tb), "identical_task_sets": ta == tb,
                     "shared": len(ta & tb), "groups": len(g), "episodes": sum(len(v) for v in g.values()),
                     "episodes_per_group": "/".join(f"{k}x{v}" for k, v in sorted(sizes.items())),
                     "repeats_0_to_4_everywhere": reps_ok, "note": extra})
        all_tasks |= {(b, t) for t in ta | tb}
        n_groups += len(g)
    summ = {"distinct_tasks": len(all_tasks), "task_groups": n_groups}
    return rows, summ


# ------------------------------------------------------------------ item 2
def item2(data: dict) -> list[dict]:
    rows = []
    for b in BENCHES:
        g = data[b]
        for c in conds_of(g):
            keys = sorted(k for k in g if k[0] == c)
            eps = [e for k in keys for e in g[k]]
            fl = [episode_flags(b, e) for e in eps]
            cnt = {k: sum(f[k] for f in fl) for k in ("runner_failed", "invalid_input", "no_tool_call", "other_error",
                                                       "request_error", "invalid")}
            extra_hasflag = (sum(bool(isinstance(e.get("verdict"), dict) and e["verdict"].get("has_error")) for e in eps)
                             if b == "RadABench" else None)
            clean = [k for k in keys if not any(episode_flags(b, e)["invalid"] for e in g[k])]
            affected = len(keys) - len(clean)

            def dv(sel):
                d = [group_div_unst(g[k]) for k in sel]
                return sum(x for x, _ in d), sum(y for _, y in d), len(d)

            da, ua, na = dv(keys)
            dc, uc, nc = dv(clean)
            rows.append({"bench": b, "condition": c, "episodes": len(eps), **{f"n_{k}": v for k, v in cnt.items()},
                         "verdict_has_error_flag": extra_hasflag, "groups": na, "groups_with_invalid": affected,
                         "groups_clean": nc, "divergent_all": da, "unstable_all": ua, "divergent_clean": dc,
                         "unstable_clean": uc})
    return rows


# ------------------------------------------------------------------ item 3
def task_mat(g: dict, cond: str, passfn=None) -> np.ndarray:
    passfn = passfn or (lambda e: bool(R.verdict_pass(e)))
    rows = []
    for k in sorted(k for k in g if k[0] == cond):
        c = sum(passfn(e) for e in g[k])
        rows.append([R.pass_hat_k(c, REPEATS, kk) for kk in KS])
    return np.array(rows, dtype=float)


def bayes_boot(mat: np.ndarray, n_draw: int = N_BAYES, seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(mat.shape[0]), size=n_draw)
    s = w @ mat
    lo, hi = np.percentile(s, [2.5, 97.5], axis=0)
    return lo, hi


def clopper_pearson(x: float, n: float, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (beta-quantile) interval; x and n may be fractional (effective sample size)."""
    lo = 0.0 if x <= 0 else float(beta.ppf(alpha / 2, x, n - x + 1))
    hi = 1.0 if x >= n else float(beta.ppf(1 - alpha / 2, x + 1, n - x))
    return lo, hi


def deff_stats(y: np.ndarray) -> dict:
    """y: tasks x repeats binary matrix. One-way ANOVA ICC and the design effect for cluster size m."""
    k, m = y.shape
    p = y.mean()
    pbar = y.mean(axis=1)
    msb = m * ((pbar - p) ** 2).sum() / (k - 1)
    msw = ((y - pbar[:, None]) ** 2).sum() / (k * (m - 1))
    den = msb + (m - 1) * msw
    if den == 0:
        return {"p": float(p), "msb": float(msb), "msw": float(msw), "icc": None, "deff": None, "n_eff": None}
    icc = (msb - msw) / den
    deff = max(1.0, 1 + (m - 1) * icc)
    return {"p": float(p), "msb": float(msb), "msw": float(msw), "icc": float(icc), "deff": float(deff),
            "n_eff": float(k * m / deff)}


def item3(data: dict) -> tuple[list[dict], list[dict]]:
    ref = {(r["bench"], r["condition"], int(r["k"])): r for r in read_csv(OUT / "rq3_passk.csv")}
    prow, drow = [], []
    for b in BENCHES:
        g = data[b]
        for c in conds_of(g):
            mat = task_mat(g, c)
            n = mat.shape[0]
            plo, phi = R.cluster_boot(mat)
            blo, bhi = bayes_boot(mat)
            y = np.array([[float(R.verdict_pass(e)) for e in g[k]] for k in sorted(k for k in g if k[0] == c)])
            ds = deff_stats(y)
            x_pool = int(y.sum())
            n_pool = y.size
            cp_naive = clopper_pearson(x_pool, n_pool)
            cp_adj = clopper_pearson(ds["p"] * ds["n_eff"], ds["n_eff"]) if ds["n_eff"] else (None, None)
            x5 = int((mat[:, 4] == 1).sum())
            cp5 = clopper_pearson(x5, n)
            for j, k in enumerate(KS):
                pt = float(mat[:, j].mean())
                old = ref[(b, c, k)]
                assert abs(float(old["pass_hat_k"]) - pt) < 1e-6 and abs(float(old["ci_lo"]) - plo[j]) < 1e-6 \
                    and abs(float(old["ci_hi"]) - phi[j]) < 1e-6, f"percentile bootstrap not reproduced {b} {c} {k}"
                nz = int((mat[:, j] > 0).sum())
                zero_w = bool(phi[j] - plo[j] <= 1e-12)
                prow.append({"bench": b, "condition": c, "k": k, "pass_hat_k": pt, "pct_lo": float(plo[j]),
                             "pct_hi": float(phi[j]), "bayes_lo": float(blo[j]), "bayes_hi": float(bhi[j]),
                             "pct_zero_width": zero_w, "pct_single_task_support": nz == 1,
                             "pct_lower_at_zero": bool(plo[j] <= 1e-12), "tasks_nonzero": nz,
                             "bayes_zero_width": bool(bhi[j] - blo[j] <= 1e-12),
                             "exact_lo": (cp_naive[0] if k == 1 else cp5[0] if k == 5 else None),
                             "exact_hi": (cp_naive[1] if k == 1 else cp5[1] if k == 5 else None),
                             "exact_kind": ("CP pooled 50 episodes, independence assumed" if k == 1 else
                                            "CP on 10 tasks (binary per task)" if k == 5 else ""),
                             "exact_deff_lo": cp_adj[0] if k == 1 else None,
                             "exact_deff_hi": cp_adj[1] if k == 1 else None,
                             "n_boot_pct": R.N_BOOT, "n_draw_bayes": N_BAYES, "seed": SEED})
            drow.append({"bench": b, "condition": c, "x": x_pool, "n": n_pool, "p": ds["p"], "msb": ds["msb"],
                         "msw": ds["msw"], "icc": ds["icc"], "deff": ds["deff"], "n_eff": ds["n_eff"],
                         "cp_lo": cp_naive[0], "cp_hi": cp_naive[1], "cp_adj_lo": cp_adj[0], "cp_adj_hi": cp_adj[1],
                         "tasks_pass5": x5, "cp5_lo": cp5[0], "cp5_hi": cp5[1]})
    return prow, drow


# ------------------------------------------------------------------ item 4
def sh_pass(e: dict, cut: float) -> bool:
    v = e.get("verdict") if isinstance(e.get("verdict"), dict) else {}
    r = v.get("reward")
    return bool(v.get("done") and r is not None and float(r) >= cut)


def item4(data: dict) -> tuple[list[dict], dict]:
    g = data["synthetic_hospital"]
    allep = [e for v in g.values() for e in v]
    # the frozen rule (runner line 254: done and reward is not None and reward >= 0.5) must be reproduced exactly
    assert all(sh_pass(e, 0.5) == bool(R.verdict_pass(e)) for e in allep), "0.5 cut-off does not reproduce verdict.pass"
    rewards = [float(e["verdict"]["reward"]) for e in allep if e["verdict"].get("reward") is not None]
    info = {"n_with_reward": len(rewards), "n_no_reward": len(allep) - len(rewards),
            "n_reward_exactly_0.5": sum(abs(r - 0.5) < 1e-12 for r in rewards),
            "n_reward_in_[0.3,0.5)": sum(0.3 <= r < 0.5 - 1e-12 for r in rewards),
            "n_reward_in_[0.5,0.6)": sum(0.5 - 1e-12 <= r < 0.6 for r in rewards),
            "n_reward_in_[0.6,0.7)": sum(0.6 <= r < 0.7 for r in rewards),
            "n_reward_ge_0.7": sum(r >= 0.7 for r in rewards),
            "distinct_rewards": sorted({round(r, 3) for r in rewards})}
    rows = []
    for cut in CUTOFFS:
        for c in conds_of(g):
            mat = task_mat(g, c, lambda e, cut=cut: sh_pass(e, cut))
            keys = sorted(k for k in g if k[0] == c)
            unst = sum(len({sh_pass(e, cut) for e in g[k]}) > 1 for k in keys)
            n_pass = sum(sh_pass(e, cut) for k in keys for e in g[k])
            blo, bhi = bayes_boot(mat)
            rows.append({"cutoff": cut, "condition": c, "episodes_pass": n_pass, "episodes": 5 * len(keys),
                         **{f"pass_hat_{k}": float(mat[:, k - 1].mean()) for k in KS},
                         "unstable_n": unst, "tasks": len(keys), "pass1_bayes_lo": float(blo[0]),
                         "pass1_bayes_hi": float(bhi[0]), "is_frozen_cutoff": abs(cut - 0.5) < 1e-12})
    return rows, info


# ------------------------------------------------------------------ item 5
def _name(a: str) -> str:
    return str(a).split("{", 1)[0]


def _atype(a: str) -> str:
    return str(a).split(":", 1)[0]


def decomp_views(bench: str) -> dict:
    """view name -> function(episode) -> hashable representation."""
    if bench == "AgentClinic":
        return {
            "full canonical sequence (current)": lambda e: tuple(_acts(e)),
            "tests only (REQUEST_TEST items, in order)": lambda e: tuple(a for a in _acts(e) if a.startswith("REQUEST_TEST")),
            "diagnosis only (DIAGNOSIS item)": lambda e: tuple(a for a in _acts(e) if a.startswith("DIAGNOSIS")),
            "action-type sequence (ASK / REQUEST_TEST / DIAGNOSIS)": lambda e: tuple(_atype(a) for a in _acts(e)),
            "number of ASK turns only": lambda e: sum(a == "ASK" for a in _acts(e)),
        }
    views = {
        "full canonical sequence (current)": lambda e: tuple(_acts(e)),
        "tool-name-only sequence (no arguments)": lambda e: tuple(_name(a) for a in _acts(e)),
        "tool-name set (unordered)": lambda e: frozenset(_name(a) for a in _acts(e)),
    }
    if bench == "synthetic_hospital":
        views["final submission only (submit_diagnosis call)"] = lambda e: next(
            (a for a in _acts(e) if str(a).startswith("submit_diagnosis")), "NONE")
    return views


def item5(data: dict) -> list[dict]:
    rows = []
    for b in BENCHES:
        g = data[b]
        for c in conds_of(g):
            keys = sorted(k for k in g if k[0] == c)
            clean = [k for k in keys if not any(episode_flags(b, e)["invalid"] for e in g[k])]
            unst = sum(len({bool(R.verdict_pass(e)) for e in g[k]}) > 1 for k in keys)
            for name, fn in decomp_views(b).items():
                def n_div(sel):
                    return sum(len({fn(e) for e in g[k]}) > 1 for k in sel)

                rows.append({"bench": b, "condition": c, "view": name, "divergent_all": n_div(keys),
                             "groups_all": len(keys), "divergent_clean": n_div(clean), "groups_clean": len(clean),
                             "mean_distinct_all": float(np.mean([len({fn(e) for e in g[k]}) for k in keys])),
                             "unstable_all": unst})
    return rows


# ------------------------------------------------------------------ item 6
def item6(data: dict) -> dict:
    files = {"driver_v3.py": EXEC / "runs" / "driver_v3.py", "v3_config.json": EXEC / "runs" / "v3_config.json",
             "AgentClinic_runner.py": EXEC / "runners" / "AgentClinic_runner.py",
             "RadABench_runner.py": EXEC / "runners" / "RadABench_runner.py",
             "synthetic_hospital_runner.py": EXEC / "runners" / "synthetic_hospital_runner.py",
             "runner_common.py": EXEC / "runners" / "runner_common.py",
             "AgentClinic patched agentclinic.py (model call)": EXEC / "repos" / "AgentClinic" / "agentclinic.py",
             "RadABench llm_client.py (model call)": EXEC / "repos" / "RadABench" / "EvalPlat" / "Utils" / "llm_client.py"}
    hits = {}
    for name, p in files.items():
        if not p.exists():
            hits[name] = ["(file not found)"]
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        hits[name] = [f"{i}: {l.strip()[:160]}" for i, l in enumerate(lines, 1) if re.search(r"seed", l, re.I)]
    # request payloads actually sent, from the per-episode raw logs
    req_keys: dict = defaultdict(Counter)
    n_logs = 0
    for b in BENCHES:
        for p in (R.RUNS_ROOT / b / "episodes").rglob("calls.json*"):
            n_logs += 1
            try:
                if p.suffix == ".jsonl":
                    recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
                    keys = {k for r in recs for k in r}
                    req_keys[(b, "calls.jsonl: logged fields")].update(keys)
                else:
                    recs = json.loads(p.read_text(encoding="utf-8"))
                    for r in recs:
                        if isinstance(r.get("request"), dict):
                            req_keys[(b, "request body keys")].update(r["request"].keys())
            except Exception:  # noqa: BLE001
                continue
    seed_in_requests = {f"{b} {kind}": ("seed" in cnt) for (b, kind), cnt in req_keys.items()}
    conf = json.loads(files["v3_config.json"].read_text(encoding="utf-8"))
    env_seeds = Counter()
    for b in ("RadABench",):
        for v in data[b].values():
            for e in v:
                env_seeds[(e["task_id"], e.get("env_seed"))] += 1
    task_seed_pairs = {}
    for (t, s), n in env_seeds.items():
        task_seed_pairs.setdefault(t, set()).add(s)
    return {"source_lines_matching_seed": hits, "raw_logs_scanned": n_logs,
            "request_payloads_contain_seed_key": seed_in_requests,
            "request_keys_seen": {f"{b} {kind}": sorted(cnt) for (b, kind), cnt in req_keys.items()},
            "role_temperatures_in_v3_config": {k: v.get("temperature") for k, v in conf["roles"].items()},
            "ollama_option_keys_in_config": [k for k in json.dumps(conf).split('"') if k in ("seed", "num_predict",
                                                                                              "top_k", "top_p")],
            "radabench_env_seed_values_per_task_constant": all(len(v) == 1 for v in task_seed_pairs.values()),
            "radabench_distinct_env_seeds": len({next(iter(v)) for v in task_seed_pairs.values()})}


# ------------------------------------------------------------------ tex
def tex_validity(rows: list[dict]) -> str:
    out = []
    for r in rows:
        d = lambda a, n: f"{a}/{n}" if n else "--"  # noqa: E731
        out.append([tex_escape(DISPLAY[r["bench"]]), r["condition"], f'{r["n_invalid"]}/{r["episodes"]}',
                    str(r["n_invalid_input"]), str(r["n_no_tool_call"]), f'{r["groups_clean"]}/{r["groups"]}',
                    d(r["divergent_all"], r["groups"]), d(r["divergent_clean"], r["groups_clean"]),
                    d(r["unstable_all"], r["groups"]), d(r["unstable_clean"], r["groups_clean"])])
    cm = ("Generated by analysis/revision_rq3.py: episode validity and divergence/instability on all groups versus "
          "groups with no invalid episode. Invalid = invalid or missing tool input, no tool call, or runner error. "
          "Do not edit by hand.")
    return booktabs("llcccccccc",
                    ["Benchmark", "Cond.", "Invalid ep.", "Invalid input", "No tool call", "Clean groups",
                     "Div., all", "Div., clean", "Unst., all", "Unst., clean"], out, cm,
                    midrules_after={1, 3})


def _iv(lo, hi) -> str:
    return f"[{lo:.2f}, {hi:.2f}]"


def tex_passk(prow: list[dict], drow: list[dict]) -> str:
    rows, mids = [], set()
    for b in BENCHES:
        for c in ("A", "B"):
            sel = [r for r in prow if r["bench"] == b and r["condition"] == c]
            for r in sorted(sel, key=lambda x: x["k"]):
                mark = ""
                if r["pct_zero_width"]:
                    mark = r"$^{\dagger}$"
                elif r["pct_single_task_support"]:
                    mark = r"$^{\ddagger}$"
                ex = _iv(r["exact_lo"], r["exact_hi"]) if r["exact_lo"] is not None else "--"
                exa = _iv(r["exact_deff_lo"], r["exact_deff_hi"]) if r["exact_deff_lo"] is not None else "--"
                rows.append([tex_escape(DISPLAY[b]) if r["k"] == 1 else "", c if r["k"] == 1 else "", str(r["k"]),
                             fnum(r["pass_hat_k"]), _iv(r["pct_lo"], r["pct_hi"]) + mark,
                             _iv(r["bayes_lo"], r["bayes_hi"]), ex, exa])
            mids.add(len(rows) - 1)
    cm = ("Generated by analysis/revision_rq3.py: pass^k with percentile bootstrap (2000 resamples), Bayesian bootstrap "
          "(Dirichlet weights over the 10 tasks, 20000 draws) and exact intervals; seed 20261004. "
          "Exact: k=1 Clopper-Pearson on the pooled 50 episodes (independence assumed); DEFF-adj. = same proportion "
          "at n_eff = 50/DEFF; k=5 Clopper-Pearson on 10 tasks. Dagger: percentile interval has zero width. "
          "Double dagger: only one of the 10 task values is nonzero. Do not edit by hand.")
    return booktabs("llcccccc", ["Benchmark", "Cond.", "$k$", "pass$^k$", "Percentile bootstrap", "Bayesian bootstrap",
                                 "Exact (pooled / 10 tasks)", "Exact, DEFF-adj."], rows, cm, midrules_after=mids)


# ------------------------------------------------------------------ markdown
def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


def f2(x) -> str:
    return "--" if x is None else f"{x:.2f}"


def build_md(d1, s1, v2, p3, dd3, r4, i4, r5, s6) -> str:
    L = []
    L.append("## 7. RQ3 revision analyses (reviewer 1, M6; added 2026-10-06)")
    L.append("")
    L.append("Command (project root): `python analysis/revision_rq3.py`. Seed 20261004 (percentile bootstrap 2,000 "
             "resamples, Bayesian bootstrap 20,000 draws). Reads `research/executed/runs/v3/*/episodes.jsonl` only; no "
             "new runs; the frozen RQ3 outputs (`rq3_*.csv`, `paper/tables/rq3_*.tex`) are not touched. The percentile "
             "bootstrap in `rq3_passk.csv` and the 0.5 cut-off are reproduced exactly inside the script (assertions "
             "passed). Sources: `rev_rq3_design.csv`, `rev_rq3_validity.csv`, `rev_rq3_passk_bayes.csv`, "
             "`rev_rq3_deff.csv`, `rev_rq3_cutoff.csv`, `rev_rq3_decomp.csv`, `rev_rq3_seed_facts.json` in "
             "`analysis/out/`; tables `paper/tables/rev_rq3_validity.tex`, `paper/tables/rev_passk_bayes.tex`.")
    L.append("")
    L.append("### 7.1 Task design")
    L.append("")
    L.append(md_table(["Benchmark", "Tasks in A", "Tasks in B", "Identical sets", "Groups", "Episodes",
                       "Episodes per group", "Repeats 0-4 in every group", "Note"],
                      [[DISPLAY[r["bench"]], r["tasks_A"], r["tasks_B"], r["identical_task_sets"], r["groups"],
                        r["episodes"], r["episodes_per_group"], r["repeats_0_to_4_everywhere"], r["note"]]
                       for r in d1]))
    L.append("")
    L.append(f"Confirmed: within each benchmark conditions A and B use the same 10 tasks, giving "
             f"{s1['distinct_tasks']} distinct (benchmark, task) pairs and {s1['task_groups']} task groups "
             "(3 benchmarks x 2 conditions x 10 tasks), each with 5 reruns. The driver builds the task list once per "
             "benchmark (`tasks(bench)` in `driver_v3.py`) and loops over conditions inside it. The 10 tasks are the "
             "first 10 of a seeded sample of 15 (`random.Random(20261004).sample(pool, 15)[:10]`). Consequence: the 20 "
             "groups of a benchmark are 10 tasks observed twice, so conditions A and B are paired and not independent "
             "samples; tests or intervals that treat 20 groups as exchangeable are wrong.")
    L.append("")
    L.append("### 7.2 Episode validity and divergence/instability on clean groups")
    L.append("")
    L.append("Definitions (from the runner and episode fields; an episode can fall in more than one category): "
             "invalid or missing tool inputs = RadABench `error` matching `benchmark-logged: ... (Missing|Invalid) ... "
             "input` (the benchmark's own validation rejected a call; `verdict.has_error` True, `verdict.pass` False by "
             "the runner rule); Synthetic Hospital trace step with `error` or `malformed`, unparsable tool arguments or "
             "a failed environment step; AgentClinic (no tool inputs) a doctor output without exactly one DIAGNOSIS "
             "action or verdict `error`/`no_diagnosis`. No tool call = no executed action, or the Synthetic Hospital "
             "runner stop `model repeatedly produced no tool call` (more than 8 user turns without a tool call). Runner "
             "error = `driver_status` not `ok`, any other non-empty `error`, or provider request errors. Clean group = "
             "none of its 5 episodes is invalid. Divergent and unstable as in section 1.2.")
    L.append("")
    L.append(md_table(["Benchmark", "Cond", "Episodes", "Invalid input", "No tool call", "Runner error", "Other error",
                       "Any invalid", "Groups with invalid", "Clean groups", "Divergent all", "Divergent clean",
                       "Unstable all", "Unstable clean"],
                      [[DISPLAY[r["bench"]], r["condition"], r["episodes"], r["n_invalid_input"], r["n_no_tool_call"],
                        r["n_runner_failed"], r["n_other_error"], r["n_invalid"], f'{r["groups_with_invalid"]}/{r["groups"]}',
                        f'{r["groups_clean"]}/{r["groups"]}', f'{r["divergent_all"]}/{r["groups"]}',
                        f'{r["divergent_clean"]}/{r["groups_clean"]}' if r["groups_clean"] else "--",
                        f'{r["unstable_all"]}/{r["groups"]}',
                        f'{r["unstable_clean"]}/{r["groups_clean"]}' if r["groups_clean"] else "--"] for r in v2]))
    L.append("")
    ra = [r for r in v2 if r["bench"] == "RadABench"]
    L.append(f"RadABench `verdict.has_error` is True in {sum(r['verdict_has_error_flag'] for r in ra)} of 100 "
             "episodes, the same episodes as the invalid-input count. Clean-group rows with 0 or very few groups carry "
             "no information about divergence or instability; read them as 'not estimable', not as agreement.")
    L.append("")
    L.append("### 7.3 pass^k intervals: percentile bootstrap, Bayesian bootstrap, exact")
    L.append("")
    L.append(md_table(["Benchmark", "Cond", "k", "pass^k", "Percentile (current)", "Bayesian bootstrap",
                       "Exact (k=1 pooled 50 eps; k=5 10 tasks)", "Exact DEFF-adj. (k=1)", "Flags"],
                      [[DISPLAY[r["bench"]], r["condition"], r["k"], f2(r["pass_hat_k"]),
                        _iv(r["pct_lo"], r["pct_hi"]), _iv(r["bayes_lo"], r["bayes_hi"]),
                        _iv(r["exact_lo"], r["exact_hi"]) if r["exact_lo"] is not None else "--",
                        _iv(r["exact_deff_lo"], r["exact_deff_hi"]) if r["exact_deff_lo"] is not None else "--",
                        ", ".join(x for x, c in (("pct zero-width", r["pct_zero_width"]),
                                                 ("pct driven by 1 task", r["pct_single_task_support"]),
                                                 ("pct lower=0", r["pct_lower_at_zero"]),
                                                 ("Bayes zero-width", r["bayes_zero_width"])) if c) or "--"]
                       for r in p3]))
    L.append("")
    L.append("Pooled pass^1 and design effect (m = 5 reruns per task, one-way ANOVA ICC, DEFF = 1 + 4 x ICC clipped at 1):")
    L.append("")
    L.append(md_table(["Benchmark", "Cond", "Pass / episodes", "p", "ICC", "DEFF", "n_eff", "CP pooled (naive)",
                       "CP at n_eff", "Tasks with 5/5 passes", "CP pass^5 (10 tasks)"],
                      [[DISPLAY[r["bench"]], r["condition"], f'{r["x"]}/{r["n"]}', f2(r["p"]),
                        f2(r["icc"]), f2(r["deff"]), f'{r["n_eff"]:.1f}' if r["n_eff"] else "--",
                        _iv(r["cp_lo"], r["cp_hi"]),
                        _iv(r["cp_adj_lo"], r["cp_adj_hi"]) if r["cp_adj_lo"] is not None else "--",
                        r["tasks_pass5"], _iv(r["cp5_lo"], r["cp5_hi"])] for r in dd3]))
    L.append("")
    zw = [r for r in p3 if r["pct_zero_width"]]
    L.append("Degenerate percentile cells (zero width): " + (", ".join(
        f'{DISPLAY[r["bench"]]} {r["condition"]} k={r["k"]}' for r in zw) or "none")
        + ". The Bayesian bootstrap is degenerate in exactly the same cells (it cannot leave the range of the task "
        "values), so it does not repair them; the exact 10-task interval at k=5 does (0 of 10 tasks with 5/5 passes "
        "gives an upper limit of 0.31). A pooled-episode Clopper-Pearson interval treats the 50 episodes as "
        "independent and is narrower than the task-level uncertainty supports whenever DEFF exceeds 1; the DEFF-adjusted "
        "column is an approximation (fractional counts), not an exact interval. With 10 tasks per cell every interval "
        "here is wide, and A and B share their tasks (section 7.1).")
    L.append("")
    L.append("### 7.4 Synthetic Hospital pass cut-off sensitivity")
    L.append("")
    L.append("Where 0.5 is set: `research/executed/runners/synthetic_hospital_runner.py` line 254, "
             "`\"pass\": bool(done and reward is not None and reward >= 0.5)`, documented at lines 43-44 as a derived "
             "binary used only for pass^k bookkeeping; `analysis/rq3_reruns.py` reads `verdict[\"pass\"]` and has no "
             "threshold of its own. The benchmark itself defines no pass/fail. Here the cut-off is varied on the stored "
             "`verdict.reward` (episodes without a submission have no reward and fail at every cut-off). The 0.5 row "
             "reproduces the frozen `verdict.pass` for all 100 episodes (assertion passed).")
    L.append("")
    L.append(md_table(["Cut-off", "Cond", "Episodes passing", "pass^1", "pass^2", "pass^3", "pass^4", "pass^5",
                       "Unstable groups", "pass^1 Bayesian 95%"],
                      [[f'{r["cutoff"]:.1f}' + (" (frozen)" if r["is_frozen_cutoff"] else ""), r["condition"],
                        f'{r["episodes_pass"]}/{r["episodes"]}', *[f2(r[f"pass_hat_{k}"]) for k in KS],
                        f'{r["unstable_n"]}/{r["tasks"]}', _iv(r["pass1_bayes_lo"], r["pass1_bayes_hi"])] for r in r4]))
    L.append("")
    L.append(f"Reward distribution (n = {i4['n_with_reward']} episodes with a reward, {i4['n_no_reward']} without): "
             f"{i4['n_reward_in_[0.3,0.5)']} in [0.3, 0.5), {i4['n_reward_exactly_0.5']} exactly 0.5, "
             f"{i4['n_reward_in_[0.5,0.6)']} in [0.5, 0.6), {i4['n_reward_in_[0.6,0.7)']} in [0.6, 0.7), "
             f"{i4['n_reward_ge_0.7']} at or above 0.7; distinct values {i4['distinct_rewards']}. Because rewards "
             "cluster on a few values, the cut-off acts on whole clusters; the frozen result is not changed.")
    L.append("")
    L.append("### 7.5 Divergence decomposition")
    L.append("")
    L.append("Computed on all complete groups (the current rule); the clean-group count is alongside. 'Tool-name' "
             "views drop every argument. AgentClinic canonical actions already drop the question text (`ASK`), so its "
             "full sequence is ASK count and order, test names and the diagnosis string.")
    L.append("")
    L.append(md_table(["Benchmark", "Cond", "View", "Divergent (all groups)", "Mean distinct sequences",
                       "Divergent (clean groups)", "Unstable verdict groups (context)"],
                      [[DISPLAY[r["bench"]], r["condition"], r["view"], f'{r["divergent_all"]}/{r["groups_all"]}',
                        f2(r["mean_distinct_all"]),
                        f'{r["divergent_clean"]}/{r["groups_clean"]}' if r["groups_clean"] else "--",
                        f'{r["unstable_all"]}/{r["groups_all"]}'] for r in r5]))
    L.append("")
    L.append("Not decomposable from the stored records: AgentClinic question text is kept only in `actions_strict` "
             "(already reported in section 1.2); RadABench tool arguments are variable names ($Image$, ...), not "
             "values, so 'argument-only' divergence is the variable-set difference already inside the canonical string.")
    L.append("")
    L.append("### 7.6 Seeds for agent, simulator and ollama (facts only)")
    L.append("")
    sl = s6["source_lines_matching_seed"]
    L.append("- Lines containing `seed` in the harness: " + "; ".join(
        f"`{k}`: " + (" | ".join(v) if v else "none") for k, v in sl.items()) + ".")
    L.append(f"- Request payloads actually sent, from {s6['raw_logs_scanned']} raw call logs: "
             + "; ".join(f"{k} = {sorted(v)}" for k, v in s6["request_keys_seen"].items())
             + ". `seed` key present in any request: " + str(any(s6["request_payloads_contain_seed_key"].values())) + ".")
    L.append("- `v3_config.json` role temperatures: " + ", ".join(
        f"{k} = {v}" for k, v in s6["role_temperatures_in_v3_config"].items())
        + " (agent null in the role block; the driver passes 0.05, 0 or 0.7 per condition). Ollama option keys "
        f"`seed`, `top_k`, `top_p`, `num_predict` in the config: {s6['ollama_option_keys_in_config'] or 'none'}. "
        "The derived tags only carry `num_ctx` 16384 per the config note (the 16k Modelfiles are not in "
        "`research/executed/ollama_modelfiles`, which holds 32k Modelfiles; not verified here).")
    L.append("- The only seeds fixed anywhere are the task sampler (`random.Random(20261004)` in `driver_v3.py`) and the "
             "RadABench environment (`random.seed(sha256(task_id)[:8])` in `RadABench_runner.py`, same for all "
             f"repeats and conditions of a task; {s6['radabench_distinct_env_seeds']} distinct values, constant within "
             f"each task: {s6['radabench_env_seed_values_per_task_constant']}). Agent and simulator/judge calls "
             "(AgentClinic through the patched `openai.ChatCompletion.create`, RadABench through `llm_client._chat_openai`, "
             "Synthetic Hospital through `client.chat.completions.create`) send `temperature` and `max_tokens` (and "
             "`tools` for Synthetic Hospital) and no `seed`. Synthetic Hospital resets with an explicit `gt_id`, so the "
             "server-side seed argument is unused. Whatever default seed or sampling state the ollama server applies when "
             "none is sent is not recorded in the episodes and was not inspected.")
    L.append("")
    return "\n".join(L)


def write_summary(text: str) -> None:
    raw = SUMMARY.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    body = raw.replace("\r\n", "\n")
    m = re.search(r"^## 7\. RQ3 revision analyses.*?(?=^## \d+\. |\Z)", body, re.S | re.M)
    if m:
        body = body[:m.start()] + body[m.end():]
    body = body.rstrip("\n") + "\n\n" + text.rstrip("\n") + "\n"
    if crlf:
        body = body.replace("\n", "\r\n")
    SUMMARY.write_bytes(body.encode("utf-8"))


def main() -> None:
    data = load()
    d1, s1 = item1(data)
    v2 = item2(data)
    p3, dd3 = item3(data)
    r4, i4 = item4(data)
    r5 = item5(data)
    s6 = item6(data)
    write_csv(OUT / "rev_rq3_design.csv", d1)
    write_csv(OUT / "rev_rq3_validity.csv", v2)
    write_csv(OUT / "rev_rq3_passk_bayes.csv", p3)
    write_csv(OUT / "rev_rq3_deff.csv", dd3)
    write_csv(OUT / "rev_rq3_cutoff.csv", r4)
    write_csv(OUT / "rev_rq3_decomp.csv", r5)
    (OUT / "rev_rq3_seed_facts.json").write_text(json.dumps(s6, indent=2, default=str), encoding="utf-8")
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / "rev_rq3_validity.tex").write_text(tex_validity(v2), encoding="utf-8", newline="\n")
    (TABLES / "rev_passk_bayes.tex").write_text(tex_passk(p3, dd3), encoding="utf-8", newline="\n")
    write_summary(build_md(d1, s1, v2, p3, dd3, r4, i4, r5, s6))
    print("distinct tasks", s1["distinct_tasks"], "groups", s1["task_groups"])
    for r in v2:
        print(r["bench"], r["condition"], "invalid", r["n_invalid"], "input", r["n_invalid_input"], "notool",
              r["n_no_tool_call"], "clean", r["groups_clean"], "div", r["divergent_all"], r["divergent_clean"],
              "unst", r["unstable_all"], r["unstable_clean"])
    for r in r4:
        print("cut", r["cutoff"], r["condition"], [round(r[f"pass_hat_{k}"], 2) for k in KS], "unst", r["unstable_n"])
    for r in r5:
        print(r["bench"], r["condition"], r["view"], r["divergent_all"], r["divergent_clean"], "/", r["groups_clean"])


if __name__ == "__main__":
    sys.exit(main())
