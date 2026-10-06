# Score card: medevoeval

Pinned: arXiv 2606.28900v1; repo - at -; accessed 2026-10-05T06:11:45Z; packet sha256 9e114ef54b5f64b6.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.71.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:56-60] "Chinese MedEvoEval-MedQA-700" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:56-60] "700-case processed episode corpus released in the accompanying artifact as Chinese MedEvoEval-MedQA-700" |
| C3 Representativeness | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:50-53] "unsafe or unsupported elements" |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:229-240] "This 100-case held-out set is not used during longitudinal-stream memory accumulation." |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2606.28900v1.html:41-46] "The doctor observes only the current visible state" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:262-268] "The experiments use API-based inference rather than local model training or fine-tuning." |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.28900v1.html:367-373] "Diagnosis agreement / Diag. kappa / Evidence corr. / Plan corr." |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:77-82] "episodes use T_{\max}=10 , E_{\max}=3 , seed 7" |
| C14 Statistical comparison | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:77-82] "episodes use T_{\max}=10 , E_{\max}=3 , seed 7" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:77-82] "computed by resampling cases while preserving the pairing" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:45-50] "The doctor selects from four structured actions" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:268-279] "The runner uses JSON-only prompts together with schema and action validation." |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:124-127] "The episodes are simulated and standardized" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:50-53] "The manager evaluates the submitted diagnosis, supporting evidence, management plan, and follow-up" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:41-46] "never directly accesses unrevealed examination fields, manager-side rubrics, or provenance metadata" |
| A10 Slice reporting (g). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.28900v1.html:170-180] "700 release-safe Chinese MedQA-derived simulated clinical cases" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
