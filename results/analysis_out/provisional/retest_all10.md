# Retest on all 10 drawn benchmarks (Claude coder)

**PROVISIONAL: Claude coder only (sonnet), intra-coder original vs retest, not resolved.**

Why `agentaudit retest --compare-only` matched 8 of 10: `plan_retest` maps each frozen id to a packet directory with `bench_dir_candidates` (`scorer/agentaudit/perturb.py`), which tries `safe_name(id)`, `safe_name(benchmark_name)` and its lower case. For `arxiv:2510.24654` (DiagGym/DiagBench) and `arxiv:2609.30027` (Synthetic Hospital) those slugs are `diaggym_diagbench` and `synthetic_hospital` (underscores). The packet, coding, scoring and retest directories are `diaggym-diagbench` and `synthetic-hospital` (hyphens, the manifest `name`). So `packet_dir` is null for both and they drop out of `compare_retest`. No files are missing; the retest coding for both exists (25 cells each). Frozen code was not edited.

`analysis/provisional_retest_all10.py` maps ids through `audit/manifests/*.yaml` and reuses the frozen statistics read-only.

All 10 benchmarks: 250 cells, 243 applicable in both runs, 0 NA mismatches. Raw agreement 0.960 (Wilson 95% 0.928-0.978; 240 of 250 exact). Ordinal alpha 0.947 (bootstrap over benchmarks, 2000 draws, seed 20261004, 95% 0.916-0.975). Quadratic weighted kappa 0.944. The 8-benchmark frozen output was raw 0.960, alpha 0.951 (0.924-0.980). Per-benchmark raw agreement is in `retest_all10_per_benchmark.csv` (0.92 to 1.00).
