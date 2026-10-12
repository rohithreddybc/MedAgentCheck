# Reproducing the headline analysis from the release

Post-freeze tools. Nothing in `repro/` is part of the frozen method: the scorer at commit 713d078 and every file in `FREEZE_MANIFEST.json` are unchanged, and `agentaudit freeze --verify .` still passes. The scripts here read released files only (`results/`, `reruns/`, `repro/tables/`), recompute the paper's headline quantities, and assert that each value equals the one the authors' analysis scripts wrote (`results/analysis_out/`, `analysis/out/RESULTS_SUMMARY.md`). They do not touch the authors' working-tree paths (`audit/`, `research/`, `paper/`), which `analysis/*.py` expect.

| Script | Reproduces | Reads | Compared with |
|---|---|---|---|
| `repro/reproduce_audit.py` | Cross-family ordinal Krippendorff alpha with bootstrap CI over benchmarks (overall and per item); REPORTED and fully reported shares per item and module with Wilson and bootstrap intervals; resolution status counts; contradiction-flag counts; prevalence bounds [resolved rule, union rule] | `results/resolved/` | `rq2_alpha.csv`, `rq1_prevalence.csv`, `rq1_modules.csv`, `rq1_resolution.csv`, `rq1_contradictions*.csv`, `rev_bounds_*.csv`, `RESULTS_SUMMARY.md` |
| `repro/reproduce_perturbation.py` | Perturbation sensitivity and specificity per coder and resolved (Wilson), with packet-cluster and item-cluster bootstrap intervals | `results/perturbation/summary.json` | `rq2_perturbation.csv`, `rev2_perturb_clusters.csv`, `revision_round2.json`, `RESULTS_SUMMARY.md` 3.4 and 8.2 |
| `repro/reproduce_retest.py` | Coder test-retest agreement (raw, Wilson, alpha with CI, weighted kappa) per coder and for the resolved level | `results/resolved/`, `results/retest/` | `rq2_retest*.csv/json`, `retest_agreement.json`, `RESULTS_SUMMARY.md` 3.3 |
| `repro/reproduce_gold.py` | Like-for-like gold comparison: coder-pair kappa, each coder versus expert, resolved versus expert, gaps with paired bootstrap CIs over benchmarks (percentile, BCa, Bayesian), the exact benchmark-level swap (sign-flip) permutation test over all 2^B swaps, the sign test, the scorer's own agreement statistics on the original cell sets, over- and under-credit counts | `repro/tables/gold_contingency.csv` | `results/gold/*/agreement.json`, `gold_coder_pair.json`, `revision_round2.json`, `rev2_gold_gaps.csv`, `rq2_gold*.csv`, `RESULTS_SUMMARY.md` 5 and 8.1 |
| `repro/reproduce_rules.py` | Resolution-rule ablation (Claude only, OpenAI only, union, intersection without the family requirement, resolved rule, resolved rule on raw scores, union on raw scores): agreement with the gold sets, paired difference to the best single coder, RQ1 module shares per rule; PABAK, Gwet AC1 and AC2 with intervals and confusion matrices; quote-verification and family-requirement counts on the audit cells | `repro/tables/gold_rule_contingency.csv`, `repro/tables/gold_rule_vs_best.csv`, `results/resolved/` | `rev_ablation.csv`, `rev_pabak.csv`, `rev_confusion.csv`, `revision_rq12.json` (gold, rq1, verification, family), `RESULTS_SUMMARY.md` 6.1 and 6.3 |
| `repro/reproduce_cap.py` | Cap-stratified analysis: RQ1 module shares and cross-family alpha for the 14 packets cut by the 150,000-token cap and the 30 that were not, capped-minus-uncapped differences, per-item shares, capped C13 and A4 cells, cap-aware shares, MedAgentBench v1/v2 merge | `repro/tables/cap_flags.csv`, `results/resolved/` | `revision_round2.json` (cap), `rev2_cap_items.csv`, `RESULTS_SUMMARY.md` 8.3 |
| `repro/reproduce_reruns.py` | Action divergence, verdict instability, same-verdict-different-actions, pass^k (k = 1..5) with cluster-bootstrap intervals, CI width of 1 versus 5 runs, Bayesian-bootstrap and exact intervals, design effect, Synthetic Hospital cut-off sensitivity | `reruns/*_episodes.jsonl` | `rq3_*.csv` (and `*_errexcl.csv`), `rev_rq3_passk_bayes.csv`, `rev_rq3_deff.csv`, `rev_rq3_cutoff.csv`, `RESULTS_SUMMARY.md` headline |
| `repro/reproduce_coauthor.py` | Paired temperature contrasts (paper Table S19): per task B minus A of pass^1, pass^5, action divergence and verdict instability, paired bootstrap intervals (per benchmark and pooled) and exact sign tests | `reruns/*_episodes.jsonl` | `coauthor_paired_contrasts.csv/.json`, `rq3_passk.csv`, `RESULTS_SUMMARY.md` 9.1 |

The ports copy the computations of `analysis/postfreeze/rq1_rq2.py`, `analysis/postfreeze/rq3_reruns.py`, `analysis/revision_rq12.py`, `analysis/revision_rq3.py`, `analysis/revision_round2.py`, `analysis/revision_coauthor.py`, `analysis/gold_coder_pair.py` and `analysis/rq2_extras.py`; the numbers are not changed. Statistics (alpha, Cohen and weighted kappa, Wilson interval, benchmark bootstrap) are the frozen functions of `agentaudit/stats.py`, imported from this checkout.

Added with these scripts, outside the frozen files: `analysis/revision_coauthor.py` (paired temperature contrasts), its outputs `results/analysis_out/coauthor_paired_contrasts.csv` and `.json`, and section 9 of `analysis/out/RESULTS_SUMMARY.md` (9.1 is reproduced; 9.2 is not, see below).

## Commands (run from the repository root)

Python 3.10 or later (the reference run used CPython 3.11.7 on Windows 11). Required packages and the versions of the reference run are in `repro/requirements.txt` (numpy, scipy, PyYAML; pandas is not needed).

    python -m venv .venv-repro
    .venv-repro/Scripts/activate            # Windows (PowerShell: .venv-repro\Scripts\Activate.ps1); POSIX: source .venv-repro/bin/activate
    python -m pip install -r repro/requirements.txt
    python -m agentaudit.cli freeze --verify .
    python repro/run_all.py

`freeze --verify` must print `{"intact": true, "problems": []}`. `run_all.py` runs the eight scripts in order (together about two minutes; the swap test over 2^22 benchmark swaps for BetterBench takes most of it; `python repro/run_all.py --skip-swap` omits it) and ends with `All reproduction scripts passed`. Each script can also be run alone, for example `python repro/reproduce_gold.py`. Reproduced tables are written to `repro/out/` (git-ignored); the scripts never write into `results/`, `reruns/` or `analysis/`.

A mismatch raises `AssertionError` with the first differing values. Values are compared to the precision the authors' CSV files print (six decimals, tolerance 1.5e-6) and the JSON files to 1e-9; the tables printed in `RESULTS_SUMMARY.md` are regenerated with the authors' formatting and searched for in the file, so a change of one printed digit fails the check.

## Benchmark-level contingency tables (`repro/tables/gold_contingency.csv`)

The ABC and BetterBench expert scores and the coders' predictions on those cells are withheld (ABC's repository has no licence; see the repository README), so the gold analysis cannot be rerun from item-level data. The table releases what the statistics need and no more: for every gold set, comparison, cell set and benchmark, the cross-tabulation of two raters' levels. Columns: `gold_set` (`abc`, `betterbench`), `comparison`, `cell_set`, `benchmark`, `row_level`, `col_level`, `count` (rows with count 0 are omitted).

- `comparison` names the two raters, and the first one is the row rater: `codex_vs_sonnet`, `codex_vs_expert`, `sonnet_vs_expert`, `resolved_vs_expert`. Coders are the OpenAI coder (gpt-5.5, `codex`) and the Claude coder (`sonnet`); `resolved` is the two-family resolved level; `expert` is the published expert score on the comparison scale (ABC 0 or 1; BetterBench 0, 1, 2, 3 for the instrument's 0, 5, 10, 15 points).
- `cell_set = common`: cells where the expert and both coders have a level (ABC: 198 cells, 9 benchmarks; BetterBench: 423 cells, 22 benchmarks). These tables give the pair statistics, the paired bootstrap, the swap test and the sign test. For `resolved_vs_expert` the cell must also have a non-NA resolved level.
- `cell_set = original`: the cells of the scorer's `agreement.json` (per rater; level `NA` kept on either side, so the counts of expert-NA and coder-NA cells can be read off). These reproduce `results/gold/*/agreement.json`.
- The cell sets are those of `analysis/gold_coder_pair.py`; `repro/make_gold_tables.py` (authors only, needs the withheld inputs) built the file. It contains no item id, item text or per-cell label. The per-benchmark totals of expert levels are visible as column sums, which is the price of benchmark-level resampling; the item-level assignment is not.

Kappa, weighted kappa, raw agreement, ordinal alpha and the bootstrap depend on the cells only through these counts, so `reproduce_gold.py` rebuilds each cross-tabulation and applies the scorer's statistics. Resampling draws benchmarks with the same random stream as the authors' scripts (seed 20261004, 2,000 resamples).

## Rule-ablation and cap tables (`repro/tables/gold_rule_contingency.csv`, `gold_rule_vs_best.csv`, `cap_flags.csv`)

All three hold aggregate counts or per-benchmark flags only; none has an item id, item text, per-cell label or prompt text. `repro/make_rule_cap_tables.py` (authors only, needs the withheld inputs) built them.

- `gold_rule_contingency.csv`: columns `gold_set` (`abc`, `betterbench`), `rule`, `benchmark`, `expert_level`, `rule_level`, `count`. For each resolution rule (`claude`, `openai`, `union`, `nofam` = intersection without the family requirement, `current` = the resolved rule, `raw` = the resolved rule on raw scores without quote verification, `union_raw`), the cross-tabulation of the expert level and the rule's level on the cells of the scorer's `agreement.json` (Claude only and OpenAI only: that coder's cells; every other rule: the cells both coders scored). Level `NA` is kept, so the NA bookkeeping (`n_gold_na`, `n_pred_na`) can be read off. The rules are the functions of `analysis/revision_rq12.py` (`apply_rule`), which use the frozen `agentaudit/resolve.py`.
- `gold_rule_vs_best.csv`: for the paired difference "rule minus best single coder", the counts of (expert, best single coder, rule) per benchmark over the cells where all three are numeric. `best_coder` is the single coder with the higher primary statistic against the expert (Claude for both gold sets); `reproduce_rules.py` recomputes it and checks the column.
- `cap_flags.csv`: one row for each of the 45 benchmarks with a prompt (the 44 coded benchmarks and HealthCraft, which has no cells): `capped` (`yes` if at least one S4 chunk was dropped by the 150,000-token cap), `tokens_before_cap` (token count of the packet before the cap), `tokens_sent`, `n_dropped_chunks`, `over_cap`, `cap_tokens`. Taken from `audit/transport/prompts/<bench>/meta.json`; `reproduce_cap.py` checks that `capped` follows from the dropped chunks and the token count.

## What reproduces from the release, and what does not

Reproduces (each value is asserted equal to the authors' output file or to the printed table in `analysis/out/RESULTS_SUMMARY.md`):

- RQ1: per-item and per-module REPORTED and fully reported shares (Wilson and bootstrap intervals); resolution status counts; contradiction flags; the interval [resolved rule, union rule]; module shares under each of the seven resolution rules; the cap-stratified shares, the capped-minus-uncapped differences, the capped C13 and A4 cells, the cap-aware shares and the MedAgentBench v1/v2 merge.
- RQ2: cross-family Krippendorff alpha overall and per item, and within the capped and uncapped strata; perturbation sensitivity and specificity per coder and resolved, with packet-cluster and item-cluster bootstrap intervals; test-retest agreement; the like-for-like gold comparison (coder-pair kappa, each coder and resolved versus expert, paired bootstrap, BCa and Bayesian intervals, the exact swap test, the sign test, over- and under-credit counts); the resolution-rule ablation against both gold sets (agreement, paired difference to the best single coder); PABAK, Gwet AC1 and AC2 with intervals and confusion matrices; quote-verification counts per coder and the cells changed by the family requirement, on the 1,100 audit cells.
- RQ3: action divergence, verdict instability, same-verdict-different-actions, pass^k (k = 1 to 5) with cluster-bootstrap, Bayesian-bootstrap and exact intervals, CI width of 1 versus 5 runs, design effect, the Synthetic Hospital cut-off sensitivity, and the paired temperature contrasts of Table S19 (RESULTS_SUMMARY 9.1), with both the default and the `--exclude-episode-errors` episode rule where the authors report both.

Needs materials that are not redistributed (not in `repro/`):

- The grader-versus-recomputation check (Synthetic Hospital: 88 episodes with a submission, 69 exact recomputations and 19 conditional checks; `rq3_grader_state*.csv`, RESULTS_SUMMARY 9.2) needs the final environment states of the episodes.
- The judge-only rerun (100 AgentClinic transcripts, three re-judgements each; `rq3_judge_rerun*`) needs the transcripts.
- Transcripts, final states and submissions contain benchmark task content (case text, patient records, reference answers), which we do not redistribute. The episode records in `reruns/` hold hashes, tool names, verdicts and rewards only.
- The episode-validity flags of `analysis/revision_rq3.py` (they read Synthetic Hospital traces); per-item gold agreement (`rq2_gold_by_item.csv`; item-level labels); the quote-verification and family-requirement counts on the gold cells (they need the coders' raw scores on the withheld expert-scored items); re-scoring the audit itself (new coder calls give different levels because the coders are hosted models without temperature control; see the repository README).

Not ported to `repro/`: the threshold table (RESULTS_SUMMARY 6.4), the Rogan-Gladen sensitivity analysis (6.5), the pilot-exclusion analysis (6.6), the A3 and A8 side-by-side table (8.4), the token totals (section 4) and the score cards. Their values are in `results/analysis_out/` and `analysis/out/RESULTS_SUMMARY.md` and are not asserted by `repro/`; the authors' scripts (`analysis/revision_rq12.py`, `analysis/revision_round2.py`, `analysis/token_totals.py`, `analysis/make_scorecards.py`) compute them from the authors' working tree.

## Credentials

No API key, token or password is in the release. The Synthetic Hospital runner (`repro/reruns_runner/runners/synthetic_hospital_runner.py`) reads the scorer token of the local benchmark server from the environment variable `SYNTHETIC_HOSPITAL_TOKEN` (or the upstream name `EPIC_SIM_SCORER_TOKEN`) and stops with an error if neither is set. The reruns used the upstream repository's default development token for its local scorer endpoint, as given in the upstream's own setup files: `epic_sim/app/config.py` (field `scorer_token`), repeated in `docker-compose.yml` and `Dockerfile`, of `https://github.com/sparkcpark/synthetic_hospital` at commit `911f34c4ac65a508543c4b3b90c373a0cd16534d`. It is not a credential of ours and is not reproduced here: read it from those files, or start the server with a token of your own and export the same value. The runner file in this release differs from the one that produced the data only in this token handling (a literal fallback was replaced by the environment read).

## Ollama tags built from the released Modelfiles

`repro/reruns_runner/ollama_modelfiles/qwen3-4b-ctx16k.Modelfile` and `llama3.1-8b-ctx16k.Modelfile` reproduce the parameters of the tags served in the reruns (`ollama show --parameters` gives the same `num_ctx 16384`, `temperature 0`, stop tokens and sampling defaults; same base weights, `aa7252f68dda` for qwen3 and `46e0c10c039e` for llama3.1). They do not reproduce the tag digests: a tag digest is the hash of the manifest and its metadata, not of the weights. The digests reported in the paper (Supplement S7) and the digests of tags built from the released files (`ollama create`, Ollama 0.40.2, built twice under different tag names with the same result; the Ollama version of the reruns was not recorded) are:

| Tag | Reported in the paper (first 12 characters; full digest also in `runners/roles.json`) | Built from the released Modelfile (first 12 characters; full digest) |
|---|---|---|
| `qwen3-4b-ctx16k` | `175cbe4a2b73` (`175cbe4a2b73ba55a2d3b8f59c0eaf2a4537145d9071836b5495dcf754975f22`) | `84a2e62d926d` (`84a2e62d926d02a0763dce1ba068be0b3ecbc3751b1ebc5097bb8982de5acba5`) |
| `llama3.1-8b-ctx16k` | `2b175d2e041c` (`2b175d2e041c7108fcead7b5fe3a202d88ed24e8912c390dcc2f8a60f28b80ae`) | `30b914c5b7c1` (`30b914c5b7c12d3dfadcfe894aae6b422ecc5280bd7ff05b0b8a8672995bf6bf`) |

Pin the models by the base digests (`runs/v3_config.json`), not by the tag digests. The `gpt-oss-20b-ctx16k` tag of the Groq profile has no released Modelfile; `gpt-oss-20b-ctx32k.Modelfile` is the v2 original.

## Executed-benchmark runner scripts

`repro/reruns_runner/` holds our driver, per-benchmark runner adapters, role/model configs, routing patch diffs and setup notes for the three executed reruns (`repro/reruns_runner/README.md`). They need the benchmark repositories, their data and local models, which are not redistributed; they are included so that the reruns can be repeated and inspected, not to reproduce the numbers (those come from the released `reruns/` records).

## Wording of level 0 in the score cards

A level of 0 (NOT REPORTED) means that the pipeline did not establish reporting from the packet as built: both coders found no verified evidence, the coders disagreed, a quotation failed verification, or the evidence was in code removed by the size cap. It is not evidence that the benchmark lacks the practice. `analysis/make_scorecards.py` writes this wording into `results/scorecards/*.md`; the Status column of each card separates an established zero from a cell that was not established.
