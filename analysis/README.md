# analysis/

`rq3_reruns.py` (RQ3), `judge_rerun.py` (judge-only rerun of recorded AgentClinic moderator calls, 3 times each; needs ollama; `--limit 2` for the 2-transcript check), `rq1_rq2.py` (RQ1, RQ2; `--exclude-rule-affected` is the R1-R7/R6a sensitivity analysis, writing `*_ruleexcl` outputs), `figures.py` (Figs 2, 4, 5), `rq2_extras.py` (gold by item and error direction, coder retest with the manifest slug fix), `results_summary.py` (writes `out/RESULTS_SUMMARY.md` from the outputs), `common.py`. `rq3_reruns.py --exclude-episode-errors` is the earlier episode rule as a sensitivity analysis; `rq1_rq2.py --gold-abc/--gold-betterbench/--perturb-run` point at the gold and perturbation run directories. Tests: `python -m pytest analysis/tests` (synthetic fixture from `mock/make_mock.py`; no real data).
CSV go to `out/`, booktabs tabulars to `paper/tables/`, vector PDFs to `paper/figures/`.

## RQ3 grader versus state (Synthetic Hospital)

Paths below are relative to `research/executed/repos/synthetic_hospital` (git commit 911f34c4ac65a508543c4b3b90c373a0cd16534d).

**The benchmark's documented success criterion is a continuous reward, not a pass/fail rule.** For `patient_diagnosis` the reward is the severity-weighted, chart-neutral problem-list F1:

- `eval/score_one.py:38-39`: `"patient_diagnosis": "weighted_problem_list_f1_neutral",` (the primary metric per task).
- `README.md:185-186`: "Rewards are the tasks' primary metrics: severity-weighted, chart-neutral F1 for patient diagnosis".
- `eval/scoring.py:528`: `w_f1_neutral = problem_list_f1(mean_w_recall, mean_precision_neutral)`; `eval/scoring.py:338-342`: the harmonic mean of recall and precision.
- `eval/score_one.py:147-150`: the reward is that metric clipped to [0, 1].
- `README.md:225-226`: "a malformed or missing submission scores 0".

The 0.5 cut-off in the runner's `verdict["pass"]` (`research/executed/runners/synthetic_hospital_runner.py:254`) is the study's derived binary for pass^k only; it is not the benchmark's criterion and is not used for grader-versus-state.

**Recomputation.** `rq3_reruns.py` calls the benchmark's own `eval.scoring.compute_all_metrics("patient_diagnosis", [submission], [reference])` on the episode's observed final state (`final_state.submission`, `final_state.reference.ground_truth`) and compares `weighted_problem_list_f1_neutral` with the reward the grader reported (`verdict.reward`). Disagreement means `|recomputed - reported| > 1e-6`. The server-side stored reward (`final_state.env_state.reward`) is compared with the reported reward as a second column.

Outcomes, counted separately:

- `agree`, `disagree`.
- `state_missing`: no final state, no reference, or the benchmark scorer cannot be imported. Not recomputable.
- `neutral_set_required`: the recomputed value differs from the reported one and the grader reports neutral predictions (`n_neutral_predictions > 0`). The chart-neutral categories come from `longitudinal_patients.profile` in the benchmark's Postgres database (`eval/chart_neutral.py:33-46`), which the episode record does not hold. Offline, the neutral set is empty, so the recomputed value is a lower bound on the reward (`eval/scoring.py:476-485`: neutral predictions only leave the precision denominator). A reported reward at or above that bound is not called a disagreement. Not recomputable exactly.

Limit: the submission in `final_state` is the one parsed by the runner from the agent's tool call; the server's trace stores only a submitted flag (`epic_sim/app/services/env_service.py:373-375`), not the arguments.

## Post-freeze additions (2026-10-06)

The scripts here run on the authors' working tree (`audit/`, `research/executed/runs/v3/`, `analysis/out/`), not on the released `results/` layout. `postfreeze/rq1_rq2.py` and `postfreeze/rq3_reruns.py` are the versions used for the paper; the files of the same names in this folder are the frozen versions listed in `FREEZE_MANIFEST.json`, which stay unchanged (`postfreeze/` imports `common.py` from this folder: `PYTHONPATH=analysis`). `out/RESULTS_SUMMARY.md` is the narrative summary of all results. `make_scorecards.py` runs on `results/` alone and writes `results/scorecards/`. `stage_release.py` records how `results/`, `reruns/` and `transport/` were derived from the working tree (quotes cut at 25 words, path scrubbing, exclusions). The statistics that need the withheld gold scores (ABC, BetterBench) can be regenerated only from the sources; see the repository README.
