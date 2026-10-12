"""Reproduce the executed-rerun metrics (action divergence, verdict instability, pass^k with intervals) from reruns/.

Port of analysis/postfreeze/rq3_reruns.py (compute: divergence, pass^k, CI width, groups, status; both the default
episode rule and the earlier `--exclude-episode-errors` rule) and of analysis/revision_rq3.py (item3: percentile,
Bayesian-bootstrap and exact intervals and the design effect; item4: Synthetic Hospital pass cut-off sensitivity).

Input: reruns/<bench>_episodes.jsonl, 100 episodes per benchmark (10 tasks x 2 conditions x 5 repeats). The authors'
scripts compare action sequences as lists; the release keeps tool names only for Synthetic Hospital (arguments carry
synthetic patient identifiers) and replaces the strict AgentClinic sequence by a hash. Two episodes have the same
canonical sequence if and only if their `actions_sha256` match (reruns/README.md), so the hashes are compared here
(`actions_strict_sha256` for the strict AgentClinic variant). The script checks that the hash partition equals the
partition by the `actions` lists wherever those lists are complete (AgentClinic, RadA-BenchPlat).

Not reproducible from the release: grader-versus-state and judge-only reruns (they need final states and transcripts),
and the episode-validity flags of analysis/revision_rq3.py item 2 (they read Synthetic Hospital traces).

Compared with results/analysis_out/rq3_divergence.csv, rq3_passk.csv, rq3_ci_width.csv, rq3_groups.csv,
rq3_svda_groups.csv, rq3_status.csv, the *_errexcl.csv variants, rev_rq3_passk_bayes.csv, rev_rq3_deff.csv,
rev_rq3_cutoff.csv, and the headline lines of analysis/out/RESULTS_SUMMARY.md.

    python repro/reproduce_reruns.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, RERUNS, SEED, SUMMARY_MD, Checker  # noqa: E402
from reproduce_audit import write_csv  # noqa: E402

BENCHES = ["AgentClinic", "RadABench", "synthetic_hospital"]
DISPLAY = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}
REPEATS = 5
EXPECTED_TASKS = 10
KS = range(1, REPEATS + 1)
N_BAYES = 20000
CUTOFFS = [0.3, 0.4, 0.5, 0.6, 0.7]


# ------------------------------------------------------------------ loading and episode rule
def load_episodes(path: Path) -> list[dict]:
    """Episode records; a repeated `_key` keeps the last record (as the authors' loader)."""
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


def episode_ok(ep: dict, exclude_errors: bool) -> bool:
    return (ep.get("driver_status", "ok") == "ok" and not (exclude_errors and ep.get("error"))
            and isinstance(ep.get("actions"), list) and verdict_pass(ep) is not None)


def build_groups(eps: list[dict], exclude_errors: bool) -> dict:
    g: dict[tuple, dict] = {}
    for ep in eps:
        key = (ep["condition_name"], ep["task_id"])
        d = g.setdefault(key, {"eps": {}, "n_seen": 0, "n_failed": 0, "temperature": None})
        d["n_seen"] += 1
        d["temperature"] = (ep.get("condition") or {}).get("temperature", d["temperature"])
        if episode_ok(ep, exclude_errors):
            d["eps"][int(ep["repeat"])] = ep
        else:
            d["n_failed"] += 1
    for d in g.values():
        d["complete"] = all(r in d["eps"] for r in range(REPEATS))
    return g


def group_stats(d: dict) -> dict:
    eps = [d["eps"][r] for r in range(REPEATS)]
    seqs = [e["actions_sha256"] for e in eps]
    strict = [e["actions_strict_sha256"] for e in eps if e.get("actions_strict_sha256")]
    passes = [bool(verdict_pass(e)) for e in eps]
    return {"n_distinct_sequences": len(set(seqs)),
            "n_distinct_sequences_strict": len(set(strict)) if len(strict) == REPEATS else None,
            "verdicts": passes, "n_pass": sum(passes), "verdict_unstable": len(set(passes)) > 1}


# ------------------------------------------------------------------ statistics
def pass_hat_k(c: int, n: int, k: int) -> float:
    return math.comb(c, k) / math.comb(n, k)


def cluster_boot(mat: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED):
    n = mat.shape[0]
    if n < 2:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = mat[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5], axis=0)
    return lo, hi


def passk_rows(bench, cond, temp, tasks, status) -> list[dict]:
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


def ciwidth_row(bench, cond, temp, task_eps, status):
    if not task_eps:
        return None
    n = len(task_eps)
    p5 = np.array([[float(verdict_pass(e)) for e in eps] for eps in task_eps])
    out = {"bench": bench, "condition": cond, "temperature": temp, "n_tasks": n, "n_boot": N_BOOT, "seed": SEED, **status}
    out["score_5run"] = float(p5.mean())
    out["score_1run"] = float(p5[:, 0].mean())
    if n < 2:
        return out
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))

    def width(v):
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


def compute(episodes: dict[str, list[dict]], exclude_errors: bool) -> dict:
    div_rows, passk, ciw, group_rows, svda, status = [], [], [], [], [], []
    for bench in BENCHES:
        eps = episodes[bench]
        groups = build_groups(eps, exclude_errors)
        for cond in sorted({c for c, _ in groups}):
            keys = sorted(k for k in groups if k[0] == cond)
            temp = next((groups[k]["temperature"] for k in keys if groups[k]["temperature"] is not None), None)
            complete = [k for k in keys if groups[k]["complete"]]
            n_seen = sum(groups[k]["n_seen"] for k in keys)
            n_failed = sum(groups[k]["n_failed"] for k in keys)
            gstats = {k: group_stats(groups[k]) for k in complete}
            tasks = list(gstats.values())
            n_c = len(tasks)
            partial = n_c < EXPECTED_TASKS
            st = {"tasks_complete": n_c, "tasks_expected": EXPECTED_TASKS, "partial": partial}
            status.append({"bench": bench, "condition": cond, "temperature": temp, "tasks_with_episodes": len(keys),
                           "tasks_complete": n_c, "tasks_expected": EXPECTED_TASKS, "episodes_seen": n_seen,
                           "episodes_ok": n_seen - n_failed, "episodes_failed": n_failed,
                           "episodes_expected": EXPECTED_TASKS * REPEATS, "partial": partial})
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
                "tasks_expected": EXPECTED_TASKS, "episodes_seen": n_seen, "episodes_failed": n_failed,
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
    return {"divergence": div_rows, "passk": passk, "ci_width": ciw, "groups": group_rows, "svda": svda, "status": status}


# ------------------------------------------------------------------ revision_rq3 items 3 and 4
def by_group(eps: list[dict]) -> dict:
    g: dict = {}
    for e in eps:
        g.setdefault((e["condition_name"], e["task_id"]), []).append(e)
    for k in g:
        g[k].sort(key=lambda e: int(e["repeat"]))
    return g


def task_mat(g: dict, cond: str, passfn=None) -> np.ndarray:
    passfn = passfn or (lambda e: bool(verdict_pass(e)))
    rows = []
    for k in sorted(k for k in g if k[0] == cond):
        c = sum(passfn(e) for e in g[k])
        rows.append([pass_hat_k(c, REPEATS, kk) for kk in KS])
    return np.array(rows, dtype=float)


def bayes_boot(mat: np.ndarray, n_draw: int = N_BAYES, seed: int = SEED):
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(mat.shape[0]), size=n_draw)
    lo, hi = np.percentile(w @ mat, [2.5, 97.5], axis=0)
    return lo, hi


def clopper_pearson(x: float, n: float, alpha: float = 0.05):
    lo = 0.0 if x <= 0 else float(beta.ppf(alpha / 2, x, n - x + 1))
    hi = 1.0 if x >= n else float(beta.ppf(1 - alpha / 2, x + 1, n - x))
    return lo, hi


def deff_stats(y: np.ndarray) -> dict:
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


def passk_intervals(data: dict) -> tuple[list[dict], list[dict]]:
    prow, drow = [], []
    for b in BENCHES:
        g = data[b]
        for c in sorted({c for c, _ in g}):
            mat = task_mat(g, c)
            n = mat.shape[0]
            plo, phi = cluster_boot(mat)
            blo, bhi = bayes_boot(mat)
            y = np.array([[float(verdict_pass(e)) for e in g[k]] for k in sorted(k for k in g if k[0] == c)])
            ds = deff_stats(y)
            x_pool, n_pool = int(y.sum()), y.size
            cp_naive = clopper_pearson(x_pool, n_pool)
            cp_adj = clopper_pearson(ds["p"] * ds["n_eff"], ds["n_eff"]) if ds["n_eff"] else (None, None)
            x5 = int((mat[:, 4] == 1).sum())
            cp5 = clopper_pearson(x5, n)
            for j, k in enumerate(KS):
                nz = int((mat[:, j] > 0).sum())
                prow.append({"bench": b, "condition": c, "k": k, "pass_hat_k": float(mat[:, j].mean()),
                             "pct_lo": float(plo[j]), "pct_hi": float(phi[j]), "bayes_lo": float(blo[j]),
                             "bayes_hi": float(bhi[j]), "pct_zero_width": bool(phi[j] - plo[j] <= 1e-12),
                             "pct_single_task_support": nz == 1, "pct_lower_at_zero": bool(plo[j] <= 1e-12),
                             "tasks_nonzero": nz, "bayes_zero_width": bool(bhi[j] - blo[j] <= 1e-12),
                             "exact_lo": (cp_naive[0] if k == 1 else cp5[0] if k == 5 else None),
                             "exact_hi": (cp_naive[1] if k == 1 else cp5[1] if k == 5 else None),
                             "exact_kind": ("CP pooled 50 episodes, independence assumed" if k == 1 else
                                            "CP on 10 tasks (binary per task)" if k == 5 else ""),
                             "exact_deff_lo": cp_adj[0] if k == 1 else None,
                             "exact_deff_hi": cp_adj[1] if k == 1 else None,
                             "n_boot_pct": N_BOOT, "n_draw_bayes": N_BAYES, "seed": SEED})
            drow.append({"bench": b, "condition": c, "x": x_pool, "n": n_pool, "p": ds["p"], "msb": ds["msb"],
                         "msw": ds["msw"], "icc": ds["icc"], "deff": ds["deff"], "n_eff": ds["n_eff"],
                         "cp_lo": cp_naive[0], "cp_hi": cp_naive[1], "cp_adj_lo": cp_adj[0], "cp_adj_hi": cp_adj[1],
                         "tasks_pass5": x5, "cp5_lo": cp5[0], "cp5_hi": cp5[1]})
    return prow, drow


def sh_pass(e: dict, cut: float) -> bool:
    v = e.get("verdict") if isinstance(e.get("verdict"), dict) else {}
    r = v.get("reward")
    return bool(v.get("done") and r is not None and float(r) >= cut)


def cutoff_rows(g: dict) -> list[dict]:
    assert all(sh_pass(e, 0.5) == bool(verdict_pass(e)) for v in g.values() for e in v), "0.5 cut-off != verdict.pass"
    rows = []
    for cut in CUTOFFS:
        for c in sorted({c for c, _ in g}):
            mat = task_mat(g, c, lambda e, cut=cut: sh_pass(e, cut))
            keys = sorted(k for k in g if k[0] == c)
            unst = sum(len({sh_pass(e, cut) for e in g[k]}) > 1 for k in keys)
            n_pass = sum(sh_pass(e, cut) for k in keys for e in g[k])
            blo, bhi = bayes_boot(mat)
            rows.append({"cutoff": cut, "condition": c, "episodes_pass": n_pass, "episodes": 5 * len(keys),
                         **{f"pass_hat_{k}": float(mat[:, k - 1].mean()) for k in KS},
                         "unstable_n": unst, "tasks": len(keys), "pass1_bayes_lo": float(blo[0]),
                         "pass1_bayes_hi": float(bhi[0]), "is_frozen_cutoff": abs(cut - 0.5) < 1e-12})
    return rows


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    ck = Checker("executed reruns (divergence, instability, pass^k)")
    episodes = {b: load_episodes(RERUNS / f"{b}_episodes.jsonl") for b in BENCHES}
    for b in BENCHES:
        ck.eq(f"{b} episodes", len(episodes[b]), 100)
    # the hash partition equals the partition by action lists where the lists are complete
    for b in ("AgentClinic", "RadABench"):
        by_hash: dict[str, set] = {}
        for e in episodes[b]:
            by_hash.setdefault(e["actions_sha256"], set()).add(json.dumps(e["actions"], separators=(",", ":")))
        ck.eq(f"{b} actions_sha256 <-> actions list is one-to-one", all(len(v) == 1 for v in by_hash.values()), True)
        ck.eq(f"{b} distinct sequences", len(by_hash), len({json.dumps(e["actions"], separators=(",", ":")) for e in episodes[b]}))

    for suffix, exclude in (("", False), ("_errexcl", True)):
        res = compute(episodes, exclude)
        fname = {"svda": "svda_groups"}  # file rq3_svda_groups.csv holds the "svda" rows
        for name in ("divergence", "passk", "ci_width", "groups", "svda", "status"):
            write_csv(a.out / f"rq3_{fname.get(name, name)}{suffix}.csv", res[name])
        keys = {"divergence": ["bench", "condition"], "passk": ["bench", "condition", "k"], "ci_width": ["bench", "condition"],
                "groups": ["bench", "condition", "task_id"], "svda": ["bench", "condition", "task_id"],
                "status": ["bench", "condition"]}
        for name, kk in keys.items():
            ck.csv_rows(f"rq3_{fname.get(name, name)}{suffix}.csv", res[name],
                        ANALYSIS_OUT / f"rq3_{fname.get(name, name)}{suffix}.csv", kk)
        if not exclude:
            main_res = res

    prow, drow = passk_intervals({b: by_group(episodes[b]) for b in BENCHES})
    write_csv(a.out / "rev_rq3_passk_bayes.csv", prow)
    write_csv(a.out / "rev_rq3_deff.csv", drow)
    ck.csv_rows("rev_rq3_passk_bayes.csv", prow, ANALYSIS_OUT / "rev_rq3_passk_bayes.csv", ["bench", "condition", "k"])
    ck.csv_rows("rev_rq3_deff.csv", drow, ANALYSIS_OUT / "rev_rq3_deff.csv", ["bench", "condition"])
    cut = cutoff_rows(by_group(episodes["synthetic_hospital"]))
    write_csv(a.out / "rev_rq3_cutoff.csv", cut)
    ck.csv_rows("rev_rq3_cutoff.csv", cut, ANALYSIS_OUT / "rev_rq3_cutoff.csv", ["cutoff", "condition"])

    # headline lines of RESULTS_SUMMARY.md
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    d = {(r["bench"], r["condition"]): r for r in main_res["divergence"]}
    head = []
    for b in BENCHES:
        for c in ("A", "B"):
            r = d[(b, c)]
            head.append((f"{DISPLAY[b]} {c} {r['divergent_n']}/{r['tasks_complete']}", r["unstable_n"], r["tasks_complete"]))
    ck.in_text("divergence headline", "divergent task groups " + ", ".join(h[0] for h in head), txt)
    ck.in_text("instability headline", "unstable verdicts " + ", ".join(f"{h[1]}/{h[2]}" for h in head) + " (same order)", txt)
    pk = {(r["bench"], r["condition"], r["k"]): r["pass_hat_k"] for r in main_res["passk"]}
    ck.in_text("pass^k headline", "pass^1 to pass^5: " + "; ".join(
        f"{DISPLAY[b]} {c} {pk[(b, c, 1)]:.2f} to {pk[(b, c, 5)]:.2f}" for b in BENCHES for c in ("A", "B")), txt)
    cw = {(r["bench"], r["condition"]): r for r in main_res["ci_width"]}
    ck.in_text("CI width headline", "CI width 5 runs versus mean 1 run: " + "; ".join(
        f"{DISPLAY[b]} {c} {cw[(b, c)]['ci_width_5run']:.2f} vs {cw[(b, c)]['ci_width_1run_mean_over_repeats']:.2f}"
        for b in BENCHES for c in ("A", "B")), txt)
    ck.done()
    for b in BENCHES:
        for c in ("A", "B"):
            r = d[(b, c)]
            print(f"{DISPLAY[b]} {c}: divergent {r['divergent_n']}/{r['tasks_complete']}, unstable {r['unstable_n']}/{r['tasks_complete']}, "
                  f"pass^1 {pk[(b, c, 1)]:.2f}, pass^5 {pk[(b, c, 5)]:.2f}")


if __name__ == "__main__":
    main()
