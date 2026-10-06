# Score card: healthcare-ai-gym

Pinned: arXiv 2605.02943v1; repo https://github.com/minstar/Healthcare_GYM at 92e9613d02036b97c8de6a7bd9db77cf1803ce41; accessed 2026-10-05T06:10:19Z; packet sha256 e28a4aeaf9b0b06b.
Cells: 25; not established (fallback to 0): 6; mean final level: 0.56.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:194-200] "Tasks are sourced from three pipelines: expert-curated seed tasks" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:51-55] "sampled without replacement from the same domain distribution as training" |
| C4 Safety and bias tests | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C5 Contamination controls | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.02943v1.html:51-55] "zero data contamination verified via test-set fingerprinting" |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:docker/README.md:45-51] "All servers call **live public APIs**" |
| C8 Oracle solver | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:84-86] "mean accuracy of 59.5% ( \pm 1.4 pp) over steps 40–60" |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A5 Tool contract specified (b). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.02943v1.html:200-207] "Tools are registered via the @is_tool(ToolType) decorator, which supports four types: READ (queries), WRITE (state modifications)" |
| A6 Tool contract verified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:217-229] "Critical violations (severity 5: contraindication ignored, dangerous dosing, missed emergency) cap total reward at 0.1" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:276-282] "evaluated via action-based scoring, measuring whether the agent executes the expected clinical tool calls" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:51-55] "TT-OPD validation accuracy is computed on a held-out set of 307 tasks" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02943v1.html:297-337] "Table 5 : Evaluation benchmark suite." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." |

## Contradiction flags (candidates only)
- C2 (codex): [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." / [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." / [S1:arxiv/2605.02943v1.html:194-200] "EHRConverter extracts MIMIC-III/IV admission episodes"
- A6 (sonnet): [S4:scripts/verl/tool_config_full.yaml:345-395] "Order a new lab test for a patient. The test will be simulated" / [S4:scripts/verl/tool_config_full.yaml:772-826] "Analyze a medical image and return findings. In simulation mode," / [S1:arxiv/2605.02943v1.html:55-66] "Base+AR uses the same multi-turn AgentRunner with 135 tools and 828K-passage KB as RL models" / [S4:bioagents/evaluation/agent_runner.py:1809-1840] "which means the paper's own Base+AR VQA row may itself be a toolless"
- A11 (codex): [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." / [S2:README.md:440-477] "All patient data is **synthetic**. No real patient information is used." / [S1:arxiv/2605.02943v1.html:194-200] "EHRConverter extracts MIMIC-III/IV admission episodes"
