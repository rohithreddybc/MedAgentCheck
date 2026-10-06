# Score card: clinicare-bench

Pinned: arXiv 2608.07796v1; repo - at -; accessed 2026-10-05T06:08:04Z; packet sha256 3fb808d1ce2a3f60.
Cells: 25; not established (fallback to 0): 3; mean final level: 1.04.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.07796v1.html:63-70] "CliniCARE-Bench is constructed on top of three datasets from the MIMIC-IV database: the core MIMIC-IV v3.1, MIMIC-IV-Note v2.2, and MIMIC-IV-ED v2.2" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:120-122] "credentialed PhysioNet users who completed the required training and executed the PhysioNet Credentialed Health Data Use Agreement" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:116-119] "We sample 30 patients per scenario using stratification across Yes , No , and Indeterminate candidate strata" |
| C4 Safety and bias tests | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:394-396] "The patient-linked artifacts, which are derived from MIMIC-IV, will be made available on PhysioNet under its credentialed access policy" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:189-193] "MIMIC data is reached only through a credential-isolated tool server, so no system can bypass the governed tools to read raw records." |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:63-70] "MIMIC-IV v3.1, MIMIC-IV-Note v2.2, and MIMIC-IV-ED v2.2" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:123-124] "two clinicians independently vetted every scenario" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:131-140] "Verdicts are scored by exact four-class match, with no partial credit." |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.07796v1.html:380-382] "they agree on 97.9% of 1,331 category decisions" |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.07796v1.html:329-335] "only 11 reach p<0.05 under a two-sided exact McNemar test and none survives Holm correction" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:127-130] "In our primary protocol each case is run once" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:364-369] "Accuracy differs by at most 4.1 points (exact McNemar p\geq 0.46 )" |
| A3 Action-level repeat-run reliability (a). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.07796v1.html:347-356] "Each system has three independent attempts on all 148 cases." |
| A4 Model and harness pinning (a/e). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:78-81] "SQL Fallback: A capped, read-only SQL interface" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:78-81] "Parameterized, clinician-verified tools which support common record-retrieval operations across the MIMIC database" |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:127-130] "Each run produces a final report, a logged sequence of tool calls, the retrieved patient and policy evidence" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:189-193] "run with web search and fetch disabled" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.07796v1.html:525-534] "Verdict accuracy (%) per scenario, all 16 systems." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.07796v1.html:63-70] "retrospective, de-identified records from the inpatient, intensive-care, and emergency departments of a single major academic medical center" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
