# Score card: medflowbench

Pinned: arXiv 2603.24649v2; repo - at -; accessed 2026-10-05T06:11:52Z; packet sha256 d1573ac7731b511d.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.52.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:154-154] "Domain Source Input unit #Cases Primary task Evidence / Strict scoring Localization scoring Radiology LUMIERE [ 54 ] BASELINE/FOLLOWUP brain MRI 139" |
| C2 Provenance and licence | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C3 Representativeness | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:10-11] "with deterministic rules using withheld ground-truth masks, annotations, or labels." |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:10-11] "using withheld ground-truth masks, annotations, or labels." |
| C7 Frozen environment | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:40-44] "Evidence gates are deterministic and may use key-slice offsets, source-series provenance, lesion-status fields, RAS points, or WSI coordinates" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2603.24649v2.html:190-192] "only 3 of 10 runs complete this functional sequence." |
| A4 Model and harness pinning (a/e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:220-225] "The released schemas contain the exact JSON definitions used at runtime." |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:25-26] "Analysis Operators invoke functions that create derived study state, such as segmentation, registration, resampling, quantitative analysis, or automated expert-model outputs." |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:225-230] "stores the instantiated prompt, image attachments, tool-call arguments, tool outputs, viewer states, screenshots, generated artifacts, and final answer" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:10-11] "deterministic rules using withheld ground-truth masks, annotations, or labels." |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2603.24649v2.html:156-158] "The reported case counts correspond to the benchmark-eligible units used for evaluation." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2603.24649v2.html:229-240] "UCSF-PDGM / Dataset / CC BY 4.0 via TCIA; subject to TCIA Data Usage Policy and Restrictions." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
