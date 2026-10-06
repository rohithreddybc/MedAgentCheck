# Score card: ecg-scroll

Pinned: arXiv 2609.33117v1; repo https://github.com/CuCl-2/ECG-Scroll at 4db14ef59d8ee78de785c12a7d4644c9c8e3dc0f; accessed 2026-10-05T06:08:56Z; packet sha256 88cd0481361ba2ae.
Cells: 25; not established (fallback to 0): 4; mean final level: 0.54.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S2:README.md:163-188] "All from [PhysioNet](https://physionet.org/); cite the original databases if you use ECG-Scroll." |
| C2 Provenance and licence | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:32-36] "The release is a suite of 390 whole-recording instances over 247 recordings spanning 2,536 hours across five databases" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:22-26] "the event timeline E is never observed directly" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:66-102] "once records are cached under `data/raw/<db>_local/` they run fully offline" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:92-94] "As a signal-grounded reference we include a Rule Agent that uses no language model" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:32-36] "their episodes are few and brief with a median duration near 16 s" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:11-36] "All verifiers return a score in `[0, 1]` and are unit-tested" |
| C13 Non-determinism safeguards | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:50-66] "write(entry) / commit / append a cursor-timestamped finding to memory" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:11-36] "All verifiers return a score in `[0, 1]` and are unit-tested" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:64-70] "each write appends an entry of type, lead, interval, value, and confidence" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:92-94] "flagged or written spans are committed to the memory ledger" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:70-89] "Metrics are accuracies in [0,1] , higher is better." |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.33117v1.html:29-31] "ECG-Scroll uses real two-lead ambulatory recordings from PhysioNet" |

## Contradiction flags (candidates only)
- C6 (codex): [S1:arxiv/2609.33117v1.html:22-26] "the event timeline E is never observed directly" / [S1:arxiv/2609.33117v1.html:22-26] "the event timeline E is never observed directly" / [S4:ecgscroll/tools.py:437-469] "from beat annotations (mitdb/ltdb)."
- C6 (sonnet): [S1:arxiv/2609.33117v1.html:22-26] "it is retained on the server and revealed to the agent chunk by chunk, never handed over in full" / [S1:arxiv/2609.33117v1.html:22-26] "the event timeline E is never observed directly" / [S1:arxiv/2609.33117v1.html:22-26] "the event timeline E is never observed directly" / [S4:ecgscroll/tools.py:368-398] "read from the time-stamped ground-truth annotations and clamped causally to the elapsed"
