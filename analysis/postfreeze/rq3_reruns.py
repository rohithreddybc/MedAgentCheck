"""RQ3: executed-rerun metrics (plan-v1.md, "Run design v3" and "Metrics").

Reads research/executed/runs/v3/<bench>/episodes.jsonl and writes, per benchmark x condition:

  rq3_divergence.csv / .tex     action divergence, verdict instability, same-verdict-different-actions
  rq3_passk.csv / .tex          pass^k, k = 1..5, cluster bootstrap 95% CI (cluster = task)
  rq3_ci_width.csv / .tex       headline-score 95% CI width from 1 run (repeat 0) versus all 5 runs
  rq3_grader_state.csv / .tex   grader verdict versus observed end state (benchmarks with a state check)
  rq3_groups.csv                one row per task group (distinct sequences, verdicts, pass count)
  rq3_svda_groups.csv           task groups with a constant verdict but different action sequences
  rq3_grader_state_episodes.csv per-episode comparison behind rq3_grader_state
  rq3_status.json               n per benchmark x condition and a partial-data flag

CSV files go to analysis/out/, tex tables (booktabs, bare tabular) to paper/tables/.

Definitions (unit = task group of R = 5 identical reruns):
  canonical action sequence   the ``actions`` list of the episode record, in order (action type plus normalised
                              arguments, as produced by the runners); the ``actions_strict`` list (AgentClinic keeps
                              the full question text) is reported as a secondary divergence column.
  divergent group             more than one distinct canonical sequence among the 5 runs.
  verdict                     binary pass: AgentClinic verdict == "correct"; other benchmarks verdict["pass"], the
                              derived binary stored by the runner (see the runner docstrings).
  unstable group              the 5 verdicts are not all equal.
  pass^k                      per task the unbiased estimator C(c, k) / C(R, k) with c passes in R runs, averaged
                              over tasks; CI by percentile bootstrap over tasks (2,000 resamples, seed 20261004).
  CI width                    headline score = mean over tasks of the per-task pass rate. "1 run" uses repeat 0 only
                              (each task contributes one binary outcome); "5 runs" uses all repeats. Both use the same
                              task resamples. The mean width over single runs 0..4 is added as a second column.
  grader vs state             synthetic_hospital only. The benchmark's documented success criterion is its reward,
                              the severity-weighted chart-neutral problem-list F1 (file:line quotes in
                              analysis/README.md). It is recomputed with the benchmark's own scorer
                              (eval.scoring.compute_all_metrics, from research/executed/repos/synthetic_hospital)
                              applied to the observed final state of the episode (stored submission and stored
                              reference) and compared with the reward the grader reported. No threshold is invented:
                              disagreement = |recomputed - reported| > 1e-6. Cases where recomputation is impossible
                              are counted separately and never folded into agreement:
                                state_missing          no final state, reference or scorer available;
                                neutral_set_required   the scorer needs the patient's chart-neutral categories, which
                                                       live in the benchmark's Postgres database and are not in the
                                                       episode record. The offline value is then a lower bound (the
                                                       neutral set only removes predictions from the precision
                                                       denominator), so a reported reward at or above it is not
                                                       called a disagreement.

Only complete task groups (R successful episodes) enter the group-level metrics; partial groups and failed episodes are
counted and reported, never imputed. Rows with fewer complete tasks than expected are marked partial.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from common import OUT, ROOT, SEED, TABLES, booktabs, fci, fnum, tex_escape, write_csv

RUNS_ROOT = ROOT / "research" / "executed" / "runs" / "v3"
BENCHES = ["AgentClinic", "RadABench", "synthetic_hospital"]
DISPLAY = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}
REPEATS = 5
EXPECTED_TASKS = 10
N_BOOT = 2000
REWARD_TOL = 1e-6
SH_REPO = ROOT / "research" / "executed" / "repos" / "synthetic_hospital"
KS = range(1, REPEATS + 1)


# ------------------------------------------------------------------ loading
def load_episodes(path: Path) -> list[dict]:
    """Episode records, one per line; a repeated ``_key`` keeps the last record (resumed runs)."""
    if not Path(path).exists():
        return []
    by_key: dict[str, dict] = {}
    order: list[str] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            ep = json.loads(line)
            k = ep.get("_key") or f"{ep.get('task_id')}|{ep.get('condition_name')}|{ep.get('repeat')}|{i}"
            if k not in by_key:
                order.append(k)
            by_key[k] = ep
    return [by_key[k] for k in order]


def verdict_pass(ep: dict) -> bool | None:
    """Binary verdict, or None when the episode has no usable verdict."""
    v = ep.get("verdict")
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("correct", "pass", "true"):
            return True
        if s in ("incorrect", "fail", "false", "wrong"):
            return False
        return None
    if isinstance(v, dict) and "pass" in v:
        return bool(v["pass"])
    return None


# ANALYSIS-SIDE FIX 1 (2026-10-06, documented in analysis/out/RESULTS_SUMMARY.md and the decision log).
# The runners set ``error`` for agent-behaviour outcomes that still carry a benchmark verdict: RadABench
# "benchmark-logged: ..." (the agent supplied invalid or missing tool inputs; verdict.pass is False by the runner's
# own rule) and synthetic_hospital "model repeatedly produced no tool call" (no submission, scored 0 by the benchmark's
# rule). driver_status is "ok" for all of them. The first version of this script dropped every episode with a non-empty
# ``error``, which removed 62 of 100 RadABench and 12 of 100 Synthetic Hospital episodes and conditioned the metrics on
# the agent not failing. Default now: an episode counts when the driver finished it and it has actions and a verdict.
# ``exclude_episode_errors=True`` reproduces the earlier rule as a sensitivity analysis (outputs get a ``_errexcl`` suffix).
EXCLUDE_EPISODE_ERRORS = False


def episode_ok(ep: dict, exclude_episode_errors: bool | None = None) -> bool:
    ex = EXCLUDE_EPISODE_ERRORS if exclude_episode_errors is None else exclude_episode_errors
    return (ep.get("driver_status", "ok") == "ok" and not (ex and ep.get("error"))
            and isinstance(ep.get("actions"), list) and verdict_pass(ep) is not None)


def seq_key(actions: list) -> str:
    return json.dumps(actions, ensure_ascii=False, separators=(",", ":"))


# ------------------------------------------------------------------ groups
def build_groups(eps: list[dict], repeats: int = REPEATS) -> dict:
    """(condition, task) -> {"eps": {repeat: ep}, "complete": bool, "n_seen": int, "n_failed": int}."""
    g: dict[tuple, dict] = {}
    for ep in eps:
        key = (ep["condition_name"], ep["task_id"])
        d = g.setdefault(key, {"eps": {}, "n_seen": 0, "n_failed": 0, "temperature": None})
        d["n_seen"] += 1
        d["temperature"] = (ep.get("condition") or {}).get("temperature", d["temperature"])
        if episode_ok(ep):
            d["eps"][int(ep["repeat"])] = ep
        else:
            d["n_failed"] += 1
    for d in g.values():
        d["complete"] = all(r in d["eps"] for r in range(repeats))
    return g


def group_stats(d: dict, repeats: int = REPEATS) -> dict:
    eps = [d["eps"][r] for r in range(repeats)]
    seqs = [seq_key(e["actions"]) for e in eps]
    strict = [seq_key(e["actions_strict"]) for e in eps if isinstance(e.get("actions_strict"), list)]
    passes = [bool(verdict_pass(e)) for e in eps]
    return {
        "n_distinct_sequences": len(set(seqs)),
        "n_distinct_sequences_strict": len(set(strict)) if len(strict) == repeats else None,
        "verdicts": passes,
        "n_pass": sum(passes),
        "verdict_unstable": len(set(passes)) > 1,
    }


# ------------------------------------------------------------------ statistics
def pass_hat_k(c: int, n: int, k: int) -> float:
    return math.comb(c, k) / math.comb(n, k)


def cluster_boot(mat: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED) -> tuple[np.ndarray, np.ndarray] | None:
    """Percentile 95% CI of the column means of ``mat`` (tasks x statistics), resampling tasks (rows).
    None when fewer than two tasks."""
    n = mat.shape[0]
    if n < 2:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = mat[idx].mean(axis=1)  # n_boot x stats
    lo, hi = np.percentile(means, [2.5, 97.5], axis=0)
    return lo, hi


def passk_rows(bench: str, cond: str, temp, tasks: list[dict], status: dict) -> list[dict]:
    rows = []
    if not tasks:
        return rows
    mat = np.array([[pass_hat_k(t["n_pass"], REPEATS, k) for k in KS] for t in tasks], dtype=float)
    ci = cluster_boot(mat)
    for j, k in enumerate(KS):
        rows.append({"bench": bench, "condition": cond, "temperature": temp, "k": k,
                     "pass_hat_k": float(mat[:, j].mean()),
                     "ci_lo": float(ci[0][j]) if ci else None, "ci_hi": float(ci[1][j]) if ci else None,
                     "n_tasks": len(tasks), "n_boot": N_BOOT, "seed": SEED, **status})
    return rows


def ciwidth_row(bench: str, cond: str, temp, task_eps: list[dict], status: dict) -> dict | None:
    """task_eps: per complete task, the ordered list of the R episode records."""
    if not task_eps:
        return None
    n = len(task_eps)
    p5 = np.array([[float(verdict_pass(e)) for e in eps] for eps in task_eps])  # n x R
    out = {"bench": bench, "condition": cond, "temperature": temp, "n_tasks": n, "n_boot": N_BOOT, "seed": SEED,
           **status}
    out["score_5run"] = float(p5.mean())
    out["score_1run"] = float(p5[:, 0].mean())
    if n < 2:
        return out
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))  # shared task resamples for every column

    def width(v: np.ndarray) -> tuple[float, float, float]:
        m = v[idx].mean(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        return float(lo), float(hi), float(hi - lo)

    out["ci_lo_1run"], out["ci_hi_1run"], out["ci_width_1run"] = width(p5[:, 0])
    out["ci_lo_5run"], out["ci_hi_5run"], out["ci_width_5run"] = width(p5.mean(axis=1))
    widths = [width(p5[:, r])[2] for r in range(REPEATS)]
    out["ci_width_1run_mean_over_repeats"] = float(np.mean(widths))
    out["ci_width_1run_min"], out["ci_width_1run_max"] = float(min(widths)), float(max(widths))
    out["width_ratio_5_over_1"] = (out["ci_width_5run"] / out["ci_width_1run"]) if out["ci_width_1run"] > 0 else None
    return out


# ------------------------------------------------------------------ grader vs state
_SCORER: dict = {}


def _benchmark_scorer(repo: Path = SH_REPO):
    """The benchmark's own ``eval.scoring.compute_all_metrics`` (None when the repository is not available)."""
    key = str(repo)
    if key not in _SCORER:
        fn = None
        if (Path(repo) / "eval" / "scoring.py").exists():
            import sys

            saved = {k: v for k, v in sys.modules.items() if k == "eval" or k.startswith("eval.")}
            for k in saved:
                del sys.modules[k]
            sys.path.insert(0, str(repo))
            try:
                from eval.scoring import compute_all_metrics as fn  # type: ignore
            except Exception:  # noqa: BLE001 - a missing dependency means "recomputation impossible"
                fn = None
            finally:
                sys.path.remove(str(repo))
                for k in [k for k in sys.modules if k == "eval" or k.startswith("eval.")]:
                    del sys.modules[k]
                sys.modules.update(saved)
        _SCORER[key] = fn
    return _SCORER[key]


def recompute_reward(ep: dict, scorer=None) -> tuple[str, float | None]:
    """(status, recomputed reward) for a patient_diagnosis episode. Status: ok or state_missing."""
    fs = ep.get("final_state")
    ref = fs.get("reference") if isinstance(fs, dict) else None
    gt = ref.get("ground_truth") if isinstance(ref, dict) else None
    if not isinstance(gt, dict) or ref.get("task") not in (None, "patient_diagnosis"):
        return "state_missing", None
    scorer = scorer or _benchmark_scorer()
    if scorer is None:
        return "state_missing", None
    sub = fs.get("submission")
    if not isinstance(sub, dict):
        return "ok", 0.0  # README.md:225-226: a malformed or missing submission scores 0
    m = scorer("patient_diagnosis", [sub], [gt])
    return "ok", float(min(1.0, max(0.0, m["weighted_problem_list_f1_neutral"])))


def reconstruct_with_neutral_count(ep: dict, n_neutral: int, scorer=None) -> float | None:
    """ANALYSIS-SIDE ADDITION 3 (secondary check for ``neutral_set_required`` episodes).

    One episode is one scored patient, so the benchmark's neutral-precision is matched / (matched + unmatched - n_neutral)
    (eval/scoring.py:476-485). The chart-neutral set itself is not in the record, but the grader reports how many
    unmatched predictions it treated as neutral (``n_neutral_predictions``). Using that reported count together with the
    benchmark's own matched count and weighted recall (both recomputed offline), the reward is rebuilt exactly. This
    checks everything except the neutral count itself, which is taken from the grader and so is not independently
    verified. Not used for the primary outcome."""
    fs = ep.get("final_state") or {}
    sub, gt = fs.get("submission"), ((fs.get("reference") or {}).get("ground_truth"))
    scorer = scorer or _benchmark_scorer()
    if scorer is None or not isinstance(sub, dict) or not isinstance(gt, dict):
        return None
    m = scorer("patient_diagnosis", [sub], [gt])
    n_pred = len(sub.get("active_diagnoses") or []) + len(sub.get("chronic_conditions") or [])
    if not n_pred:
        n_pred = len(sub.get("diagnoses") or [])
    matched = round(m["problem_list_precision"] * n_pred)
    unmatched = n_pred - matched
    denom = matched + unmatched - int(n_neutral)
    prec_n = matched / denom if denom > 0 else m["problem_list_precision"]
    wr = m["weighted_problem_list_recall"]
    f1 = 0.0 if wr + prec_n == 0 else 2 * wr * prec_n / (wr + prec_n)
    return float(min(1.0, max(0.0, f1)))


def grader_state_rows(bench: str, eps: list[dict], tol: float = REWARD_TOL, scorer=None):
    per_ep, agg = [], {}
    for ep in eps:
        if not episode_ok(ep):
            continue
        fs = ep.get("final_state")
        if not (isinstance(fs, dict) and "reference" in fs):
            continue  # benchmark without an observable end state
        v = ep["verdict"] if isinstance(ep.get("verdict"), dict) else {}
        reported = v.get("reward")
        status, rec = recompute_reward(ep, scorer)
        n_neutral = (v.get("metrics") or {}).get("n_neutral_predictions")
        server = (fs.get("env_state") or {}).get("reward")
        sub_obj = fs.get("submission")
        if reported is None and sub_obj is None and status == "ok":
            # ANALYSIS-SIDE FIX 2: the agent never submitted, so the grader never ran and reported no reward
            # (README.md:225-226 would score it 0). Nothing to compare; counted separately, never as agreement.
            outcome = "no_submission"
        elif reported is None or status != "ok":
            outcome = "state_missing"
        elif abs(rec - float(reported)) <= tol:
            outcome = "agree"
        elif n_neutral and float(reported) >= rec:
            outcome = "neutral_set_required"
        else:
            outcome = "disagree"
        recon = (reconstruct_with_neutral_count(ep, n_neutral, scorer)
                 if outcome == "neutral_set_required" else None)
        per_ep.append({"bench": bench, "condition": ep["condition_name"], "task_id": ep["task_id"],
                       "reconstructed_with_reported_neutral_count": recon,
                       "reconstruction_agrees": (None if recon is None else abs(recon - float(reported)) <= tol),
                       "repeat": ep["repeat"], "reported_reward": reported, "recomputed_reward": rec,
                       "server_state_reward": server, "n_neutral_predictions_reported": n_neutral,
                       "outcome": outcome,
                       "server_state_differs_from_reported": (None if server is None or reported is None
                                                               else abs(float(server) - float(reported)) > tol)})
    for cond in sorted({r["condition"] for r in per_ep}):
        sel = [r for r in per_ep if r["condition"] == cond]

        def cnt(o, sel=sel):
            return sum(r["outcome"] == o for r in sel)

        agg[cond] = {"bench": bench, "condition": cond, "n_episodes": len(sel), "agree": cnt("agree"),
                     "disagree": cnt("disagree"), "neutral_set_required": cnt("neutral_set_required"),
                     "no_submission": cnt("no_submission"), "state_missing": cnt("state_missing"),
                     "neutral_reconstruction_agrees": sum(r["reconstruction_agrees"] is True for r in sel),
                     "neutral_reconstruction_disagrees": sum(r["reconstruction_agrees"] is False for r in sel),
                     "server_state_differs_from_reported": sum(bool(r["server_state_differs_from_reported"])
                                                               for r in sel),
                     "reward_tolerance": tol}
    return per_ep, list(agg.values())


# ------------------------------------------------------------------ main computation
def compute(runs_root: Path = RUNS_ROOT, benches: list[str] | None = None, expected_tasks: int = EXPECTED_TASKS,
            scorer=None, exclude_episode_errors: bool = False) -> dict:
    global EXCLUDE_EPISODE_ERRORS
    EXCLUDE_EPISODE_ERRORS = exclude_episode_errors
    benches = benches or BENCHES
    div_rows, passk, ciw, group_rows, svda, gs_ep, gs_agg, status = [], [], [], [], [], [], [], []
    for bench in benches:
        eps = load_episodes(Path(runs_root) / bench / "episodes.jsonl")
        if not eps:
            continue
        groups = build_groups(eps)
        conds = sorted({c for c, _ in groups})
        for cond in conds:
            keys = sorted(k for k in groups if k[0] == cond)
            temp = next((groups[k]["temperature"] for k in keys if groups[k]["temperature"] is not None), None)
            complete = [k for k in keys if groups[k]["complete"]]
            n_seen = sum(groups[k]["n_seen"] for k in keys)
            n_failed = sum(groups[k]["n_failed"] for k in keys)
            gstats = {k: group_stats(groups[k]) for k in complete}
            tasks = list(gstats.values())
            n_c = len(tasks)
            partial = n_c < expected_tasks
            st = {"tasks_complete": n_c, "tasks_expected": expected_tasks, "partial": partial}
            status.append({"bench": bench, "condition": cond, "temperature": temp,
                           "tasks_with_episodes": len(keys), "tasks_complete": n_c, "tasks_expected": expected_tasks,
                           "episodes_seen": n_seen, "episodes_ok": n_seen - n_failed,
                           "episodes_failed": n_failed, "episodes_expected": expected_tasks * REPEATS,
                           "partial": partial})
            for k in keys:
                gs = gstats.get(k)
                group_rows.append({"bench": bench, "condition": cond, "task_id": k[1],
                                   "episodes_seen": groups[k]["n_seen"], "episodes_ok": len(groups[k]["eps"]),
                                   "complete": groups[k]["complete"],
                                   "n_distinct_sequences": gs["n_distinct_sequences"] if gs else None,
                                   "n_distinct_sequences_strict": gs["n_distinct_sequences_strict"] if gs else None,
                                   "n_pass": gs["n_pass"] if gs else None,
                                   "verdicts": "".join("P" if v else "F" for v in gs["verdicts"]) if gs else None,
                                   "divergent": (gs["n_distinct_sequences"] > 1) if gs else None,
                                   "verdict_unstable": gs["verdict_unstable"] if gs else None})
            n_div = sum(t["n_distinct_sequences"] > 1 for t in tasks)
            strict_ok = [t for t in tasks if t["n_distinct_sequences_strict"] is not None]
            n_div_s = sum(t["n_distinct_sequences_strict"] > 1 for t in strict_ok) if strict_ok else None
            n_uns = sum(t["verdict_unstable"] for t in tasks)
            same = [(k, gstats[k]) for k in complete
                    if not gstats[k]["verdict_unstable"] and gstats[k]["n_distinct_sequences"] > 1]
            for k, t in same:
                svda.append({"bench": bench, "condition": cond, "task_id": k[1],
                             "verdict": "pass" if t["verdicts"][0] else "fail",
                             "n_distinct_sequences": t["n_distinct_sequences"]})
            div_rows.append({
                "bench": bench, "condition": cond, "temperature": temp, "tasks_complete": n_c,
                "tasks_expected": expected_tasks, "episodes_seen": n_seen, "episodes_failed": n_failed,
                "divergent_n": n_div, "divergent_prop": n_div / n_c if n_c else None,
                "divergent_strict_n": n_div_s,
                "divergent_strict_prop": (n_div_s / len(strict_ok)) if strict_ok else None,
                "mean_distinct_sequences": float(np.mean([t["n_distinct_sequences"] for t in tasks])) if n_c else None,
                "unstable_n": n_uns, "unstable_prop": n_uns / n_c if n_c else None,
                "same_verdict_diff_actions_n": len(same),
                "same_verdict_diff_actions_prop": len(same) / n_c if n_c else None,
                "svda_all_pass_n": sum(t["verdicts"][0] for _, t in same),
                "svda_all_fail_n": sum(not t["verdicts"][0] for _, t in same),
                "partial": partial})
            passk += passk_rows(bench, cond, temp, tasks, st)
            r = ciwidth_row(bench, cond, temp, [[groups[k]["eps"][i] for i in range(REPEATS)] for k in complete], st)
            if r:
                ciw.append(r)
        pe, agg = grader_state_rows(bench, eps, scorer=scorer)
        gs_ep += pe
        gs_agg += agg
    return {"divergence": div_rows, "passk": passk, "ci_width": ciw, "groups": group_rows, "svda": svda,
            "grader_state_episodes": gs_ep, "grader_state": gs_agg, "status": status}


# ------------------------------------------------------------------ tex
def _cond_label(cond: str, temp) -> str:
    return f"{cond} ($T{{=}}{temp:g}$)" if isinstance(temp, (int, float)) else cond


def _mark(partial: bool) -> str:
    return r"$^{\dagger}$" if partial else ""


def _header_comment(res: dict, what: str) -> str:
    part = [s for s in res["status"] if s["partial"]]
    lines = [f"Generated by analysis/rq3_reruns.py: {what}. Do not edit by hand."]
    if part:
        lines.append("PARTIAL DATA (DRAFT): rows marked with a dagger have fewer than the expected "
                     f"{EXPECTED_TASKS} complete task groups; regenerate when the runs finish.")
    return "\n".join(lines)


def tex_tables(res: dict) -> dict[str, str]:
    out = {}
    d = res["divergence"]
    rows = []
    for r in d:
        rows.append([tex_escape(DISPLAY.get(r["bench"], r["bench"])) + _mark(r["partial"]),
                     _cond_label(r["condition"], r["temperature"]),
                     f'{r["tasks_complete"]}/{r["tasks_expected"]}',
                     f'{r["divergent_n"]} ({100 * r["divergent_prop"]:.0f}\\%)' if r["tasks_complete"] else "--",
                     f'{r["unstable_n"]} ({100 * r["unstable_prop"]:.0f}\\%)' if r["tasks_complete"] else "--",
                     f'{r["same_verdict_diff_actions_n"]} ({100 * r["same_verdict_diff_actions_prop"]:.0f}\\%)'
                     if r["tasks_complete"] else "--"])
    out["rq3_divergence.tex"] = booktabs(
        "llcccc", ["Benchmark", "Condition", "Tasks", "Divergent", "Unstable", "Same verdict, diff.\\ actions"], rows,
        _header_comment(res, "action divergence, verdict instability, same verdict with different actions"))
    rows = []
    for key in sorted({(r["bench"], r["condition"]) for r in res["passk"]}):
        sel = [r for r in res["passk"] if (r["bench"], r["condition"]) == key]
        r0 = sel[0]
        cells = [f'{fnum(r["pass_hat_k"])} {fci(r["ci_lo"], r["ci_hi"])}' for r in sorted(sel, key=lambda x: x["k"])]
        rows.append([tex_escape(DISPLAY.get(key[0], key[0])) + _mark(r0["partial"]),
                     _cond_label(key[1], r0["temperature"]), f'{r0["n_tasks"]}'] + cells)
    out["rq3_passk.tex"] = booktabs(
        "llcccccc", ["Benchmark", "Condition", "Tasks"] + [f"$k={k}$" for k in KS], rows,
        _header_comment(res, "pass^k with cluster bootstrap 95% CI (cluster = task, 2000 resamples, seed 20261004)"))
    rows = []
    for r in res["ci_width"]:
        rows.append([tex_escape(DISPLAY.get(r["bench"], r["bench"])) + _mark(r["partial"]),
                     _cond_label(r["condition"], r["temperature"]), f'{r["n_tasks"]}',
                     fnum(r.get("score_1run")), fnum(r.get("ci_width_1run")),
                     fnum(r.get("score_5run")), fnum(r.get("ci_width_5run"))])
    out["rq3_ci_width.tex"] = booktabs(
        "llccccc", ["Benchmark", "Condition", "Tasks", "Score, 1 run", "CI width, 1 run", "Score, 5 runs",
                    "CI width, 5 runs"], rows,
        _header_comment(res, "headline-score 95% CI width, repeat 0 versus all 5 repeats"))
    if res["grader_state"]:
        rows = []
        for r in res["grader_state"]:
            rows.append([tex_escape(DISPLAY.get(r["bench"], r["bench"])), r["condition"], f'{r["n_episodes"]}',
                         f'{r["agree"]}', f'{r["disagree"]}', f'{r["neutral_set_required"]}', f'{r["no_submission"]}',
                         f'{r["state_missing"]}'])
        out["rq3_grader_state.tex"] = booktabs(
            "llcccccc", ["Benchmark", "Condition", "Episodes", "Agree", "Disagree", "Not recomputable (neutral set)",
                         "No submission", "State missing"], rows,
            _header_comment(res, "reported reward versus the benchmark's own scorer recomputed on the final state"))
    return out


def run(runs_root: Path = RUNS_ROOT, out_dir: Path = OUT, tables_dir: Path = TABLES, benches=None,
        expected_tasks: int = EXPECTED_TASKS, scorer=None, exclude_episode_errors: bool = False) -> dict:
    res = compute(runs_root, benches, expected_tasks, scorer, exclude_episode_errors)
    sfx = "_errexcl" if exclude_episode_errors else ""

    def nm(name: str) -> str:
        stem, dot, ext = name.rpartition(".")
        return f"{stem}{sfx}{dot}{ext}"

    out_dir, tables_dir = Path(out_dir), Path(tables_dir)
    write_csv(out_dir / nm("rq3_divergence.csv"), res["divergence"])
    write_csv(out_dir / nm("rq3_passk.csv"), res["passk"])
    write_csv(out_dir / nm("rq3_ci_width.csv"), res["ci_width"])
    write_csv(out_dir / nm("rq3_groups.csv"), res["groups"])
    write_csv(out_dir / nm("rq3_svda_groups.csv"), res["svda"],
              ["bench", "condition", "task_id", "verdict", "n_distinct_sequences"])
    if res["grader_state"]:
        write_csv(out_dir / nm("rq3_grader_state.csv"), res["grader_state"])
        write_csv(out_dir / nm("rq3_grader_state_episodes.csv"), res["grader_state_episodes"])
    write_csv(out_dir / nm("rq3_status.csv"), res["status"])
    any_partial = any(s["partial"] for s in res["status"]) or not res["status"]
    (out_dir / nm("rq3_status.json")).write_text(json.dumps(
        {"partial": any_partial, "seed": SEED, "n_boot": N_BOOT, "repeats": REPEATS,
         "exclude_episode_errors": exclude_episode_errors,
         "expected_tasks_per_condition": expected_tasks, "rows": res["status"]}, indent=2), encoding="utf-8")
    tables_dir.mkdir(parents=True, exist_ok=True)
    for name, text in tex_tables(res).items():
        (tables_dir / nm(name)).write_text(text, encoding="utf-8", newline="\n")
    res["partial"] = any_partial
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--tables", type=Path, default=TABLES)
    ap.add_argument("--bench", action="append", help="repeat to select benchmarks (default: all three)")
    ap.add_argument("--expected-tasks", type=int, default=EXPECTED_TASKS)
    ap.add_argument("--exclude-episode-errors", action="store_true",
                    help="sensitivity: drop episodes whose record has a non-empty `error` (earlier rule); *_errexcl outputs")
    a = ap.parse_args(argv)
    res = run(a.runs_root, a.out, a.tables, a.bench, a.expected_tasks, exclude_episode_errors=a.exclude_episode_errors)
    print("PARTIAL DATA" if res["partial"] else "complete data")
    for s in res["status"]:
        print(f'{s["bench"]:20s} {s["condition"]}: tasks complete {s["tasks_complete"]}/{s["tasks_expected"]}, '
              f'episodes {s["episodes_ok"]}/{s["episodes_expected"]} (failed {s["episodes_failed"]})')
    for r in res["divergence"]:
        if r["tasks_complete"]:
            print(f'{r["bench"]:20s} {r["condition"]}: divergent {r["divergent_n"]}/{r["tasks_complete"]}, '
                  f'unstable {r["unstable_n"]}, same-verdict-diff-actions {r["same_verdict_diff_actions_n"]}')


if __name__ == "__main__":
    main()
