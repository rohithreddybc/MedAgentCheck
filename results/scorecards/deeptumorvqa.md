# Score card: deeptumorvqa

Pinned: arXiv 2605.09679v1; repo https://github.com/Schuture/DeepTumorVQA at 1df7460db6b95a4fc550bf34d75571057e1d4c4b; accessed 2026-10-05T06:08:38Z; packet sha256 f35ba6d8c25741cf.
Cells: 25; not established (fallback to 0): 1; mean final level: 1.17.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:212-222] "Table 6: Overview of public abdominal CT datasets collected in DeepTumorVQA." |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:723-728] "sourced from publicly available, de-identified datasets that have undergone institutional review board (IRB) approval at their respective institutions." |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:224-226] "designed to maximize demographic and pathological diversity" |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:668-676] "We stratify accuracy by age, sex, CT scanner manufacturer, and contrast phase" |
| C5 Contamination controls | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:43-49] "Train/test splits are patient-level with zero overlap." |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:743-768] "All experiments use the following software stack:" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:684-688] "two practicing radiologists—a junior (7 years experience) and a senior (13 years)" |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:247-253] "Recognition templates (2-option binary, random baseline 50%):" |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:844-848] "model rankings are perfectly preserved" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:766-783] "All inference uses greedy decoding ( temperature=0 , do_sample=False )" |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:53-60] "95% binomial CIs are \pm 1.0% at N =10,000" |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:766-783] "Training uses seed 42 for data shuffling, weight initialization, and dropout." |
| A2 Uncertainty with stated resampling unit (e). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:567-580] "a clustered bootstrap that resamples at the volume level (991 test volumes)" |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:766-783] "All inference uses greedy decoding ( temperature=0 , do_sample=False )" |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:800-818] "We provide detailed specifications for each of the four diagnostic tools" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:49-53] "Tool outputs are sourced from expert annotations (oracle), TotalSegmentator auto-segmentation (predicted), or visual crops (vision)" |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2605.09679v1.html:53-60] "trajectory quality, comprising tool set Jaccard" |
| A9 Agent-channel contamination (f). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:104-114] "Overall / Recog. / Meas. / Vis.R. / Med.R." |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2605.09679v1.html:723-728] "The CT volumes are de-identified and sourced from publicly available datasets." |

## Contradiction flags (candidates only)
- A4 (sonnet): [S1:arxiv/2605.09679v1.html:766-783] "All inference uses greedy decoding ( temperature=0 , do_sample=False )" / [S1:arxiv/2605.09679v1.html:49-53] "We implement four diagnostic tools in a ReAct-style [ 57 ] agent loop (up to 8 steps)" / [S4:src/deeptumorvqa/evaluate.py:111-139] "Agent max steps (default 5)."
- A5 (sonnet): [S1:arxiv/2605.09679v1.html:818-829] "Output: JSON with fields: mask_found (bool), voxel_count (int), bounding_box (6-tuple), center_of_mass (3-tuple)." / [S1:arxiv/2605.09679v1.html:818-829] "type (string), one of volume , mean_HU , diameter , count ." / [S4:src/deeptumorvqa/eval/tools.py:168-216] "Supports: volume_cm3, mean_hu, max_diameter_mm, lesion_count,"
- A6 (sonnet): [S1:arxiv/2605.09679v1.html:434-439] "With pre-computation, each tool call reduces from 3–4 seconds (NIfTI loading) to < 1 millisecond (dictionary lookup)." / [S1:arxiv/2605.09679v1.html:798-799] "our predicted cache contains 0% lesion mask coverage for liver/kidney/pancreas/colon tumors" / [S1:arxiv/2605.09679v1.html:434-439] "With pre-computation, each tool call reduces from 3–4 seconds (NIfTI loading) to < 1 millisecond (dictionary lookup)." / [S4:src/deeptumorvqa/eval/tools.py:168-216] "Run 3D segmentation on the CT scan. Returns voxel count and bounding"
