# Score card: h-adminsim

Pinned: arXiv 2602.05407v3; repo https://github.com/ljm565/H-AdminSim at 693210cdba425e559c379e078527fbda163b4124; accessed 2026-10-05T06:10:00Z; packet sha256 75f24bb162116818.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.44.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:249-254] "Through web crawling, we collected 427 disease–symptom pairs" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2602.05407v3.html:249-254] "Through web crawling, we collected 427 disease–symptom pairs" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:60-62] "each reflecting distinct institutional characteristics" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/0 |  |
| C8 Oracle solver | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| C14 Statistical comparison | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:60-62] "yielding 516, 769, and 5,052 synthesized patient profiles" |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:124-125] "the reasoning option set to low for the GPT-5 series" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:src/h_adminsim/tools/scheduling_rule.py:256-299] "Return the earliest available schedule for a preferred doctor." |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:51-61] "All FHIR operations are executed in real time throughout the simulation." |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2602.05407v3.html:51-61] "new Patient and Appointment FHIR resources are created" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:294-297] "the evaluation examines whether the staff agent completes the task execution" |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:67-73] "Intake / Scheduling (T) / Scheduling (R)" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2602.05407v3.html:1-9] "All data used in this study were synthetically generated." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
