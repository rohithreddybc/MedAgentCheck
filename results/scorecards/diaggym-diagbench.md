# Score card: diaggym-diagbench

Pinned: arXiv 2510.24654v2; repo https://github.com/MAGIC-AI4Med/DiagGym at bc497195e57690bd73381d6114b3a307108a8c91; accessed 2026-10-05T06:08:47Z; packet sha256 44841e200e698b35.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.80.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:91-100] "Domain / Source Dataset / Access / Clinical Setting / # Cases / # Rubrics" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:279-285] "Due to licensing restrictions, we are unable to directly open-source the dataset." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:89-90] "covering multi-source patient distributions, including global case reports, outpatient records, and synthesized differential diagnosis cases" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:246-252] "we strictly selected case reports published after January 2025." |
| C6 Agent isolated from gold | 0 | not_established | 1 | codex 1/1; sonnet 1/0 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:91-100] "referenced multi-turn diagnostic trajectory : a physician-curated sequence extracted from real EHR records" |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 1/1; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2510.24654v2.html:383-387] "the LLM judge demonstrated high reliability across all metrics." |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:DiagAgent/eval/single_turn/metric_accuracy.py:1-54] "def workflow(messages, model="gpt-4o", temperature=0.0, max_tokens=1024):" |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2510.24654v2.html:110-114] "Error bars show 95% confidence intervals." |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:278-278] "We implement zero-shot inference for most settings, with the sole exception of prompt 8 ." |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:150-164] "All metrics are reported with 95% Confidence Intervals" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:49-51] "GPT-4o, version gpt-4o-2024-08-06" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:719-730] "If more information is needed:" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:371-374] "we instruct GPT-4o employing Prompt 10 to count the number of examination names" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:103-105] "diagnostic agents continually interact with the environment and sequentially propose examination queries" |
| A8 Grader reads state, or justifies transcript grading (c). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:246-252] "To rigorously prevent data leakage and assess generalization on unseen data" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.24654v2.html:91-100] "The benchmark spans one in-domain center and three out-of-domain (OOD) centers." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S2:README.md:23-36] "Researchers with valid [CITI certification](https://physionet.org/content/mimiciv/view-required-training/3.1/#1) may also contact the authors directly for immediate access." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
