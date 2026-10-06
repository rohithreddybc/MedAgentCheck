# Score card: codeclinic

Pinned: arXiv 2605.09675v1; repo https://github.com/tossowski/CodeClinic at 784f1203945e946b9d6c836a49c50a63822e7280; accessed 2026-10-05T06:08:18Z; packet sha256 43774935fb924d5c.
Cells: 25; not established (fallback to 0): 4; mean final level: 0.74.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S2:mimic-iv/buildmimic/duckdb/README.md:42-104] "These instructions were tested with MIMIC-IV v2.2." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:453-487] "This codebase requires access to [MIMIC-IV](https://mimic.mit.edu/), a de-identified clinical database." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:36-40] "sampled with a stratification which preserves the natural mix of ICU patients" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:56-58] "the remaining 90% is the held-out test set" |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:mimic-iv/buildmimic/duckdb/README.md:42-104] "These instructions were tested with MIMIC-IV v2.2." |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:74-78] "a single error anywhere in the 13-step horizon counts as a full failure" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:tests/README.md:1-31] "can validate the pipeline end-to-end against the public MIMIC-IV demo" |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/1; sonnet 1/0 |  |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09675v1.html:106-108] "Error bars: 95% bootstrapped interval across 2000 resamples." |
| A1 Run count per reported number (e). | 0 | not_established | 1 | codex 1/1; sonnet 1/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:106-108] "Error bars: 95% bootstrapped interval across 2000 resamples." |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:tests/README.md:1-31] "Real concept SQL + session tooling against a built MIMIC-IV demo DuckDB." |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:74-78] "answers are judged by exact match with 1% tolerance" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:33-36] "strict visibility constraints that limit it to data available up to the current checkpoint" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09675v1.html:93-102] "Table 2 reports accuracy across 63 concepts by difficulty level." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S2:README.md:453-487] "This codebase requires access to [MIMIC-IV](https://mimic.mit.edu/), a de-identified clinical database." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
