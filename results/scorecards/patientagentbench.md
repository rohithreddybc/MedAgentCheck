# Score card: patientagentbench

Pinned: arXiv 2607.25485v1; repo https://github.com/amazon-science/PatientAgentBench at c9bfa1b57253d731582cb64da4e9dfe6fe633f15; accessed 2026-10-05T06:13:02Z; packet sha256 85c030b8af76f81a.
Cells: 25; not established (fallback to 0): 4; mean final level: 1.00.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:210-213] "All patient profiles, clinical narratives, and conversations are fully synthetic; no real patient health information or personally identifiable information is used" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:72-76] "the attribute distributions in Table 2 calculated directly over these generated entries" |
| C4 Safety and bias tests | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:209-209] "our disaggregated analysis (Section 5.4 ) surfaces small but directionally consistent gaps" |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:102-103] "there is no fixed answer key to memorize" |
| C6 Agent isolated from gold | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:95-95] "the assistant does not receive the patient story, the underlying task, or the personality traits" |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:102-103] "no per-scenario answer key" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:187-190] "Adjacent agreement ( \pm 1) ranged from 79% to 93% across all dimensions" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:163-202] "`--seed`, `-s` / Random seed for reproducibility / None" |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:141-142] "three statistically distinct performance tiers emerge from the aggregate scores, separated by gaps with non-overlapping confidence intervals" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:124-128] "Each model was evaluated on all 1,200 benchmark scenarios" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:129-140] "Per-model results across six dimensions for the 10 baseline foundation models (N=1,200 conversations per model" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:89-91] "structured natural-language specification of its purpose, required and optional parameters, return format, and behavioral preconditions" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:tests/test_prescription_tools.py:331-367] "Test that refill output contains confirmation, pickup timeline, and pharmacy." |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:84-88] "scheduling an appointment marks a slot as unavailable" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:155-157] "Surfacing such mismatches requires inspecting the full tool trace" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.25485v1.html:95-95] "the assistant does not receive the patient story, the underlying task, or the personality traits" |
| A10 Slice reporting (g). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.25485v1.html:183-183] "Personality type is the strongest performance driver across all benchmark attributes." |
| A11 Environment-state provenance (h). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
