# Score card: rada-benchplat

Pinned: arXiv 2412.09529v4; repo https://github.com/MAGIC-AI4Med/RadABench at ee45eb2ffa65541b5deb013135caf825e471ac53; accessed 2026-10-05T06:13:30Z; packet sha256 d5c075a54c280669.
Cells: 25; not established (fallback to 0): 3; mean final level: 0.72.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:27-29] "we construct a test set of 165 real-world cases from Chest Imagenome Wu et al. (2021) and RadGenome-BrainMRI datasets" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:EvalPlat/RealEnv/README.md:1-34] "Both require credentialed access, so the pixels cannot be redistributed here." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:278-279] "the 165 cases span two imaging modalities (X-ray and MRI), two anatomical regions (chest and head & neck)" |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:187-191] "Bias/Diversity checks whether the sampled items avoid obvious demographic or disease shortcuts" |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:187-191] "No Leakage checks that the question, metadata, or prompt does not directly reveal the answer." |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S2:EvalPlat/RealEnv/README.md:31-71] "They are separate fields on purpose: merging them would leak the label into the input." |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:EvalPlat/RealEnv/README.md:31-71] "Sampling is seeded, so the same `--seed` over the same source data reproduces the same manifest." |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:187-191] "Tool Necessity verifies that answering the QA pair requires the intended radiology tools rather than shortcut reasoning alone." |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:187-191] "Ambiguity measures whether the task target and reference answer are clear enough to support reliable evaluation." |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:EvalPlat/RealEnv/README.md:31-71] "Sampling is seeded, so the same `--seed` over the same source data reproduces the same manifest." |
| C14 Statistical comparison | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:61-65] "few-shot learning and multi-agent collaboration yield significant wins ( p<0.05 )" |
| A1 Run count per reported number (e). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:308-308] "Each card specifies: (1) tool name and category; (2) supported anatomy, modality, and image dimensionality;" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:152-191] "python tests/test_autotb_realloop.py  # 25 checks, AutoTB build/replan closure" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:189-202] "Treatment Planner (TP) is a treatment planning tool (or system) to provide treatment plans based on current clinical findings." |
| A8 Grader reads state, or justifies transcript grading (c). | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:EvalPlat/RealEnv/README.md:31-71] "`RealCase.reference` holds the answer. They are separate fields on purpose" |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2412.09529v4.html:67-70] "165 cases across organ/anomaly grounding, diagnosis with grounding clues, and standard report generation (55 cases each)." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S2:EvalPlat/RealEnv/README.md:1-34] "Both require credentialed access, so the pixels cannot be redistributed here." |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
