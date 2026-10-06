# Score card: klinikebench

Pinned: arXiv 2609.38480v1; repo https://github.com/Zehui127/klinikebench-train at 311b2191cb8a5dc19ed55ef1f811c056aea72531; accessed 2026-10-05T06:10:41Z; packet sha256 028c401b43a37f71.
Cells: 25; not established (fallback to 0): 2; mean final level: 0.84.

A documentary 0 means the property is absent from every surface checked; it never means the benchmark lacks the practice. Contradiction flags are candidates only until verified against the benchmark's own documentation and offered for right of reply. Quotes are at most 25 words, copied from the cited source for verification; they remain the work of its authors.

| Item | Final | Status | Majority | Coders (raw/effective) | Evidence |
|---|---|---|---|---|---|
| C1 Traceability | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:29-35] "PrimeKG and HPO annotations supply disease–phenotype associations" |
| C2 Provenance and licence | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:29-35] "supplemented by public case reports" |
| C3 Representativeness | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:46-53] "The corpus contains 304 distinct target-diagnosis labels" |
| C4 Safety and bias tests | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C5 Contamination controls | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:41-46] "we also provide a split of 283 training tasks and 50 held-out test tasks" |
| C6 Agent isolated from gold | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:53-62] "The patient persona and scoring key remain inaccessible to the agent." |
| C7 Frozen environment | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S2:README.md:54-90] "installs from our `uv.lock` with `--frozen`" |
| C8 Oracle solver | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:33-42] "Clinicians then inspect live patient–agent simulations and revise inconsistent responses" |
| C9 Out-of-scope side effects detectable | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C10 Trivial success unlikely | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:46-53] "Strict pass@1 requires all gates and all must-ask topics." |
| C11 Trivial-agent result | 0 | established_zero | 0 | codex 0/0; sonnet 0/0 |  |
| C12 Evaluator validated | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:104-109] "Thirty clinicians assessed 35 virtual-patient conversations and 15 MTS-Dialog references" |
| C13 Non-determinism safeguards | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:61-64] "Patient simulation uses temperature 0.7 and history judging uses temperature 0." |
| C14 Statistical comparison | 0 | not_established | 1 | codex 1/0; sonnet 1/1 |  |
| A1 Run count per reported number (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:53-62] "with one rollout per model–task pair" |
| A2 Uncertainty with stated resampling unit (e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:348-364] "Paired-bootstrap 95% confidence intervals describe uncertainty in the change in strict pass@1" |
| A3 Action-level repeat-run reliability (a). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:330-350] "GPT-5.4-mini (repeat) / 26 / 28 / 24 / 20" |
| A4 Model and harness pinning (a/e). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:61-64] "Patient simulation uses temperature 0.7 and history judging uses temperature 0." |
| A5 Tool contract specified (b). | 2 | resolved | 2 | codex 2/2; sonnet 2/2 | [S1:arxiv/2609.38480v1.html:218-224] "clinic tools , which returns their names, descriptions, and JSON parameter schemas." |
| A6 Tool contract verified (b). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:244-248] "A local dispatch audit of the findings-enabled corpus covered all 3,550 exposed task–tool pairs" |
| A7 Write-action disclosure (d). | 1 | resolved | 1 | codex 2/2; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:231-240] "These actions do not trigger external clinical services." |
| A8 Grader reads state, or justifies transcript grading (c). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:41-46] "The resulting dialogue and tool trace are passed to the verifier." |
| A9 Agent-channel contamination (f). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:33-42] "diagnosis and scoring criteria remain hidden from the evaluated agent." |
| A10 Slice reporting (g). | 0 | not_established | 0 | codex 1/1; sonnet 0/0 |  |
| A11 Environment-state provenance (h). | 1 | resolved | 1 | codex 1/1; sonnet 1/1 | [S1:arxiv/2609.38480v1.html:29-35] "Clinicians select a target disease and associated findings" |

## Contradiction flags (candidates only)
- C6 (codex): [S1:arxiv/2609.38480v1.html:53-62] "The patient persona and scoring key remain inaccessible to the agent." / [S2:README.md:155-188] "It could therefore read the answer key in `/var/lib/caa`." / [S4:klinikebench_train/prepare_tasks.py:1-34] "SkyRL pins Harbor 0.1.44, which ignores [environment.env], [agent] user"
- A9 (codex): [S1:arxiv/2609.38480v1.html:33-42] "diagnosis and scoring criteria remain hidden from the evaluated agent." / [S2:README.md:155-188] "It could therefore read the answer key in `/var/lib/caa`." / [S2:README.md:155-188] "Evaluation with a current Harbor (`scripts/eval.sh`) runs the agent unprivileged."
