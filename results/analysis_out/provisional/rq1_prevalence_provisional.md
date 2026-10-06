# Provisional RQ1 prevalence (Claude coder)

**PROVISIONAL: Claude coder only, not resolved.** Coder: sonnet (claude-sonnet-5-5 via Claude Code subagent), effective level after quote verification, 44 coded benchmarks (the 45th frozen-list packet has no coding), 25 items each (14 core C1-C14, 11 agent A1-A11). NA cells leave the denominator. No second coder, no resolution, no adjudication: the codex coder exists but is not used here, so these shares are one model's reading and cannot be called resolved. Per-item Wilson intervals treat benchmarks as independent.

## Module aggregates (pooled applicable cells; bootstrap over benchmarks, seed 20261004, 2000 draws)

| Metric | Agent module | Core module | Agent minus core |
|---|---|---|---|
| Share reported (level >= 1) | 72.1% (95% bootstrap 67.0%-76.8%) | 64.2% (95% bootstrap 59.3%-69.6%) | 7.8% (95% bootstrap 2.5%-13.2%) |
| Share fully reported (level 2) | 10.7% (95% bootstrap 7.6%-13.9%) | 11.7% (95% bootstrap 8.8%-15.0%) | -1.0% (95% bootstrap -4.2%-2.3%) |
| Mean level (0-2) | 0.83 (0.76-0.89) | 0.76 (0.69-0.84) | 0.07 (0.00-0.13) |

Contradiction flags: 16 in total (11 on agent items, 5 on core items); candidate findings only, not verified against benchmark documentation or sent for right of reply.

## Per item

| Item | Module | n | >=1 (Wilson 95%) | =2 (Wilson 95%) | mean | contradiction flags (verified) |
|---|---|---|---|---|---|---|
| C1 Traceability | core | 44 | 95% (85%-99%) | 18% (10%-32%) | 1.14 | 0 (0) |
| C2 Provenance and licence | core | 44 | 98% (88%-100%) | 20% (11%-35%) | 1.18 | 0 (0) |
| C3 Representativeness | core | 44 | 86% (73%-94%) | 0% (0%-8%) | 0.86 | 0 (0) |
| C4 Safety and bias tests | core | 44 | 36% (24%-51%) | 5% (1%-15%) | 0.41 | 0 (0) |
| C5 Contamination controls | core | 44 | 57% (42%-70%) | 7% (2%-18%) | 0.64 | 0 (0) |
| C6 Agent isolated from gold | core | 44 | 61% (47%-74%) | 20% (11%-35%) | 0.82 | 2 (2) |
| C7 Frozen environment | core | 44 | 82% (68%-90%) | 2% (0%-12%) | 0.84 | 2 (2) |
| C8 Oracle solver | core | 44 | 64% (49%-76%) | 2% (0%-12%) | 0.66 | 0 (0) |
| C9 Out-of-scope side effects detectable | core | 18 | 39% (20%-61%) | 0% (0%-18%) | 0.39 | 0 (0) |
| C10 Trivial success unlikely | core | 44 | 52% (38%-66%) | 2% (0%-12%) | 0.55 | 0 (0) |
| C11 Trivial-agent result | core | 44 | 2% (0%-12%) | 0% (0%-8%) | 0.02 | 0 (0) |
| C12 Evaluator validated | core | 44 | 66% (51%-78%) | 41% (28%-56%) | 1.07 | 0 (0) |
| C13 Non-determinism safeguards | core | 44 | 75% (61%-85%) | 14% (6%-27%) | 0.89 | 1 (1) |
| C14 Statistical comparison | core | 44 | 70% (56%-82%) | 25% (15%-39%) | 0.95 | 0 (0) |
| A1 Run count per reported number (e). | agent | 44 | 57% (42%-70%) | 11% (5%-24%) | 0.68 | 0 (0) |
| A2 Uncertainty with stated resampling unit (e). | agent | 44 | 50% (36%-64%) | 2% (0%-12%) | 0.52 | 0 (0) |
| A3 Action-level repeat-run reliability (a). | agent | 44 | 27% (16%-42%) | 14% (6%-27%) | 0.41 | 0 (0) |
| A4 Model and harness pinning (a/e). | agent | 44 | 50% (36%-64%) | 0% (0%-8%) | 0.50 | 5 (5) |
| A5 Tool contract specified (b). | agent | 43 | 91% (78%-96%) | 12% (5%-24%) | 1.02 | 2 (2) |
| A6 Tool contract verified (b). | agent | 43 | 74% (60%-85%) | 0% (0%-8%) | 0.74 | 2 (2) |
| A7 Write-action disclosure (d). | agent | 31 | 100% (89%-100%) | 39% (24%-56%) | 1.39 | 0 (0) |
| A8 Grader reads state, or justifies transcript grading (c). | agent | 44 | 98% (88%-100%) | 9% (4%-21%) | 1.07 | 0 (0) |
| A9 Agent-channel contamination (f). | agent | 44 | 73% (58%-84%) | 0% (0%-8%) | 0.73 | 2 (2) |
| A10 Slice reporting (g). | agent | 44 | 91% (79%-96%) | 5% (1%-15%) | 0.95 | 0 (0) |
| A11 Environment-state provenance (h). | agent | 44 | 91% (79%-96%) | 34% (22%-49%) | 1.25 | 0 (0) |
