# Score card: cp-env

Pinned: arXiv 2512.10206v2; repo https://github.com/SPIRAL-MED/CP_ENV at 6c33121d96baf610c9c5b15bf3429129555e5acb; accessed 2026-10-05T06:08:27Z; packet sha256 5a6cfe49aa484156.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.32.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.10206v2.html:35-38] "We source data from top-tier medical journals containing detailed clinical encounter information Zhu et al. (2025a) ." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.10206v2.html:35-38] "The effectiveness of the agentic hospital relies fundamentally on realistic patient simulation." |
| C3 Representativeness | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.10206v2.html:189-200] "without access to actual laboratory results or final diagnoses" |
| C7 Frozen environment | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C14 Statistical comparison | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:codes/utils/tools.py:40-81] "Fetches the results of a completed diagnostic test from the patient's medical record." |
| A6 Tool contract verified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2512.10206v2.html:46-47] "requiring physician agents to document clinical reports after each patient interaction" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.10206v2.html:48-51] "we systematically collected comprehensive interaction data from LLMs throughout the complete healthcare workflow" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A10 Slice reporting (g). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.10206v2.html:35-38] "with each patient role derived from comprehensive medical records" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
