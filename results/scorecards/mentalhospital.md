# Score card: mentalhospital

Pinned: arXiv 2607.08257v1; repo - at -; accessed 2026-10-05T06:12:30Z; packet sha256 3394c63f97225b81.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.76.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:24-28] "1,193 de-identified psychiatric EHR cases obtained through an approved collaborative data-use partnership" |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:260-264] "the requirement for individual informed consent was waived by the relevant ethics boards" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:237-240] "The age distribution of single-diagnosis and comorbid cases is shown in Figure 6" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:132-134] "These cases were strictly excluded from all MentalEval training data." |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:32-36] "The doctor agent cannot directly access \mathcal{K}^{\mathrm{pat}}_{c} , \mathcal{K}^{\mathrm{exam}}_{c} , or \mathcal{Y}^{*}_{c}" |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:100-102] "The expert group consists of 5 licensed psychiatrists and 3 psychology experts." |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 0/0; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:96-100] "We use a conservative semantic similarity threshold of \tau=0.85 for high-precision automatic matching" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:132-134] "Expert-guided DPO further improves agreement, reaching an average QWK of 0.944, accuracy of 0.790, and MAE of 0.210." |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:436-436] "The matching process is repeated three times, and the averaged results are used to reduce stochastic judgment variance." |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:135-139] "overall mean score of 3.88/5 (95% bootstrap CI: [3.78, 3.98])" |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:443-444] "95% bootstrap confidence intervals" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:269-271] "the output to be a JSON array enclosed by explicit markers" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:42-48] "records the doctor–patient trajectory \tau_{c} , collects examination requests" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:96-100] "k\preceq y_{c} indicates that checkpoint k is semantically entailed by the generated output y_{c}" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2607.08257v1.html:213-217] "De-identified benchmark cases and derived evaluation checkpoints will be provided only through controlled research access" |
| A10 Slice reporting (g). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2607.08257v1.html:213-217] "De-identified benchmark cases and derived evaluation checkpoints will be provided only through controlled research access" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
