# Score card: med-inquire

Pinned: arXiv 2601.22964v1; repo https://github.com/yf-he/EvoClinician at d9bd3f4b70d77cac7336049a2f1f0a135f1410cc; accessed 2026-10-05T06:10:49Z; packet sha256 591cd95ce169ed2e.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.46.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:101-108] "The patient cases come from DiagnosisArena ( Zhu et al., 2025 )" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:101-108] "a collection of 915 real-world medical cases taken from reports published in 10 major medical journals" |
| C3 Representativeness | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2601.22964v1.html:51-58] "The agent does not receive the hidden case file or the ground-truth diagnosis information." |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:211-217] "If any component uses randomness" |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:97-102] "Shaded bands show an approximate 95\% interval based on the running standard error" |
| A1 Run count per reported number (e). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:97-102] "computed from the first t cases" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:218-227] "one simple option is JSON with two fields: action_type and action_text" |
| A6 Tool contract verified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2601.22964v1.html:141-143] "actively gather information through sequential questions and test orders" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:69-76] "the final Judge score S_{i} , and the total cost C_{i}" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:248-261] "the query text for retrieval should be derived only from the dialogue history up to turn t" |
| A10 Slice reporting (g). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.22964v1.html:101-108] "915 real-world medical cases taken from reports published in 10 major medical journals" |

## Contradiction flags (candidates only)
- C6 (codex): [S1:arxiv/2601.22964v1.html:51-58] "The agent does not receive the hidden case file or the ground-truth diagnosis information." / [S1:arxiv/2601.22964v1.html:51-58] "The agent does not receive the hidden case file or the ground-truth diagnosis information." / [S4:evoclinician/med_inquire/env.py:103-133] "f"GROUND TRUTH DIAGNOSIS:\n{case.ground_truth_diagnosis}\n""
- A9 (sonnet): [S1:arxiv/2601.22964v1.html:91-96] "the Evolver does not add rules that mention case-specific identifiers" / [S1:arxiv/2601.22964v1.html:91-96] "the Evolver does not add rules that mention case-specific identifiers" / [S4:evoclinician/agents/evolver.py:1-52] "f"{entry.action_content}. Rationale: {entry.rationale}""
