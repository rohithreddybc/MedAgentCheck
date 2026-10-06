# Score card: ehr-robustgym

Pinned: arXiv 2609.39371v1; repo - at -; accessed 2026-10-05T06:09:17Z; packet sha256 11dd50d5fbbdaa47.
Cells: 25; not established (fallback to 0): 4; mean final level: 0.74.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2609.39371v1.html:9-10] "Built on MIMIC-IV records containing 365K patients, 31 tables, and over 500M records" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:133-135] "released through PhysioNet for research under credentialed access" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:41-45] "The test set is balanced across two query scopes (504 pairs each) and three Noise types (336 pairs each)." |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:41-45] "Patient-level tasks use disjoint patient identifiers across training and test sets" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:41-45] "Condition labels, pairing information, reference SQL, and reference answers are hidden from the agent" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:109-112] "GPT-5.2 (high) ( OpenAI, 2025b ) performs this verification." |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:38-40] "We retain a pair only when both reference SQL queries execute successfully" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:44-59] "Abstention Validity requires NULL and visible evidence from tool calls" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | not_established | 0 | codex 2/2; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:121-124] "Sampling details and per-condition results are provided in Appendix" |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:121-124] "Pass@ k measures the fraction of questions solved by at least one of k attempts" |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2609.39371v1.html:121-124] "GPT-5.4 reaches 82.4% Pass@4 but only 44.5% pass^4" |
| A4 Model and harness pinning (a/e). | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| A5 Tool contract specified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:44-59] "Answer Match checks the requested values, units, and associated records" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:41-45] "reference SQL, and reference answers are hidden from the agent" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.39371v1.html:44-59] "Clean / Noise success rates (Pass@1, %, \uparrow )." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2609.39371v1.html:133-135] "privacy-preserving processing, including removal of protected health information, random identifier replacement, and patient-level date shifting" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
