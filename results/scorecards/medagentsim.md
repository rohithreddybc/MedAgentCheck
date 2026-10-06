# Score card: medagentsim

Pinned: arXiv 2503.22678v2; repo https://github.com/MAXNORM8650/MedAgentSim at 6d1409724ca247dc50be1827818f2132a277e68b; accessed 2026-10-05T06:11:22Z; packet sha256 17b97ffe98722300.
Cells: 25; not established (fallback to 0): 6; mean final level: 0.36.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:30-31] "tested across three primary benchmarks: NEJM [ 24 ] , MedQA [ 8 ] , and MIMIC-IV [ 9 ]" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:30-31] "MIMIC-IV features 288 clinical cases, providing a diverse set of real-world medical interactions." |
| C3 Representativeness | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:67-82] "comparing model performance under different cognitive and implicit bias conditions." |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:16-19] "the doctor starts with no prior knowledge of the patient’s condition and need to ask questions" |
| C7 Frozen environment | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 0/0; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:30-31] "accuracy logs were manually reviewed to ensure reliability." |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/0 |  |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:13-15] "requesting imaging results (e.g., MRI, X-Ray) prior to making a diagnosis." |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:30-31] "Model accuracy is evaluated using a binary true/false metric for the final diagnosis" |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:35-48] "Performance of Multi-Agent Clinic (Basic) and MedAgentSim (Our) models across medical benchmarks." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2503.22678v2.html:30-31] "MIMIC-IV features 288 clinical cases, providing a diverse set of real-world medical interactions." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
