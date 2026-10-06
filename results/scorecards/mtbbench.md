# Score card: mtbbench

Pinned: arXiv 2511.20490v1; repo https://github.com/bunnelab/mtbbench at ac8151bc7c659a291610f14204e5f67f0bd7b908; accessed 2026-10-05T06:12:44Z; packet sha256 4a2a6814d11a76f1.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.52.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:29-34] "We curated a subset of 26 patient cases from the HANCOCK dataset" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:29-34] "the HANCOCK dataset (CC BY 4.0)" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:29-34] "For each selected patient, an average of 40 modality-specific files are available" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:208-214] "the final set of questions in MTBBench were sent for external manual review by domain specialists" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:92-93] "outcome and recurrence prediction remain the most difficult, with accuracies near random (50%)" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:50-61] "Mean accuracy and 95% confidence intervals of various LLMs by task" |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:90-92] "we sample with replacement from the set of question outcomes per model" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:247-251] "we use the gpt-4o-2024-08-06 checkpoint for gpt4o" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:neurips25/models/agent_with_tools.py:197-220] "To use CONCH you must provide the H&E image name and extension and a list of options" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:250-255] "Model outputs are parsed using regular expressions to extract answers." |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:50-61] "Mean accuracy and 95% confidence intervals of various LLMs by task" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2511.20490v1.html:38-43] "a clinicogenomic resource of cancer patients linking genomic profiles with structured clinical timelines" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
