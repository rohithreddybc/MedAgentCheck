# Score card: clinenv

Pinned: arXiv 2606.02568v1; repo https://github.com/ylin766/ClinEnv at c033d74ed776a852ae185b80a987798586f4caf7; accessed 2026-10-05T06:07:49Z; packet sha256 12bec17ff6d47336.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.71.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.02568v1.html:38-43] "ClinEnv is built from MIMIC-IV v3.1 ( Johnson et al., 2023a ) and MIMIC-IV-Note v2.2" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:197-201] "distributed through PhysioNet under a credentialed data use agreement" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:342-349] "sample the remainder to span the full range of case horizons" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:94-103] "Must meet PhysioNet’s compliance standards before use." |
| C6 Agent isolated from gold | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.02568v1.html:305-310] "prevents coded outcomes and discharge summaries from being passively exposed to the model" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:38-43] "ClinEnv is built from MIMIC-IV v3.1 ( Johnson et al., 2023a ) and MIMIC-IV-Note v2.2" |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:env/runtime/environment_controller.py:578-616] "extra_kwargs: dict = {"tool_choice": "auto", "temperature": 0, "parallel_tool_calls": False}" |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:172-176] "Shaded bands are standard errors." |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:172-176] "Shaded bands are standard errors." |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:75-92] "submit_medication / Both / Submit medication decision" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:299-305] "the evaluation record stores matching assignments and process metrics" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:305-310] "prevents coded outcomes and discharge summaries from being passively exposed to the model" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.02568v1.html:182-193] "Table 6: Decision-type decomposition." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.02568v1.html:197-201] "ClinEnv is derived from MIMIC-IV and MIMIC-IV-Note, which are de-identified" |

## Contradiction flags (candidates only)
- A5 (sonnet): [S4:env/tools/env_tools.py:100-147] "Ask the patient a question about their symptoms, history, or concerns." / [S1:arxiv/2606.02568v1.html:65-78] "returning nothing for tests not on record" / [S1:arxiv/2606.02568v1.html:75-92] "submit_plan | Both | Submit other management decision" / [S4:env/tools/env_tools.py:181-222] "{"submit_medication", "submit_diagnosis", "submit_procedure"}"
