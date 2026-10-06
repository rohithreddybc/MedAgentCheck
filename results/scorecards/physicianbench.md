# Score card: physicianbench

Pinned: arXiv 2605.02240v1; repo https://github.com/HealthRex/PhysicianBench at c7efa8fd5b1e4744ada50668efe4b7e84023cbb0; accessed 2026-10-05T06:13:20Z; packet sha256 c3459bab5321c5be.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.76.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:184-187] "Source clinical scenarios are drawn from de-identified electronic health records (EHR) in the STARR" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:52-54] "derived from real clinical records in the STAnford Research Repository (STARR)" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:136-176] "Table A2: Clinical-area coverage across 21 subspecialties." |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:191-197] "Patient safety. Whether any recommended action could cause patient harm." |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:64-66] "Each task ships as a self-contained Docker image bundling a HAPI FHIR JPA server" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:52-54] "a reference solution summary and review checklist supporting structured physician validation" |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:54-58] "every task undergoes multi-round review by a panel of 11 human physicians" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:61-63] "use the provider’s default temperature" |
| C14 Statistical comparison | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A1 Run count per reported number (e). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.02240v1.html:61-63] "run 3 independent trials to compute the reliability metrics" |
| A2 Uncertainty with stated resampling unit (e). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A3 Action-level repeat-run reliability (a). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.02240v1.html:64-66] "Pass^3 ( Yao et al., 2025 ) =c^{k}/n^{k}" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:61-63] "reasoning-effort parameter, we set it to high" |
| A5 Tool contract specified (b). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.02240v1.html:37-37] "write tools return the created resource or a file-write confirmation" |
| A6 Tool contract verified (b). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:35-36] "Each task instance runs in an isolated Docker container" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:46-50] "hybrid graders combine deterministic ground-truth computation from FHIR data with LLM-assisted extraction" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.02240v1.html:70-72] "Table 3 reports pass@1 broken down by clinical specialty." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S2:README.md:17-66] "distributed as a Docker image archive on Stanford Redivis" |

## Contradiction flags (candidates only)
- A4 (sonnet): [S1:arxiv/2605.02240v1.html:61-63] "For models that support a reasoning-effort parameter, we set it to high and run 3 independent trials to compute the reliability metrics." / [S1:arxiv/2605.02240v1.html:61-63] "We allow up to 100 tool-calling turns per task" / [S4:scripts/run_task.py:239-267] "parser.add_argument("--max-steps", type=int, default=200)"
