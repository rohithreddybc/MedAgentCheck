# Score card: ehr-complex

Pinned: arXiv 2606.23301v1; repo - at -; accessed 2026-10-05T06:09:10Z; packet sha256 68a3819a1643d574.
Cells: 25; not established (fallback to 0): 4; mean final level: 0.87.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.23301v1.html:127-131] "EHR-Complex is built on MIMIC-IV v3.1" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:156-160] "MIMIC-IV is derived from routine clinical records at Beth Israel Deaconess Medical Center" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:127-131] "single hospital system, including its EHR schema, ICU information system, coding conventions, patient population" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:123-127] "from the training set (with no test overlap)" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:168-174] "The SQL and verified answer are never exposed to the model during inference" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:127-131] "EHR-Complex is built on MIMIC-IV v3.1" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:72-75] "all validated by execution" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| C13 Non-determinism safeguards | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.23301v1.html:97-103] "All runs use a temperature of 0" |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2606.23301v1.html:97-103] "All runs use a temperature of 0" |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.23301v1.html:314-330] "Pass^k (temperature=0.0) measures the proportion of tasks where all k runs are correct" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:168-174] "Except for the Pass@k ablations, evaluation uses temperature 0.0." |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:168-174] "submit intermediate tool calls as valid JSON" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:40-47] "where y denotes the final answer extracted from trajectory" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:168-174] "The SQL and verified answer are never exposed to the model during inference" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.23301v1.html:76-88] "Table 3: Evaluation Results on the EHR-Complex Test Set." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.23301v1.html:156-160] "MIMIC-IV v3.1, a large-scale de-identified EHR database" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
