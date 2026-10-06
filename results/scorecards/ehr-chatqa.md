# Score card: ehr-chatqa

Pinned: arXiv 2509.23415v2; repo https://github.com/glee4810/EHR-ChatQA at 8b97b9a303ce601690224435c3aa54dab19c4d00; accessed 2026-10-05T06:09:04Z; packet sha256 c72bfae2d27b4c2d.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.65.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:43-51] "we use two publicly available EHR databases with distinct schemas and data recording practices: MIMIC-IV" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:90-92] "EHR-ChatQA utilizes publicly available, de-identified EHR datasets (MIMIC-IV-demo and eICU-demo)" |
| C3 Representativeness | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:52-54] "we rename all table and column names" |
| C6 Agent isolated from gold | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:1-53] "Two environments are included:" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:202-204] "we manually verify that the SQL execution produces the intended result" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:180-184] "We compare the resulting output to the ground truth (GT) SQL output" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| C13 Non-determinism safeguards | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.23415v2.html:61-65] "The temperature for all agent LLMs is set to 0.0" |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.23415v2.html:65-68] "We set k=5 throughout the experiments." |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:61-65] "The temperature for all agent LLMs is set to 0.0" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:src/envs/mimic_iv_star/tools/sql_execute.py:39-67] "Execute a SQL query against the database and get back the result." |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:184-188] "correctness is evaluated based on the content within the <answer></answer> tags" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:43-51] "Table 2: EHR-ChatQA task statistics." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.23415v2.html:90-92] "publicly available, de-identified EHR datasets (MIMIC-IV-demo and eICU-demo)" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
