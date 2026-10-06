"""Build analysis/out/RESULTS_SUMMARY.md from the CSV/JSON outputs in analysis/out/ (no number is typed by hand).

Run after rq3_reruns.py, judge_rerun.py, rq1_rq2.py (primary, --exclude-rule-affected), rq2_extras.py.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from common import OUT, ROOT

from agentaudit.stats import wilson  # noqa: E402

NAMES = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}


def rd(name: str) -> list[dict]:
    p = OUT / name
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fl(x):
    return None if x in ("", None) else float(x)


def f3(x, d=3):
    x = fl(x)
    return "--" if x is None else f"{x:.{d}f}"


def pc(x, d=1):
    x = fl(x)
    return "--" if x is None else f"{100 * x:.{d}f}%"


def ci(lo, hi, d=3):
    return "--" if fl(lo) is None else f"[{fl(lo):.{d}f}, {fl(hi):.{d}f}]"


def pci(lo, hi, d=1):
    return "--" if fl(lo) is None else f"[{100 * fl(lo):.{d}f}, {100 * fl(hi):.{d}f}]"


def table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def item_key(i: str):
    return (0 if i[0] == "C" else 1, int(i[1:]))


def main() -> None:
    L: list[str] = []
    A = L.append
    A("# RESULTS SUMMARY (final-data run, 2026-10-06)\n")
    A("Every number below is read from a file in `analysis/out/` (source given per section) by "
      "`analysis/results_summary.py`. Seed 20261004, 2,000 bootstrap resamples throughout. "
      "All results are final (the OpenAI-coder perturbation and retest were completed 2026-10-06).\n")
    A("## 0. Status and analysis-side changes\n")
    A("No frozen scorer file was edited. Analysis-side changes made in this run (each documented where it lives):\n")
    A("1. `rq3_reruns.py` `episode_ok`: the first version dropped every episode whose record had a non-empty `error`. "
      "Those are agent-behaviour outcomes that carry a benchmark verdict (RadABench `benchmark-logged: ...` = invalid or "
      "missing tool inputs, verdict.pass False by the runner rule; Synthetic Hospital `model repeatedly produced no tool "
      "call` = no submission, scored 0), all with `driver_status` ok and 0 driver failures. The old rule removed 62 of 100 "
      "RadABench and 12 of 100 Synthetic Hospital episodes and left 3/10 and 2/10 complete RadABench task groups. Default "
      "is now: an episode counts when the driver finished it and it has actions and a verdict. The old rule is kept as "
      "`--exclude-episode-errors` (outputs `*_errexcl`) and reported in section 1.7.")
    A("2. `rq3_reruns.py` grader-vs-state: episodes with no submission have no grader reward; they are counted as "
      "`no_submission`, never as agreement.")
    A("3. `rq3_reruns.py` `reconstruct_with_neutral_count`: secondary check for the `neutral_set_required` episodes (uses the "
      "grader's reported neutral count; not an independent verification of that count).")
    A("4. `rq1_rq2.py` `manifest_slugs`: the frozen `bench_dir_candidates` cannot match hyphenated or renamed slugs, so only 7 "
      "of 14 rule-affected benchmarks were found by the `--exclude-rule-affected` switch. Ids are now mapped through "
      "`audit/manifests/*.yaml` (`frozen_list_id` to `name`); all 14 match. Same root cause as the retest bug logged on "
      "2026-10-05.")
    A("5. `rq1_rq2.py` `load_resolved`: HealthCraft (coder failure for both families, empty `cells`) is skipped, so the "
      "population is 44 benchmarks. `gold_table` and `perturbation_table` accept the actual locations (`--gold-abc`, "
      "`--gold-betterbench`, `--perturb-run`).")
    A("6. `rq2_extras.py`: retest mapped through manifests (analysis-side slug fix, as `provisional_retest_all10.py`).")
    A("7. Frozen CLI run read-only on existing records: `agentaudit perturb --out audit/perturb --summarise` (wrote "
      "`audit/perturb/perturb/summary.json` and `summary.csv`, which did not exist). Perturbation plan check: 39 of the 40 "
      "design variants ran; the missing one is v13 = arxiv:2605.21496 = HealthCraft (no base result). No hyphenated "
      "benchmark was dropped (the plan keys on arXiv/PubMed ids, not slugs).\n")
    A("8. OpenAI-coder completion (2026-10-06): `audit/transport/run_codex_prompts.py` (perturbation, 39 variants) and `audit/transport/run_codex_retest.py` (the 2 retest benchmarks the CLI retest skipped) call the frozen `CodexHeadlessBackend` on the exported prompts, which are the prompts the Claude coder received; `import_validation.py --coder codex` stores them with the package scoring and verification code, and `finalize_retest` resolves the retest run and rewrites `retest_agreement.json` for all 10 drawn benchmarks (the package `map_bench_dirs` is replaced in memory only; no frozen file is edited).\n")

    # ---------------------------------------------------------------- RQ3
    A("## 1. RQ3 (end-to-end variability; run design v3)\n")
    A("Sources: `rq3_status.csv`, `rq3_divergence.csv`, `rq3_passk.csv`, `rq3_ci_width.csv`, `rq3_grader_state.csv`, "
      "`rq3_grader_state_episodes.csv`, `rq3_groups.csv`, `rq3_svda_groups.csv`; tables `paper/tables/rq3_*.tex`; "
      "Fig 5 `paper/figures/fig5_ci_width.pdf`. Unit = task group of 5 reruns; 10 tasks per benchmark and condition; "
      "A = benchmark temperature (AgentClinic 0.05, others 0), B = 0.7. Data complete: 300 of 300 episodes, 0 driver "
      "failures. Non-random selection of 3 benchmarks: existence findings, not population rates.\n")
    st = rd("rq3_status.csv")
    A("### 1.1 Coverage\n")
    A(table(["Benchmark", "Cond", "Complete task groups", "Episodes ok/expected", "Episodes whose record has `error` (kept)"],
            [[NAMES[r["bench"]], r["condition"], f'{r["tasks_complete"]}/{r["tasks_expected"]}',
              f'{r["episodes_ok"]}/{r["episodes_expected"]}', ""] for r in st]))
    ee = {}
    import rq3_reruns as R
    for b in R.BENCHES:
        for ep in R.load_episodes(R.RUNS_ROOT / b / "episodes.jsonl"):
            ee[(b, ep["condition_name"])] = ee.get((b, ep["condition_name"]), 0) + bool(ep.get("error"))
    L[-1] = table(["Benchmark", "Cond", "Complete task groups", "Episodes ok/expected",
                   "Episodes with `error` in record (kept; agent failures with a verdict)"],
                  [[NAMES[r["bench"]], r["condition"], f'{r["tasks_complete"]}/{r["tasks_expected"]}',
                    f'{r["episodes_ok"]}/{r["episodes_expected"]}', ee.get((r["bench"], r["condition"]), 0)] for r in st])
    A("\n### 1.2 Action divergence, verdict instability, same verdict with different actions\n")
    dv = rd("rq3_divergence.csv")
    A(table(["Benchmark", "Cond", "T", "Divergent groups", "Mean distinct sequences", "Unstable verdict groups",
             "Same verdict, different actions", "(all-pass / all-fail)"],
            [[NAMES[r["bench"]], r["condition"], r["temperature"], f'{r["divergent_n"]}/{r["tasks_complete"]} ({pc(r["divergent_prop"], 0)})',
              f3(r["mean_distinct_sequences"], 2), f'{r["unstable_n"]}/{r["tasks_complete"]} ({pc(r["unstable_prop"], 0)})',
              f'{r["same_verdict_diff_actions_n"]}/{r["tasks_complete"]} ({pc(r["same_verdict_diff_actions_prop"], 0)})',
              f'{r["svda_all_pass_n"]} / {r["svda_all_fail_n"]}'] for r in dv]))
    ac = [r for r in dv if r["bench"] == "AgentClinic"]
    A("\nAgentClinic strict-question divergence (full question text): " +
      "; ".join(f'{r["condition"]} {r["divergent_strict_n"]}/{r["tasks_complete"]}' for r in ac) + ".")
    tot_g = sum(int(r["tasks_complete"]) for r in dv)
    A(f"Pooled over the 6 benchmark x condition cells ({tot_g} task groups): divergent "
      f"{sum(int(r['divergent_n']) for r in dv)}, unstable verdict {sum(int(r['unstable_n']) for r in dv)}, "
      f"same verdict with different actions {sum(int(r['same_verdict_diff_actions_n']) for r in dv)}.\n")
    A("### 1.3 pass^k (k = 1..5), cluster bootstrap 95% CI over tasks\n")
    pk = rd("rq3_passk.csv")
    rows = []
    for key in dict.fromkeys((r["bench"], r["condition"]) for r in pk):
        sel = sorted([r for r in pk if (r["bench"], r["condition"]) == key], key=lambda r: int(r["k"]))
        rows.append([NAMES[key[0]], key[1], sel[0]["n_tasks"]] +
                    [f'{f3(r["pass_hat_k"], 2)} {ci(r["ci_lo"], r["ci_hi"], 2)}' for r in sel])
    A(table(["Benchmark", "Cond", "Tasks", "k=1", "k=2", "k=3", "k=4", "k=5"], rows))
    A("\n### 1.4 Headline-score CI width, 1 run versus 5 runs\n")
    cw = rd("rq3_ci_width.csv")
    A(table(["Benchmark", "Cond", "Score 1 run (repeat 0)", "CI 1 run", "Width 1 run", "Width 1 run, mean over repeats 0-4 (min-max)",
             "Score 5 runs", "CI 5 runs", "Width 5 runs", "Ratio 5 runs / repeat 0", "Ratio 5 runs / mean 1 run"],
            [[NAMES[r["bench"]], r["condition"], f3(r["score_1run"], 2), ci(r["ci_lo_1run"], r["ci_hi_1run"], 2),
              f3(r["ci_width_1run"], 2),
              f'{f3(r["ci_width_1run_mean_over_repeats"], 2)} ({f3(r["ci_width_1run_min"], 2)}-{f3(r["ci_width_1run_max"], 2)})',
              f3(r["score_5run"], 2), ci(r["ci_lo_5run"], r["ci_hi_5run"], 2), f3(r["ci_width_5run"], 2),
              f3(r["width_ratio_5_over_1"], 2),
              f3(fl(r["ci_width_5run"]) / fl(r["ci_width_1run_mean_over_repeats"]), 2)] for r in cw]))
    A("\nThe 1-run width depends on which repeat is used (see the min-max column), so the mean over single runs is the "
      "fairer reference; against it the 5-run width is narrower in all six cells (ratio 0.69 to 0.97). Against repeat 0 "
      "alone it is wider for RadA-BenchPlat (ratio above 1) because repeat 0 had 1 pass in 10 tasks, which makes its "
      "bootstrap narrow near zero; the 5-run width carries the between-task spread of per-task pass rates. With 10 tasks "
      "per cell, five runs narrow the interval only modestly in most cells, and the task sample, not the run count, "
      "dominates the width. Report both ratios.\n")
    A("### 1.5 Grader versus observed state (Synthetic Hospital, patient_diagnosis)\n")
    gs = rd("rq3_grader_state.csv")
    A(table(["Cond", "Episodes", "Agree", "Disagree", "Not exactly recomputable (neutral set)", "...rebuilt with grader's neutral count: agree / disagree",
             "No submission (no grader reward)", "State missing", "Server-stored reward differs from reported"],
            [[r["condition"], r["n_episodes"], r["agree"], r["disagree"], r["neutral_set_required"],
              f'{r["neutral_reconstruction_agrees"]} / {r["neutral_reconstruction_disagrees"]}', r["no_submission"],
              r["state_missing"], r["server_state_differs_from_reported"]] for r in gs]))
    ge = rd("rq3_grader_state_episodes.csv")
    sub = [r for r in ge if r["outcome"] != "no_submission"]
    pos = [r for r in sub if fl(r["reported_reward"]) and fl(r["reported_reward"]) > 0]
    A(f"\nOf {len(sub)} episodes with a submission, {len(pos)} have reward above 0 (so agreement is not only trivial zeros). "
      "Disagreement = |recomputed - reported| > 1e-6 with the benchmark's own `eval.scoring.compute_all_metrics` "
      "(commit 911f34c4) on the stored submission and reference. The 0.5 cut-off behind pass^k is the study's derived "
      "binary, not the benchmark's criterion. Limit: the submission is the one the runner parsed from the agent's tool "
      "call; the server stores only a submitted flag.\n")
    A("### 1.6 Judge-only instability (AgentClinic; local ollama judge llama3.1-8b-ctx16k, T=0, 3 re-judgements per transcript)\n")
    jp = OUT / "rq3_judge_rerun.json"
    if jp.exists():
        j = json.loads(jp.read_text(encoding="utf-8"))
        u, dd = j["transcripts_with_unstable_rejudgements"], j["transcripts_where_any_rejudgement_differs_from_recorded"]
        rj = j["rejudgements_differing_from_recorded"]
        A(f"Source: `rq3_judge_rerun.json`, `.csv`, `.jsonl`. Model digest {j.get('judge_digest')}. Transcripts: {j['transcripts']} "
          f"(all complete AgentClinic episodes, limit {j.get('limit')}); re-judgements: {j['rejudgements']}.\n")
        A(f"- Transcripts whose 3 re-judgements are not all identical: {u['k']}/{u['n']} = {pc(u['share'], 1)} "
          f"(Wilson 95% {pci(*u['wilson95'])}).")
        A(f"- Transcripts where any re-judgement differs from the recorded verdict: {dd['k']}/{dd['n']} = {pc(dd['share'], 1)} "
          f"(Wilson 95% {pci(*dd['wilson95'])}).")
        A(f"- Individual re-judgements differing from the recorded verdict: {rj['k']}/{rj['n']} = {pc(rj['share'], 1)}.")
        recs = rd("rq3_judge_rerun.csv")
        for cond in ("A", "B"):
            sel = [r for r in recs if r["condition"] == cond]
            k = sum(r["all_identical"] != "True" for r in sel)
            w = wilson(k, len(sel)) if sel else (None, None)
            A(f"- Condition {cond}: unstable {k}/{len(sel)}" + (f" (Wilson {pci(*w)})" if sel else ""))
        for v in ("correct", "incorrect"):
            sel = [r for r in recs if r["recorded_verdict"] == v]
            k = sum(r["all_match_recorded"] != "True" for r in sel)
            A(f"- Recorded verdict {v}: {k}/{len(sel)} transcripts with at least one differing re-judgement")
        A("\nThe agent and simulator were not rerun, so any change is judge variance. Ollama at temperature 0 is not "
          "guaranteed bit-deterministic. Compare with end-to-end AgentClinic verdict instability in 1.2: the judge alone "
          "accounts for the share above; the rest of the end-to-end instability comes from the agent and simulator.\n")
    else:
        A("PENDING: `rq3_judge_rerun.json` not present.\n")
    A("### 1.7 Sensitivity: earlier episode rule (episodes with `error` in the record dropped), files `*_errexcl.csv`\n")
    ex = rd("rq3_status_errexcl.csv")
    exd = {(r["bench"], r["condition"]): r for r in rd("rq3_divergence_errexcl.csv")}
    exp = {(r["bench"], r["condition"]): r for r in rd("rq3_passk_errexcl.csv") if r["k"] == "1"}
    A(table(["Benchmark", "Cond", "Complete task groups", "Divergent", "Unstable", "pass^1"],
            [[NAMES[r["bench"]], r["condition"], f'{r["tasks_complete"]}/10',
              (f'{exd[(r["bench"], r["condition"])]["divergent_n"]}' if (r["bench"], r["condition"]) in exd else "--"),
              (f'{exd[(r["bench"], r["condition"])]["unstable_n"]}' if (r["bench"], r["condition"]) in exd else "--"),
              (f3(exp[(r["bench"], r["condition"])]["pass_hat_k"], 2) if (r["bench"], r["condition"]) in exp else "--")] for r in ex]))
    A("\nThe earlier rule would have left RadABench and part of Synthetic Hospital as PARTIAL on a subset that excludes the "
      "agent's failures; it is not used for the paper.\n")

    # ---------------------------------------------------------------- RQ1
    prev = rd("rq1_prevalence.csv")
    mods = rd("rq1_modules.csv")
    A("## 2. RQ1 (reporting prevalence, 44 benchmarks)\n")
    A("Sources: `rq1_prevalence.csv`, `rq1_modules.csv`, `rq1_resolution.csv`, `rq1_contradictions*.csv`, "
      "`rq1_prevalence_ruleexcl.csv`, `rq1_modules_ruleexcl.csv`, `rq1_rule_*.csv`; tables `paper/tables/rq1_*.tex`; Fig 4 "
      "`paper/figures/fig4_prevalence.pdf`. Share REPORTED = resolved level >= 1; fully reported = level 2; NA leaves the "
      "denominator; Wilson 95% CI (descriptive: items within a benchmark are not independent). 44 benchmarks scored by both "
      "coder families; HealthCraft is a coder failure for both families (about 390k-token packet, beyond the context "
      "window; no cells) and is reported separately, not as a benchmark with scores. The sample is the frozen list of 45, "
      "not a random sample.\n")
    A("HealthCraft (reported separately; source `audit/BUILD_LOG.md`, decision log 2026-10-05/06): packet 1,065,370 tokens before "
      "the 150k cap and 382,521 after dropping every droppable S4 chunk (S2 alone is 233,961 tokens and the frozen rule never "
      "drops it), beyond the coder context window; both families failed, recorded as a coder failure. It has no cells in the "
      "prevalence, module or alpha results, and its perturbation variant (v13) did not run.\n")
    rs = {r["status"]: r for r in rd("rq1_resolution.csv")}
    A(f"Resolution: {rs['TOTAL_CELLS']['n_cells']} cells; {rs['resolved']['n_cells']} resolved by the two-family rule "
      f"({pc(rs['resolved']['share'])}), established_zero {rs['established_zero']['n_cells']}, na_accepted "
      f"{rs['na_accepted']['n_cells']}, na_rejected_as_zero {rs['na_rejected_as_zero']['n_cells']}, not_established "
      f"{rs['not_established']['n_cells']}; fallback to not established (level 0) {rs['ALL_FALLBACK']['n_cells']} "
      f"({pc(rs['ALL_FALLBACK']['share'])}); primary rule equals majority rule in {rs['PRIMARY_EQUALS_MAJORITY']['n_cells']} "
      f"cells ({pc(rs['PRIMARY_EQUALS_MAJORITY']['share'])}).\n")
    A("### 2.1 Module summary\n")
    A(table(["Module", "Rule", "Benchmarks", "Applicable cells", "Reported", "Wilson 95%", "Bootstrap 95% (benchmarks)",
             "Fully reported", "Wilson 95%", "Bootstrap 95%", "Mean per-benchmark fraction of max"],
            [[r["module"], r["rule"], r["n_benchmarks"], r["n_applicable_cells"], pc(r["share_reported"]),
              pci(r["reported_wilson_lo"], r["reported_wilson_hi"]), pci(r["reported_boot_lo"], r["reported_boot_hi"]),
              pc(r["share_full"]), pci(r["full_wilson_lo"], r["full_wilson_hi"]), pci(r["full_boot_lo"], r["full_boot_hi"]),
              f3(r["mean_bench_fraction_of_max"], 3)] for r in mods]))
    A("\n### 2.2 Per item (primary resolved rule; majority-rule sensitivity alongside)\n")
    res = {r["item"]: r for r in prev if r["rule"] == "resolved"}
    mj = {r["item"]: r for r in prev if r["rule"] == "majority"}
    rows = []
    for it in sorted(res, key=item_key):
        r, m = res[it], mj[it]
        rows.append([it, r["title"], r["n_applicable"], r["n_na"], f'{r["n_reported"]} ({pc(r["share_reported"])})',
                     pci(r["reported_lo"], r["reported_hi"]), f'{r["n_full"]} ({pc(r["share_full"])})',
                     pci(r["full_lo"], r["full_hi"]), r["n_fallback"], pc(m["share_reported"]), pc(m["share_full"])])
    A(table(["Item", "Property", "n appl.", "NA", "Reported", "Wilson 95%", "Fully reported", "Wilson 95%",
             "Fallback cells", "Majority: reported", "Majority: full"], rows))
    A("\n### 2.3 Contradiction flags (candidates only: not checked against documentation, no right of reply yet)\n")
    cb = rd("rq1_contradictions_by_bench.csv")
    ci_ = rd("rq1_contradictions.csv")
    flagged = [r for r in cb if int(r["cells_with_flag"])]
    ncells = sum(int(r["cells_with_flag"]) for r in cb)
    nagent = sum(int(r["cells_with_flag"]) for r in ci_ if r["item"].startswith("A"))
    A(f"- {ncells} cells carry a coder-raised flag, in {len(flagged)} of 44 benchmarks; {sum(int(r['cells_flag_verified_quote']) for r in cb)} "
      f"with a verified quote; {sum(int(r['cells_flag_two_families']) for r in cb)} flagged by both families. "
      f"{nagent} are on agent-module items, {ncells - nagent} on core items.")
    A("- Per item (cells with a flag): " + ", ".join(f'{r["item"]} {r["cells_with_flag"]}' for r in sorted(ci_, key=lambda r: item_key(r['item']))
                                                  if int(r["cells_with_flag"])) + ".")
    A("- Per benchmark: " + "; ".join(f'{r["bench"]} ({r["items"]})' for r in flagged) + ".\n")
    A("### 2.4 Sensitivity: excluding rule-affected benchmarks (R1-R7/R6a; design-review T7)\n")
    exl = rd("rq1_rule_excluded.csv")
    A(f"Excluded {len(exl)} benchmarks, leaving {len(res and mods) and [r for r in rd('rq1_modules_ruleexcl.csv') if r['rule'] == 'resolved'][0]['n_benchmarks']}: " +
      ", ".join(r["bench"] for r in exl) + ". (All 14 matched after analysis-side fix 4.)\n")
    A(table(["Module", "Rule", "Benchmarks", "Applicable cells", "Reported", "Bootstrap 95%", "Fully reported", "Bootstrap 95%"],
            [[r["module"], r["rule"], r["n_benchmarks"], r["n_applicable_cells"], pc(r["share_reported"]),
              pci(r["reported_boot_lo"], r["reported_boot_hi"]), pc(r["share_full"]), pci(r["full_boot_lo"], r["full_boot_hi"])]
             for r in rd("rq1_modules_ruleexcl.csv")]))
    dl = rd("rq1_rule_sensitivity_delta.csv")
    big = sorted(dl, key=lambda r: -abs(fl(r["reported_diff"])))[:5]
    A("\nPer-item reported share, all 44 vs excluded set: largest shifts " +
      "; ".join(f'{r["item"]} {pc(r["reported_all"])} to {pc(r["reported_excl"])} ({100 * fl(r["reported_diff"]):+.1f} points)' for r in big) +
      f". Largest absolute shift in fully reported: {max(abs(fl(r['full_diff'])) for r in dl) * 100:.1f} points. Full per-item table: `rq1_rule_sensitivity_delta.csv`.\n")

    # ---------------------------------------------------------------- RQ2
    A("## 3. RQ2 (validity and reliability of the automated audit)\n")
    A("### 3.1 Cross-family agreement, Codex gpt-5.5 versus Claude Sonnet (ordinal Krippendorff alpha, raw scores, NA missing)\n")
    A("Source: `rq2_alpha.csv`, `audit/agreement/agreement.json`; CI bootstrap over 44 benchmarks.\n")
    al = [r for r in rd("rq2_alpha.csv") if r["set"].startswith("all:")]
    ov = [r for r in al if r["scope"] == "overall"][0]
    A(f"Overall: alpha = {f3(ov['alpha'])} (95% CI {ci(ov['ci_lo'], ov['ci_hi'])}), {ov['units']} cells, {ov['benchmarks']} benchmarks.\n")
    its = sorted([r for r in al if r["scope"] == "item"], key=lambda r: item_key(r["item"]))
    A(table(["Item", "alpha", "95% CI", "Cells"], [[r["item"], f3(r["alpha"]), ci(r["ci_lo"], r["ci_hi"]), r["units"]] for r in its]))
    low = sorted([r for r in its if fl(r["alpha"]) is not None], key=lambda r: fl(r["alpha"]))[:3]
    A("\nLowest items: " + ", ".join(f'{r["item"]} {f3(r["alpha"], 2)}' for r in low) +
      ". Items with empty alpha are constant across coders (no variance). The pair and the all-coder set are identical "
      "(two coders), so `rq2_alpha.csv` carries both rows.\n")
    A("### 3.2 Agreement with published expert scores (gold)\n")
    A("Sources: `rq2_gold.csv`, `rq2_gold_direction.csv`, `rq2_gold_by_item.csv`, `audit/gold_abc/gold-abc/agreement/`, "
      "`audit/gold_bb/gold-betterbench/agreement/`. Effective score (a 1+ without a verified quote counts as 0). ABC: 9 "
      "benchmarks, binary; BetterBench: 22 benchmarks, 0-3. BetterBench CIs bootstrap over benchmarks. ABC gold is "
      "unlicensed: only aggregates are reported. Expert coding exists for core-like reuse items only (no gold for A-items, "
      "design-review T3).\n")
    gd = rd("rq2_gold.csv")
    A(table(["Set", "Coder", "Cells", "Raw agreement", "Wilson 95%", "Majority-class baseline", "Cohen kappa", "Quadratic-weighted kappa",
             "Primary statistic [95% CI, bootstrap]"],
            [[r["set"], r["coder"], r["n_cells"], f3(r["raw_agreement"]), ci(r["raw_lo"], r["raw_hi"]), f3(r["majority_baseline"]),
              f3(r["cohen_kappa"]), f3(r["weighted_kappa_quadratic"]) if r["weighted_kappa_quadratic"] else "--",
              f'{r["primary_statistic"]} {f3(r["primary_value"])} {ci(r["primary_ci_lo"], r["primary_ci_hi"])}'] for r in gd]))
    A("\nRaw agreement is close to the majority-class baseline for every coder, so the kappa values are the informative "
      "statistic; they are fair (ABC 0.25-0.29) to moderate (BetterBench weighted 0.45-0.53). Cross-family alpha (0.77) is "
      "much higher than coder-versus-expert agreement, and the Claude coder is highly self-consistent (3.3): the gap is "
      "consistent with a systematic difference between the coders and the expert scores (construct reading or instrument "
      "version), not random coder noise. The expert scores are not error-free either; the audit is presented as scalable "
      "screening with quantified error, not as equivalent to expert coding.\n")
    A("Error direction (disagreements only; over-credit = coder above the expert level). Single coders split about evenly "
      "(Claude 43% and 51% over-credit; Codex 49% and 45%); the RESOLVED label under-credits more (64% under on ABC, 63% on "
      "BetterBench), which fits the resolution rule falling back to level 0 when the families disagree (17.3% of cells fell "
      "back), though the file does not separate that cause. ABC is binary, so within-one-level is trivially 100%.\n")
    dr = rd("rq2_gold_direction.csv")
    A(table(["Set", "Coder", "Cells", "NA left out", "Disagreements", "Over-credit", "Under-credit", "Over share [Wilson 95%]", "Within one level"],
            [[r["set"], r["coder"], r["n"], r["n_na_left_out"], int(r["n_over"]) + int(r["n_under"]), r["n_over"], r["n_under"],
              f'{pc(r["share_over_of_disagree"])} {pci(r["over_lo"], r["over_hi"])}', pc(r["within_one"])] for r in dr]))
    A("\nPer-item agreement and direction (RESOLVED; all coders in `rq2_gold_by_item.csv`):\n")
    for s in ("ABC", "BetterBench"):
        sel = [r for r in rd("rq2_gold_by_item.csv") if r["set"] == s and r["coder"] == "RESOLVED"]
        A(f"**{s}** (flag = agreement below 0.5)\n")
        A(table(["Item", "Title", "n", "Agree", "Agreement", "Over", "Under", "Flag"],
                [[r["item"], r["title"][:48], r["n"], r["agree"], f3(r["agreement"], 2), r["n_over"], r["n_under"],
                  r["flag_agreement_lt_0.5"]] for r in sel]))
        A("")
    A("### 3.3 Coder test-retest (original vs retest, raw scores; seeded draw of 10 of 45 benchmarks, seed 20261004)\n")
    A("Sources: `rq2_retest.csv`, `rq2_retest.json`, `rq2_retest_per_benchmark.csv` (slug fix: analysis-side change 6). "
      "CLIs do not guarantee temperature 0.\n")
    rt = rd("rq2_retest.csv")
    A(table(["Coder", "Status", "Benchmarks", "Cells", "Exact", "Raw agreement [Wilson 95%]", "Ordinal alpha [95% CI]", "Quadratic-weighted kappa"],
            [[r["coder"], "PARTIAL" if r["partial"] == "True" else "complete", r["n_benchmarks"], r["n_cells"], r["n_exact"],
              f'{f3(r["raw_agreement"])} {ci(r["raw_lo"], r["raw_hi"])}', f'{f3(r["alpha_ordinal"])} {ci(r["alpha_lo"], r["alpha_hi"])}',
              f3(r["weighted_kappa_quadratic"])] for r in rt]))
    rj = json.loads((OUT / "rq2_retest.json").read_text(encoding="utf-8"))
    for c, d in rj["coders"].items():
        if d["partial"]:
            A(f"\nPARTIAL: {c} retest exists for {d['n_benchmarks']} of 10 drawn benchmarks ({', '.join(d['benchmarks_with_retest'])}); "
              f"missing: {', '.join(d['benchmarks_missing'])}.")
    _ra = json.loads((ROOT / "audit" / "retest" / "retest_agreement.json").read_text(encoding="utf-8"))
    if _ra.get("resolved"):
        A(f"\nResolved level, original versus retest (resolution rule applied to each run separately; `audit/retest/retest_agreement.json`, "
          f"all 10 drawn benchmarks): {_ra['resolved']['n_cells']} cells, raw agreement {f3(_ra['resolved']['raw_agreement'])}, "
          f"ordinal alpha {f3(_ra['resolved']['alpha_ordinal'])}.")
    A("\nProvenance: the Codex retest of 8 benchmarks ran through the Codex command-line interface (`agentaudit retest`); the other 2 "
      "(synthetic-hospital, diaggym-diagbench; the frozen code skips them, slug bug) were answered by the same coder (gpt-5.5, "
      "`CodexHeadlessBackend`) on the identical retest prompts the Claude coder received, through `audit/transport/run_codex_retest.py`, "
      "and imported with `import_validation.py --mode retest --coder codex`. The Claude retest ran through Claude Code subagents.")
    A("\n### 3.4 Perturbation sensitivity and specificity (OpenAI coder gpt-5.5, Claude Sonnet, resolved)\n")
    A("Sources: `rq2_perturbation.csv` (from the frozen `perturb --summarise` summary, `audit/perturb/perturb/summary.json`, "
      "rewritten after the Codex answers were imported via `audit/transport/import_validation.py --mode perturb --coder codex`; "
      "Codex answered the exported prompts through the transport `audit/transport/run_codex_prompts.py`, the same prompts the Claude "
      "coder received). 39 variants, 832 coded cells per coder and for RESOLVED (542 positive, 290 negative); 143 planned cells "
      "dropped (78 base level 0, 57 base level 2, 8 S4-comment patterns). Sensitivity = inject/buried/paraphrase reach level 2. "
      "Specificity: deletion must give level 0, decoy must not rise above the base level; both are relative to the base result "
      "(change-detection, design-review T1). RESOLVED applies the frozen resolution rule to the two coders' verified perturbed scores.\n")
    pt = rd("rq2_perturbation.csv")
    rows = []
    for coder in ("codex", "sonnet", "RESOLVED"):
        for metric, scope, vt in [("sensitivity", "overall", ""), ("sensitivity_any_level", "overall", "")] +                 [("sensitivity", "type", t) for t in ("inject", "buried", "paraphrase")] + [("specificity", "overall", "")] +                 [("specificity", "type", t) for t in ("deletion", "decoy")]:
            for r in pt:
                if (r["coder"], r["scope"], r["metric"], r["vtype"]) == (coder, scope, metric, vt) and not r["item"]:
                    rows.append([coder, metric, vt or "all", f'{r["hits"]}/{r["n"]}', pc(r["rate"]), pci(r["wilson_lo"], r["wilson_hi"])])
    A(table(["Coder", "Metric", "Type", "Hits/n", "Rate", "Wilson 95%"], rows))
    A("\nSpecificity is the weak side for every coder and for the resolved level: after the reporting chunk is deleted the coder still "
      "credits the property in most cells (deletion level 0: Sonnet 16/117, OpenAI 17/117, resolved 23/117); this may reflect the "
      "property being stated elsewhere in the packet, which this design cannot separate, so it is a finding about the "
      "coder-plus-packet pipeline, not about the coder alone. The decomposition of the failing cells (`perturb_diagnosis.md`) was "
      "written for Sonnet and has not been repeated for the OpenAI coder or the resolved level.\n")
    A("Per item: sensitivity and specificity with n; items with fewer than 10 cells are thin.\n")
    byit = {}
    for r in pt:
        if r["scope"] == "item":
            byit.setdefault(r["item"], {}).setdefault(r["coder"], {})[r["metric"]] = r
    rows = []
    for it in sorted(byit, key=item_key):
        row = [it]
        for coder in ("sonnet", "codex", "RESOLVED"):
            d = byit[it].get(coder, {})
            s_, sp = d.get("sensitivity"), d.get("specificity")
            row += [f'{s_["hits"]}/{s_["n"]} ({pc(s_["rate"], 0)})' if s_ else "--",
                    f'{sp["hits"]}/{sp["n"]} ({pc(sp["rate"], 0)})' if sp else "--"]
        rows.append(row)
    A(table(["Item", "Sonnet sens.", "Sonnet spec.", "OpenAI sens.", "OpenAI spec.", "Resolved sens.", "Resolved spec."], rows))
    A("\nPer item by type (`item_type` scope) is in `rq2_perturbation.csv`.\n")
    # headline block
    A("## Headline numbers\n")
    pk1 = {(r["bench"], r["condition"], r["k"]): r for r in pk}
    A("- RQ3 (final, 300 episodes): divergent task groups " + ", ".join(
        f'{NAMES[r["bench"]]} {r["condition"]} {r["divergent_n"]}/10' for r in dv) + "; unstable verdicts " + ", ".join(
        f'{r["unstable_n"]}/10' for r in dv) + " (same order).")
    A("- pass^1 to pass^5: " + "; ".join(
        f'{NAMES[b]} {c} {f3(pk1[(b, c, "1")]["pass_hat_k"], 2)} to {f3(pk1[(b, c, "5")]["pass_hat_k"], 2)}'
        for b, c in dict.fromkeys((r["bench"], r["condition"]) for r in pk)) + ".")
    A("- CI width 5 runs versus mean 1 run: " + "; ".join(
        f'{NAMES[r["bench"]]} {r["condition"]} {f3(r["ci_width_5run"], 2)} vs {f3(r["ci_width_1run_mean_over_repeats"], 2)}'
        for r in cw) + ".")
    A(f"- Grader versus state (Synthetic Hospital): 0 disagreements in {sum(int(r['agree']) + int(r['neutral_set_required']) for r in gs)} "
      f"episodes with a submission ({sum(int(r['agree']) for r in gs)} exact, {sum(int(r['neutral_set_required']) for r in gs)} not "
      f"exactly recomputable offline but consistent), {sum(int(r['no_submission']) for r in gs)} episodes with no submission.")
    _j = json.loads((OUT / "rq3_judge_rerun.json").read_text(encoding="utf-8")) if (OUT / "rq3_judge_rerun.json").exists() else None
    if _j:
        A(f"- Judge-only: {_j['transcripts_with_unstable_rejudgements']['k']}/{_j['transcripts']} transcripts with unstable re-judgements "
          f"(all {_j['transcripts']} AgentClinic transcripts x 3, not a subsample); "
          f"{_j['transcripts_where_any_rejudgement_differs_from_recorded']['k']}/{_j['transcripts']} differ from the recorded verdict.")
    _m = {(r["module"], r["rule"]): r for r in mods}
    A(f"- RQ1 (44 benchmarks): reported share core {pc(_m[('core', 'resolved')]['share_reported'])}, agent {pc(_m[('agent', 'resolved')]['share_reported'])}; "
      f"fully reported core {pc(_m[('core', 'resolved')]['share_full'])}, agent {pc(_m[('agent', 'resolved')]['share_full'])}; "
      f"majority rule core {pc(_m[('core', 'majority')]['share_reported'])}, agent {pc(_m[('agent', 'majority')]['share_reported'])}; "
      f"26 contradiction candidates in 13 benchmarks.")
    _ov = [r for r in rd("rq2_alpha.csv") if r["set"].startswith("all:") and r["scope"] == "overall"][0]
    A(f"- RQ2: cross-family alpha {f3(_ov['alpha'])} {ci(_ov['ci_lo'], _ov['ci_hi'])}; gold ABC kappa (resolved) "
      f"{f3([r for r in rd('rq2_gold.csv') if r['set'] == 'abc' and r['coder'] == 'RESOLVED'][0]['cohen_kappa'], 2)}, BetterBench weighted kappa (resolved) "
      f"{f3([r for r in rd('rq2_gold.csv') if r['set'] == 'betterbench' and r['coder'] == 'RESOLVED'][0]['weighted_kappa_quadratic'], 2)}; "
      f"Claude retest alpha {f3([r for r in rt if r['coder'] == 'sonnet'][0]['alpha_ordinal'], 3)} (10 benchmarks); "
      f"OpenAI retest alpha {f3([r for r in rt if r['coder'] == 'codex'][0]['alpha_ordinal'], 3)} (raw {f3([r for r in rt if r['coder'] == 'codex'][0]['raw_agreement'])}, "
      f"weighted kappa {f3([r for r in rt if r['coder'] == 'codex'][0]['weighted_kappa_quadratic'])}; 10 benchmarks), resolved retest alpha {f3(_ra['resolved']['alpha_ordinal'], 3)}; "
      "perturbation sensitivity / frozen specificity: " + "; ".join(
          f"{lab} {pc([r for r in pt if r['coder'] == cd and r['scope'] == 'overall' and r['metric'] == 'sensitivity'][0]['rate'])} / "
          f"{pc([r for r in pt if r['coder'] == cd and r['scope'] == 'overall' and r['metric'] == 'specificity'][0]['rate'])}"
          for cd, lab in (("sonnet", "Sonnet"), ("codex", "OpenAI"), ("RESOLVED", "resolved"))) + ".\n")
    k = next(i for i, x in enumerate(L) if x.startswith("## Headline numbers"))
    hl = L[k:]
    del L[k:]
    top = next(i for i, x in enumerate(L) if x.startswith("## 0. Status"))
    L[top:top] = hl
    (OUT / "RESULTS_SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("written", OUT / "RESULTS_SUMMARY.md", len(L))


if __name__ == "__main__":
    main()
