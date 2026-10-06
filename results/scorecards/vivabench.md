# Score card: vivabench

Pinned: arXiv 2510.10278v1; repo - at -; accessed 2026-10-05T06:13:57Z; packet sha256 8febce06cdd40fe2.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.83.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:41-44] "Each entry includes a unique identifier ( uid ), source information, free-text clinical vignette , diagnosis with differentials" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:36-37] "we sourced clinical vignettes exclusively from publicly available repositories" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:210-213] "VivaBench consists of 990 cases across nine specialty groups" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:218-226] "Generated sentences exhibited consistently low textual similarity to the original second sentences" |
| C6 Agent isolated from gold | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:214-218] "4 clinicians provided a provisional diagnosis based on the clinical picture over 14 unseen cases" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2510.10278v1.html:271-273] "we evaluated their precision (Pr) and recall (Rc) in mapping free-text queries to the correct structured information keys" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2510.10278v1.html:49-55] "Each model was tested at temperature 0" |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:214-218] "0.68 ± 0.09 top-3 accuracy versus 0.52 ± 0.07" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:86-93] "we conducted only a single evaluation run for each model" |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:274-277] "100 distinct queries were each submitted 10 times" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:280-283] "Each model was accessed through OpenRouter [ 4 ] and tested at temperature = 0" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:300-308] "Available actions: history : Interview the patient directly." |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:271-273] "we evaluated their precision (Pr) and recall (Rc) in mapping free-text queries" |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2510.10278v1.html:284-288] "Category-specific request limits were also enforced: 10 for history" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:289-290] "The complete output trace for each model interaction—including all queries, retrieved information" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:240-240] "strictly adhering to the information boundaries established by the deterministic parsing logic" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:65-68] "Subgroup analysis demonstrated variation in model performance across different specialty groups" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2510.10278v1.html:183-184] "PubMed case reports were selected as the primary source" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
