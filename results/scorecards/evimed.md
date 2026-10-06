# Score card: evimed

Pinned: arXiv 2601.19773v1; repo https://github.com/nanshine/EID-Benchmark at 7b6da74dfdcffc4f87e3e7ff37a09e33b821cb57; accessed 2026-10-05T06:09:27Z; packet sha256 47bebd2e375feae6.
Cells: 25; not established (fallback to 0): 6; mean final level: 0.42.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:171-176] "EviMed-1K integrates five complementary sources that cover general medicine, specialty diagnosis, complex multi-specialty reasoning, rare diseases, and real-world clinical records." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:180-186] "ClinicalBench yan2024clinicallab is derived from de-identified electronic medical records with both structured and unstructured content." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:180-186] "we sample 200 distinct diseases using a frequency-stratified scheme." |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:135-148] "we compare the diagnostic Success Rate of the original case descriptions against the concatenated constructed evidences in a static evaluation." |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:162-170] "Both the simulated patient and the simulated reporter operate with a context window of 1 and a temperature of 0" |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:162-170] "temperature of 0, resulting in stateless behavior with respect to dialogue history and deterministic decoding across all experiments." |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:162-170] "Both the simulated patient and the simulated reporter operate with a context window of 1 and a temperature of 0" |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:21-25] "the simulated patient and the simulated reporter return information grounded in the case record." |
| A7 Write-action disclosure (d). | 0 | na_rejected_as_zero | 0 | codex NA/NA; sonnet 1/1 |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:171-176] "We use an LLM judge to score each of the five items against the reference diagnosis using a three-level rubric." |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.19773v1.html:44-54] "Table 1 summarizes the benchmark statistics, including the average number of patient evidences and examination evidences per case in each source dataset." |
| A11 Environment-state provenance (h). | 0 | not_established | 1 | codex 1/1; sonnet 1/0 |  |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
