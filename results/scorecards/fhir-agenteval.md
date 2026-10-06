# Score card: fhir-agenteval

Pinned: arXiv -; repo - at -; accessed 2026-10-05T06:09:42Z; packet sha256 9627012f96999ec1.
Cells: 25; not established (fallback to 0): 7; mean final level: 0.48.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C2 Provenance and licence | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C3 Representativeness | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:71-81] "evaluate on three variations of the remaining 22 held-out tasks" |
| C6 Agent isolated from gold | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:39-43] "A reference implementation by human engineers that performs the optimal sequence of FHIR operations." |
| C9 Out-of-scope side effects detectable | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:43-50] "We iteratively review soft validator feedback and inspect runs" |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:80-83] "mean task success rate (± standard deviation) over three runs" |
| A1 Run count per reported number (e). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:87-90] "Same-prompt variance captures run-to-run variability for identical task descriptions" |
| A3 Action-level repeat-run reliability (a). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:87-90] "Same-prompt variance (run-to-run variability) : This component captures variability across three runs" |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:51-56] "exposing 5 tools: createResource, searchResources, getResourceById, updateResource , and deleteResource" |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:extra/pmc12919212-fhir-agenteval:39-43] "tasks involving creation or modification (23 out of 43 tasks)" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:39-43] "verify server-side resource state and field-level changes" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:71-81] "remaining 22 held-out tasks" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:extra/pmc12919212-fhir-agenteval:117-121] "Figure 11a shows token usage distributions grouped by task difficulty levels (1, 2, or 3)." |
| A11 Environment-state provenance (h). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
