# Score card: medmcp-calc

Pinned: arXiv 2601.23049v2; repo https://github.com/SPIRAL-MED/MedMCP-Calc at 26304c5b02bfca22ecd0cdef69bcf5bff8e71891; accessed 2026-10-05T06:12:15Z; packet sha256 d6e2383d626eb77d.
Cells: 25; not established (fallback to 0): 4; mean final level: 0.52.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:363-377] "we constructed a dataset containing nine core tables based on MIMIC-IV v3.1" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:139-143] "Patient data were derived from MIMIC-IV, a publicly available, de-identified dataset compliant with HIPAA regulations" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:46-46] "selected patients with complete records across all tables, yielding a cohort of 49,419 patients" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:29-32] "a Google Search server with search and fetch tools for retrieving up-to-date medical references" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:47-51] "referenced all elements against patient information through item-by-item review and correction" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2601.23049v2.html:351-365] "Table 9 reports per-dimension agreement rates,, and Cohen’s Kappa" |
| C13 Non-determinism safeguards | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C14 Statistical comparison | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:codes/medmcpcalc_mcp/servers/postgres_executor/server.py:52-95] "Execute a read-only SQL query on the PostgreSQL database." |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:151-209] "Expected output shows successful tool execution for all three servers" |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:351-365] "extract the final calculator names, numerical results, and retrieved SQL fields into a standardized JSON format" |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:79-88] "The evaluation encompassed model performance across four clinical domains" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2601.23049v2.html:139-143] "Synthesized records were generated to supplement task-specific scenarios" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
