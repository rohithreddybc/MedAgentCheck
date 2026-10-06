# RESULTS SUMMARY (final-data run, 2026-10-06)

Every number below is read from a file in `analysis/out/` (source given per section) by `analysis/results_summary.py`. Seed 20261004, 2,000 bootstrap resamples throughout. All results are final (the OpenAI-coder perturbation and retest were completed 2026-10-06).

## Headline numbers

- RQ3 (final, 300 episodes): divergent task groups AgentClinic A 10/10, AgentClinic B 10/10, RadA-BenchPlat A 9/10, RadA-BenchPlat B 10/10, Synthetic Hospital A 5/10, Synthetic Hospital B 10/10; unstable verdicts 5/10, 6/10, 1/10, 2/10, 1/10, 4/10 (same order).
- pass^1 to pass^5: AgentClinic A 0.46 to 0.20; AgentClinic B 0.30 to 0.00; RadA-BenchPlat A 0.16 to 0.10; RadA-BenchPlat B 0.20 to 0.10; Synthetic Hospital A 0.38 to 0.30; Synthetic Hospital B 0.22 to 0.00.
- CI width 5 runs versus mean 1 run: AgentClinic A 0.46 vs 0.60; AgentClinic B 0.36 vs 0.52; RadA-BenchPlat A 0.40 vs 0.42; RadA-BenchPlat B 0.46 vs 0.48; Synthetic Hospital A 0.58 vs 0.60; Synthetic Hospital B 0.38 vs 0.50.
- Grader versus state (Synthetic Hospital): 0 disagreements in 88 episodes with a submission (69 exact, 19 not exactly recomputable offline but consistent), 12 episodes with no submission.
- Judge-only: 0/100 transcripts with unstable re-judgements (all 100 AgentClinic transcripts x 3, not a subsample); 1/100 differ from the recorded verdict.
- RQ1 (44 benchmarks): reported share core 53.7%, agent 62.5%; fully reported core 8.7%, agent 7.5%; majority rule core 58.6%, agent 69.3%; 26 contradiction candidates in 13 benchmarks.
- RQ2: cross-family alpha 0.771 [0.733, 0.806]; gold ABC kappa (resolved) 0.29, BetterBench weighted kappa (resolved) 0.47; Claude retest alpha 0.947 (10 benchmarks); OpenAI retest alpha 0.856 (raw 0.880, weighted kappa 0.856; 10 benchmarks), resolved retest alpha 0.894; perturbation sensitivity / frozen specificity: Sonnet 97.2% / 40.3%; OpenAI 95.8% / 40.0%; resolved 93.7% / 47.2%.

## 0. Status and analysis-side changes

No frozen scorer file was edited. Analysis-side changes made in this run (each documented where it lives):

1. `rq3_reruns.py` `episode_ok`: the first version dropped every episode whose record had a non-empty `error`. Those are agent-behaviour outcomes that carry a benchmark verdict (RadABench `benchmark-logged: ...` = invalid or missing tool inputs, verdict.pass False by the runner rule; Synthetic Hospital `model repeatedly produced no tool call` = no submission, scored 0), all with `driver_status` ok and 0 driver failures. The old rule removed 62 of 100 RadABench and 12 of 100 Synthetic Hospital episodes and left 3/10 and 2/10 complete RadABench task groups. Default is now: an episode counts when the driver finished it and it has actions and a verdict. The old rule is kept as `--exclude-episode-errors` (outputs `*_errexcl`) and reported in section 1.7.
2. `rq3_reruns.py` grader-vs-state: episodes with no submission have no grader reward; they are counted as `no_submission`, never as agreement.
3. `rq3_reruns.py` `reconstruct_with_neutral_count`: secondary check for the `neutral_set_required` episodes (uses the grader's reported neutral count; not an independent verification of that count).
4. `rq1_rq2.py` `manifest_slugs`: the frozen `bench_dir_candidates` cannot match hyphenated or renamed slugs, so only 7 of 14 rule-affected benchmarks were found by the `--exclude-rule-affected` switch. Ids are now mapped through `audit/manifests/*.yaml` (`frozen_list_id` to `name`); all 14 match. Same root cause as the retest bug logged on 2026-10-05.
5. `rq1_rq2.py` `load_resolved`: HealthCraft (coder failure for both families, empty `cells`) is skipped, so the population is 44 benchmarks. `gold_table` and `perturbation_table` accept the actual locations (`--gold-abc`, `--gold-betterbench`, `--perturb-run`).
6. `rq2_extras.py`: retest mapped through manifests (analysis-side slug fix, as `provisional_retest_all10.py`).
7. Frozen CLI run read-only on existing records: `agentaudit perturb --out audit/perturb --summarise` (wrote `audit/perturb/perturb/summary.json` and `summary.csv`, which did not exist). Perturbation plan check: 39 of the 40 design variants ran; the missing one is v13 = arxiv:2605.21496 = HealthCraft (no base result). No hyphenated benchmark was dropped (the plan keys on arXiv/PubMed ids, not slugs).

8. OpenAI-coder completion (2026-10-06): `audit/transport/run_codex_prompts.py` (perturbation, 39 variants) and `audit/transport/run_codex_retest.py` (the 2 retest benchmarks the CLI retest skipped) call the frozen `CodexHeadlessBackend` on the exported prompts, which are the prompts the Claude coder received; `import_validation.py --coder codex` stores them with the package scoring and verification code, and `finalize_retest` resolves the retest run and rewrites `retest_agreement.json` for all 10 drawn benchmarks (the package `map_bench_dirs` is replaced in memory only; no frozen file is edited).

## 1. RQ3 (end-to-end variability; run design v3)

Sources: `rq3_status.csv`, `rq3_divergence.csv`, `rq3_passk.csv`, `rq3_ci_width.csv`, `rq3_grader_state.csv`, `rq3_grader_state_episodes.csv`, `rq3_groups.csv`, `rq3_svda_groups.csv`; tables `paper/tables/rq3_*.tex`; Fig 5 `paper/figures/fig5_ci_width.pdf`. Unit = task group of 5 reruns; 10 tasks per benchmark and condition; A = benchmark temperature (AgentClinic 0.05, others 0), B = 0.7. Data complete: 300 of 300 episodes, 0 driver failures. Non-random selection of 3 benchmarks: existence findings, not population rates.

### 1.1 Coverage

| Benchmark | Cond | Complete task groups | Episodes ok/expected | Episodes with `error` in record (kept; agent failures with a verdict) |
|---|---|---|---|---|
| AgentClinic | A | 10/10 | 50/50 | 0 |
| AgentClinic | B | 10/10 | 50/50 | 0 |
| RadA-BenchPlat | A | 10/10 | 50/50 | 29 |
| RadA-BenchPlat | B | 10/10 | 50/50 | 33 |
| Synthetic Hospital | A | 10/10 | 50/50 | 5 |
| Synthetic Hospital | B | 10/10 | 50/50 | 7 |

### 1.2 Action divergence, verdict instability, same verdict with different actions

| Benchmark | Cond | T | Divergent groups | Mean distinct sequences | Unstable verdict groups | Same verdict, different actions | (all-pass / all-fail) |
|---|---|---|---|---|---|---|---|
| AgentClinic | A | 0.05 | 10/10 (100%) | 4.80 | 5/10 (50%) | 5/10 (50%) | 2 / 3 |
| AgentClinic | B | 0.7 | 10/10 (100%) | 5.00 | 6/10 (60%) | 4/10 (40%) | 0 / 4 |
| RadA-BenchPlat | A | 0.0 | 9/10 (90%) | 2.40 | 1/10 (10%) | 8/10 (80%) | 1 / 7 |
| RadA-BenchPlat | B | 0.7 | 10/10 (100%) | 3.40 | 2/10 (20%) | 8/10 (80%) | 1 / 7 |
| Synthetic Hospital | A | 0.0 | 5/10 (50%) | 1.50 | 1/10 (10%) | 4/10 (40%) | 1 / 3 |
| Synthetic Hospital | B | 0.7 | 10/10 (100%) | 4.60 | 4/10 (40%) | 6/10 (60%) | 0 / 6 |

AgentClinic strict-question divergence (full question text): A 10/10; B 10/10.
Pooled over the 6 benchmark x condition cells (60 task groups): divergent 54, unstable verdict 19, same verdict with different actions 35.

### 1.3 pass^k (k = 1..5), cluster bootstrap 95% CI over tasks

| Benchmark | Cond | Tasks | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|---|---|
| AgentClinic | A | 10 | 0.46 [0.22, 0.68] | 0.33 [0.13, 0.57] | 0.26 [0.05, 0.52] | 0.22 [0.02, 0.50] | 0.20 [0.00, 0.50] |
| AgentClinic | B | 10 | 0.30 [0.12, 0.48] | 0.16 [0.03, 0.31] | 0.09 [0.01, 0.20] | 0.04 [0.00, 0.10] | 0.00 [0.00, 0.00] |
| RadA-BenchPlat | A | 10 | 0.16 [0.00, 0.40] | 0.13 [0.00, 0.36] | 0.11 [0.00, 0.32] | 0.10 [0.00, 0.30] | 0.10 [0.00, 0.30] |
| RadA-BenchPlat | B | 10 | 0.20 [0.00, 0.46] | 0.16 [0.00, 0.40] | 0.14 [0.00, 0.38] | 0.12 [0.00, 0.34] | 0.10 [0.00, 0.30] |
| Synthetic Hospital | A | 10 | 0.38 [0.10, 0.68] | 0.36 [0.10, 0.64] | 0.34 [0.10, 0.60] | 0.32 [0.06, 0.60] | 0.30 [0.00, 0.60] |
| Synthetic Hospital | B | 10 | 0.22 [0.04, 0.42] | 0.13 [0.00, 0.30] | 0.08 [0.00, 0.20] | 0.04 [0.00, 0.10] | 0.00 [0.00, 0.00] |

### 1.4 Headline-score CI width, 1 run versus 5 runs

| Benchmark | Cond | Score 1 run (repeat 0) | CI 1 run | Width 1 run | Width 1 run, mean over repeats 0-4 (min-max) | Score 5 runs | CI 5 runs | Width 5 runs | Ratio 5 runs / repeat 0 | Ratio 5 runs / mean 1 run |
|---|---|---|---|---|---|---|---|---|---|---|
| AgentClinic | A | 0.50 | [0.20, 0.80] | 0.60 | 0.60 (0.60-0.60) | 0.46 | [0.22, 0.68] | 0.46 | 0.77 | 0.77 |
| AgentClinic | B | 0.30 | [0.10, 0.60] | 0.50 | 0.52 (0.50-0.60) | 0.30 | [0.12, 0.48] | 0.36 | 0.72 | 0.69 |
| RadA-BenchPlat | A | 0.10 | [0.00, 0.30] | 0.30 | 0.42 (0.30-0.50) | 0.16 | [0.00, 0.40] | 0.40 | 1.33 | 0.95 |
| RadA-BenchPlat | B | 0.10 | [0.00, 0.30] | 0.30 | 0.48 (0.30-0.60) | 0.20 | [0.00, 0.46] | 0.46 | 1.53 | 0.96 |
| Synthetic Hospital | A | 0.30 | [0.00, 0.60] | 0.60 | 0.60 (0.60-0.60) | 0.38 | [0.10, 0.68] | 0.58 | 0.97 | 0.97 |
| Synthetic Hospital | B | 0.20 | [0.00, 0.50] | 0.50 | 0.50 (0.30-0.60) | 0.22 | [0.04, 0.42] | 0.38 | 0.76 | 0.76 |

The 1-run width depends on which repeat is used (see the min-max column), so the mean over single runs is the fairer reference; against it the 5-run width is narrower in all six cells (ratio 0.69 to 0.97). Against repeat 0 alone it is wider for RadA-BenchPlat (ratio above 1) because repeat 0 had 1 pass in 10 tasks, which makes its bootstrap narrow near zero; the 5-run width carries the between-task spread of per-task pass rates. With 10 tasks per cell, five runs narrow the interval only modestly in most cells, and the task sample, not the run count, dominates the width. Report both ratios.

### 1.5 Grader versus observed state (Synthetic Hospital, patient_diagnosis)

| Cond | Episodes | Agree | Disagree | Not exactly recomputable (neutral set) | ...rebuilt with grader's neutral count: agree / disagree | No submission (no grader reward) | State missing | Server-stored reward differs from reported |
|---|---|---|---|---|---|---|---|---|
| A | 50 | 35 | 0 | 10 | 10 / 0 | 5 | 0 | 0 |
| B | 50 | 34 | 0 | 9 | 9 / 0 | 7 | 0 | 0 |

Of 88 episodes with a submission, 36 have reward above 0 (so agreement is not only trivial zeros). Disagreement = |recomputed - reported| > 1e-6 with the benchmark's own `eval.scoring.compute_all_metrics` (commit 911f34c4) on the stored submission and reference. The 0.5 cut-off behind pass^k is the study's derived binary, not the benchmark's criterion. Limit: the submission is the one the runner parsed from the agent's tool call; the server stores only a submitted flag.

### 1.6 Judge-only instability (AgentClinic; local ollama judge llama3.1-8b-ctx16k, T=0, 3 re-judgements per transcript)

Source: `rq3_judge_rerun.json`, `.csv`, `.jsonl`. Model digest 2b175d2e041c7108fcead7b5fe3a202d88ed24e8912c390dcc2f8a60f28b80ae. Transcripts: 100 (all complete AgentClinic episodes, limit None); re-judgements: 300.

- Transcripts whose 3 re-judgements are not all identical: 0/100 = 0.0% (Wilson 95% [0.0, 3.7]).
- Transcripts where any re-judgement differs from the recorded verdict: 1/100 = 1.0% (Wilson 95% [0.2, 5.4]).
- Individual re-judgements differing from the recorded verdict: 3/300 = 1.0%.
- Condition A: unstable 0/50 (Wilson [0.0, 7.1])
- Condition B: unstable 0/50 (Wilson [0.0, 7.1])
- Recorded verdict correct: 1/38 transcripts with at least one differing re-judgement
- Recorded verdict incorrect: 0/62 transcripts with at least one differing re-judgement

The agent and simulator were not rerun, so any change is judge variance. Ollama at temperature 0 is not guaranteed bit-deterministic. Compare with end-to-end AgentClinic verdict instability in 1.2: the judge alone accounts for the share above; the rest of the end-to-end instability comes from the agent and simulator.

### 1.7 Sensitivity: earlier episode rule (episodes with `error` in the record dropped), files `*_errexcl.csv`

| Benchmark | Cond | Complete task groups | Divergent | Unstable | pass^1 |
|---|---|---|---|---|---|
| AgentClinic | A | 10/10 | 10 | 5 | 0.46 |
| AgentClinic | B | 10/10 | 10 | 6 | 0.30 |
| RadA-BenchPlat | A | 3/10 | 3 | 0 | 0.33 |
| RadA-BenchPlat | B | 2/10 | 2 | 0 | 0.50 |
| Synthetic Hospital | A | 8/10 | 3 | 0 | 0.38 |
| Synthetic Hospital | B | 4/10 | 4 | 2 | 0.25 |

The earlier rule would have left RadABench and part of Synthetic Hospital as PARTIAL on a subset that excludes the agent's failures; it is not used for the paper.

## 2. RQ1 (reporting prevalence, 44 benchmarks)

Sources: `rq1_prevalence.csv`, `rq1_modules.csv`, `rq1_resolution.csv`, `rq1_contradictions*.csv`, `rq1_prevalence_ruleexcl.csv`, `rq1_modules_ruleexcl.csv`, `rq1_rule_*.csv`; tables `paper/tables/rq1_*.tex`; Fig 4 `paper/figures/fig4_prevalence.pdf`. Share REPORTED = resolved level >= 1; fully reported = level 2; NA leaves the denominator; Wilson 95% CI (descriptive: items within a benchmark are not independent). 44 benchmarks scored by both coder families; HealthCraft is a coder failure for both families (about 390k-token packet, beyond the context window; no cells) and is reported separately, not as a benchmark with scores. The sample is the frozen list of 45, not a random sample.

HealthCraft (reported separately; source `audit/BUILD_LOG.md`, decision log 2026-10-05/06): packet 1,065,370 tokens before the 150k cap and 382,521 after dropping every droppable S4 chunk (S2 alone is 233,961 tokens and the frozen rule never drops it), beyond the coder context window; both families failed, recorded as a coder failure. It has no cells in the prevalence, module or alpha results, and its perturbation variant (v13) did not run.

Resolution: 1100 cells; 613 resolved by the two-family rule (55.7%), established_zero 262, na_accepted 35, na_rejected_as_zero 7, not_established 183; fallback to not established (level 0) 190 (17.3%); primary rule equals majority rule in 1039 cells (94.5%).

### 2.1 Module summary

| Module | Rule | Benchmarks | Applicable cells | Reported | Wilson 95% | Bootstrap 95% (benchmarks) | Fully reported | Wilson 95% | Bootstrap 95% | Mean per-benchmark fraction of max |
|---|---|---|---|---|---|---|---|---|---|---|
| core | resolved | 44 | 596 | 53.7% | [49.7, 57.7] | [49.0, 58.6] | 8.7% | [6.7, 11.3] | [5.9, 11.9] | 0.313 |
| agent | resolved | 44 | 469 | 62.5% | [58.0, 66.7] | [57.8, 67.1] | 7.5% | [5.4, 10.2] | [5.1, 10.1] | 0.350 |
| core | majority | 44 | 596 | 58.6% | [54.6, 62.4] | [53.7, 64.0] | 9.7% | [7.6, 12.4] | [6.7, 13.1] | 0.343 |
| agent | majority | 44 | 469 | 69.3% | [65.0, 73.3] | [64.3, 73.9] | 8.1% | [6.0, 10.9] | [5.5, 10.8] | 0.387 |

### 2.2 Per item (primary resolved rule; majority-rule sensitivity alongside)

| Item | Property | n appl. | NA | Reported | Wilson 95% | Fully reported | Wilson 95% | Fallback cells | Majority: reported | Majority: full |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Traceability | 44 | 0 | 39 (88.6%) | [76.0, 95.0] | 5 (11.4%) | [5.0, 24.0] | 4 | 93.2% | 13.6% |
| C2 | Provenance and licence | 44 | 0 | 40 (90.9%) | [78.8, 96.4] | 7 (15.9%) | [7.9, 29.4] | 4 | 95.5% | 15.9% |
| C3 | Representativeness | 44 | 0 | 35 (79.5%) | [65.5, 88.8] | 0 (0.0%) | [0.0, 8.0] | 6 | 81.8% | 0.0% |
| C4 | Safety and bias tests | 44 | 0 | 14 (31.8%) | [20.0, 46.6] | 2 (4.5%) | [1.3, 15.1] | 4 | 31.8% | 4.5% |
| C5 | Contamination controls | 44 | 0 | 24 (54.5%) | [40.1, 68.3] | 3 (6.8%) | [2.3, 18.2] | 5 | 54.5% | 6.8% |
| C6 | Agent isolated from gold | 44 | 0 | 22 (50.0%) | [35.8, 64.2] | 5 (11.4%) | [5.0, 24.0] | 6 | 54.5% | 11.4% |
| C7 | Frozen environment | 44 | 0 | 23 (52.3%) | [37.9, 66.2] | 1 (2.3%) | [0.4, 11.8] | 14 | 54.5% | 2.3% |
| C8 | Oracle solver | 44 | 0 | 25 (56.8%) | [42.2, 70.3] | 0 (0.0%) | [0.0, 8.0] | 12 | 61.4% | 2.3% |
| C9 | Out-of-scope side effects detectable | 24 | 20 | 3 (12.5%) | [4.3, 31.0] | 0 (0.0%) | [0.0, 13.8] | 11 | 16.7% | 0.0% |
| C10 | Trivial success unlikely | 44 | 0 | 22 (50.0%) | [35.8, 64.2] | 1 (2.3%) | [0.4, 11.8] | 17 | 50.0% | 2.3% |
| C11 | Trivial-agent result | 44 | 0 | 0 (0.0%) | [0.0, 8.0] | 0 (0.0%) | [0.0, 8.0] | 1 | 0.0% | 0.0% |
| C12 | Evaluator validated | 44 | 0 | 25 (56.8%) | [42.2, 70.3] | 16 (36.4%) | [23.8, 51.1] | 6 | 63.6% | 40.9% |
| C13 | Non-determinism safeguards | 44 | 0 | 23 (52.3%) | [37.9, 66.2] | 2 (4.5%) | [1.3, 15.1] | 16 | 72.7% | 6.8% |
| C14 | Statistical comparison | 44 | 0 | 25 (56.8%) | [42.2, 70.3] | 10 (22.7%) | [12.8, 37.0] | 9 | 70.5% | 25.0% |
| A1 | Run count per reported number (e). | 44 | 0 | 21 (47.7%) | [33.8, 62.1] | 3 (6.8%) | [2.3, 18.2] | 11 | 56.8% | 9.1% |
| A2 | Uncertainty with stated resampling unit (e). | 44 | 0 | 18 (40.9%) | [27.7, 55.6] | 1 (2.3%) | [0.4, 11.8] | 7 | 43.2% | 2.3% |
| A3 | Action-level repeat-run reliability (a). | 44 | 0 | 10 (22.7%) | [12.8, 37.0] | 5 (11.4%) | [5.0, 24.0] | 3 | 27.3% | 13.6% |
| A4 | Model and harness pinning (a/e). | 44 | 0 | 19 (43.2%) | [29.7, 57.8] | 0 (0.0%) | [0.0, 8.0] | 9 | 54.5% | 0.0% |
| A5 | Tool contract specified (b). | 43 | 1 | 33 (76.7%) | [62.3, 86.8] | 4 (9.3%) | [3.7, 21.6] | 10 | 90.7% | 9.3% |
| A6 | Tool contract verified (b). | 43 | 1 | 21 (48.8%) | [34.6, 63.2] | 0 (0.0%) | [0.0, 8.2] | 13 | 60.5% | 0.0% |
| A7 | Write-action disclosure (d). | 31 | 13 | 30 (96.8%) | [83.8, 99.4] | 7 (22.6%) | [11.4, 39.8] | 1 | 96.8% | 22.6% |
| A8 | Grader reads state, or justifies transcript grading (c). | 44 | 0 | 41 (93.2%) | [81.8, 97.7] | 1 (2.3%) | [0.4, 11.8] | 2 | 97.7% | 2.3% |
| A9 | Agent-channel contamination (f). | 44 | 0 | 26 (59.1%) | [44.4, 72.3] | 0 (0.0%) | [0.0, 8.0] | 9 | 59.1% | 0.0% |
| A10 | Slice reporting (g). | 44 | 0 | 37 (84.1%) | [70.6, 92.1] | 1 (2.3%) | [0.4, 11.8] | 6 | 90.9% | 2.3% |
| A11 | Environment-state provenance (h). | 44 | 0 | 37 (84.1%) | [70.6, 92.1] | 13 (29.5%) | [18.2, 44.2] | 4 | 93.2% | 31.8% |

### 2.3 Contradiction flags (candidates only: not checked against documentation, no right of reply yet)

- 26 cells carry a coder-raised flag, in 13 of 44 benchmarks; 26 with a verified quote; 3 flagged by both families. 15 are on agent-module items, 11 on core items.
- Per item (cells with a flag): C2 3, C6 4, C7 2, C13 1, C14 1, A4 5, A5 2, A6 3, A9 3, A11 2.
- Per benchmark: abra (A11;A4;A6;C2); agentclinic (C7); clinenv (A5); deeptumorvqa (A4;A5;A6); ecg-scroll (C6); healthagentbench (A9;C6); healthcare-ai-gym (A11;A6;C2); klinikebench (A9;C6); med-inquire (A9;C6); medsp1000 (A4;C13;C2); physassistbench (A4;C7); physicianbench (A4); rha-safety (C14).

### 2.4 Sensitivity: excluding rule-affected benchmarks (R1-R7/R6a; design-review T7)

Excluded 14 benchmarks, leaving 30: clindef, clinicalagent-bench, diaggym-diagbench, evimed, h-adminsim, healthcare-ai-gym, med-inquire, medagentbench-v2, medagentsim, medimageedu, medsp1000, openhospital, rha-safety, vivabench. (All 14 matched after analysis-side fix 4.)

| Module | Rule | Benchmarks | Applicable cells | Reported | Bootstrap 95% | Fully reported | Bootstrap 95% |
|---|---|---|---|---|---|---|---|
| core | resolved | 30 | 406 | 58.4% | [52.0, 64.0] | 9.6% | [5.9, 14.1] |
| agent | resolved | 30 | 317 | 65.0% | [60.1, 70.1] | 10.1% | [7.0, 13.3] |
| core | majority | 30 | 406 | 63.3% | [56.4, 69.4] | 10.8% | [6.8, 15.4] |
| agent | majority | 30 | 317 | 71.0% | [66.5, 75.5] | 10.7% | [7.5, 13.8] |

Per-item reported share, all 44 vs excluded set: largest shifts C7 52.3% to 70.0% (+17.7 points); C10 50.0% to 66.7% (+16.7 points); C14 56.8% to 46.7% (-10.2 points); C6 50.0% to 60.0% (+10.0 points); C8 56.8% to 66.7% (+9.8 points). Largest absolute shift in fully reported: 10.5 points. Full per-item table: `rq1_rule_sensitivity_delta.csv`.

## 3. RQ2 (validity and reliability of the automated audit)

### 3.1 Cross-family agreement, Codex gpt-5.5 versus Claude Sonnet (ordinal Krippendorff alpha, raw scores, NA missing)

Source: `rq2_alpha.csv`, `audit/agreement/agreement.json`; CI bootstrap over 44 benchmarks.

Overall: alpha = 0.771 (95% CI [0.733, 0.806]), 1100 cells, 44 benchmarks.

| Item | alpha | 95% CI | Cells |
|---|---|---|---|
| C1 | 0.602 | [0.285, 0.834] | 44 |
| C2 | 0.588 | [0.285, 0.815] | 44 |
| C3 | 0.462 | [-0.024, 0.801] | 44 |
| C4 | 0.826 | [0.625, 0.957] | 44 |
| C5 | 0.813 | [0.622, 0.961] | 44 |
| C6 | 0.773 | [0.606, 0.882] | 44 |
| C7 | 0.379 | [0.054, 0.634] | 44 |
| C8 | 0.489 | [0.157, 0.750] | 44 |
| C9 | 0.514 | [0.000, 0.879] | 44 |
| C10 | 0.196 | [-0.130, 0.486] | 44 |
| C11 | 0.000 | [-0.036, 0.000] | 44 |
| C12 | 0.914 | [0.764, 1.000] | 44 |
| C13 | 0.601 | [0.310, 0.809] | 44 |
| C14 | 0.914 | [0.803, 0.982] | 44 |
| A1 | 0.734 | [0.521, 0.881] | 44 |
| A2 | 0.748 | [0.505, 0.916] | 44 |
| A3 | 0.953 | [0.849, 1.000] | 44 |
| A4 | 0.814 | [0.590, 0.955] | 44 |
| A5 | 0.543 | [0.173, 0.809] | 44 |
| A6 | 0.559 | [0.271, 0.801] | 44 |
| A7 | 0.016 | [-0.359, 0.348] | 44 |
| A8 | 0.561 | [-0.036, 1.000] | 44 |
| A9 | 0.525 | [0.207, 0.784] | 44 |
| A10 | 0.407 | [-0.012, 0.753] | 44 |
| A11 | 0.848 | [0.660, 0.968] | 44 |

Lowest items: C11 0.00, A7 0.02, C10 0.20. Items with empty alpha are constant across coders (no variance). The pair and the all-coder set are identical (two coders), so `rq2_alpha.csv` carries both rows.

### 3.2 Agreement with published expert scores (gold)

Sources: `rq2_gold.csv`, `rq2_gold_direction.csv`, `rq2_gold_by_item.csv`, `audit/gold_abc/gold-abc/agreement/`, `audit/gold_bb/gold-betterbench/agreement/`. Effective score (a 1+ without a verified quote counts as 0). ABC: 9 benchmarks, binary; BetterBench: 22 benchmarks, 0-3. BetterBench CIs bootstrap over benchmarks. ABC gold is unlicensed: only aggregates are reported. Expert coding exists for core-like reuse items only (no gold for A-items, design-review T3).

| Set | Coder | Cells | Raw agreement | Wilson 95% | Majority-class baseline | Cohen kappa | Quadratic-weighted kappa | Primary statistic [95% CI, bootstrap] |
|---|---|---|---|---|---|---|---|---|
| abc | codex | 198 | 0.646 | [0.578, 0.710] | 0.621 | 0.253 | -- | cohen_kappa 0.253 [0.122, 0.382] |
| abc | sonnet | 198 | 0.657 | [0.588, 0.719] | 0.621 | 0.289 | -- | cohen_kappa 0.289 [0.106, 0.442] |
| abc | RESOLVED | 198 | 0.646 | [0.578, 0.710] | 0.621 | 0.286 | -- | cohen_kappa 0.286 [0.149, 0.404] |
| betterbench | codex | 423 | 0.511 | [0.463, 0.558] | 0.485 | 0.300 | 0.450 | weighted_kappa_quadratic 0.450 [0.382, 0.521] |
| betterbench | sonnet | 425 | 0.527 | [0.480, 0.574] | 0.482 | 0.327 | 0.530 | weighted_kappa_quadratic 0.530 [0.454, 0.598] |
| betterbench | RESOLVED | 425 | 0.513 | [0.466, 0.560] | 0.482 | 0.314 | 0.472 | weighted_kappa_quadratic 0.472 [0.405, 0.540] |

Raw agreement is close to the majority-class baseline for every coder, so the kappa values are the informative statistic; they are fair (ABC 0.25-0.29) to moderate (BetterBench weighted 0.45-0.53). Cross-family alpha (0.77) is much higher than coder-versus-expert agreement, and the Claude coder is highly self-consistent (3.3): the gap is consistent with a systematic difference between the coders and the expert scores (construct reading or instrument version), not random coder noise. The expert scores are not error-free either; the audit is presented as scalable screening with quantified error, not as equivalent to expert coding.

Error direction (disagreements only; over-credit = coder above the expert level). Single coders split about evenly (Claude 43% and 51% over-credit; Codex 49% and 45%); the RESOLVED label under-credits more (64% under on ABC, 63% on BetterBench), which fits the resolution rule falling back to level 0 when the families disagree (17.3% of cells fell back), though the file does not separate that cause. ABC is binary, so within-one-level is trivially 100%.

| Set | Coder | Cells | NA left out | Disagreements | Over-credit | Under-credit | Over share [Wilson 95%] | Within one level |
|---|---|---|---|---|---|---|---|---|
| ABC | codex | 198 | 0 | 70 | 34 | 36 | 48.6% [37.2, 60.0] | 100.0% |
| ABC | sonnet | 198 | 0 | 68 | 29 | 39 | 42.6% [31.6, 54.5] | 100.0% |
| ABC | RESOLVED | 198 | 0 | 70 | 25 | 45 | 35.7% [25.5, 47.4] | 100.0% |
| BetterBench | codex | 423 | 17 | 207 | 94 | 113 | 45.4% [38.8, 52.2] | 76.4% |
| BetterBench | sonnet | 425 | 15 | 201 | 102 | 99 | 50.7% [43.9, 57.6] | 80.9% |
| BetterBench | RESOLVED | 425 | 15 | 207 | 77 | 130 | 37.2% [30.9, 44.0] | 77.2% |

Per-item agreement and direction (RESOLVED; all coders in `rq2_gold_by_item.csv`):

**ABC** (flag = agreement below 0.5)

| Item | Title | n | Agree | Agreement | Over | Under | Flag |
|---|---|---|---|---|---|---|---|
| R.1 | Benchmark is fully or at least partially open-so | 9 | 9 | 1.00 | 0 | 0 |  |
| R.2 | Benchmark offers an open-source evaluation harne | 9 | 8 | 0.89 | 0 | 1 |  |
| R.3 | Measures to prevent data contamination, such as  | 9 | 6 | 0.67 | 2 | 1 |  |
| R.4 | Measures or plans to update challenges over time | 9 | 5 | 0.56 | 4 | 0 |  |
| R.5 | States the relationship between the agent capabi | 9 | 8 | 0.89 | 0 | 1 |  |
| R.6 | States the evaluation subject of the benchmark ( | 9 | 8 | 0.89 | 0 | 1 |  |
| R.7 | Describes steps taken to prevent, identify and c | 9 | 7 | 0.78 | 2 | 0 |  |
| R.8 | Qualitative discussion of the impact of unavoida | 9 | 6 | 0.67 | 3 | 0 |  |
| R.9 | Quantitative analysis of the impact of unavoidab | 9 | 5 | 0.56 | 3 | 1 |  |
| R.10 | Reports statistical significance metrics such as | 9 | 8 | 0.89 | 1 | 0 |  |
| R.11 | Gives guidance on interpreting results given eva | 9 | 5 | 0.56 | 4 | 0 |  |
| R.12 | Reports results of non-AI baselines (e.g., human | 9 | 8 | 0.89 | 1 | 0 |  |
| R.13 | Reports results of trivial agents (e.g., one tha | 9 | 8 | 0.89 | 0 | 1 |  |
| T.1 | For self-hosted tools, the prompt explicitly sta | 9 | 3 | 0.33 | 0 | 6 | FLAG |
| T.2 | For API-based tools, service availability and ra | 9 | 3 | 0.33 | 0 | 6 | FLAG |
| T.3 | API interruptions are detected and the evaluatio | 9 | 2 | 0.22 | 0 | 7 | FLAG |
| T.4 | Legacy data and state are fully cleaned up befor | 9 | 4 | 0.44 | 0 | 5 | FLAG |
| T.5 | Agents are fully isolated from ground-truth resu | 9 | 5 | 0.56 | 1 | 3 |  |
| T.6 | Environment setup is fully reproducible and froz | 9 | 1 | 0.11 | 0 | 8 | FLAG |
| T.7 | Correctness of ground-truth annotation is verifi | 9 | 6 | 0.67 | 2 | 1 |  |
| T.8 | Correctness of task setup (solvability) is verif | 9 | 6 | 0.67 | 2 | 1 |  |
| T.9 | An automatic oracle solver demonstrates the task | 9 | 7 | 0.78 | 0 | 2 |  |

**BetterBench** (flag = agreement below 0.5)

| Item | Title | n | Agree | Agreement | Over | Under | Flag |
|---|---|---|---|---|---|---|---|
| J.1-1 | Definition of tested capability or characteristi | 22 | 17 | 0.77 | 2 | 3 |  |
| J.1-5 | Involvement of domain experts | 22 | 8 | 0.36 | 0 | 14 | FLAG |
| J.1-6 | Integration of domain literature | 22 | 12 | 0.55 | 8 | 2 |  |
| J.1-9 | Includes floors and ceilings for metric | 22 | 7 | 0.32 | 2 | 13 | FLAG |
| J.1-12 | Addresses input sensitivity | 22 | 13 | 0.59 | 1 | 8 |  |
| J.2-1 | Availability of evaluation code | 22 | 17 | 0.77 | 2 | 3 |  |
| J.2-2 | Script to replicate results is explicitly includ | 22 | 6 | 0.27 | 11 | 5 | FLAG |
| J.2-4 | Supports evaluation of models via API calls | 14 | 9 | 0.64 | 4 | 1 |  |
| J.2-5 | Supports evaluation of local models | 22 | 11 | 0.50 | 2 | 9 |  |
| J.2-7 | Inclusion of 'training_on_test_set' task | 17 | 12 | 0.71 | 3 | 2 |  |
| J.2-8 | Assess need for warnings for sensitive/harmful c | 22 | 12 | 0.55 | 10 | 0 |  |
| J.2-9 | Release requirements specified | 22 | 10 | 0.45 | 10 | 2 | FLAG |
| J.3-4 | Code documentation available | 22 | 9 | 0.41 | 6 | 7 | FLAG |
| J.3-8 | Documentation of benchmark construction process | 22 | 10 | 0.45 | 2 | 10 | FLAG |
| J.3-11 | Documentation of data sources and how the data w | 21 | 16 | 0.76 | 2 | 3 |  |
| J.3-12 | Documentation of the data preprocessing steps ta | 21 | 8 | 0.38 | 1 | 12 | FLAG |
| J.3-16 | Documentation of evaluation metric(s) | 22 | 16 | 0.73 | 2 | 4 |  |
| J.3-17 | Report statistical significance of benchmark res | 22 | 6 | 0.27 | 8 | 8 | FLAG |
| J.3-19 | Specifies applicable license | 22 | 7 | 0.32 | 1 | 14 | FLAG |
| J.4-1 | Code usability checked within the last year | 22 | 12 | 0.55 | 0 | 10 |  |

### 3.3 Coder test-retest (original vs retest, raw scores; seeded draw of 10 of 45 benchmarks, seed 20261004)

Sources: `rq2_retest.csv`, `rq2_retest.json`, `rq2_retest_per_benchmark.csv` (slug fix: analysis-side change 6). CLIs do not guarantee temperature 0.

| Coder | Status | Benchmarks | Cells | Exact | Raw agreement [Wilson 95%] | Ordinal alpha [95% CI] | Quadratic-weighted kappa |
|---|---|---|---|---|---|---|---|
| codex | complete | 10 | 250 | 220 | 0.880 [0.834, 0.915] | 0.856 [0.802, 0.897] | 0.856 |
| sonnet | complete | 10 | 250 | 240 | 0.960 [0.928, 0.978] | 0.947 [0.916, 0.975] | 0.944 |

Resolved level, original versus retest (resolution rule applied to each run separately; `audit/retest/retest_agreement.json`, all 10 drawn benchmarks): 250 cells, raw agreement 0.936, ordinal alpha 0.894.

Provenance: the Codex retest of 8 benchmarks ran through the Codex command-line interface (`agentaudit retest`); the other 2 (synthetic-hospital, diaggym-diagbench; the frozen code skips them, slug bug) were answered by the same coder (gpt-5.5, `CodexHeadlessBackend`) on the identical retest prompts the Claude coder received, through `audit/transport/run_codex_retest.py`, and imported with `import_validation.py --mode retest --coder codex`. The Claude retest ran through Claude Code subagents.

### 3.4 Perturbation sensitivity and specificity (OpenAI coder gpt-5.5, Claude Sonnet, resolved)

Sources: `rq2_perturbation.csv` (from the frozen `perturb --summarise` summary, `audit/perturb/perturb/summary.json`, rewritten after the Codex answers were imported via `audit/transport/import_validation.py --mode perturb --coder codex`; Codex answered the exported prompts through the transport `audit/transport/run_codex_prompts.py`, the same prompts the Claude coder received). 39 variants, 832 coded cells per coder and for RESOLVED (542 positive, 290 negative); 143 planned cells dropped (78 base level 0, 57 base level 2, 8 S4-comment patterns). Sensitivity = inject/buried/paraphrase reach level 2. Specificity: deletion must give level 0, decoy must not rise above the base level; both are relative to the base result (change-detection, design-review T1). RESOLVED applies the frozen resolution rule to the two coders' verified perturbed scores.

| Coder | Metric | Type | Hits/n | Rate | Wilson 95% |
|---|---|---|---|---|---|
| codex | sensitivity | all | 519/542 | 95.8% | [93.7, 97.2] |
| codex | sensitivity_any_level | all | 538/542 | 99.3% | [98.1, 99.7] |
| codex | sensitivity | inject | 176/187 | 94.1% | [89.8, 96.7] |
| codex | sensitivity | buried | 175/181 | 96.7% | [93.0, 98.5] |
| codex | sensitivity | paraphrase | 168/174 | 96.6% | [92.7, 98.4] |
| codex | specificity | all | 116/290 | 40.0% | [34.5, 45.7] |
| codex | specificity | deletion | 17/117 | 14.5% | [9.3, 22.0] |
| codex | specificity | decoy | 99/173 | 57.2% | [49.8, 64.4] |
| sonnet | sensitivity | all | 527/542 | 97.2% | [95.5, 98.3] |
| sonnet | sensitivity_any_level | all | 541/542 | 99.8% | [99.0, 100.0] |
| sonnet | sensitivity | inject | 181/187 | 96.8% | [93.2, 98.5] |
| sonnet | sensitivity | buried | 178/181 | 98.3% | [95.2, 99.4] |
| sonnet | sensitivity | paraphrase | 168/174 | 96.6% | [92.7, 98.4] |
| sonnet | specificity | all | 117/290 | 40.3% | [34.9, 46.1] |
| sonnet | specificity | deletion | 16/117 | 13.7% | [8.6, 21.1] |
| sonnet | specificity | decoy | 101/173 | 58.4% | [50.9, 65.5] |
| RESOLVED | sensitivity | all | 508/542 | 93.7% | [91.4, 95.5] |
| RESOLVED | sensitivity_any_level | all | 537/542 | 99.1% | [97.9, 99.6] |
| RESOLVED | sensitivity | inject | 172/187 | 92.0% | [87.2, 95.1] |
| RESOLVED | sensitivity | buried | 173/181 | 95.6% | [91.5, 97.7] |
| RESOLVED | sensitivity | paraphrase | 163/174 | 93.7% | [89.0, 96.4] |
| RESOLVED | specificity | all | 137/290 | 47.2% | [41.6, 53.0] |
| RESOLVED | specificity | deletion | 23/117 | 19.7% | [13.5, 27.8] |
| RESOLVED | specificity | decoy | 114/173 | 65.9% | [58.6, 72.5] |

Specificity is the weak side for every coder and for the resolved level: after the reporting chunk is deleted the coder still credits the property in most cells (deletion level 0: Sonnet 16/117, OpenAI 17/117, resolved 23/117); this may reflect the property being stated elsewhere in the packet, which this design cannot separate, so it is a finding about the coder-plus-packet pipeline, not about the coder alone. The decomposition of the failing cells (`perturb_diagnosis.md`) was written for Sonnet and has not been repeated for the OpenAI coder or the resolved level.

Per item: sensitivity and specificity with n; items with fewer than 10 cells are thin.

| Item | Sonnet sens. | Sonnet spec. | OpenAI sens. | OpenAI spec. | Resolved sens. | Resolved spec. |
|---|---|---|---|---|---|---|
| C1 | 20/20 (100%) | 6/13 (46%) | 19/20 (95%) | 6/13 (46%) | 19/20 (95%) | 6/13 (46%) |
| C2 | 18/18 (100%) | 8/14 (57%) | 17/18 (94%) | 4/14 (29%) | 17/18 (94%) | 8/14 (57%) |
| C3 | 22/23 (96%) | 11/15 (73%) | 23/23 (100%) | 11/15 (73%) | 22/23 (96%) | 12/15 (80%) |
| C4 | 23/23 (100%) | 9/12 (75%) | 23/23 (100%) | 7/12 (58%) | 23/23 (100%) | 9/12 (75%) |
| C5 | 21/21 (100%) | 4/15 (27%) | 21/21 (100%) | 2/15 (13%) | 21/21 (100%) | 5/15 (33%) |
| C6 | 21/21 (100%) | 1/7 (14%) | 21/21 (100%) | 2/7 (29%) | 21/21 (100%) | 2/7 (29%) |
| C7 | 22/24 (92%) | 5/11 (45%) | 24/24 (100%) | 6/11 (55%) | 22/24 (92%) | 6/11 (55%) |
| C8 | 24/24 (100%) | 10/11 (91%) | 24/24 (100%) | 8/11 (73%) | 24/24 (100%) | 10/11 (91%) |
| C9 | 23/23 (100%) | 2/8 (25%) | 20/23 (87%) | 6/8 (75%) | 20/23 (87%) | 6/8 (75%) |
| C10 | 22/22 (100%) | 4/14 (29%) | 22/22 (100%) | 2/14 (14%) | 22/22 (100%) | 4/14 (29%) |
| C11 | 20/23 (87%) | 3/8 (38%) | 20/23 (87%) | 3/8 (38%) | 18/23 (78%) | 3/8 (38%) |
| C12 | 17/17 (100%) | 2/12 (17%) | 17/17 (100%) | 2/12 (17%) | 17/17 (100%) | 2/12 (17%) |
| C13 | 23/23 (100%) | 1/11 (9%) | 23/23 (100%) | 1/11 (9%) | 23/23 (100%) | 1/11 (9%) |
| C14 | 19/19 (100%) | 6/10 (60%) | 19/19 (100%) | 6/10 (60%) | 19/19 (100%) | 6/10 (60%) |
| A1 | 21/21 (100%) | 2/14 (14%) | 20/21 (95%) | 3/14 (21%) | 20/21 (95%) | 3/14 (21%) |
| A2 | 23/23 (100%) | 6/11 (55%) | 23/23 (100%) | 7/11 (64%) | 23/23 (100%) | 7/11 (64%) |
| A3 | 21/21 (100%) | 6/7 (86%) | 21/21 (100%) | 3/7 (43%) | 21/21 (100%) | 6/7 (86%) |
| A4 | 16/24 (67%) | 3/12 (25%) | 19/24 (79%) | 3/12 (25%) | 14/24 (58%) | 3/12 (25%) |
| A5 | 19/19 (100%) | 3/10 (30%) | 19/19 (100%) | 4/10 (40%) | 19/19 (100%) | 4/10 (40%) |
| A6 | 24/24 (100%) | 3/8 (38%) | 15/24 (62%) | 4/8 (50%) | 15/24 (62%) | 4/8 (50%) |
| A7 | 20/20 (100%) | 4/11 (36%) | 20/20 (100%) | 6/11 (55%) | 20/20 (100%) | 6/11 (55%) |
| A8 | 23/23 (100%) | 4/14 (29%) | 23/23 (100%) | 4/14 (29%) | 23/23 (100%) | 4/14 (29%) |
| A9 | 24/24 (100%) | 3/12 (25%) | 24/24 (100%) | 3/12 (25%) | 24/24 (100%) | 5/12 (42%) |
| A10 | 23/23 (100%) | 8/16 (50%) | 23/23 (100%) | 9/16 (56%) | 23/23 (100%) | 10/16 (62%) |
| A11 | 18/19 (95%) | 3/14 (21%) | 19/19 (100%) | 4/14 (29%) | 18/19 (95%) | 5/14 (36%) |

Per item by type (`item_type` scope) is in `rq2_perturbation.csv`.

## 4. Token totals (added 2026-10-06)

Source: `audit/transport/prompts/*/meta.json`, key `prompt_tokens_est` (estimated prompt tokens, four characters per token) of the 45 main-audit packet prompts. The totals do not include the prompts of the gold, perturbation or retest runs (`prompts_gold_abc`, `prompts_gold_betterbench`, `prompts_perturb`, `prompts_retest`), which were not used for the paper's totals. Script: `analysis/token_totals.py`, run from the project root as

```
python analysis/token_totals.py
```

| Quantity | Value |
|---|---|
| Prompts (packets) | 45 |
| Total estimated prompt tokens, all 45 prompts | 3,981,598 |
| Median per prompt | 63,219 |
| Total, the 44 coded packets (HealthCraft excluded; its prompt is 387,594) | 3,594,004 |

The paper's 3,981,598 / 63,219 / 3,594,004 match this recomputation.

## 5. Like-for-like agreement on gold cells (added 2026-10-06)

Question: is the coder-vs-expert kappa (ABC 0.29 Cohen; BetterBench 0.47 quadratic-weighted) comparable with the cross-family alpha (0.77, audit items)? Not as printed: they use different statistics on different cells. Here the same gold cells carry the same statistics for coder-vs-coder (codex vs sonnet) and coder-vs-expert. Scorer code paths (`agentaudit.gold`: `load_gold`, `items_for_set`, `load_predictions`, `resolved_predictions`, `agreement_stats`) are reused: effective score (a 1+ without a verified quote counts as 0), same item set, NA cells left out, BetterBench 0/5/10/15 mapped to 0-3, same gold cutoff. The script asserts that the per-coder and resolved n, kappa, weighted kappa, raw agreement and bootstrap CIs equal `agreement.json`.

Command (project root):

```
python analysis/gold_coder_pair.py --write-summary
```

Script `analysis/gold_coder_pair.py`; machine-readable output `analysis/out/gold_coder_pair.json`. Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, the same resample used for every statistic in a set (so differences are paired), percentile 95% CI. Values to two decimals.

### 5.1 ABC gold (primary statistic: Cohen kappa)

Common cells (expert, codex and sonnet all scored): n = 198 cells, 9 benchmarks. agreement.json n_cells: codex 198, sonnet 198, resolved 198 (identical to the common set).

| Pair | n | Primary (95% CI) | Cohen kappa | Raw agreement | Krippendorff alpha (ordinal) |
|---|---|---|---|---|---|
| codex vs sonnet | 198 | 0.71 [0.59, 0.80] | 0.71 | 0.86 | 0.71 |
| codex vs expert | 198 | 0.25 [0.12, 0.38] | 0.25 | 0.65 | 0.25 |
| sonnet vs expert | 198 | 0.29 [0.11, 0.44] | 0.29 | 0.66 | 0.29 |
| resolved vs expert | 198 | 0.29 | 0.29 | 0.65 | 0.28 |

Differences in the primary statistic (coder pair minus coder-vs-expert), paired bootstrap over benchmarks:

| Difference | Point | 95% CI | Share of resamples > 0 |
|---|---|---|---|
| pair - codex/expert | +0.46 | [0.34, 0.59] | 1.000 |
| pair - sonnet/expert | +0.42 | [0.25, 0.62] | 1.000 |
| pair - mean(coder/expert) | +0.44 | [0.30, 0.60] | 1.000 |
| sonnet/expert - codex/expert | +0.04 | [-0.06, 0.13] | 0.753 |

agreement.json values reproduced on the original cell sets (assertion passed): codex n=198, primary 0.2527, CI [0.12, 0.38]; sonnet n=198, primary 0.2887, CI [0.11, 0.44]; resolved n=198, primary 0.2859, CI [0.15, 0.40].

### 5.2 BetterBench gold (primary statistic: quadratic-weighted kappa)

Common cells (expert, codex and sonnet all scored): n = 423 cells, 22 benchmarks. agreement.json n_cells: codex 423, sonnet 425, resolved 425; the common set drops cells where one coder answered NA, so coder-vs-expert values below can differ slightly from agreement.json (the published values are in the last paragraph of this subsection).

| Pair | n | Primary (95% CI) | Cohen kappa | Raw agreement | Krippendorff alpha (ordinal) |
|---|---|---|---|---|---|
| codex vs sonnet | 423 | 0.76 [0.69, 0.82] | 0.58 | 0.70 | 0.76 |
| codex vs expert | 423 | 0.45 [0.38, 0.52] | 0.30 | 0.51 | 0.45 |
| sonnet vs expert | 423 | 0.52 [0.45, 0.60] | 0.32 | 0.52 | 0.52 |
| resolved vs expert | 423 | 0.47 | 0.31 | 0.51 | 0.45 |

Differences in the primary statistic (coder pair minus coder-vs-expert), paired bootstrap over benchmarks:

| Difference | Point | 95% CI | Share of resamples > 0 |
|---|---|---|---|
| pair - codex/expert | +0.31 | [0.24, 0.38] | 1.000 |
| pair - sonnet/expert | +0.24 | [0.13, 0.34] | 1.000 |
| pair - mean(coder/expert) | +0.28 | [0.19, 0.36] | 1.000 |
| sonnet/expert - codex/expert | +0.08 | [0.01, 0.14] | 0.990 |

agreement.json values reproduced on the original cell sets (assertion passed): codex n=423, primary 0.4499, CI [0.38, 0.52]; sonnet n=425, primary 0.5297, CI [0.45, 0.60]; resolved n=425, primary 0.4722, CI [0.41, 0.54].

### 5.3 Human-human ceiling in the literature

`research/instruments/crosswalk.md` section 1 records no human-human agreement figure for ABC and none for BetterBench. The only published human ceiling on a comparable instrument is MedCheck's Fleiss kappa of 0.78 on 5 benchmarks, on MedCheck's own instrument; it does not transfer to ABC or BetterBench items. This script did not re-verify those papers; the statement rests on the crosswalk (its Reliability-statistic row: MedCheck Fleiss 0.78, ABC none reported, BetterBench none reported).

## 6. Revision analyses (reviews round 1)

Added 2026-10-06 for the simulated reviews (R1 M1c, M2, M3, M3b, M5; R2; R3). Nothing was rescored: every value comes from `audit/resolved/*.json` (both coders' raw and effective scores per cell), `audit/coding`, `audit/gold_abc/gold-abc` and `audit/gold_bb/gold-betterbench`. Reuses `analysis/common.py`, `analysis/rq1_rq2.py` (prevalence, module summary, alpha table) and the scorer (`agentaudit.gold`, `agentaudit.resolve`, `agentaudit.stats`). Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, percentile 95% CI. Values in percent unless stated. Like-for-like coder-pair kappa on gold cells is in section 5 (`analysis/gold_coder_pair.py`) and is not repeated.

Command (project root):

```
python analysis/revision_rq12.py --write-summary
```

Outputs: `analysis/out/revision_rq12.json` (all values), `analysis/out/rev_*.csv`, `paper/tables/rev_ablation.tex`, `rev_bounds.tex`, `rev_pabak.tex`. Validation inside the script (assertions): the single-coder and current-rule gold statistics equal `agreement.json` (n, primary statistic, raw agreement, bootstrap CI); the current rule re-derived from the stored votes equals the stored `final` in all 1,100 audit cells; the raw-score rule equals the stored `majority_final` in all 1,100 cells.

### 6.1 Ablation of the resolution rule (R1 M3)

Rules, per cell, from the two coders' scores (codex = OpenAI gpt-5.5; sonnet = Claude Sonnet). Effective score = raw score with a 1+ set to 0 when no quote verifies (and NA set to 0 where NA is not allowed). Claude only / OpenAI only: that coder's effective score (NA leaves the denominator). Union: higher of the two effective scores (NA only if both NA; one NA takes the other coder's score). Current: highest level at least two coders support at that level or above, supporters spanning two families, else 0 (a level beats NA; NA accepted only from both coders). Intersection without family requirement: the same with the family test off. Raw: the current rule applied to raw scores (no quote verification). Union raw: extra row.

**Is the intersection without the family requirement identical to the current rule?** Yes, by construction and empirically. Exactly two coders exist (one per family), so any set of at least two supporters is one coder of each family and the family test is always met. Cells changed by the family requirement: 0 of 1100 audit cells; ABC gold: 0; BetterBench gold: 0. With these two coders the current rule is the lower of the two effective scores, except that one NA with one numeric score gives 0.

Agreement with gold (same cells as `agreement.json`; ABC: Cohen kappa, binary; BetterBench: quadratic weighted kappa, 0-3). CI: bootstrap over benchmarks.

| Rule | ABC n | ABC raw agr. | ABC Cohen kappa [95% CI] | BB n | BB raw agr. | BB weighted kappa (quad.) [95% CI] | BB unweighted kappa |
|---|---|---|---|---|---|---|---|
| Claude only (Sonnet), verified | 198 | 0.66 | 0.29 [0.11, 0.44] | 425 | 0.53 | 0.53 [0.45, 0.60] | 0.33 |
| OpenAI only (gpt-5.5), verified | 198 | 0.65 | 0.25 [0.12, 0.38] | 423 | 0.51 | 0.45 [0.38, 0.52] | 0.30 |
| Union: max of the two verified scores | 198 | 0.66 | 0.25 [0.08, 0.41] | 425 | 0.53 | 0.51 [0.44, 0.58] | 0.32 |
| Intersection, no family requirement | 198 | 0.65 | 0.29 [0.15, 0.40] | 425 | 0.51 | 0.47 [0.41, 0.54] | 0.31 |
| Current resolved rule (verified, cross-family) | 198 | 0.65 | 0.29 [0.15, 0.40] | 425 | 0.51 | 0.47 [0.41, 0.54] | 0.31 |
| Current rule on raw scores (no quote verification) | 198 | 0.68 | 0.34 [0.19, 0.48] | 425 | 0.54 | 0.56 [0.50, 0.62] | 0.36 |
| Union on raw scores (extra) | 198 | 0.65 | 0.24 [0.07, 0.40] | 425 | 0.53 | 0.53 [0.45, 0.59] | 0.32 |

Does any rule beat the best single coder? Best single coder against gold: ABC claude (0.29); BetterBench claude (0.53). Paired difference in the primary statistic (rule minus best single coder, on the cells both scored, same bootstrap resamples):

| Rule | ABC difference [95% CI] | ABC n | BetterBench difference [95% CI] | BetterBench n |
|---|---|---|---|---|
| Union: max of the two verified scores | -0.03 [-0.08, 0.02] | 198 | -0.02 [-0.05, 0.02] | 425 |
| Intersection, no family requirement | -0.00 [-0.06, 0.07] | 198 | -0.06 [-0.11, -0.01] | 425 |
| Current resolved rule (verified, cross-family) | -0.00 [-0.06, 0.07] | 198 | -0.06 [-0.11, -0.01] | 425 |
| Current rule on raw scores (no quote verification) | +0.05 [-0.01, 0.12] | 198 | +0.03 [0.00, 0.07] | 425 |
| Union on raw scores (extra) | -0.05 [-0.10, 0.01] | 198 | -0.00 [-0.03, 0.03] | 425 |

RQ1 module shares on the 44 audit benchmarks under each rule (REPORTED = level 1 or 2; FULL = level 2; bootstrap 95% CI over benchmarks).

| Rule | Core cells | Core REPORTED | Core FULL | Agent cells | Agent REPORTED | Agent FULL |
|---|---|---|---|---|---|---|
| Claude only (Sonnet), verified | 590 | 64.2 [59.3, 69.6] | 11.7 [8.8, 15.0] | 469 | 72.1 [67.0, 76.8] | 10.7 [7.6, 13.9] |
| OpenAI only (gpt-5.5), verified | 596 | 60.9 [56.7, 65.0] | 11.9 [8.5, 15.6] | 468 | 67.1 [62.6, 71.7] | 11.5 [8.6, 14.5] |
| Union: max of the two verified scores | 596 | 70.8 [66.6, 75.0] | 14.8 [11.4, 18.6] | 469 | 76.5 [71.9, 81.0] | 14.7 [11.5, 18.1] |
| Intersection, no family requirement | 596 | 53.7 [49.0, 58.6] | 8.7 [5.9, 11.9] | 469 | 62.5 [57.8, 67.1] | 7.5 [5.1, 10.1] |
| Current resolved rule (verified, cross-family) | 596 | 53.7 [49.0, 58.6] | 8.7 [5.9, 11.9] | 469 | 62.5 [57.8, 67.1] | 7.5 [5.1, 10.1] |
| Current rule on raw scores (no quote verification) | 596 | 58.6 [53.7, 64.0] | 9.7 [6.7, 13.1] | 469 | 69.3 [64.3, 73.9] | 8.1 [5.5, 10.8] |
| Union on raw scores (extra) | 596 | 72.1 [67.9, 76.2] | 14.9 [11.5, 18.9] | 469 | 78.5 [73.7, 82.8] | 15.1 [11.8, 18.7] |

Quote verification (audit, 1,100 cells per coder): raw 1+ scores whose effective score became 0 because no quote verified.

| Coder | Cells | Raw 1+ (not NA) | Removed by verification | Share of raw 1+ (%) | of which raw 1 | of which raw 2 | Raw NA |
|---|---|---|---|---|---|---|---|
| codex | 1100 | 741 | 64 | 8.6 | 52 | 12 | 36 |
| sonnet | 1100 | 731 | 14 | 1.9 | 14 | 0 | 41 |

Gold cells (same item sets): ABC codex removed 6 of 127 raw positives, sonnet 1 of 114; BetterBench codex 26 of 335, sonnet 5 of 339. Audit cells where the current rule differs from the raw-score rule: 61 of 1100; where it differs from the union: 228.

### 6.2 Bounds on RQ1 prevalence: [current rule, union rule] (R1 M3b)

The interval is between the current (conservative: lower of the two verified scores) and the union rule (higher of the two). Denominators are identical under both rules (a cell is NA under either rule only when both coders gave NA), so the intervals differ only in the numerators. These are rule bounds, not bounds on the truth: errors shared by both coders (and the 0.29 and 0.47 gold agreement in 5.1 and 5.2) are not covered. The last column pairs the lower Wilson (item) or bootstrap (module) limit of the current rule with the upper limit of the union rule.

| Unit | n appl. | REPORTED: current to union | CI envelope | FULL: current to union | CI envelope | REPORTED union on raw | FULL union on raw |
|---|---|---|---|---|---|---|---|
| core (module) | 596 | 53.7 to 70.8 | [49.0, 75.0] | 8.7 to 14.8 | [5.9, 18.6] | 72.1 | 14.9 |
| agent (module) | 469 | 62.5 to 76.5 | [57.8, 81.0] | 7.5 to 14.7 | [5.1, 18.1] | 78.5 | 15.1 |
| C1 Traceability | 44 | 88.6 to 97.7 | [76.0, 99.6] | 11.4 to 27.3 | [5.0, 41.8] | 97.7 | 27.3 |
| C2 Provenance and licence | 44 | 90.9 to 100.0 | [78.8, 100.0] | 15.9 to 29.5 | [7.9, 44.2] | 100.0 | 29.5 |
| C3 Representativeness | 44 | 79.5 to 93.2 | [65.5, 97.7] | 0.0 to 2.3 | [0.0, 11.8] | 93.2 | 2.3 |
| C4 Safety and bias tests | 44 | 31.8 to 40.9 | [20.0, 55.6] | 4.5 to 6.8 | [1.3, 18.2] | 40.9 | 6.8 |
| C5 Contamination controls | 44 | 54.5 to 65.9 | [40.1, 78.1] | 6.8 to 6.8 | [2.3, 18.2] | 65.9 | 6.8 |
| C6 Agent isolated from gold | 44 | 50.0 to 63.6 | [35.8, 76.2] | 11.4 to 31.8 | [5.0, 46.6] | 63.6 | 34.1 |
| C7 Frozen environment | 44 | 52.3 to 81.8 | [37.9, 90.5] | 2.3 to 4.5 | [0.4, 15.1] | 84.1 | 4.5 |
| C8 Oracle solver | 44 | 56.8 to 84.1 | [42.2, 92.1] | 0.0 to 2.3 | [0.0, 11.8] | 84.1 | 2.3 |
| C9 Out-of-scope side effects detectable | 24 | 12.5 to 37.5 | [4.3, 57.3] | 0.0 to 0.0 | [0.0, 13.8] | 37.5 | 0.0 |
| C10 Trivial success unlikely | 44 | 50.0 to 84.1 | [35.8, 92.1] | 2.3 to 4.5 | [0.4, 15.1] | 88.6 | 4.5 |
| C11 Trivial-agent result | 44 | 0.0 to 2.3 | [0.0, 11.8] | 0.0 to 0.0 | [0.0, 8.0] | 2.3 | 0.0 |
| C12 Evaluator validated | 44 | 56.8 to 70.5 | [42.2, 81.8] | 36.4 to 43.2 | [23.8, 57.8] | 70.5 | 43.2 |
| C13 Non-determinism safeguards | 44 | 52.3 to 77.3 | [37.9, 87.2] | 4.5 to 13.6 | [1.3, 26.7] | 88.6 | 13.6 |
| C14 Statistical comparison | 44 | 56.8 to 77.3 | [42.2, 87.2] | 22.7 to 27.3 | [12.8, 41.8] | 77.3 | 27.3 |
| A1 Run count per reported number (e). | 44 | 47.7 to 70.5 | [33.8, 81.8] | 6.8 to 13.6 | [2.3, 26.7] | 72.7 | 13.6 |
| A2 Uncertainty with stated resampling unit (e). | 44 | 40.9 to 54.5 | [27.7, 68.3] | 2.3 to 2.3 | [0.4, 11.8] | 56.8 | 2.3 |
| A3 Action-level repeat-run reliability (a). | 44 | 22.7 to 29.5 | [12.8, 44.2] | 11.4 to 18.2 | [5.0, 32.0] | 29.5 | 18.2 |
| A4 Model and harness pinning (a/e). | 44 | 43.2 to 56.8 | [29.7, 70.3] | 0.0 to 0.0 | [0.0, 8.0] | 63.6 | 0.0 |
| A5 Tool contract specified (b). | 43 | 76.7 to 95.3 | [62.3, 98.7] | 9.3 to 14.0 | [3.7, 27.3] | 100.0 | 16.3 |
| A6 Tool contract verified (b). | 43 | 48.8 to 76.7 | [34.6, 86.8] | 0.0 to 2.3 | [0.0, 12.1] | 79.1 | 2.3 |
| A7 Write-action disclosure (d). | 31 | 96.8 to 100.0 | [83.8, 100.0] | 22.6 to 71.0 | [11.4, 83.9] | 100.0 | 71.0 |
| A8 Grader reads state, or justifies transcript grading (c). | 44 | 93.2 to 97.7 | [81.8, 99.6] | 2.3 to 9.1 | [0.4, 21.2] | 97.7 | 9.1 |
| A9 Agent-channel contamination (f). | 44 | 59.1 to 79.5 | [44.4, 88.8] | 0.0 to 0.0 | [0.0, 8.0] | 79.5 | 0.0 |
| A10 Slice reporting (g). | 44 | 84.1 to 95.5 | [70.6, 98.7] | 2.3 to 9.1 | [0.4, 21.2] | 97.7 | 9.1 |
| A11 Environment-state provenance (h). | 44 | 84.1 to 93.2 | [70.6, 97.7] | 29.5 to 38.6 | [18.2, 53.4] | 93.2 | 40.9 |

### 6.3 Prevalence-adjusted agreement with gold (R1 M1c)

PABAK = (p_o - 1/q)/(1 - 1/q), equal to 2 p_o - 1 for binary ABC. Gwet AC1: p_e = sum_k pi_k (1 - pi_k)/(q - 1), pi_k the mean of the two raters' proportions in category k. BetterBench (q = 4): quadratic agreement weights w = 1 - ((k - l)/3)^2; weighted PABAK = (p_a - mean w)/(1 - mean w) with uniform marginals; Gwet AC2: p_e = T_w/(q(q - 1)) sum_k pi_k (1 - pi_k), T_w = sum of all weights. CI: bootstrap over benchmarks (same resamples for all statistics of a row).

**ABC (binary)**

| Rule | n | Raw agr. | Majority-class baseline | Cohen kappa | PABAK [95% CI] | Gwet AC1 [95% CI] |
|---|---|---|---|---|---|---|
| Claude only (Sonnet), verified | 198 | 0.66 | 0.62 | 0.29 | 0.31 [0.14, 0.47] | 0.34 [0.17, 0.52] |
| OpenAI only (gpt-5.5), verified | 198 | 0.65 | 0.62 | 0.25 | 0.29 [0.19, 0.41] | 0.33 [0.23, 0.45] |
| Union: max of the two verified scores | 198 | 0.66 | 0.62 | 0.25 | 0.31 [0.16, 0.47] | 0.36 [0.22, 0.53] |
| Intersection, no family requirement | 198 | 0.65 | 0.62 | 0.29 | 0.29 [0.17, 0.40] | 0.31 [0.19, 0.43] |
| Current resolved rule (verified, cross-family) | 198 | 0.65 | 0.62 | 0.29 | 0.29 [0.17, 0.40] | 0.31 [0.19, 0.43] |
| Current rule on raw scores (no quote verification) | 198 | 0.68 | 0.62 | 0.34 | 0.35 [0.21, 0.52] | 0.37 [0.23, 0.55] |
| Union on raw scores (extra) | 198 | 0.65 | 0.62 | 0.24 | 0.30 [0.15, 0.46] | 0.36 [0.21, 0.52] |

**BetterBench (0-3)**

| Rule | n | Raw agr. | Majority-class baseline | Weighted kappa (quad.) | Weighted PABAK [95% CI] | Gwet AC2 [95% CI] | Unweighted PABAK | Unweighted AC1 |
|---|---|---|---|---|---|---|---|---|
| Claude only (Sonnet), verified | 425 | 0.53 | 0.48 | 0.53 | 0.42 [0.33, 0.51] | 0.52 [0.43, 0.60] | 0.37 | 0.39 |
| OpenAI only (gpt-5.5), verified | 423 | 0.51 | 0.48 | 0.45 | 0.30 [0.22, 0.39] | 0.42 [0.36, 0.50] | 0.35 | 0.36 |
| Union: max of the two verified scores | 425 | 0.53 | 0.48 | 0.51 | 0.42 [0.33, 0.50] | 0.53 [0.45, 0.62] | 0.37 | 0.39 |
| Intersection, no family requirement | 425 | 0.51 | 0.48 | 0.47 | 0.31 [0.22, 0.40] | 0.42 [0.35, 0.49] | 0.35 | 0.37 |
| Current resolved rule (verified, cross-family) | 425 | 0.51 | 0.48 | 0.47 | 0.31 [0.22, 0.40] | 0.42 [0.35, 0.49] | 0.35 | 0.37 |
| Current rule on raw scores (no quote verification) | 425 | 0.54 | 0.48 | 0.56 | 0.46 [0.38, 0.53] | 0.54 [0.47, 0.61] | 0.39 | 0.41 |
| Union on raw scores (extra) | 425 | 0.53 | 0.48 | 0.53 | 0.44 [0.36, 0.52] | 0.55 [0.47, 0.63] | 0.37 | 0.39 |

Confusion matrices (rows expert, columns scorer; counts of cells; aggregate counts only, no per-cell ABC gold values). ABC, 0 = not satisfied, 1 = satisfied:

| Rule | gold 0 / scorer 0 | gold 0 / scorer 1 | gold 1 / scorer 0 | gold 1 / scorer 1 |
|---|---|---|---|---|
| Claude only (Sonnet), verified | 46 | 29 | 39 | 84 |
| OpenAI only (gpt-5.5), verified | 41 | 34 | 36 | 87 |
| Union: max of the two verified scores | 37 | 38 | 30 | 93 |
| Intersection, no family requirement | 50 | 25 | 45 | 78 |
| Current resolved rule (verified, cross-family) | 50 | 25 | 45 | 78 |
| Current rule on raw scores (no quote verification) | 50 | 25 | 39 | 84 |
| Union on raw scores (extra) | 36 | 39 | 30 | 93 |

BetterBench, Current resolved rule (verified, cross-family) (rows expert 0-3, columns scorer 0-3):

| gold \ scorer | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | 76 | 24 | 28 | 3 |
| 1 | 5 | 5 | 3 | 1 |
| 2 | 11 | 8 | 38 | 18 |
| 3 | 44 | 10 | 52 | 99 |

BetterBench, Union: max of the two verified scores (rows expert 0-3, columns scorer 0-3):

| gold \ scorer | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | 49 | 33 | 37 | 12 |
| 1 | 3 | 5 | 5 | 1 |
| 2 | 1 | 9 | 34 | 31 |
| 3 | 21 | 12 | 36 | 136 |

Confusion matrices for every rule are in `analysis/out/rev_confusion.csv`.

### 6.4 Thresholds: per-item prevalence next to cross-family alpha (R1 M5)

Prevalence: resolved rule, share of applicable cells at level 1 or 2 (REPORTED) and at level 2 (FULL), Wilson 95% CI. Alpha: ordinal Krippendorff alpha on raw scores, NA missing, codex vs sonnet, bootstrap CI over benchmarks (equals `rq2_alpha.csv`). Agreement columns: share of cells where both coders scored (neither NA) with the same score (exact), the same side of the REPORTED threshold (>=1), and the same side of the FULL threshold (=2).

| Item | Module | n appl. | REPORTED | FULL | Alpha [95% CI] | Pairs | Exact agr. (%) | Agr. at >=1 (%) | Agr. at =2 (%) |
|---|---|---|---|---|---|---|---|---|---|
| C1 | core | 44 | 88.6 [76.0, 95.0] | 11.4 [5.0, 24.0] | 0.60 [0.28, 0.83] | 44 | 82 | 95 | 86 |
| C2 | core | 44 | 90.9 [78.8, 96.4] | 15.9 [7.9, 29.4] | 0.59 [0.28, 0.82] | 44 | 82 | 95 | 86 |
| C3 | core | 44 | 79.5 [65.5, 88.8] | 0.0 [0.0, 8.0] | 0.46 [-0.02, 0.80] | 44 | 86 | 89 | 98 |
| C4 | core | 44 | 31.8 [20.0, 46.6] | 4.5 [1.3, 15.1] | 0.83 [0.62, 0.96] | 44 | 89 | 91 | 98 |
| C5 | core | 44 | 54.5 [40.1, 68.3] | 6.8 [2.3, 18.2] | 0.81 [0.62, 0.96] | 44 | 89 | 89 | 100 |
| C6 | core | 44 | 50.0 [35.8, 64.2] | 11.4 [5.0, 24.0] | 0.77 [0.61, 0.88] | 44 | 68 | 91 | 77 |
| C7 | core | 44 | 52.3 [37.9, 66.2] | 2.3 [0.4, 11.8] | 0.38 [0.05, 0.63] | 44 | 68 | 70 | 98 |
| C8 | core | 44 | 56.8 [42.2, 70.3] | 0.0 [0.0, 8.0] | 0.49 [0.16, 0.75] | 44 | 77 | 77 | 100 |
| C9 | core | 24 | 12.5 [4.3, 31.0] | 0.0 [0.0, 13.8] | 0.51 [0.00, 0.88] | 18 | 78 | 78 | 100 |
| C10 | core | 44 | 50.0 [35.8, 64.2] | 2.3 [0.4, 11.8] | 0.20 [-0.13, 0.49] | 44 | 59 | 61 | 98 |
| C11 | core | 44 | 0.0 [0.0, 8.0] | 0.0 [0.0, 8.0] | 0.00 [-0.04, 0.00] | 44 | 98 | 98 | 100 |
| C12 | core | 44 | 56.8 [42.2, 70.3] | 36.4 [23.8, 51.1] | 0.91 [0.76, 1.00] | 44 | 93 | 93 | 98 |
| C13 | core | 44 | 52.3 [37.9, 66.2] | 4.5 [1.3, 15.1] | 0.60 [0.31, 0.81] | 44 | 77 | 84 | 93 |
| C14 | core | 44 | 56.8 [42.2, 70.3] | 22.7 [12.8, 37.0] | 0.91 [0.80, 0.98] | 44 | 91 | 93 | 98 |
| A1 | agent | 44 | 47.7 [33.8, 62.1] | 6.8 [2.3, 18.2] | 0.73 [0.52, 0.88] | 44 | 80 | 84 | 95 |
| A2 | agent | 44 | 40.9 [27.7, 55.6] | 2.3 [0.4, 11.8] | 0.75 [0.51, 0.92] | 44 | 86 | 86 | 100 |
| A3 | agent | 44 | 22.7 [12.8, 37.0] | 11.4 [5.0, 24.0] | 0.95 [0.85, 1.00] | 44 | 93 | 98 | 95 |
| A4 | agent | 44 | 43.2 [29.7, 57.8] | 0.0 [0.0, 8.0] | 0.81 [0.59, 0.95] | 44 | 91 | 91 | 100 |
| A5 | agent | 43 | 76.7 [62.3, 86.8] | 9.3 [3.7, 21.6] | 0.54 [0.17, 0.81] | 43 | 84 | 91 | 93 |
| A6 | agent | 43 | 48.8 [34.6, 63.2] | 0.0 [0.0, 8.2] | 0.56 [0.27, 0.80] | 43 | 79 | 81 | 98 |
| A7 | agent | 31 | 96.8 [83.8, 99.4] | 22.6 [11.4, 39.8] | 0.02 [-0.36, 0.35] | 30 | 50 | 100 | 50 |
| A8 | agent | 44 | 93.2 [81.8, 97.7] | 2.3 [0.4, 11.8] | 0.56 [-0.04, 1.00] | 44 | 93 | 100 | 93 |
| A9 | agent | 44 | 59.1 [44.4, 72.3] | 0.0 [0.0, 8.0] | 0.52 [0.21, 0.78] | 44 | 80 | 80 | 100 |
| A10 | agent | 44 | 84.1 [70.6, 92.1] | 2.3 [0.4, 11.8] | 0.41 [-0.01, 0.75] | 44 | 86 | 93 | 93 |
| A11 | agent | 44 | 84.1 [70.6, 92.1] | 29.5 [18.2, 44.2] | 0.85 [0.66, 0.97] | 44 | 91 | 100 | 91 |

**A7 verification.** Alpha = 0.016 [-0.36, 0.35] on 44 units (30 pairable) from 44 benchmarks: confirmed (the flagged 0.02). Codex x sonnet raw scores (codex|sonnet: count): NA|NA: 13, NA|1: 1, 1|1: 8, 1|2: 5, 2|1: 10, 2|2: 7. Among the 30 cells scored by both, no cell has a 0 from either coder: the coders agree on whether write-actions are disclosed (100% at >=1) but split on 1 versus 2 (50% at =2; exact 50%). The low alpha is a threshold (level 1 versus 2) disagreement in a range-restricted item, not disagreement on presence. Expected exact agreement by chance from the two coders' marginals is 0.49, against 0.50 observed. The item is NA (both coders) in 13 of 44 cells.

### 6.5 Misclassification sensitivity: Rogan-Gladen correction (R1 M5)

Correction: p_true = (p_apparent + Sp - 1)/(Se + Sp - 1), p_apparent the resolved-rule share on the audit cells, Se and Sp the sensitivity and specificity of the resolved score against the experts. **Assumption (not tested):** these rates are measured on 9 ABC benchmarks (22 task-validity and outcome-validity items) and 22 BetterBench benchmarks (20 criteria) and are transferred unchanged to our 25 reporting items on 44 medical-agent benchmarks; the experts are a reference, not truth (ABC and BetterBench have no published human-human agreement, section 5.3), and error rates need not be the same across items, instrument or domain. Binarisations: ABC is binary, resolved level 1 = satisfied (used for both the REPORTED and the FULL share; ABC has no partial level). BetterBench: resolved >= t versus expert >= t with t = 2 (partially met or better) for REPORTED and t = 3 (fully met) for FULL. Bootstrap: audit benchmarks and gold benchmarks resampled independently in the same replicate (2,000, seed 20261004); replicates with Se + Sp - 1 <= 0.05 are dropped (counts below); CI is the percentile interval of the unclipped corrected value, clipped CI in the last column.

| Gold set | Share | Module | Sensitivity (Wilson) | Specificity (Wilson) | Youden J | Apparent (%) | Corrected (%) | Bootstrap 95% CI | CI clipped to 0-100 | Replicates used / dropped |
|---|---|---|---|---|---|---|---|---|---|---|
| ABC | reported | core | 78/123 = 0.63 [0.55, 0.71] | 50/75 = 0.67 [0.55, 0.76] | 0.30 | 53.7 | 67.7 | [41.2, 88.3] | [41.2, 88.3] | 1999 / 1 |
| ABC | reported | agent | 78/123 = 0.63 [0.55, 0.71] | 50/75 = 0.67 [0.55, 0.76] | 0.30 | 62.5 | 96.9 | [79.0, 125.2] | [79.0, 100.0] | 1999 / 1 |
| ABC | full | core | 78/123 = 0.63 [0.55, 0.71] | 50/75 = 0.67 [0.55, 0.76] | 0.30 | 8.7 | -81.8 | [-216.3, -29.1] | [0.0, 0.0] | 1999 / 1 |
| ABC | full | agent | 78/123 = 0.63 [0.55, 0.71] | 50/75 = 0.67 [0.55, 0.76] | 0.30 | 7.5 | -86.0 | [-220.5, -32.6] | [0.0, 0.0] | 1999 / 1 |
| BetterBench | reported | core | 207/280 = 0.74 [0.68, 0.79] | 110/145 = 0.76 [0.68, 0.82] | 0.50 | 53.7 | 59.4 | [47.9, 72.1] | [47.9, 72.1] | 2000 / 0 |
| BetterBench | reported | agent | 207/280 = 0.74 [0.68, 0.79] | 110/145 = 0.76 [0.68, 0.82] | 0.50 | 62.5 | 77.0 | [65.7, 89.8] | [65.7, 89.8] | 2000 / 0 |
| BetterBench | full | core | 99/205 = 0.48 [0.42, 0.55] | 198/220 = 0.90 [0.85, 0.93] | 0.38 | 8.7 | -3.3 | [-18.4, 9.4] | [0.0, 9.4] | 2000 / 0 |
| BetterBench | full | agent | 99/205 = 0.48 [0.42, 0.55] | 198/220 = 0.90 [0.85, 0.93] | 0.38 | 7.5 | -6.6 | [-21.1, 6.1] | [0.0, 6.1] | 2000 / 0 |

Reading: the correction is only informative where the apparent share exceeds the false-positive rate (1 - Sp) and Youden's J is not small. Outside [0, 100] (apparent share below 1 - Sp, or an overshoot): ABC full core (-81.8); ABC full agent (-86.0); BetterBench full core (-3.3); BetterBench full agent (-6.6). These are not prevalence estimates; they show the expert-derived rates cannot be applied there. Within range (the ABC agent upper limit still exceeds 100): ABC reported core: 53.7 to 67.7 (CI [41.2, 88.3]); ABC reported agent: 62.5 to 96.9 (CI [79.0, 125.2]); BetterBench reported core: 53.7 to 59.4 (CI [47.9, 72.1]); BetterBench reported agent: 62.5 to 77.0 (CI [65.7, 89.8]).

### 6.6 Excluding the five pilot benchmarks (R1 M2)

Pilot benchmarks (rubric/pilot: round 1 `coderA/B_scores.csv` = AgentClinic, FHIR-AgentBench, HealthAgentBench; round 2 `r2_coder*_scores.csv` = EHR-ChatQA, MedAgentSim; decision log 2026-10-04; protocol-v1 "five pilot benchmarks"): `agentclinic`, `ehr-chatqa`, `fhir-agentbench`, `healthagentbench`, `medagentsim`. Remaining: 39 of 44 benchmarks. Resolved rule; CI: bootstrap over benchmarks.

| Module | Cells (all 44) | REPORTED (all 44) | FULL (all 44) | Cells (39) | REPORTED (39) | FULL (39) |
|---|---|---|---|---|---|---|
| core | 596 | 53.7 [49.0, 58.6] | 8.7 [5.9, 11.9] | 528 | 53.2 [48.0, 58.5] | 8.5 [5.3, 12.0] |
| agent | 469 | 62.5 [57.8, 67.1] | 7.5 [5.1, 10.1] | 418 | 62.9 [58.0, 67.4] | 7.2 [4.8, 9.8] |

Cross-family alpha (overall): all 44 benchmarks 0.771 [0.733, 0.806] on 1100 units; excluding the pilot 0.761 [0.725, 0.797] on 975 units from 39 benchmarks.

| Item | REPORTED, 44 (n) | REPORTED, 39 (n) | FULL, 44 | FULL, 39 | Alpha, 44 | Alpha, 39 [95% CI] |
|---|---|---|---|---|---|---|
| C1 | 88.6 (44) | 87.2 (39) | 11.4 | 10.3 | 0.60 | 0.61 [0.28, 0.84] |
| C2 | 90.9 (44) | 89.7 (39) | 15.9 | 15.4 | 0.59 | 0.55 [0.23, 0.80] |
| C3 | 79.5 (44) | 82.1 (39) | 0.0 | 0.0 | 0.46 | 0.58 [0.01, 0.90] |
| C4 | 31.8 (44) | 30.8 (39) | 4.5 | 5.1 | 0.83 | 0.81 [0.60, 0.95] |
| C5 | 54.5 (44) | 53.8 (39) | 6.8 | 7.7 | 0.81 | 0.80 [0.57, 0.96] |
| C6 | 50.0 (44) | 48.7 (39) | 11.4 | 10.3 | 0.77 | 0.78 [0.60, 0.89] |
| C7 | 52.3 (44) | 51.3 (39) | 2.3 | 2.6 | 0.38 | 0.36 [0.01, 0.63] |
| C8 | 56.8 (44) | 56.4 (39) | 0.0 | 0.0 | 0.49 | 0.51 [0.18, 0.78] |
| C9 | 12.5 (24) | 9.5 (21) | 0.0 | 0.0 | 0.51 | 0.45 [-0.12, 0.87] |
| C10 | 50.0 (44) | 48.7 (39) | 2.3 | 2.6 | 0.20 | 0.15 [-0.22, 0.46] |
| C11 | 0.0 (44) | 0.0 (39) | 0.0 | 0.0 | 0.00 | 0.00 [-0.03, 0.00] |
| C12 | 56.8 (44) | 53.8 (39) | 36.4 | 38.5 | 0.91 | 0.91 [0.74, 1.00] |
| C13 | 52.3 (44) | 53.8 (39) | 4.5 | 2.6 | 0.60 | 0.63 [0.32, 0.83] |
| C14 | 56.8 (44) | 59.0 (39) | 22.7 | 20.5 | 0.91 | 0.89 [0.76, 0.98] |
| A1 | 47.7 (44) | 48.7 (39) | 6.8 | 2.6 | 0.73 | 0.65 [0.40, 0.84] |
| A2 | 40.9 (44) | 41.0 (39) | 2.3 | 2.6 | 0.75 | 0.72 [0.48, 0.91] |
| A3 | 22.7 (44) | 23.1 (39) | 11.4 | 12.8 | 0.95 | 0.99 [0.97, 1.00] |
| A4 | 43.2 (44) | 43.6 (39) | 0.0 | 0.0 | 0.81 | 0.79 [0.56, 0.95] |
| A5 | 76.7 (43) | 76.9 (39) | 9.3 | 10.3 | 0.54 | 0.54 [0.17, 0.80] |
| A6 | 48.8 (43) | 51.3 (39) | 0.0 | 0.0 | 0.56 | 0.54 [0.23, 0.78] |
| A7 | 96.8 (31) | 96.4 (28) | 22.6 | 25.0 | 0.02 | -0.02 [-0.40, 0.34] |
| A8 | 93.2 (44) | 92.3 (39) | 2.3 | 0.0 | 0.56 | 0.40 [-0.07, 1.00] |
| A9 | 59.1 (44) | 64.1 (39) | 0.0 | 0.0 | 0.52 | 0.47 [0.10, 0.76] |
| A10 | 84.1 (44) | 82.1 (39) | 2.3 | 2.6 | 0.41 | 0.45 [-0.01, 0.80] |
| A11 | 84.1 (44) | 82.1 (39) | 29.5 | 28.2 | 0.85 | 0.83 [0.63, 0.96] |


## 7. RQ3 revision analyses (reviewer 1, M6; added 2026-10-06)

Command (project root): `python analysis/revision_rq3.py`. Seed 20261004 (percentile bootstrap 2,000 resamples, Bayesian bootstrap 20,000 draws). Reads `research/executed/runs/v3/*/episodes.jsonl` only; no new runs; the frozen RQ3 outputs (`rq3_*.csv`, `paper/tables/rq3_*.tex`) are not touched. The percentile bootstrap in `rq3_passk.csv` and the 0.5 cut-off are reproduced exactly inside the script (assertions passed). Sources: `rev_rq3_design.csv`, `rev_rq3_validity.csv`, `rev_rq3_passk_bayes.csv`, `rev_rq3_deff.csv`, `rev_rq3_cutoff.csv`, `rev_rq3_decomp.csv`, `rev_rq3_seed_facts.json` in `analysis/out/`; tables `paper/tables/rev_rq3_validity.tex`, `paper/tables/rev_passk_bayes.tex`.

### 7.1 Task design

| Benchmark | Tasks in A | Tasks in B | Identical sets | Groups | Episodes | Episodes per group | Repeats 0-4 in every group | Note |
|---|---|---|---|---|---|---|---|---|
| AgentClinic | 10 | 10 | True | 20 | 100 | 5x20 | True |  |
| RadA-BenchPlat | 10 | 10 | True | 20 | 100 | 5x20 | True | 10 distinct cases, 10 (case, QA chain) tasks |
| Synthetic Hospital | 10 | 10 | True | 20 | 100 | 5x20 | True | 10 distinct patients |

Confirmed: within each benchmark conditions A and B use the same 10 tasks, giving 30 distinct (benchmark, task) pairs and 60 task groups (3 benchmarks x 2 conditions x 10 tasks), each with 5 reruns. The driver builds the task list once per benchmark (`tasks(bench)` in `driver_v3.py`) and loops over conditions inside it. The 10 tasks are the first 10 of a seeded sample of 15 (`random.Random(20261004).sample(pool, 15)[:10]`). Consequence: the 20 groups of a benchmark are 10 tasks observed twice, so conditions A and B are paired and not independent samples; tests or intervals that treat 20 groups as exchangeable are wrong.

### 7.2 Episode validity and divergence/instability on clean groups

Definitions (from the runner and episode fields; an episode can fall in more than one category): invalid or missing tool inputs = RadABench `error` matching `benchmark-logged: ... (Missing|Invalid) ... input` (the benchmark's own validation rejected a call; `verdict.has_error` True, `verdict.pass` False by the runner rule); Synthetic Hospital trace step with `error` or `malformed`, unparsable tool arguments or a failed environment step; AgentClinic (no tool inputs) a doctor output without exactly one DIAGNOSIS action or verdict `error`/`no_diagnosis`. No tool call = no executed action, or the Synthetic Hospital runner stop `model repeatedly produced no tool call` (more than 8 user turns without a tool call). Runner error = `driver_status` not `ok`, any other non-empty `error`, or provider request errors. Clean group = none of its 5 episodes is invalid. Divergent and unstable as in section 1.2.

| Benchmark | Cond | Episodes | Invalid input | No tool call | Runner error | Other error | Any invalid | Groups with invalid | Clean groups | Divergent all | Divergent clean | Unstable all | Unstable clean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AgentClinic | A | 50 | 0 | 0 | 0 | 0 | 0 | 0/10 | 10/10 | 10/10 | 10/10 | 5/10 | 5/10 |
| AgentClinic | B | 50 | 0 | 0 | 0 | 0 | 0 | 0/10 | 10/10 | 10/10 | 10/10 | 6/10 | 6/10 |
| RadA-BenchPlat | A | 50 | 29 | 0 | 0 | 0 | 29 | 7/10 | 3/10 | 9/10 | 3/3 | 1/10 | 0/3 |
| RadA-BenchPlat | B | 50 | 33 | 0 | 0 | 0 | 33 | 8/10 | 2/10 | 10/10 | 2/2 | 2/10 | 0/2 |
| Synthetic Hospital | A | 50 | 0 | 5 | 0 | 0 | 5 | 2/10 | 8/10 | 5/10 | 3/8 | 1/10 | 0/8 |
| Synthetic Hospital | B | 50 | 0 | 7 | 0 | 0 | 7 | 6/10 | 4/10 | 10/10 | 4/4 | 4/10 | 2/4 |

RadABench `verdict.has_error` is True in 62 of 100 episodes, the same episodes as the invalid-input count. Clean-group rows with 0 or very few groups carry no information about divergence or instability; read them as 'not estimable', not as agreement.

### 7.3 pass^k intervals: percentile bootstrap, Bayesian bootstrap, exact

| Benchmark | Cond | k | pass^k | Percentile (current) | Bayesian bootstrap | Exact (k=1 pooled 50 eps; k=5 10 tasks) | Exact DEFF-adj. (k=1) | Flags |
|---|---|---|---|---|---|---|---|---|
| AgentClinic | A | 1 | 0.46 | [0.22, 0.68] | [0.24, 0.68] | [0.32, 0.61] | [0.22, 0.72] | -- |
| AgentClinic | A | 2 | 0.33 | [0.13, 0.57] | [0.14, 0.58] | -- | -- | -- |
| AgentClinic | A | 3 | 0.26 | [0.05, 0.52] | [0.08, 0.52] | -- | -- | -- |
| AgentClinic | A | 4 | 0.22 | [0.02, 0.50] | [0.05, 0.49] | -- | -- | -- |
| AgentClinic | A | 5 | 0.20 | [0.00, 0.50] | [0.03, 0.48] | [0.03, 0.56] | -- | pct lower=0 |
| AgentClinic | B | 1 | 0.30 | [0.12, 0.48] | [0.13, 0.50] | [0.18, 0.45] | [0.12, 0.54] | -- |
| AgentClinic | B | 2 | 0.16 | [0.03, 0.31] | [0.05, 0.32] | -- | -- | -- |
| AgentClinic | B | 3 | 0.09 | [0.01, 0.20] | [0.02, 0.20] | -- | -- | -- |
| AgentClinic | B | 4 | 0.04 | [0.00, 0.10] | [0.01, 0.10] | -- | -- | pct lower=0 |
| AgentClinic | B | 5 | 0.00 | [0.00, 0.00] | [0.00, 0.00] | [0.00, 0.31] | -- | pct zero-width, pct lower=0, Bayes zero-width |
| RadA-BenchPlat | A | 1 | 0.16 | [0.00, 0.40] | [0.02, 0.40] | [0.07, 0.29] | [0.02, 0.48] | pct lower=0 |
| RadA-BenchPlat | A | 2 | 0.13 | [0.00, 0.36] | [0.02, 0.36] | -- | -- | pct lower=0 |
| RadA-BenchPlat | A | 3 | 0.11 | [0.00, 0.32] | [0.01, 0.34] | -- | -- | pct lower=0 |
| RadA-BenchPlat | A | 4 | 0.10 | [0.00, 0.30] | [0.00, 0.33] | -- | -- | pct driven by 1 task, pct lower=0 |
| RadA-BenchPlat | A | 5 | 0.10 | [0.00, 0.30] | [0.00, 0.33] | [0.00, 0.45] | -- | pct driven by 1 task, pct lower=0 |
| RadA-BenchPlat | B | 1 | 0.20 | [0.00, 0.46] | [0.04, 0.45] | [0.10, 0.34] | [0.03, 0.52] | pct lower=0 |
| RadA-BenchPlat | B | 2 | 0.16 | [0.00, 0.40] | [0.02, 0.40] | -- | -- | pct lower=0 |
| RadA-BenchPlat | B | 3 | 0.14 | [0.00, 0.38] | [0.02, 0.37] | -- | -- | pct lower=0 |
| RadA-BenchPlat | B | 4 | 0.12 | [0.00, 0.34] | [0.01, 0.35] | -- | -- | pct lower=0 |
| RadA-BenchPlat | B | 5 | 0.10 | [0.00, 0.30] | [0.00, 0.33] | [0.00, 0.45] | -- | pct driven by 1 task, pct lower=0 |
| Synthetic Hospital | A | 1 | 0.38 | [0.10, 0.68] | [0.13, 0.67] | [0.25, 0.53] | [0.12, 0.71] | -- |
| Synthetic Hospital | A | 2 | 0.36 | [0.10, 0.64] | [0.12, 0.64] | -- | -- | -- |
| Synthetic Hospital | A | 3 | 0.34 | [0.10, 0.60] | [0.11, 0.63] | -- | -- | -- |
| Synthetic Hospital | A | 4 | 0.32 | [0.06, 0.60] | [0.10, 0.61] | -- | -- | -- |
| Synthetic Hospital | A | 5 | 0.30 | [0.00, 0.60] | [0.08, 0.60] | [0.07, 0.65] | -- | pct lower=0 |
| Synthetic Hospital | B | 1 | 0.22 | [0.04, 0.42] | [0.07, 0.43] | [0.12, 0.36] | [0.06, 0.49] | -- |
| Synthetic Hospital | B | 2 | 0.13 | [0.00, 0.30] | [0.03, 0.30] | -- | -- | pct lower=0 |
| Synthetic Hospital | B | 3 | 0.08 | [0.00, 0.20] | [0.01, 0.19] | -- | -- | pct lower=0 |
| Synthetic Hospital | B | 4 | 0.04 | [0.00, 0.10] | [0.01, 0.10] | -- | -- | pct lower=0 |
| Synthetic Hospital | B | 5 | 0.00 | [0.00, 0.00] | [0.00, 0.00] | [0.00, 0.31] | -- | pct zero-width, pct lower=0, Bayes zero-width |

Pooled pass^1 and design effect (m = 5 reruns per task, one-way ANOVA ICC, DEFF = 1 + 4 x ICC clipped at 1):

| Benchmark | Cond | Pass / episodes | p | ICC | DEFF | n_eff | CP pooled (naive) | CP at n_eff | Tasks with 5/5 passes | CP pass^5 (10 tasks) |
|---|---|---|---|---|---|---|---|---|---|---|
| AgentClinic | A | 23/50 | 0.46 | 0.51 | 3.03 | 16.5 | [0.32, 0.61] | [0.22, 0.72] | 2 | [0.03, 0.56] |
| AgentClinic | B | 15/50 | 0.30 | 0.37 | 2.46 | 20.3 | [0.18, 0.45] | [0.12, 0.54] | 0 | [0.00, 0.31] |
| RadA-BenchPlat | A | 8/50 | 0.16 | 0.80 | 4.18 | 12.0 | [0.07, 0.29] | [0.02, 0.48] | 1 | [0.00, 0.45] |
| RadA-BenchPlat | B | 10/50 | 0.20 | 0.77 | 4.08 | 12.2 | [0.10, 0.34] | [0.03, 0.52] | 1 | [0.00, 0.45] |
| Synthetic Hospital | A | 19/50 | 0.38 | 0.92 | 4.69 | 10.7 | [0.25, 0.53] | [0.12, 0.71] | 3 | [0.07, 0.65] |
| Synthetic Hospital | B | 11/50 | 0.22 | 0.51 | 3.03 | 16.5 | [0.12, 0.36] | [0.06, 0.49] | 0 | [0.00, 0.31] |

Degenerate percentile cells (zero width): AgentClinic B k=5, Synthetic Hospital B k=5. The Bayesian bootstrap is degenerate in exactly the same cells (it cannot leave the range of the task values), so it does not repair them; the exact 10-task interval at k=5 does (0 of 10 tasks with 5/5 passes gives an upper limit of 0.31). A pooled-episode Clopper-Pearson interval treats the 50 episodes as independent and is narrower than the task-level uncertainty supports whenever DEFF exceeds 1; the DEFF-adjusted column is an approximation (fractional counts), not an exact interval. With 10 tasks per cell every interval here is wide, and A and B share their tasks (section 7.1).

### 7.4 Synthetic Hospital pass cut-off sensitivity

Where 0.5 is set: `research/executed/runners/synthetic_hospital_runner.py` line 254, `"pass": bool(done and reward is not None and reward >= 0.5)`, documented at lines 43-44 as a derived binary used only for pass^k bookkeeping; `analysis/rq3_reruns.py` reads `verdict["pass"]` and has no threshold of its own. The benchmark itself defines no pass/fail. Here the cut-off is varied on the stored `verdict.reward` (episodes without a submission have no reward and fail at every cut-off). The 0.5 row reproduces the frozen `verdict.pass` for all 100 episodes (assertion passed).

| Cut-off | Cond | Episodes passing | pass^1 | pass^2 | pass^3 | pass^4 | pass^5 | Unstable groups | pass^1 Bayesian 95% |
|---|---|---|---|---|---|---|---|---|---|
| 0.3 | A | 19/50 | 0.38 | 0.36 | 0.34 | 0.32 | 0.30 | 1/10 | [0.13, 0.67] |
| 0.3 | B | 13/50 | 0.26 | 0.17 | 0.14 | 0.12 | 0.10 | 4/10 | [0.09, 0.49] |
| 0.4 | A | 19/50 | 0.38 | 0.36 | 0.34 | 0.32 | 0.30 | 1/10 | [0.13, 0.67] |
| 0.4 | B | 11/50 | 0.22 | 0.13 | 0.08 | 0.04 | 0.00 | 4/10 | [0.07, 0.43] |
| 0.5 (frozen) | A | 19/50 | 0.38 | 0.36 | 0.34 | 0.32 | 0.30 | 1/10 | [0.13, 0.67] |
| 0.5 (frozen) | B | 11/50 | 0.22 | 0.13 | 0.08 | 0.04 | 0.00 | 4/10 | [0.07, 0.43] |
| 0.6 | A | 4/50 | 0.08 | 0.06 | 0.04 | 0.02 | 0.00 | 1/10 | [0.00, 0.27] |
| 0.6 | B | 3/50 | 0.06 | 0.01 | 0.00 | 0.00 | 0.00 | 2/10 | [0.01, 0.15] |
| 0.7 | A | 4/50 | 0.08 | 0.06 | 0.04 | 0.02 | 0.00 | 1/10 | [0.00, 0.27] |
| 0.7 | B | 1/50 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 1/10 | [0.00, 0.07] |

Reward distribution (n = 88 episodes with a reward, 12 without): 2 in [0.3, 0.5), 8 exactly 0.5, 23 in [0.5, 0.6), 2 in [0.6, 0.7), 5 at or above 0.7; distinct values [0.0, 0.2, 0.211, 0.25, 0.308, 0.333, 0.5, 0.571, 0.667, 1.0]. Because rewards cluster on a few values, the cut-off acts on whole clusters; the frozen result is not changed.

### 7.5 Divergence decomposition

Computed on all complete groups (the current rule); the clean-group count is alongside. 'Tool-name' views drop every argument. AgentClinic canonical actions already drop the question text (`ASK`), so its full sequence is ASK count and order, test names and the diagnosis string.

| Benchmark | Cond | View | Divergent (all groups) | Mean distinct sequences | Divergent (clean groups) | Unstable verdict groups (context) |
|---|---|---|---|---|---|---|
| AgentClinic | A | full canonical sequence (current) | 10/10 | 4.80 | 10/10 | 5/10 |
| AgentClinic | A | tests only (REQUEST_TEST items, in order) | 10/10 | 4.20 | 10/10 | 5/10 |
| AgentClinic | A | diagnosis only (DIAGNOSIS item) | 10/10 | 4.00 | 10/10 | 5/10 |
| AgentClinic | A | action-type sequence (ASK / REQUEST_TEST / DIAGNOSIS) | 10/10 | 4.50 | 10/10 | 5/10 |
| AgentClinic | A | number of ASK turns only | 10/10 | 3.90 | 10/10 | 5/10 |
| AgentClinic | B | full canonical sequence (current) | 10/10 | 5.00 | 10/10 | 6/10 |
| AgentClinic | B | tests only (REQUEST_TEST items, in order) | 10/10 | 4.80 | 10/10 | 6/10 |
| AgentClinic | B | diagnosis only (DIAGNOSIS item) | 10/10 | 4.00 | 10/10 | 6/10 |
| AgentClinic | B | action-type sequence (ASK / REQUEST_TEST / DIAGNOSIS) | 10/10 | 4.40 | 10/10 | 6/10 |
| AgentClinic | B | number of ASK turns only | 10/10 | 4.20 | 10/10 | 6/10 |
| RadA-BenchPlat | A | full canonical sequence (current) | 9/10 | 2.40 | 3/3 | 1/10 |
| RadA-BenchPlat | A | tool-name-only sequence (no arguments) | 6/10 | 1.60 | 1/3 | 1/10 |
| RadA-BenchPlat | A | tool-name set (unordered) | 4/10 | 1.40 | 0/3 | 1/10 |
| RadA-BenchPlat | B | full canonical sequence (current) | 10/10 | 3.40 | 2/2 | 2/10 |
| RadA-BenchPlat | B | tool-name-only sequence (no arguments) | 7/10 | 2.30 | 2/2 | 2/10 |
| RadA-BenchPlat | B | tool-name set (unordered) | 7/10 | 2.00 | 2/2 | 2/10 |
| Synthetic Hospital | A | full canonical sequence (current) | 5/10 | 1.50 | 3/8 | 1/10 |
| Synthetic Hospital | A | tool-name-only sequence (no arguments) | 4/10 | 1.40 | 2/8 | 1/10 |
| Synthetic Hospital | A | tool-name set (unordered) | 4/10 | 1.40 | 2/8 | 1/10 |
| Synthetic Hospital | A | final submission only (submit_diagnosis call) | 5/10 | 1.50 | 3/8 | 1/10 |
| Synthetic Hospital | B | full canonical sequence (current) | 10/10 | 4.60 | 4/4 | 4/10 |
| Synthetic Hospital | B | tool-name-only sequence (no arguments) | 8/10 | 2.80 | 2/4 | 4/10 |
| Synthetic Hospital | B | tool-name set (unordered) | 8/10 | 2.30 | 2/4 | 4/10 |
| Synthetic Hospital | B | final submission only (submit_diagnosis call) | 10/10 | 4.60 | 4/4 | 4/10 |

Not decomposable from the stored records: AgentClinic question text is kept only in `actions_strict` (already reported in section 1.2); RadABench tool arguments are variable names ($Image$, ...), not values, so 'argument-only' divergence is the variable-set difference already inside the canonical string.

### 7.6 Seeds for agent, simulator and ollama (facts only)

- Lines containing `seed` in the harness: `driver_v3.py`: 6: Design: first 10 of each benchmark's seeded sample (random.Random(20261004).sample(pool, 15)[:10]), | 27: SEED = 20261004 | 77: r = random.Random(SEED); `v3_config.json`: none; `AgentClinic_runner.py`: none; `RadABench_runner.py`: 15: final_state, verdict, raw_log_path, usage, calls, env_seed, error} | 29: (random.sample of supported organs etc.), so the runner seeds `random` from a stable hash of | 31: conditions for a task. env_seed is recorded. | 100: env_seed = int(hashlib.sha256(a.task_id.encode()).hexdigest()[:8], 16) | 101: random.seed(env_seed) | 241: "env_seed": env_seed,; `synthetic_hospital_runner.py`: none; `runner_common.py`: none; `AgentClinic patched agentclinic.py (model call)`: none; `RadABench llm_client.py (model call)`: none.
- Request payloads actually sent, from 300 raw call logs: AgentClinic calls.jsonl: logged fields = ['backend', 'latency_s', 'messages', 'model', 'response', 'system_fingerprint', 'temperature', 'ts', 'usage']; RadABench request body keys = ['max_tokens', 'messages', 'model', 'temperature']; synthetic_hospital request body keys = ['max_tokens', 'messages', 'model', 'temperature', 'tools']. `seed` key present in any request: False.
- `v3_config.json` role temperatures: agent = None, simulator = 0, judge = 0 (agent null in the role block; the driver passes 0.05, 0 or 0.7 per condition). Ollama option keys `seed`, `top_k`, `top_p`, `num_predict` in the config: none. The derived tags only carry `num_ctx` 16384 per the config note (the 16k Modelfiles are not in `research/executed/ollama_modelfiles`, which holds 32k Modelfiles; not verified here).
- The only seeds fixed anywhere are the task sampler (`random.Random(20261004)` in `driver_v3.py`) and the RadABench environment (`random.seed(sha256(task_id)[:8])` in `RadABench_runner.py`, same for all repeats and conditions of a task; 10 distinct values, constant within each task: True). Agent and simulator/judge calls (AgentClinic through the patched `openai.ChatCompletion.create`, RadABench through `llm_client._chat_openai`, Synthetic Hospital through `client.chat.completions.create`) send `temperature` and `max_tokens` (and `tools` for Synthetic Hospital) and no `seed`. Synthetic Hospital resets with an explicit `gt_id`, so the server-side seed argument is unused. Whatever default seed or sampling state the ollama server applies when none is sent is not recorded in the episodes and was not inspected.

## 8. Round-2 analyses (simulated reviews round 2; added 2026-10-06)

Command (project root): `python analysis/revision_round2.py --write-summary`. Script `analysis/revision_round2.py`, seed 20261004. Nothing was rescored: every value comes from `audit/resolved`, `audit/coding`, `audit/verified`, `audit/gold_*`, `audit/perturb/perturb/summary.json`, `audit/transport/prompts/*/meta.json` and the files in `analysis/out/`. Outputs: `revision_round2.json`, `rev2_gold_gaps.csv`, `rev2_perturb_clusters.csv`, `rev2_cap_items.csv`; tables `paper/tables/rev2_gaps.tex`, `rev2_perturb_clusters.tex`. Validation inside the script (assertions): the table-based kappa equals the scorer's statistic on all common cells; the point estimates and the 2,000-resample percentile intervals equal section 5 exactly; the Claude perturbation counts equal 527/542 and 117/290 and each coder has 832 perturbation cells. All analyses here are post hoc.

### 8.1 Like-for-like gaps: benchmark-level tests and interval variants (R1 C3)

Gap = kappa(coder pair) - kappa(coder, expert) on the identical cells of section 5 (ABC: Cohen kappa, 198 cells, 9 benchmarks; BetterBench: quadratic-weighted kappa, 423 cells, 22 benchmarks). Intervals: percentile = the 2,000-resample interval over benchmarks of section 5; BCa = bias-corrected and accelerated, acceleration from the leave-one-benchmark-out jackknife; Bayesian bootstrap = 20,000 Dirichlet(1) weight draws over benchmarks, 2.5th and 97.5th percentiles. **Swap test**: under the null that the expert labels and the other coder's labels are exchangeable with respect to the anchor coder, the labels of the two can be swapped benchmark by benchmark; all 2^9 = 512 (ABC) and 2^22 = 4,194,304 (BetterBench) swaps are enumerated and the p-value is the share of swaps whose gap is at least as large in absolute value (two-sided; the smallest attainable two-sided value is 2/2^B because the full swap gives the negative of the observed gap). **Sign test**: per benchmark, raw agreement of the pair minus raw agreement of the coder with the expert; exact two-sided binomial test on the non-tied benchmarks (a per-benchmark kappa is unstable on 20 to 30 cells, so raw agreement is used for the sign).

**ABC** (198 cells, 9 benchmarks)

| Gap | Point | Percentile 95% | BCa 95% | Bayesian bootstrap 95% | Posterior share > 0 | Swap test p (one-sided / two-sided) | Sign test (positive / non-tied; two-sided p) |
|---|---|---|---|---|---|---|---|
| pair minus OpenAI/expert | +0.46 | [0.34, 0.59] | [0.34, 0.60] | [0.35, 0.58] | 1.000 | 0.002 / 0.004 (512 swaps) | 9 / 9 (0 ties); p = 0.004 |
| pair minus Claude/expert | +0.42 | [0.25, 0.62] | [0.25, 0.62] | [0.26, 0.60] | 1.000 | 0.004 / 0.008 (512 swaps) | 8 / 9 (0 ties); p = 0.039 |
| pair minus mean(coder/expert) | +0.44 | [0.30, 0.60] | [0.30, 0.61] | [0.31, 0.59] | 1.000 | n/a (not defined for the mean) | n/a |

**BetterBench** (423 cells, 22 benchmarks)

| Gap | Point | Percentile 95% | BCa 95% | Bayesian bootstrap 95% | Posterior share > 0 | Swap test p (one-sided / two-sided) | Sign test (positive / non-tied; two-sided p) |
|---|---|---|---|---|---|---|---|
| pair minus OpenAI/expert | +0.31 | [0.24, 0.38] | [0.24, 0.38] | [0.24, 0.38] | 1.000 | <0.001 / <0.001 (4,194,304 swaps) | 20 / 21 (1 ties); p <0.001 |
| pair minus Claude/expert | +0.24 | [0.13, 0.34] | [0.13, 0.33] | [0.13, 0.33] | 1.000 | <0.001 / <0.001 (4,194,304 swaps) | 20 / 22 (0 ties); p <0.001 |
| pair minus mean(coder/expert) | +0.28 | [0.19, 0.36] | [0.20, 0.36] | [0.20, 0.35] | 1.000 | n/a (not defined for the mean) | n/a |

### 8.2 Perturbation table with packet-cluster intervals (R1 C3, M4)

The 832 labelled cells of the 39 variant packets, for the OpenAI coder (gpt-5.5), Claude Sonnet and the resolved level. Each variant packet is built on a different benchmark (39 benchmarks for 39 variants, `perturb_diagnosis_cells.csv`), so the variant cluster is a packet cluster and a benchmark cluster at once. Percentile bootstrap, 2,000 resamples of clusters with replacement, seed 20261004, pooled rate per resample; the Wilson interval (cells independent) is beside it. Item clusters (25) are a second view: the same item is planted or deleted in many packets. The multiplexed design adds dependence that neither cluster view removes (cross-item interference, section 3.4 and `perturb_diagnosis.md`).

| Coder | Rate | Hits/n | Rate | Wilson 95% | Variant-cluster 95% (39) | Width ratio vs Wilson | Item-cluster 95% (25) | Width ratio vs Wilson |
|---|---|---|---|---|---|---|---|---|
| codex | sensitivity | 519/542 | 95.8% | [93.7, 97.2] | [93.9, 97.5] | 1.04 | [91.7, 98.9] | 2.10 |
| codex | inject | 176/187 | 94.1% | [89.8, 96.7] | [90.3, 97.2] | 1.00 | [89.3, 97.9] | 1.24 |
| codex | buried | 175/181 | 96.7% | [93.0, 98.5] | [94.4, 98.9] | 0.80 | [92.9, 99.5] | 1.19 |
| codex | paraphrase | 168/174 | 96.6% | [92.7, 98.4] | [93.6, 98.8] | 0.91 | [92.4, 100.0] | 1.33 |
| codex | specificity | 116/290 | 40.0% | [34.5, 45.7] | [34.8, 45.6] | 0.96 | [31.7, 48.1] | 1.46 |
| codex | deletion | 17/117 | 14.5% | [9.3, 22.0] | [9.3, 20.0] | 0.84 | [6.8, 22.9] | 1.27 |
| codex | decoy | 99/173 | 57.2% | [49.8, 64.4] | [49.7, 65.4] | 1.08 | [47.2, 67.1] | 1.36 |
| sonnet | sensitivity | 527/542 | 97.2% | [95.5, 98.3] | [95.8, 98.5] | 0.94 | [93.9, 99.6] | 2.02 |
| sonnet | inject | 181/187 | 96.8% | [93.2, 98.5] | [94.2, 98.9] | 0.89 | [93.6, 99.5] | 1.10 |
| sonnet | buried | 178/181 | 98.3% | [95.2, 99.4] | [96.6, 100.0] | 0.81 | [94.9, 100.0] | 1.21 |
| sonnet | paraphrase | 168/174 | 96.6% | [92.7, 98.4] | [93.8, 98.9] | 0.88 | [92.6, 99.4] | 1.19 |
| sonnet | specificity | 117/290 | 40.3% | [34.9, 46.1] | [35.4, 45.2] | 0.87 | [31.7, 49.2] | 1.56 |
| sonnet | deletion | 16/117 | 13.7% | [8.6, 21.1] | [8.1, 19.6] | 0.93 | [5.6, 22.8] | 1.38 |
| sonnet | decoy | 101/173 | 58.4% | [50.9, 65.5] | [51.7, 65.5] | 0.94 | [46.5, 70.3] | 1.63 |
| RESOLVED | sensitivity | 508/542 | 93.7% | [91.4, 95.5] | [91.7, 95.7] | 0.97 | [88.7, 98.0] | 2.25 |
| RESOLVED | inject | 172/187 | 92.0% | [87.2, 95.1] | [87.9, 95.3] | 0.93 | [86.5, 96.8] | 1.31 |
| RESOLVED | buried | 173/181 | 95.6% | [91.5, 97.7] | [93.1, 98.1] | 0.81 | [90.7, 99.4] | 1.40 |
| RESOLVED | paraphrase | 163/174 | 93.7% | [89.0, 96.4] | [90.1, 96.7] | 0.89 | [87.7, 98.3] | 1.44 |
| RESOLVED | specificity | 137/290 | 47.2% | [41.6, 53.0] | [41.9, 52.9] | 0.96 | [39.0, 55.9] | 1.48 |
| RESOLVED | deletion | 23/117 | 19.7% | [13.5, 27.8] | [13.8, 25.9] | 0.84 | [11.1, 29.4] | 1.28 |
| RESOLVED | decoy | 114/173 | 65.9% | [58.6, 72.5] | [58.6, 73.3] | 1.05 | [55.0, 76.8] | 1.55 |

### 8.3 Cap-stratified RQ1 shares and alpha; version merge (R2 M3)

Cap flags are in `audit/transport/prompts/<bench>/meta.json` (`tokens_before_cap`, `n_dropped_chunks`), not in `audit/packets/*/manifest.json`, which carries no cap field (the cap is applied at scoring time; `audit/BUILD_LOG.md`). Capped = at least one S4 chunk dropped by the 150,000-token cap: 14 of the 44 coded benchmarks (clinicalagent-bench, codeclinic, diaggym-diagbench, healthagentbench, healthcare-ai-gym, medagentsim, medcta, mtbbench, openhospital, patientagentbench, physassistbench, physicianbench, rada-benchplat, synthetic-hospital); the other 30 are uncapped. HealthCraft is also capped and has no cells. Resolved rule; CI = percentile bootstrap over benchmarks within the stratum (2,000, seed 20261004); the difference (capped minus uncapped) uses independent resampling in each stratum.

| Module | Stratum | Benchmarks | Applicable cells | REPORTED | 95% CI | Fully reported | 95% CI |
|---|---|---|---|---|---|---|---|
| core | capped | 14 | 191 | 58.1% | [49.7, 66.1] | 9.9% | [5.2, 15.7] |
| core | uncapped | 30 | 405 | 51.6% | [45.7, 57.6] | 8.1% | [4.7, 12.1] |
| core | all | 44 | 596 | 53.7% | [49.0, 58.6] | 8.7% | [5.9, 11.9] |
| agent | capped | 14 | 147 | 59.2% | [49.7, 68.8] | 8.8% | [4.1, 14.4] |
| agent | uncapped | 30 | 322 | 64.0% | [58.8, 69.2] | 6.8% | [4.0, 9.6] |
| agent | all | 44 | 469 | 62.5% | [57.8, 67.1] | 7.5% | [5.1, 10.1] |

Difference, capped minus uncapped, in points (percentile 95% interval): core rep +6.5 [-3.7, +17.1]; core full +1.8 [-4.4, +8.7]; agent rep -4.8 [-15.2, +6.0]; agent full +2.0 [-3.4, +8.1].

Cross-family ordinal alpha (raw scores, NA missing), overall: capped 0.794 [0.717, 0.847] on 350 cells in 14 benchmarks; uncapped 0.759 [0.713, 0.799] on 750 cells in 30 benchmarks (all 44: 0.771).

Items with the largest capped-minus-uncapped difference in the REPORTED share (resolved rule; n = applicable benchmarks):

| Item | Capped (n) | Uncapped (n) | Difference (points) |
|---|---|---|---|
| C14 | 78.6% (14) | 46.7% (30) | +31.9 |
| A5 | 61.5% (13) | 83.3% (30) | -21.8 |
| A8 | 78.6% (14) | 100.0% (30) | -21.4 |
| C10 | 64.3% (14) | 43.3% (30) | +21.0 |
| C8 | 42.9% (14) | 63.3% (30) | -20.5 |
| C3 | 92.9% (14) | 73.3% (30) | +19.5 |

- C13: 8 of 14 cells in capped packets resolved to 0 (status counts {'not_established': 7, 'resolved': 6, 'established_zero': 1}), against 13 of 30 in uncapped packets; REPORTED 42.9% capped against 56.7% uncapped.
- A4: 9 of 14 cells in capped packets resolved to 0 (status counts {'established_zero': 5, 'not_established': 4, 'resolved': 5}), against 16 of 30 in uncapped packets; REPORTED 35.7% capped against 46.7% uncapped.
- Cap-aware shares (the 17 capped C13 and A4 cells that resolved to 0 are treated as not established and left out of the denominator): core REPORTED 54.4% (n = 588), fully reported 8.8%; agent REPORTED 63.7% (n = 460), fully reported 7.6%.

MedAgentBench v1 and v2 merged (resolved rule; the merged unit takes the higher resolved level per item, NA only when both are NA):

| Variant | Benchmarks | Core cells | Core REPORTED [95%] | Core full | Agent cells | Agent REPORTED [95%] | Agent full |
|---|---|---|---|---|---|---|---|
| all 44 (v1 and v2 separate) | 44 | 596 | 53.7% [49.0, 58.6] | 8.7% | 469 | 62.5% [57.8, 67.1] | 7.5% |
| v2 dropped (v1 kept) | 43 | 582 | 54.1% [49.4, 59.1] | 8.9% | 458 | 62.9% [58.1, 67.7] | 7.6% |
| v1 dropped (v2 kept) | 43 | 582 | 54.1% [49.4, 59.1] | 8.9% | 458 | 62.2% [57.3, 67.1] | 7.6% |
| merged (higher level per item) | 43 | 582 | 54.8% [50.2, 59.8] | 8.9% | 458 | 63.1% [58.3, 68.0] | 7.6% |

### 8.4 Audit A3 and A8 beside the rerun findings (R2 M5)

Resolved level = the audit's two-family rule (section 2); raw = each coder's score before quote verification; quotes are the coders' verbatim excerpts. Cap: whether the packet lost S4 chunks to the 150,000-token cap. A3 asks for action-level repeat-run reliability, A8 for the grader's input and its validation. No audit score was recomputed or compared statistically with a rerun outcome; the table sets stored results side by side.

| Benchmark | Cap | Item | Resolved | Status | OpenAI raw / Claude raw | OpenAI quote | Claude quote |
|---|---|---|---|---|---|---|---|
| AgentClinic | not capped | A3 | 0 | not_established | 1 / 0 | "standard error of the mean accuracy across multiple runs" | none |
| AgentClinic | not capped | A8 | 1 | resolved | 1 / 1 | "the diagnosis text produced by the doctor agent can be quite unstructured" | "This agent is necessary because the diagnosis text produced by the doctor agent can be quite unstructured depending on the model" |
| RadA-BenchPlat | capped (201 chunks dropped) | A3 | 0 | established_zero | 0 / 0 | none | none |
| RadA-BenchPlat | capped (201 chunks dropped) | A8 | 0 | not_established | 1 / 1 | "The logs preserve construction status, validation outcome, and downstream invocation outcome" | "task-specific automatic metrics, including Dice/Jaccard for grounding, Accuracy/Jaccard for diagnosis, and RadGraph-F1/RaTE for reports"; "We also collect LLM-based ratings and blinded human ratings from two expert radiologists to assess clinical plausibility." |
| Synthetic Hospital | capped (220 chunks dropped) | A3 | 0 | established_zero | 0 / 0 | none | none |
| Synthetic Hospital | capped (220 chunks dropped) | A8 | 1 | resolved | 1 / 1 | "Rewards are the tasks' primary metrics" | "predictions are scored by clinical-concept overlap rather than surface wording" |

Rerun findings (stored results, sections 1 and 7): task groups with more than one action sequence (condition A / B, of 10) AgentClinic 10 / 10; RadA-BenchPlat 9 / 10; Synthetic Hospital 5 / 10; groups with an unstable verdict AgentClinic 5 / 6; RadA-BenchPlat 1 / 2; Synthetic Hospital 1 / 4. Invalid episodes (of 50): AgentClinic 0 / 0; RadA-BenchPlat 29 / 33; Synthetic Hospital 5 / 7. Grader check (Synthetic Hospital): condition A: 0 disagreements in 45 episodes with a submission (5 with none); condition B: 0 disagreements in 43 episodes with a submission (7 with none). Judge-only rerun (AgentClinic): 0 of 100 transcripts unstable, 1 of 100 differing from the recorded verdict. RadA-BenchPlat has no grader check.

Reading (facts only): A3 resolves to 0 (not REPORTED) for AgentClinic, RadA-BenchPlat, Synthetic Hospital, so on the audit none of the three reports repeat-run behaviour, and the reruns found more than one action sequence in 24 of 30 task groups at the benchmark's own temperature (condition A) and 30 of 30 at 0.7 (condition B). For AgentClinic the A3 zero is a not-established cell (the OpenAI coder gave 1 on a score-level statement, Claude gave 0). A8 resolves to 1 for AgentClinic, 0 for RadA-BenchPlat, 1 for Synthetic Hospital; the RadA-BenchPlat 0 is a not-established cell (both coders gave 1, one without a verified quote). None of the six A8 rationales reports a validation on known-correct and known-incorrect outcomes, and the rerun checks (a recomputation of a reward, a judge repeated at temperature 0) are not such a validation. The RadA-BenchPlat and Synthetic Hospital packets were capped, so a zero for them can reflect removed code.

### 8.5 Alpha and prevalence for the low-alpha extremes (R1 C4, R3)

The text of section V-A named A7 among the items REPORTED by at least 90% and C11 as REPORTED by none while stating that items with alpha below 0.5 are not ranked. Values (cross-family ordinal alpha, 44 cells each, bootstrap CI over benchmarks; REPORTED share of applicable cells):

| Item | Alpha [95% CI] | Applicable | REPORTED | Fully reported |
|---|---|---|---|---|
| A7 | 0.02 [-0.36, 0.35] | 31 | 96.8% | 22.6% |
| C11 | 0.00 [-0.04, 0.00] | 44 | 0.0% | 0.0% |
| C10 | 0.20 [-0.13, 0.49] | 44 | 50.0% | 2.3% |
| C7 | 0.38 [0.05, 0.63] | 44 | 52.3% | 2.3% |
| A10 | 0.41 [-0.01, 0.75] | 44 | 84.1% | 2.3% |
| C3 | 0.46 [-0.02, 0.80] | 44 | 79.5% | 0.0% |
| C8 | 0.49 [0.16, 0.75] | 44 | 56.8% | 0.0% |

Items with alpha below 0.5 (7): C3, C7, C8, C10, C11, A7, A10. Items at 0.8 or above (7): C4, C5, C12, C14, A3, A4, A11. The other high-share items are C2 (90.9%, alpha 0.59) and A8 (93.2%, alpha 0.56), which also lie below 0.8; A7 (96.8%, alpha 0.02) and C11 (0.0%, alpha 0.00) are the two extremes of the share ranking and have the two lowest alphas, so neither is a ranked extreme.
