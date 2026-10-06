# Score card: synthetic-hospital

Pinned: arXiv 2609.30027v1; repo https://github.com/sparkcpark/synthetic_hospital at 911f34c4ac65a508543c4b3b90c373a0cd16534d; accessed 2026-10-05T06:13:51Z; packet sha256 9efcd297336dac19.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.83.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:18-20] "We ingest USMLE-style board questions and supplementary medical knowledge from flashcard decks and reference documents." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:10-10] "Synthetic Hospital is built entirely from publicly available medical-education material containing no protected health information." |
| C3 Representativeness | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:291-296] "Synthetic Hospital closely matches the ICD-10 chapter distribution of its source corpus" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2609.30027v1.html:27-28] "no chart or source material crosses split boundaries" |
| C6 Agent isolated from gold | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S2:harbor/README.md:29-56] "postgres and redis are on an internal network the agent container is not attached to" |
| C7 Frozen environment | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S3:github/releases:1-2] "Synthetic Hospital v1.3 (tag v1.3, published 2026-09-25T12:44:31Z)" |
| C8 Oracle solver | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:183-206] "a malformed or empty submission scores 0 rather than raising" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2609.30027v1.html:49-49] "The graph recovered 111 of the 119 relationships (93%)" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:224-247] "`reset(task=, split=, seed=)` samples deterministically" |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:69-73] "range across physicians / 0.21–0.89" |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:204-225] "obs.tools (function schemas)" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:25-27] "The completed records are served through a production-style clinical environment" |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:183-206] "Rewards are the tasks' primary metrics" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:204-225] "Assessment and plan sections are stripped from every observation" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.30027v1.html:35-40] "For each task, we report the standardized input, expected output, primary evaluation metric" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S2:README.md:283-289] "The released data files are fully synthetic and redistributable" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
