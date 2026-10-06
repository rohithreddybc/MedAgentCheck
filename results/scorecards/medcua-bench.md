# Score card: medcua-bench

Pinned: arXiv 2606.03203v1; repo - at -; accessed 2026-10-05T06:11:38Z; packet sha256 a7d1d7f8ba599d12.
Cells: 25; not established (fallback to 0): 7; mean final level: 0.64.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:213-218] "The 18 scenarios cover 10 medical domains and three page-fidelity tiers." |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.03203v1.html:115-117] "MedCUA-Bench contains no real patient information" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:241-245] "intentionally diverse in age, sex and comorbidity profile" |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:48-53] "Violations are assigned to five dimensions: patient identity, data accuracy, information fidelity, record integrity, and workflow safety." |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:43-46] "These traces are hidden from the agent and are consulted only by the deterministic checker" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:36-39] "One scenario runs OpenEMR v7.0.2" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:385-390] "A single trained operator drove a fresh Chromium 1280\times 800 session" |
| C9 Out-of-scope side effects detectable | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:48-53] "the checker compares the final page state, the agent’s final message, request traces, and navigation traces against the expected values" |
| C11 Trivial-agent result | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:51-61] "Each model runs all 432 task instances once" |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:350-353] "default sampling parameters" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:43-46] "The action space follows the BrowserGym pixel interface and is restricted to low-level operations" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:43-46] "including method, URL, and payload" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:48-53] "the checker compares the final page state, the agent’s final message, request traces, and navigation traces against the expected values" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:213-218] "Each scenario contributes 12 base tasks split across easy/medium/hard difficulty bands" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.03203v1.html:115-117] "the OpenEMR tier is seeded with five synthetic demonstration patients" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
