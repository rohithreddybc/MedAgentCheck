# Score card: medsp1000

Pinned: arXiv 2606.05112v1; repo https://github.com/MAGIC-AI4Med/MedSP1000 at 2806984cb331d6fedc2c0555e3c1c4a54171c77a; accessed 2026-10-05T06:12:24Z; packet sha256 59396e28124f6efa.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.84.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:135-139] "a Supplementary CSV file lists all 613 source articles with their titles, original authors, and MedEdPORTAL URLs" |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.05112v1.html:133-135] "no patient recruitment, no new collection of patient data, and no access to protected health information" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:21-24] "The final MedSP1000 span a broad range of clinical specialties" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C6 Agent isolated from gold | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.05112v1.html:96-97] "must never non-causally access future disease progression, untriggered test results, or the evaluator’s reference answers" |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:121-166] "The frozen ACGME rubrics used for scoring ship in this repo" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:27-27] "clinicians also corrected any identified errors, yielding a human-verified clean subset" |
| C9 Out-of-scope side effects detectable | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.05112v1.html:28-28] "evaluator agent’s per-rubric judgements agreed with human adjudication" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:41-47] "implemented using deterministic decoding (temperature = 0)" |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.05112v1.html:34-41] "the bottom line is its 95% confidence interval" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:130-133] "we run each case N times independently under identical settings (here N=5 )" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:34-41] "95% confidence interval (bootstrap over cases)" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:124-127] "We evaluated the model version gpt-5.5 using the official API." |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:107-107] "procedures, treatments, and dispositions, when the source materials specify them" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:108-109] "it receives the full interaction trajectory alongside the rubric packet" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:20-20] "It first receives only the “scenario initialization” packet" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:55-57] "the remaining two specialties of the 17-specialty taxonomy contained too few cases" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.05112v1.html:133-135] "source materials are instructional standardized-patient and simulation cases and do not contain identifiable patient information" |

## Contradiction flags (candidates only)
- C2 (codex): [S1:arxiv/2606.05112v1.html:133-135] "no patient recruitment, no new collection of patient data, and no access to protected health information" / [S1:arxiv/2606.05112v1.html:135-139] "under a CC BY-NC-SA licence" / [S2:README.md:229-254] "Released under the [MIT License](LICENSE)."
- C13 (codex): [S1:arxiv/2606.05112v1.html:41-47] "implemented using deterministic decoding (temperature = 0)" / [S1:arxiv/2606.05112v1.html:41-47] "implemented using deterministic decoding (temperature = 0)" / [S4:src/simulate/api.py:284-319] "if resolved_temperature is not None: create_kwargs["temperature"] = resolved_temperature"
- C13 (sonnet): [S1:arxiv/2606.05112v1.html:41-47] "are implemented using deterministic decoding (temperature = 0)" / [S1:arxiv/2606.05112v1.html:41-47] "are implemented using deterministic decoding (temperature = 0)" / [S4:src/simulate/api.py:94-130] "self.default_temperature: float | None = None"
- A4 (codex): [S1:arxiv/2606.05112v1.html:124-127] "We evaluated the model version gpt-5.5 using the official API." / [S1:arxiv/2606.05112v1.html:124-127] "We evaluated the model version gpt-5.5 using the official API." / [S4:src/analysis/compute_eval_stats.py:1-49] "Generate evaluation statistics report and figures for GPT-5.1"
- A4 (sonnet): [S1:arxiv/2606.05112v1.html:124-127] "We evaluated the model version gpt-5.5 using the official API." / [S1:arxiv/2606.05112v1.html:41-47] "are implemented using deterministic decoding (temperature = 0)" / [S1:arxiv/2606.05112v1.html:41-47] "are implemented using deterministic decoding (temperature = 0)" / [S4:src/simulate/api.py:94-130] "self.default_temperature: float | None = None"
