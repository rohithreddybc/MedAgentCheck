# Score card: medagentbench-v1

Pinned: arXiv 2501.14654v2; repo https://github.com/stanfordmlgroup/MedAgentBench at 99260117137b09f04837a8c18d18a1107efa55ae; accessed 2026-10-05T06:10:57Z; packet sha256 7cb4fa0e85a3b620.
Cells: 25; not established (fallback to 0): 2; mean final level: 0.52.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:33-47] "patient profiles are extracted from a deidentified clinical data warehouse curated by the STARR" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:33-47] "patient profiles are extracted from a deidentified clinical data warehouse curated by the STARR" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:33-47] "The characteristics of the cohort are summarized in Table 2 ." |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:configs/tasks/medagentbench.yaml:1-13] "data_file: "data/medagentbench/test_data_v2.json"" |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2501.14654v2.html:66-69] "We set the temperature to zero for all models except o3-mini." |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:66-69] "we exclusively adopt pass@1 in our benchmark" |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:66-69] "We set the temperature to zero for all models except o3-mini." |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:69-70] "These functions are defined as JSON schemas which are manually translated based on FHIR API documentation." |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:69-70] "we conduct a simple sanity check to make sure the payload data is JSON-loadable" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:61-65] "For action-based tasks, we manually write many rule-based sanity checks" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:69-70] "If the agent system invokes a finish request, we save the entire conversation for grading purpose." |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:75-91] "half (150) only require information retrieval via GET requests" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2501.14654v2.html:33-47] "Benchmark examples are based on real patient cases that were deidentified and jittered." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
