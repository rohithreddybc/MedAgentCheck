# Score card: agentclinic

Pinned: arXiv 2405.07960v5; repo https://github.com/SamuelSchmidgall/AgentClinic at b6fbe22300e99a267a7ac94eaa465ab552eef741; accessed 2026-10-05T06:07:28Z; packet sha256 9317b34007eed926.
Cells: 25; not established (fallback to 0): 5; mean final level: 0.68.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:24-26] "we use a random sample of diagnostic questions from the US Medical Licensing Exam (USMLE), from deidentified electronic health records (MIMIC-IV)" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:1-37] "AgentClinic-MIMIC-IV, based on real clinical cases from MIMIC-IV (requires approval from https://physionet.org/content/mimiciv/2.2/)" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:240-259] "The following are the racial demographic statistics from MIMIC-IV patients" |
| C4 Safety and bias tests | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:37-37] "For bias evaluations we test GPT-4 as well as Mixtral-8x7B." |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:73-73] "MedQA performance is not predictive of AgentClinic-MedQA accuracy" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:24-26] "we separate information by what is provided to each agent" |
| C7 Frozen environment | 0 | not_established | 0 | codex 0/0; sonnet 1/1 |  |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:28-31] "We also evaluate human physician performance collected from three physicians" |
| C9 Out-of-scope side effects detectable | 0 | na_rejected_as_zero | 0 | codex 0/0; sonnet NA/NA |  |
| C10 Trivial success unlikely | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:72-72] "strong LLM judges like GPT-4 can match both controlled and crowd-sourced human preferences well" |
| C13 Non-determinism safeguards | 0 | not_established | 1 | codex 1/0; sonnet 1/0 |  |
| C14 Statistical comparison | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2405.07960v5.html:173-201] "Claude 3.5: 62.1% accuracy with a 95% CI of [55%, 68%]" |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:199-207] "calculated based on the standard error of the mean accuracy across multiple runs" |
| A3 Action-level repeat-run reliability (a). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:366-370] "Research [database] [search query]" |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:9-11] "doctor agents can perform simulated medical exams" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:362-364] "the doctor agent can write useful tips" |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:144-147] "the diagnosis text produced by the doctor agent can be quite unstructured" |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2405.07960v5.html:435-448] "AgentClinic-Spec / 260 cases derived from from MedMCQA" |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:1-37] "based on real clinical cases from MIMIC-IV (requires approval from https://physionet.org/content/mimiciv/2.2/)" |

## Contradiction flags (candidates only)
- C7 (sonnet): [S1:arxiv/2405.07960v5.html:165-169] "GPT-4 ( gpt-4-0613 ) is a large-scale, multimodal LLM which is able to process both image and text inputs." / [S4:agentclinic.py:64-96] "model="gpt-4-turbo-preview","
