# Score card: medcta

Pinned: arXiv 2606.11702v1; repo https://github.com/IVUL-KAUST/MedCTA at eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c; accessed 2026-10-05T06:11:31Z; packet sha256 8d78dbd8c5266b65.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.78.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:49-51] "We start from existing medical VQA datasets and curated clinical education resources" |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.11702v1.html:274-298] "All inputs come from public datasets approved for research use." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:495-500] "We report modality and body-system coverage, but demographic attributes are unavailable" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:500-505] "we perform all evaluation after freezing the validated benchmark" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:500-505] "Reference trajectories are not included in model prompts during autonomous evaluation." |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:500-505] "GoogleSearch does not query the live web during benchmark evaluation." |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:59-60] "The refined chain is then executed and logged in structured JSON format" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:36-39] "solving it requires decomposition into multiple subproblems and strategic invocation of tools" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.11702v1.html:385-397] "Aggregate clinical score / 0.62 / 0.60 / 13.5" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:320-321] "tool invocations to be executed deterministically and logged in structured JSON format" |
| C14 Statistical comparison | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:371-375] "a normal-approximation 95% confidence interval for the per-task mean score" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:320-321] "Each tool is defined by a standardized input–output interface" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:416-421] "A tool call is considered valid if (i) the selected tool exists in \mathcal{D}" |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:82-87] "Clinical Reasoning evaluates evidence usage and summary quality." |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:500-505] "GoogleSearch does not query the live web during benchmark evaluation." |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.11702v1.html:64-71] "CT (20.0%), report-based inputs (20.0%), histopathology (18.3%), X-ray (9.6%)" |
| A11 Environment-state provenance (h). | 0 | not_established | 1 | codex 2/0; sonnet 1/1 |  |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
