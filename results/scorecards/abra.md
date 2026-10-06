# Score card: abra

Pinned: arXiv 2605.11224v1; repo https://github.com/Luab/ABRA at 688814615dc368a66276798cb864fe9a587d7e6c; accessed 2026-10-05T06:07:20Z; packet sha256 68dfd19d753310d2.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.68.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2605.11224v1.html:52-58] "ABRA tasks are synthesised programmatically from three public TCIA cohorts" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:217-225] "Table 6: Datasets used by ABRA after local filtering." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:217-225] "Studies counts distinct StudyInstanceUID s; Series counts individual DICOM series" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:78-135] "assert a == b, 'manifest mismatch — your DICOM differs from the reference set'" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:314-321] "Reference trajectories T_{\text{ref}} are constructed deterministically by each task generator" |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:81-91] "Detection rate minus 0.1 per false positive, clamped to [0,1]" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2605.11224v1.html:90-94] "decode at temperature 0 with provider-default reasoning effort" |
| C14 Statistical comparison | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:90-94] "report a single run per (model, task) pair" |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A3 Action-level repeat-run reliability (a). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S2:README.md:159-210] "reports `pass^k` (probability that ALL k repeats of a task succeed)" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:90-94] "cap output at 20,048 tokens per response, decode at temperature 0" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:66-74] "Each tool is presented as a typed JSON function-calling schema" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:189-195] "we expose two oracle tools that simulate calls to external CAD models" |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.11224v1.html:42-44] "Episodes run in isolated browser contexts" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:44-48] "the ordered sequence of tool calls, per-call return values and execution metadata" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:365-385] "Table 13 gives the per-task-type Planning, Execution, and Outcome scores" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.11224v1.html:210-216] "ABRA draws its studies from three public collections" |

## Contradiction flags (candidates only)
- C2 (codex): [S1:arxiv/2605.11224v1.html:217-225] "Table 6: Datasets used by ABRA after local filtering." / [S1:arxiv/2605.11224v1.html:217-225] "Duke Breast Cancer MRI | Bilateral breast MRI | 50 | 50 | 278 | MR (270), SEG (8) | Saha et al. [2021] | ..."
- A4 (sonnet): [S1:arxiv/2605.11224v1.html:94-107] "API snapshots: GPT-5.4 ( gpt-5.4-2026-03-05 ), GPT-5.4-nano ( gpt-5.4-nano-2026-03-17 )" / [S1:arxiv/2605.11224v1.html:90-94] "decode at temperature 0 with provider-default reasoning effort (medium across all evaluated models)" / [S1:arxiv/2605.11224v1.html:90-94] "we additionally cap output at 20,048 tokens per response"
- A6 (codex): [S1:arxiv/2605.11224v1.html:189-195] "we expose two oracle tools that simulate calls to external CAD models" / [S1:arxiv/2605.11224v1.html:189-195] "we expose two oracle tools that simulate calls to external CAD models" / [S4:src/tasks/tool_registry.py:355-389] "Query an external pathology detection model for findings in a CT series."
- A11 (codex): [S1:arxiv/2605.11224v1.html:210-216] "ABRA draws its studies from three public collections" / [S1:arxiv/2605.11224v1.html:217-225] "Duke Breast Cancer MRI | Bilateral breast MRI | 50 | 50 | 278 | MR (270), SEG (8) | Saha et al. [2021] | ..."
