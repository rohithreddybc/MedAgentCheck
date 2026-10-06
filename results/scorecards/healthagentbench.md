# Score card: healthagentbench

Pinned: arXiv 2606.31179v1; repo https://github.com/microsoft/HealthAgentBench at bcbb8085fd549469e2dc7455f4bfd68a1b98895a; accessed 2026-10-05T06:10:09Z; packet sha256 465ef5ac32aec57a.
Cells: 25; not established (fallback to 0): 2; mean final level: 1.00.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:288-299] "Version pin: MIMIC-CXR v2.1.0 PhysioNet release." |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:364-375] "Access: HuggingFace gated under OpenRAIL; HF_TOKEN required at bootstrap." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:335-339] "Selection criteria: The tasks are selected to cover patient profiles stratified across clinical specialties (ages 15–70, both sexes)." |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:47-53] "Gold labels and verifier code are mounted only into the verifier step, never into the agent container." |
| C6 Agent isolated from gold | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.31179v1.html:299-306] "gold target Findings are never agent-visible; they live only in the verifier." |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:204-224] "Stable Harbor version used here: `0.8.0`" |
| C8 Oracle solver | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C9 Out-of-scope side effects detectable | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:241-259] "default config is byte-identical to upstream" |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:37-39] "HealthAgentBench have a low random-guess success rate—typically below 10\%" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:280-290] "verifier uses CheXprompt [ 36 ]" |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.31179v1.html:62-64] "error bars are Wilson 95% confidence intervals." |
| A1 Run count per reported number (e). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.31179v1.html:57-59] "Across 3 attempts on 54 tasks (i.e 162 trials)" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:62-64] "pooled over all trials (trial-weighted)." |
| A3 Action-level repeat-run reliability (a). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:57-59] "Across 3 attempts on 54 tasks (i.e 162 trials)" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:57-59] "with xhigh reasoning effort" |
| A5 Tool contract specified (b). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A6 Tool contract verified (b). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:6-7] "until it writes the corrected report to /workspace/submission.json" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:288-299] "Per-trial: CheXprompt LLM-as-a-judge 5-vote majority" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:47-53] "We also disable web browsing capabilities from agents" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.31179v1.html:65-66] "exact per-(agent, category) success rate, time, and cost are tabulated" |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.31179v1.html:29-35] "All tasks contain real clinical data including patient data or clinical documents" |

## Contradiction flags (candidates only)
- C6 (sonnet): [S1:arxiv/2606.31179v1.html:47-53] "Gold labels and verifier code are mounted only into the verifier step, never into the agent container." / [S1:arxiv/2606.31179v1.html:299-306] "Two-service split: bootstrap holds PhysioNet credentials ( PN_USER , PN_PASS ); the main agent service has none." / [S1:arxiv/2606.31179v1.html:299-306] "the main agent service has none." / [S4:tasks/xray_report_correction_case_01/environment/docker-compose.yaml:27-61] "NOTE: PN_USER / PN_PASS in the same .env do get loaded into main"
- A9 (sonnet): [S1:arxiv/2606.31179v1.html:47-53] "We also disable web browsing capabilities from agents to block the agent browsing internet for gold labels." / [S1:arxiv/2606.31179v1.html:47-53] "We do not redistribute data and labels" / [S1:arxiv/2606.31179v1.html:299-306] "Therefore, the agent cannot simply download the gold Findings from PhysioNet." / [S4:tasks/xray_report_correction_case_01/environment/docker-compose.yaml:27-61] "NOTE: PN_USER / PN_PASS in the same .env do get loaded into main"
