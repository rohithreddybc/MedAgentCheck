"""Co-author review analyses (response round 1): paired temperature contrasts for the executed reruns.

Reads analysis/out/rq3_groups.csv (one row per task group: benchmark, condition, task, passes out of 5, divergent,
verdict_unstable). Nothing is rescored and no model is called.

For each benchmark (10 tasks) and for all 30 tasks pooled, the same task is observed under condition A (the benchmark's
own temperature) and condition B (T = 0.7). Per-task paired difference d_t = B - A of
  pass^1   c_t / 5                         (unbiased estimator, C(c,1)/C(5,1))
  pass^5   C(c_t, 5) / C(5, 5)             (1 when all five runs pass, else 0)
  divergence   1 if the five runs of the task yield more than one canonical action sequence, else 0
  instability  1 if the five runs of the task yield more than one verdict, else 0
Reported: mean paired difference, 95% percentile paired bootstrap interval over tasks (2,000 resamples, seed 20261004;
one resample serves every statistic; the pooled interval resamples tasks within benchmark), and an exact two-sided
binomial sign test on the tasks with a non-zero difference.

Run from the project root:
    python analysis/revision_coauthor.py                  # computes, writes CSV/JSON and paper/tables/coauthor_paired.tex
    python analysis/revision_coauthor.py --write-summary  # also (re)writes section 9 of analysis/out/RESULTS_SUMMARY.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict

import numpy as np
from scipy import stats as sps

from common import OUT, SEED, TABLES, write_csv

N_BOOT = 2000
R = 5
DISPLAY = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}
STATS = [("pass1", "pass$^1$"), ("pass5", "pass$^5$"), ("divergence", "Action divergence"), ("instability", "Verdict instability")]


def load() -> dict:
    rows = list(csv.DictReader(open(OUT / "rq3_groups.csv", encoding="utf-8")))
    by = defaultdict(dict)
    for r in rows:
        assert r["complete"] == "True" and int(r["episodes_ok"]) == R
        by[(r["bench"], r["task_id"])][r["condition"]] = r
    assert len(by) == 30 and all(set(v) == {"A", "B"} for v in by.values())
    return by


def task_stats(r: dict) -> dict:
    c = int(r["n_pass"])
    return {"pass1": math.comb(c, 1) / math.comb(R, 1), "pass5": math.comb(c, 5) / math.comb(R, 5),
            "divergence": 1.0 if r["divergent"] == "True" else 0.0,
            "instability": 1.0 if r["verdict_unstable"] == "True" else 0.0}


def main(write_summary: bool) -> None:
    by = load()
    benches = sorted({b for b, _ in by})
    tasks = {b: sorted(t for bb, t in by if bb == b) for b in benches}
    # per-task values under each condition and the paired difference B - A
    A, B, D = {}, {}, {}
    for (b, t), v in by.items():
        A[(b, t)], B[(b, t)] = task_stats(v["A"]), task_stats(v["B"])
        D[(b, t)] = {s: B[(b, t)][s] - A[(b, t)][s] for s, _ in STATS}
    # sanity: condition means equal the stored pass^k table
    pk = {(r["bench"], r["condition"], r["k"]): float(r["pass_hat_k"]) for r in csv.DictReader(open(OUT / "rq3_passk.csv", encoding="utf-8"))}
    for b in benches:
        for cond, M in (("A", A), ("B", B)):
            for k, s in (("1", "pass1"), ("5", "pass5")):
                m = float(np.mean([M[(b, t)][s] for t in tasks[b]]))
                assert abs(m - pk[(b, cond, k)]) < 0.0051, (b, cond, k, m, pk[(b, cond, k)])

    rng = np.random.default_rng(SEED)
    idx10 = rng.integers(0, 10, size=(N_BOOT, 10))  # one resample serves every statistic and every benchmark
    out_rows, res = [], {}
    groups = [(b, [(b, t) for t in tasks[b]]) for b in benches] + [("All three", [(b, t) for b in benches for t in tasks[b]])]
    for name, keys in groups:
        for s, label in STATS:
            d = np.array([D[k][s] for k in keys])
            a = np.array([A[k][s] for k in keys])
            bb = np.array([B[k][s] for k in keys])
            if name == "All three":  # resample tasks within benchmark, then pool
                parts = [np.array([D[(b, t)][s] for t in tasks[b]])[idx10] for b in benches]
                boot = np.concatenate(parts, axis=1).mean(axis=1)
            else:
                boot = d[idx10].mean(axis=1)
            lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
            pos, neg, tie = int((d > 1e-12).sum()), int((d < -1e-12).sum()), int((np.abs(d) <= 1e-12).sum())
            p = float(sps.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else 1.0
            row = {"benchmark": DISPLAY.get(name, name), "n_tasks": len(keys), "statistic": s, "mean_A": float(a.mean()),
                   "mean_B": float(bb.mean()), "diff_B_minus_A": float(d.mean()), "ci95_lo": lo, "ci95_hi": hi,
                   "tasks_B_higher": pos, "tasks_B_lower": neg, "tasks_tied": tie, "sign_test_p_two_sided": p,
                   "n_boot": N_BOOT, "seed": SEED}
            out_rows.append(row)
            res[(name, s)] = row
    write_csv(OUT / "coauthor_paired_contrasts.csv", out_rows)
    (OUT / "coauthor_paired_contrasts.json").write_text(json.dumps(out_rows, indent=1), encoding="utf-8")

    # LaTeX table (supplement)
    def sgn(x: float) -> str:
        t = f"{abs(x):.2f}"
        return ("$-$" + t) if x < -0.005 else t

    L = ["% Generated by analysis/revision_coauthor.py. Do not edit by hand.",
         "\\begin{tabular}{llrcccc}", "\\toprule",
         "\\textbf{Benchmark} & \\textbf{Statistic} & \\textbf{Tasks} & \\textbf{Difference} & \\textbf{95\\% interval} & \\textbf{Higher / lower / tied} & \\textbf{Sign test $p$} \\\\",
         "\\midrule"]
    for name, keys in groups:
        for j, (s, label) in enumerate(STATS):
            r = res[(name, s)]
            L.append(f"{DISPLAY.get(name, name) if j == 0 else ''} & {label} & {r['n_tasks'] if j == 0 else ''} & {sgn(r['diff_B_minus_A'])} & "
                     f"[{sgn(r['ci95_lo'])}, {sgn(r['ci95_hi'])}] & {r['tasks_B_higher']} / {r['tasks_B_lower']} / {r['tasks_tied']} & {r['sign_test_p_two_sided']:.3f} \\\\")
        if name != "All three":
            L.append("\\addlinespace")
    L += ["\\bottomrule", "\\end{tabular}", ""]
    (TABLES / "coauthor_paired.tex").write_text("\n".join(L), encoding="utf-8")

    n_int0 = sum(1 for r in out_rows if r["ci95_lo"] <= 0 <= r["ci95_hi"])
    print(f"{len(out_rows)} contrasts; {n_int0} intervals include 0")
    for r in out_rows:
        print(f"{r['benchmark']:20s} {r['statistic']:12s} n={r['n_tasks']:2d} A={r['mean_A']:.2f} B={r['mean_B']:.2f} "
              f"d={r['diff_B_minus_A']:+.3f} [{r['ci95_lo']:+.3f},{r['ci95_hi']:+.3f}] +{r['tasks_B_higher']}/-{r['tasks_B_lower']}/={r['tasks_tied']} p={r['sign_test_p_two_sided']:.3f}")

    if write_summary:
        S = ["## 9. Co-author review analyses (response round 1; added 2026-10-12)", "",
             "### 9.1 Paired temperature contrasts for the executed reruns (co-author point 4b)", "",
             "Command (project root): `python analysis/revision_coauthor.py --write-summary`. Source: `rq3_groups.csv` (60 task groups = 30 (benchmark, task) pairs "
             "observed under condition A, the benchmark's own temperature, and condition B, T = 0.7; every group has 5 successful episodes). "
             "Per task, d = B - A of pass^1 (c/5), pass^5 (1 if c = 5, else 0; the unbiased estimator C(c,5)/C(5,5)), action divergence (more than one "
             "canonical action sequence) and verdict instability (more than one verdict). Mean paired difference with a 95% percentile paired bootstrap "
             "interval over tasks (2,000 resamples, seed 20261004; one resample serves all statistics; the pooled row resamples tasks within benchmark) and an "
             "exact two-sided binomial sign test on the tasks with a non-zero difference. Condition means reproduce `rq3_passk.csv` (asserted). "
             "Files: `coauthor_paired_contrasts.csv/.json`, `paper/tables/coauthor_paired.tex`.", "",
             "| Benchmark | Statistic | Tasks | Mean A | Mean B | B - A | 95% interval | B higher / lower / tied | Sign test p |", "|---|---|---|---|---|---|---|---|---|"]
        for r in out_rows:
            S.append(f"| {r['benchmark']} | {r['statistic']} | {r['n_tasks']} | {r['mean_A']:.3f} | {r['mean_B']:.3f} | {r['diff_B_minus_A']:+.3f} | "
                     f"[{r['ci95_lo']:+.3f}, {r['ci95_hi']:+.3f}] | {r['tasks_B_higher']} / {r['tasks_B_lower']} / {r['tasks_tied']} | {r['sign_test_p_two_sided']:.3f} |")
        S += ["", f"Intervals that include 0: {n_int0} of {len(out_rows)}.", ""]
        S += ["### 9.2 Grader recomputation split (co-author point 1)", "",
              "From `rq3_grader_state.csv`: Synthetic Hospital, 88 episodes with a submission = 69 exact recomputations (35 in A + 34 in B; reward within 1e-6 of the "
              "benchmark's own scorer) + 19 conditional checks (10 + 9; the scorer needs the chart-neutral category count, which is not in the episode record, so the "
              "reward was rebuilt with the grader-reported neutral count). 0 disagreements in both groups; 12 episodes with no submission. "
              "The 19 are a secondary check, not an independent verification of the neutral count.", ""]
        p = OUT / "RESULTS_SUMMARY.md"
        txt = p.read_text(encoding="utf-8")
        i = txt.find("## 9. Co-author review analyses")
        if i >= 0:
            txt = txt[:i].rstrip("\n") + "\n\n"
        else:
            txt = txt.rstrip("\n") + "\n\n"
        p.write_text(txt + "\n".join(S), encoding="utf-8")
        print("wrote section 9 of RESULTS_SUMMARY.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-summary", action="store_true")
    main(ap.parse_args().write_summary)
