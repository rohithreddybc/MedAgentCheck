# Score card: rha-safety

Pinned: arXiv 2604.26577v2; repo https://github.com/kztakemoto/RHASafety at 69391da398f091814b33b70c0ac39531f3a33259; accessed 2026-10-05T06:13:38Z; packet sha256 191cad38f696793c.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.64.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:17-19] "For each category, 30 harmful instructions were generated using GPT-4.1" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:1-57] "This project is licensed under the MIT License." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:58-65] "30 scenarios per category; Table 2" |
| C4 Safety and bias tests | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2604.26577v2.html:12-15] "we additionally evaluate all 72 models on a paired benign instruction dataset" |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C8 Oracle solver | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 0/0; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:46-47] "both authors manually spot-checked a random subset of five responses per harmful instruction category" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:39-40] "temperature was set to 0.0 for all models where this parameter is supported" |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2604.26577v2.html:81-84] "A one-sided Wilcoxon rank-sum test confirmed that this difference was highly significant" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:38-39] "Each instruction was evaluated in an independent session with no carry-over of context between instructions." |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:43-45] "The evaluator was GPT-5.4 (gpt-5.4-2026-03-05)" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:225-226] ""Skill": [ "navigateToLocation", "navigateToItemLocation", "pickObject", "releaseObject", "summarizePatientInformation"" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:38-39] "A mock server received the LLM’s response and returned a simulated execution acknowledgment" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:36-37] "with the robot skills assumed to execute correctly given a valid JSON-formatted command" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:43-45] "the evaluator was provided with the patient room scenario description, the harmful instruction, the LLM’s textual response" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2604.26577v2.html:81-84] "Category-specific violation rates by model family, shown as a radar chart." |
| A11 Environment-state provenance (h). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |

## Contradiction flags (candidates only)
- C14 (codex): [S1:arxiv/2604.26577v2.html:81-84] "A one-sided Wilcoxon rank-sum test confirmed that this difference was highly significant" / [S1:arxiv/2604.26577v2.html:53-55] "Differences in violation rates between proprietary and open-weight models were assessed using a two-sided Wilcoxon rank-sum test." / [S1:arxiv/2604.26577v2.html:81-84] "A one-sided Wilcoxon rank-sum test confirmed that this difference was highly significant"
