# Score card: openhospital

Pinned: arXiv 2603.14771v3; repo https://github.com/ZJU-LLMs/Agent-Kernel at c14b6e59ab6df517238ae64e9a9b0ac1a7bb3be7; accessed 2026-10-05T06:12:53Z; packet sha256 f8eaa7721851f03d.
Cells: 25; not established (fallback to 0): 8; mean final level: 0.44.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:21-24] "583 distinct diseases and 467 binary comorbidities across 19 clinical departments" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2603.14771v3.html:90-97] "OpenHospital is constructed entirely using synthetic data" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:34-36] "Self-BLEU4 score of 0.4111 and a TF-IDF diversity score of 0.8727" |
| C4 Safety and bias tests | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C5 Contamination controls | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:44-47] "objective diagnoses and examination reports remain hidden" |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:53-59] "this metric penalizes unnecessary tests while rewarding the prioritization of informative examinations" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:74-79] "This downward trend is highly significant" |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:68-75] "Qwen/Qwen3-Next-80B-A3B-Instruct model ( Yang et al., 2025 )" |
| A5 Tool contract specified (b). | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S2:demo/OpenHospital/README.md:172-202] "`SCHEDULE_EXAMINATION`: used to evaluate examination rationality" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:demo/OpenHospital/README.md:172-202] "`LLM_INFERENCE`: used to count prompt tokens" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:62-68] "partitioned into training and test sets at a 9:1 ratio" |
| A10 Slice reporting (g). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.14771v3.html:21-24] "a multi-stage data synthesis pipeline powered by DeepSeek-v3.1 model" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
