# Score card: clindef

Pinned: arXiv 2512.23440v1; repo - at -; accessed 2026-10-05T06:07:41Z; packet sha256 ac37dda04b45c9eb.
Cells: 25; not established (fallback to 0): 9; mean final level: 0.58.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:20-26] "For each diagnostic session, \mathcal{G} first samples a disease node d\in K_{G} and retrieves the corresponding descriptive passage T_{d}\subset K_{E}" |
| C3 Representativeness | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:109-112] "This overconfidence creates the illusion of certainty and poses a potential safety risk" |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:26-29] "Contamination resistance , since the space of possible cases is huge and instantiated dynamically at evaluation time" |
| C6 Agent isolated from gold | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C7 Frozen environment | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2512.23440v1.html:205-208] "Pearson correlations fell within 0.80–0.87, while Spearman correlations ranged from 0.81–0.86" |
| C13 Non-determinism safeguards | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:79-91] "Diagnostic accuracy, efficiency, and quality (mean \pm standard error) on ClinDEF" |
| A1 Run count per reported number (e). | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:79-91] "Diagnostic accuracy, efficiency, and quality (mean \pm standard error) on ClinDEF" |
| A3 Action-level repeat-run reliability (a). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:228-232] "inference hyperparameters fixed to temperature =0.0 and top-p =1.0" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:35-45] "\mathcal{A}_{D}=\{\texttt{Ask},\,\texttt{Test},\,\texttt{Diag}\}" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:44-50] "the Patient A_{P} and Examiner A_{E} agents are deterministic simulators" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2512.23440v1.html:44-50] "Test results in o_{t}^{D}=r_{t} , denoting a request for an objective examination." |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:63-71] "we employ an “LLM-as-a-Judge” paradigm grounded in established OSCE evaluation principles" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:51-56] "Each response u_{t} is strictly constrained by the structured case profile \mathcal{C}" |
| A10 Slice reporting (g). | 0 | not_established | 0 | codex 1/0; sonnet 0/0 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2512.23440v1.html:233-240] "we employed LLMs for the knowledge-grounded synthesis of patient cases" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
