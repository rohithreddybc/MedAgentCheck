"""Reproduce the paired temperature contrasts for the executed reruns (paper Table S19; RESULTS_SUMMARY section 9.1) from reruns/.

Port of analysis/revision_coauthor.py. The task groups (30 (benchmark, task) pairs, each observed under condition A, the
benchmark's own temperature, and condition B, T = 0.7, with 5 successful episodes each) are rebuilt from the released
episode records reruns/*_episodes.jsonl by the same code as repro/reproduce_reruns.py. Per task, d = B - A of
  pass^1  c/5,  pass^5  (1 if c = 5, else 0),  action divergence (more than one canonical action sequence),
  verdict instability (more than one verdict).
Mean paired difference, 95% percentile paired bootstrap interval over tasks (2,000 resamples, seed 20261004; one resample
serves all statistics; the pooled row resamples tasks within benchmark) and an exact two-sided binomial sign test on the
tasks with a non-zero difference.

Compared (assertions) with
  results/analysis_out/coauthor_paired_contrasts.csv and .json
  results/analysis_out/rq3_passk.csv          (condition means)
  analysis/out/RESULTS_SUMMARY.md             section 9.1 (all 16 table rows and the count of intervals that include 0)

Not reproduced: section 9.2 (grader recomputation split), which needs the final environment states.

    python repro/reproduce_coauthor.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, RERUNS, SEED, SUMMARY_MD, Checker, read_csv_rows, read_json  # noqa: E402
from reproduce_audit import write_csv  # noqa: E402
from reproduce_reruns import BENCHES, compute, load_episodes  # noqa: E402

R = 5
DISPLAY = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}
STATS = ["pass1", "pass5", "divergence", "instability"]


def load_pairs(groups: list[dict]) -> dict:
    by: dict = {}
    for r in groups:
        assert str(r["complete"]) == "True" and int(r["episodes_ok"]) == R
        by.setdefault((r["bench"], r["task_id"]), {})[r["condition"]] = r
    assert len(by) == 30 and all(set(v) == {"A", "B"} for v in by.values())
    return by


def task_stats(r: dict) -> dict:
    c = int(r["n_pass"])
    return {"pass1": math.comb(c, 1) / math.comb(R, 1), "pass5": math.comb(c, 5) / math.comb(R, 5),
            "divergence": 1.0 if str(r["divergent"]) == "True" else 0.0,
            "instability": 1.0 if str(r["verdict_unstable"]) == "True" else 0.0}


def contrasts(by: dict, ck: Checker) -> list[dict]:
    benches = sorted({b for b, _ in by})
    tasks = {b: sorted(t for bb, t in by if bb == b) for b in benches}
    A, B, D = {}, {}, {}
    for (b, t), v in by.items():
        A[(b, t)], B[(b, t)] = task_stats(v["A"]), task_stats(v["B"])
        D[(b, t)] = {s: B[(b, t)][s] - A[(b, t)][s] for s in STATS}
    pk = {(r["bench"], r["condition"], r["k"]): float(r["pass_hat_k"]) for r in read_csv_rows(ANALYSIS_OUT / "rq3_passk.csv")}
    for b in benches:
        for cond, M in (("A", A), ("B", B)):
            for k, s in (("1", "pass1"), ("5", "pass5")):
                m = float(np.mean([M[(b, t)][s] for t in tasks[b]]))
                ck.n += 1
                if abs(m - pk[(b, cond, k)]) >= 0.0051:
                    ck.fails.append(f"condition mean {b} {cond} pass^{k}: reproduced {m}, rq3_passk.csv {pk[(b, cond, k)]}")
    rng = np.random.default_rng(SEED)
    idx10 = rng.integers(0, 10, size=(N_BOOT, 10))
    out_rows = []
    groups = [(b, [(b, t) for t in tasks[b]]) for b in benches] + [("All three", [(b, t) for b in benches for t in tasks[b]])]
    for name, keys in groups:
        for s in STATS:
            d = np.array([D[k][s] for k in keys])
            a = np.array([A[k][s] for k in keys])
            bb = np.array([B[k][s] for k in keys])
            if name == "All three":
                parts = [np.array([D[(b, t)][s] for t in tasks[b]])[idx10] for b in benches]
                boot = np.concatenate(parts, axis=1).mean(axis=1)
            else:
                boot = d[idx10].mean(axis=1)
            lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
            pos, neg, tie = int((d > 1e-12).sum()), int((d < -1e-12).sum()), int((np.abs(d) <= 1e-12).sum())
            p = float(sps.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else 1.0
            out_rows.append({"benchmark": DISPLAY.get(name, name), "n_tasks": len(keys), "statistic": s, "mean_A": float(a.mean()),
                             "mean_B": float(bb.mean()), "diff_B_minus_A": float(d.mean()), "ci95_lo": lo, "ci95_hi": hi,
                             "tasks_B_higher": pos, "tasks_B_lower": neg, "tasks_tied": tie, "sign_test_p_two_sided": p,
                             "n_boot": N_BOOT, "seed": SEED})
    return out_rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    ck = Checker("paired temperature contrasts (Table S19, RESULTS_SUMMARY 9.1)")
    episodes = {b: load_episodes(RERUNS / f"{b}_episodes.jsonl") for b in BENCHES}
    groups = compute(episodes, False)["groups"]
    rows = contrasts(load_pairs(groups), ck)
    write_csv(a.out / "coauthor_paired_contrasts.csv", rows)
    ck.csv_rows("coauthor_paired_contrasts.csv", rows, ANALYSIS_OUT / "coauthor_paired_contrasts.csv", ["benchmark", "statistic"])
    ref = read_json(ANALYSIS_OUT / "coauthor_paired_contrasts.json")
    ck.eq("json row count", len(rows), len(ref))
    for mine, want in zip(rows, ref):
        for k, v in want.items():
            ck.eq(f"json {want['benchmark']} {want['statistic']} {k}", mine[k], v, 1e-9)
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    for r in rows:
        ck.in_text(f"9.1 {r['benchmark']} {r['statistic']}",
                   f"| {r['benchmark']} | {r['statistic']} | {r['n_tasks']} | {r['mean_A']:.3f} | {r['mean_B']:.3f} | {r['diff_B_minus_A']:+.3f} | "
                   f"[{r['ci95_lo']:+.3f}, {r['ci95_hi']:+.3f}] | {r['tasks_B_higher']} / {r['tasks_B_lower']} / {r['tasks_tied']} | "
                   f"{r['sign_test_p_two_sided']:.3f} |", txt)
    n0 = sum(1 for r in rows if r["ci95_lo"] <= 0 <= r["ci95_hi"])
    ck.in_text("9.1 intervals including 0", f"Intervals that include 0: {n0} of {len(rows)}.", txt)
    ck.done()
    pooled = {r["statistic"]: r for r in rows if r["benchmark"] == "All three"}
    print("pooled B - A: " + "; ".join(f"{s} {pooled[s]['diff_B_minus_A']:+.3f} [{pooled[s]['ci95_lo']:+.3f}, {pooled[s]['ci95_hi']:+.3f}]"
                                        for s in STATS))


if __name__ == "__main__":
    main()
