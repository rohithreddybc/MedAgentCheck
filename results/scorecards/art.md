# Score card: art

Pinned: arXiv 2601.08988v1; repo - at -; accessed 2026-10-05T06:07:35Z; packet sha256 736152b09a23dc3f.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.44.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:37-41] "From EHR observation data (50,000 records of 695 patients), we extracted scenarios matching each of the failure modes." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:37-41] "Tasks are synthesized by extracting real patient scenarios (e.g., MRN, timestamps, demographics, lab results) from the EHR database" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:37-41] "From EHR observation data (50,000 records of 695 patients), we extracted scenarios matching each of the failure modes." |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Models operate in stateless mode (temperature=0, no conversation history) to prevent memorization effects." |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Models operate in stateless mode (temperature=0, no conversation history) to prevent memorization effects." |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Models operate in stateless mode (temperature=0, no conversation history) to prevent memorization effects." |
| A5 Tool contract specified (b). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:27-30] "POST {fhir_api_base} MedicationRequest" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Each task is scored by exact-match comparison against ground-truth values computed from the EHR database." |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Models operate in stateless mode (temperature=0, no conversation history) to prevent memorization effects." |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:58-63] "Success Rate (SR, %) with 200 tasks per category." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.08988v1.html:37-41] "The real clinical data (e.g., lab results, timestamps, patient demographics) remains authentic and unchanged" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
