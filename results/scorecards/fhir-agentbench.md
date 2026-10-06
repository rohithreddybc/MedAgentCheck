# Score card: fhir-agentbench

Pinned: arXiv 2509.19319v2; repo https://github.com/glee4810/FHIR-AgentBench at bbb42909a5a7eb907d1cd91f72a560729e7037ea; accessed 2026-10-05T06:09:36Z; packet sha256 06ee1488a43a7ba7.
Cells: 25; not established (fallback to 0): 0; mean final level: 0.74.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.19319v2.html:33-36] "we use two sources: (1) EHRSQL-2024 ( Lee et al., 2024 )" |
| C2 Provenance and licence | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.19319v2.html:1-9] "patient records used in this work are from the PhysioNet website and licensed under the Open Data Commons Open Database License v1.0" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.19319v2.html:47-51] "The final FHIR-AgentBench comprises 2,931 question–context–FHIR resource–answer pairs" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C6 Agent isolated from gold | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:34-60] "Download [MIMIC-IV Clinical Database Demo on FHIR](https://physionet.org/content/mimic-iv-fhir-demo/2.1.0/)" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.19319v2.html:43-47] "When answers are non-empty, the corresponding FHIR IDs are always present." |
| C9 Out-of-scope side effects detectable | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.19319v2.html:169-199] "can be correct by chance, especially for binary Yes/No questions." |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.19319v2.html:59-62] "Manual review of 500 samples confirmed a 97% agreement rate with human judgment" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:evaluation_metrics.py:51-97] "response = litellm.completion(model=litellm_model, messages=messages, temperature=0.0)" |
| C14 Statistical comparison | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A1 Run count per reported number (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A2 Uncertainty with stated resampling unit (e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A3 Action-level repeat-run reliability (a). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A4 Model and harness pinning (a/e). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A5 Tool contract specified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S4:tools/resource_tools.py:79-120] ""resource_type": {"type": "string", "description": "FHIR resource type"}" |
| A6 Tool contract verified (b). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A7 Write-action disclosure (d). | NA | na_accepted | NA | codex NA/NA; sonnet NA/NA |  |
| A8 Grader reads state, or justifies transcript grading (c). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.19319v2.html:59-62] "as agents generate answers in free-text" |
| A9 Agent-channel contamination (f). | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| A10 Slice reporting (g). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2509.19319v2.html:169-199] "Performance of different agentic approaches on FHIR-AgentBench by correct resource type" |
| A11 Environment-state provenance (h). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2509.19319v2.html:25-27] "de-identified, real patient records from MIMIC-IV-FHIR" |

## Contradiction flags (candidates only)
None with a verified contradicting quote.
