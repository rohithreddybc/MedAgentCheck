# Coding manual v1.0 (candidate freeze; Opus, 2026-10-04)

Supersedes the anchors in `rubric-v1.md`, whose item list is unchanged: 14 core items and 11 agent items. The changes come from pilot round 1, in which two independent coders scored AgentClinic, FHIR-AgentBench and HealthAgentBench and agreed on 63 of 75 cells (`rubric/pilot/`). Pilot scores are never reused.

## G. Global rules
- **G1 What is scored.** Each item scores what the benchmark *reports* on public surfaces S1 (paper and appendix), S2 (README and docs) and S3 (release notes), at the pinned version.
- **G1a Surfaces that count as reporting.** S1-S3 count. Agent-visible prompts and tool descriptions (S5) also count, but only for A5, A6(iii) and A7(ii), because those elements are about what the agent is told. Other code (S4 that is not S5), including code comments, never counts as reporting; it can only raise a contradiction flag (G2).
- **G2 Contradiction flag.** If code (S4) or an agent-visible surface (S5) shows the opposite of a reported property, keep the reported score and set `contradicted = y` with both quotes. A flag is a candidate finding only. It is verified against the benchmark's own documentation and offered for right of reply before it is reported. Exception: under A4, a model identifier that differs between S1 and S4 counts as absent.
- **G3 Recording.** A score of 1 or 2 carries a quote of 25 words or fewer and its location. A score of 0 or NA carries `searched:` followed by the S1-S5 places checked. A-items record `element_flags` as `n/3`.
- **G4 Anchors for element items.** 2 = all elements present; 1 = at least one element present; 0 = none. Item-specific anchors below override this.
- **G5 Disclosed weakness.** A benchmark that reports evidence showing a property is weak (e.g., "chance success is high") scores as reporting it (1), and the note records the weakness.
- **G6 Pinning.** Pin the arXiv version, the repo commit or tag (GitHub API) and the access date. If the repo moved after the paper, score the paper version and the commit nearest to it, and record both.
- **G7 NA.** NA is allowed only where an item's NA clause applies. "Not mentioned" is 0, never NA.

## C. Core items (anchors)
- **C1 Traceability.** 2 = dataset name, version or snapshot date, platform, and a route from a task to its source record. 1 = source named without version or route. 0 = none.
- **C2 Provenance and licence.** 2 = origin, collection method and licence or terms, plus consent or IRB status or an explicit "not required". 1 = origin plus any one of the others. 0 = origin not stated. A repo licence that conflicts with the source licence is recorded in the note; the score is not lowered.
- **C3 Representativeness.** 2 = comparison against a named target population. 1 = descriptive statistics or a stated sampling design. 0 = none.
- **C4 Safety and bias tests.** 2 = both an unsafe-output test and a bias test. 1 = one of them. 0 = neither.
- **C5 Contamination controls.** 2 = a developer-side control (gating, canary, encryption, held-out set) plus a measured check. 1 = any control or any indirect empirical check. 0 = a limitation sentence only, or nothing.
- **C6 Agent isolated from gold.** 2 = the paper or docs state that the agent cannot reach ground truth at run time AND name the mechanism (no mount, no credential, no network path, labels not public). 1 = isolation stated without a mechanism. 0 = not addressed.
- **C7 Frozen environment.** 2 = data, software and any simulator or judge model pinned, with no live external call at evaluation time other than the model under test. 1 = data pinned while some evaluator, simulator or service is live or unpinned. 0 = nothing pinned.
- **C8 Oracle solver.** 2 = a scripted reference solution is run through the grader and the result is reported. 1 = manual or agent-based solvability evidence. 0 = none.
- **C9 Out-of-scope side effects detectable.** NA when no task changes environment state. 2 = the grader checks unchanged as well as changed state. 1 = partial (some tasks). 0 = not checked.
- **C10 Trivial success unlikely.** 2 = an empirical random or trivial-agent rate, or an explicit chance rate per metric. 1 = a stated design argument, or a disclosed chance rate that is large (G5). 0 = none.
- **C11 Trivial-agent result.** 2 = a do-nothing or random agent's score is reported for all tasks. 1 = for some tasks. 0 = none.
- **C12 Evaluator validated.** 2 = the benchmark's own validation on its own outputs, with agreement or error figures. 1 = cited external validation, or validation without figures. 0 = none. Deterministic verifiers count as validated only with tests or reference-solution evidence.
- **C13 Non-determinism safeguards.** 2 = seeds or temperature 0 plus a repeated-run policy stated in S1-S3. 1 = safeguards visible only in code, or covering only part of the harness. 0 = none.
- **C14 Statistical comparison.** 2 = a CI or a test for the headline model comparison. 1 = SD, range or a CI without any comparison claim tested. 0 = none. "Significant" with no test = 1 at most, noted.

## A. Agent items (elements; G4 anchors unless stated)
- **A1 Run count.** (i) a number of runs per task behind headline scores ("multiple runs" without a number = absent); (ii) a seed, the decoding controls used, or an explicit statement that the API exposes none; (iii) independence of runs stated.
- **A2 Uncertainty with unit.** (i) a CI or SE on headline scores; (ii) the resampling or variance unit named ("pooled trials" counts as unit = trial); (iii) clustering of tasks within patients, templates or task groups addressed.
- **A3 Repeat-run reliability.** 0 = no rerun information beyond a single-run CI. 1 = score-level variation across identical reruns, or per-task repeat outcomes (k of n). 2 = an all-runs metric (pass^k or equivalent) or action- or state-level agreement across reruns, with the run count.
- **A4 Pinning.** (i) a provider snapshot ID or a release date (family name alone = absent; an S1/S4 mismatch = absent); (ii) decoding parameters, including reasoning effort where applicable; (iii) a harness tag or commit stated as matching the reported numbers (a dependency pin alone = partial, recorded in the note).
- **A5 Tool contract specified.** NA when the benchmark defines no tool interface and the agent uses only its own harness tools (shell, file edit). Text-command protocols are not NA. (i) a schema or an enforced grammar; (ii) side effects per tool (read or write); (iii) return semantics, including errors. Record whether (ii) reaches S5.
- **A6 Tool contract verified.** NA as for A5. (i) tests or conformance checks of tools; (ii) disclosure of any simulated, stubbed or no-op behaviour (if nothing is simulated and S1 says so, (ii) and (iii) count as present); (iii) that disclosure reaches S5.
- **A7 Write-action disclosure.** NA unless some action changes environment state or represents a clinical order, prescription, note or message, whether executed or simulated. (i) which actions write or are irreversible; (ii) executed, simulated or sandboxed (record S5 reach); (iii) whether unsafe or unnecessary writes are scored.
- **A8 Grader input and validation.** (i) grader input named (end state, action log, transcript, answer string, or LLM judge); (ii) the rationale for a non-state grader; (iii) validation on labelled correct and incorrect outcomes (injected, or human labels on at least 100 outputs) with per-class error rates. 2 needs (iii).
- **A9 Agent-channel contamination.** (i) controls on leakage through tools, retrieval, web access, cross-task memory, and agent-visible prompts or examples; (ii) held-out labels absent from every public surface (hidden at run time but public in the repo = partial, recorded); (iii) a canary or provenance marker.
- **A10 Slice reporting.** (i) results per task partition that the paper names as a benchmark axis; (ii) results per patient subgroup, applicable whenever the source data hold demographic fields; (iii) n per reported slice.
- **A11 Environment-state provenance.** (i) the source of records stated as real de-identified, synthetic (generator named) or mixed; never inferred; (ii) any one of: an IRB determination, a DUA or credentialing requirement, or the de-identification method; (iii) data terms stated separately from the code licence.

## Procedure per benchmark
1. Pin the version (G6). 2. Read the LLM evidence sheet if one exists, but score from the sources themselves. 3. Score all 25 items in the order C1..C14, A1..A11. 4. Record the time taken. 5. Do not discuss scores with the other coder until both sheets are submitted.
