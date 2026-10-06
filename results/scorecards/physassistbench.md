# Score card: physassistbench

Pinned: arXiv 2606.18613v4; repo https://github.com/HINTLab/PhysAssistBench at 12aa0eccf102f65f7715bbc4a3264bd4f31f7bd0; accessed 2026-10-05T06:13:11Z; packet sha256 3bb96a2ded3f098f.
Cells: 25; not established (fallback to 0): 6; mean final level: 0.72.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:205-212] "PhysAssistBench is built on MIMIC-IV Johnson et al. (2023) , released on PhysioNet under the PhysioNet Credentialed Health Data Licence 1.5.0 ." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:415-420] "The sessions are evenly distributed across four clinical scenarios, with 81 sessions per scenario, and three data richness tiers, with 108 sessions per tier." |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:438-466] "An LLM judge audits the gold answer for hallucination, numerical inconsistency with the tool observations, clinical safety, and completeness." |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:213-224] "Benchmark sessions must not be used as training data for evaluated models, to prevent leaderboard contamination." |
| C6 Agent isolated from gold | 0 | not_established | 1 | codex 2/0; sonnet 1/1 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:322-330] "During evaluation, each tool call returns the corresponding fixed response through deterministic replay; the patient LLM is not invoked online." |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:59-62] "eight trained annotators verified and corrected all turn-level annotated fields, including the implicitness labels, rubric items, and gold tool calls" |
| C9 Out-of-scope side effects detectable | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:372-376] "Calls MedicationRequest.create (no other write)" |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:438-466] "Rule-based structural checks verify tool cardinality (Table H2 ) and parameter completeness." |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.18613v4.html:273-286] "The judge and trained-annotator labels agree on 3,685 items, yielding 95.37% agreement." |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:109-110] "whose narrow cross-model standard deviation (5.6–7.6) indicates that multi-tool composition resists model scale." |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:78-86] "temperature=0.2 , and a maximum of 16 tool calls per turn" |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A5 Tool contract specified (b). | 0 | not_established | 1 | codex 2/0; sonnet 1/1 |  |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:438-466] "A deterministic checker verifies that key EHR tool calls returned non-empty results" |
| A7 Write-action disclosure (d). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2606.18613v4.html:313-321] "these 3 tools simulate EHR write operations and are used primarily in Write/Update turns" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2606.18613v4.html:72-75] "Tool invocation is evaluated implicitly through rubric-based scoring" |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:213-224] "Benchmark sessions must not be used as training data for evaluated models, to prevent leaderboard contamination." |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2606.18613v4.html:481-500] "Table I1: Rubric score (%) per clinical scenario, English and Chinese separately." |
| A11 Environment-state provenance (h). | 0 | not_established | 2 | codex 2/0; sonnet 2/2 |  |

## Contradiction flags (candidates only)
- C7 (sonnet): [S1:arxiv/2606.18613v4.html:52-56] "enables deterministic evaluation via response replay" / [S1:arxiv/2606.18613v4.html:78-86] "Rubric scoring is performed by a fixed GPT-5.4-mini judge which is identical across all models." / [S1:arxiv/2606.18613v4.html:78-86] "Rubric scoring is performed by a fixed GPT-5.4-mini judge which is identical across all models." / [S4:physassistbench/run_eval.py:659-692] "If GATEWAY_OPENAI_API_KEY is set, use gpt-5-mini-2025-08-07 as rubric/IIRS judge." / [S4:physassistbench/run_eval.py:659-692] "Falls back to DeepSeek if the key is absent."
- A4 (sonnet): [S1:arxiv/2606.18613v4.html:78-86] "All models run with reasoning (“thinking”) mode enabled ( reasoning_effort=high for the GPT-5 series)" / [S1:arxiv/2606.18613v4.html:78-86] "All models run with reasoning (“thinking”) mode enabled ( reasoning_effort=high for the GPT-5 series)" / [S4:physassistbench/eval_runner.py:124-168] "consistent with the "thinking off" eval policy"
