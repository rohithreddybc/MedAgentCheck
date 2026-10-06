# Score card: gpagentbench-2k

Pinned: arXiv 2608.30188v2; repo https://github.com/jianing-lab/GPAgentBench at 7f8f67e5f2983fab9c272400a54666cfe9e2a497; accessed 2026-10-05T06:09:51Z; packet sha256 2d2de582cb51f02c.
Cells: 25; not established (fallback to 0): 6; mean final level: 0.76.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:25-27] "GPAgentBench-2K was constructed using real-world GP visit records from a primary-care network." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:345-350] "GPAgentBench-2K is under a non-commercial research-use license." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:177-185] "male patients account for 57.6% and females for 42.4% of the 2,256 cases with recorded gender data." |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:219-221] "The safety cost captures two types of management errors: (1) Missed Referral (Miss Refer)" |
| C5 Contamination controls | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2608.30188v2.html:22-26] "the ground-truth diagnosis and disposition is hidden from the agent." |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:28-29] "collected cases undergo rigorous validation by two senior physicians." |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 0/0; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:42-45] "The agent must generate XML-style tags" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.30188v2.html:229-242] "The averaged Cohen’s \kappa between GPT-5.4 judge and physicians is 0.92 for Dx accuracy and 0.89 for Tx score." |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:68-78] "Parentheses report the standard error of the mean." |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:306-320] "mean \pm standard error across test cases." |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2608.30188v2.html:42-45] "The agent must generate XML-style tags" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.30188v2.html:49-56] "For zero-shot benchmarking of off-the-shelf LLMs, we simply sample rollouts of the policy within the environment" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:209-214] "We use GPT-5.4 as an automated judge to assign a binary score" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:29-32] "To prevent label leakage, we remove diagnostic statements and treatment recommendations from the clinical notes." |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2608.30188v2.html:89-96] "Table 2: Comparison of different metrics of Qwen2.5 (7B) optimized using GRPO and C-GRPO." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2608.30188v2.html:357-363] "The original clinical records were rigorously anonymized prior to any processing." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
