# Addendum (post hoc, written before any coding): validation of the agent items without new human labels

Date: 2026-10-14. Status: fixed before the coders are run, and it never changes the frozen protocol. Every result it produces is reported as post hoc.

## Why this addendum exists

Reviewers asked for expert labels for A1-A11 and for a specificity estimate against negatives that are established independently of the coders. No new human coding is possible (author ruling 2026-10-06). Both requests can be met with references that already exist outside the coders:

- **Design facts.** A benchmark with no action interface cannot report an agent-specific property.
- **Published expert labels.** These exist for adjacent constructs: ABC (all 42 items, 10 agentic benchmarks) and BetterBench (all 46 criteria, 23 benchmarks). The files are in research/gold/.

## Material

The 31 gold packets already built are coded with the unchanged audit prompt: all 25 MedAgentCheck items, the frozen scorer, both coder families, quote verification and the resolved rule. They are 22 BetterBench packets (audit/gold_bb/gold-betterbench/packets) and 9 ABC packets (audit/gold_abc/gold-abc/packets).

## Study 1: known-groups specificity

Negative group N. These benchmarks are static, with no action interface; under eligibility condition E2 they are not agent benchmarks. The assignment follows the task format stated in each benchmark's own paper. N has 13 benchmarks:

> ARC-Challenge, BBQ, BOLD, DecodingTrust, GPQA, GSM8k, HellaSwag, HumanEval, MedMNIST_v2, MLCommons_AI_Safety_v0.5, MMLU, TruthfulQA, WinoGrande.

Positive group P. These benchmarks have an action interface. P has 10 benchmarks:

> the 9 ABC benchmarks (BIRD-Bench, GAIA, KernelBench, MLE-bench, OSWorld, SWE-Lancer, SWE-bench_Verified, WebArena, tau-bench) and AgentBench.

Excluded as ambiguous: the remaining BetterBench packets, which are RL or simulation environments without LLM tool calls or are not clearly static. They are ALE, FinRL-Meta, Machiavelli, PDEBench, Procgen, RL_Unplugged, SafeBench and Wordcraft.

Items tested. These are the six items that require an action interface: A3 (repeat-run reliability of actions), A5 (tool contract specified), A6 (tool contract verified), A7 (write-action disclosure), A9 (agent-channel contamination) and A11 (environment-state provenance). A1, A2, A4, A8 and A10 apply to any benchmark and are not tested.

Ground truth. For N x {A3, A5, A6, A7, A9, A11}, the correct score is NA or 0. That makes 78 cells.

Primary outcome. The false-credit rate is the share of these 78 cells with a level of 1 or more. It is reported:
- per coder (verified scores) and for the resolved level;
- with a Wilson 95% interval and a bootstrap interval over the 13 benchmarks (2,000 resamples, seed 20261004).

Specificity on construct-absent documentation is 1 minus that rate. These negatives are easy: the construct is absent from the whole document. The estimate is therefore an upper bound for documentation in which the construct is partly present. That caveat is stated wherever the number appears.

Secondary outcome (known-groups contrast). This is the share of cells credited at level 1 or more in P minus that share in N, on the same six items, with a bootstrap interval over benchmarks. It is reported per coder and resolved.

## Study 2: convergence with published expert labels on adjacent constructs

The mapping is fixed here, taken from the crosswalk (Supplementary Table S15, "nearest existing items"). The mapped items are adjacent, not equivalent, so the expected association is moderate at most.

| Agent item | BetterBench criteria (BB benchmarks) | ABC items (ABC benchmarks) |
|---|---|---|
| A1, A2 (e) | J.3-17 | R.10 |
| A3 (a) | J.3-17 | O.f.2, O.c.1 |
| A5, A6 (b) | none | T.1, T.2, T.3, T.6 |
| A8 (c) | J.1-13 | O.g.1, O.g.2, O.g.3, T.7, T.9, R.13 |
| A9 (f) | J.2-3, J.2-6, J.2-7, J.2-9 | R.3, R.4, T.5 |
| A10 (g) | J.3-14 | none |
| A11 (h) | J.3-8, J.3-11, J.3-12, J.3-13 | T.6 |

Expert reference per cell (benchmark x agent item):
- BetterBench: the mean of the mapped criteria scores rescaled to 0-1 (0, 5, 10, 15 mapped to 0, 1/3, 2/3, 1).
- ABC: the share of mapped items scored 1.
- Expert NA or missing items are dropped.
- A cell with no mapped item is not used.

Statistic. Spearman correlation between the coder level (0-2, verified) and the expert reference, pooled over cells. It is computed per coder and resolved, with a bootstrap interval over benchmarks. As a dichotomous view, it also reports agreement of "coder level >= 1" with "expert reference > 0", with Cohen's kappa. NA coder cells are dropped and counted.

Interpretation fixed in advance:
- A positive association with an interval above 0 is convergent evidence for the agent items' constructs.
- An interval spanning 0 is reported as no evidence of convergence.
- Neither result validates the clinical items on clinical benchmarks.

## Reporting

Both studies are labelled post hoc and reported whatever the result. The release gains the aggregate outputs only. No expert per-cell labels and no benchmark files are redistributed.
