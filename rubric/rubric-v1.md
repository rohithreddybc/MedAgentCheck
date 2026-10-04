# Rubric v1 (DRAFT, not frozen) — agentic clinical benchmark checklist

Status: Opus draft 2026-10-04. Freezes only with the OSF protocol. Pilot on 3 benchmarks before freezing; any item with pilot kappa < 0.6 gets its anchors rewritten, and the change is logged.

## Design rules (from decision log)
- Two modules. **Core (reused)**: items taken from MedCheck v2 (2508.04325v2), BetterBench (2411.12990) and ABC (2507.02825v5) where they apply to agentic clinical benchmarks, cited by source id. **Agent module (new)**: only items covering the eight agent-specific constructs where the crosswalk (`research/instruments/crosswalk.md`) found PARTIAL or NONE coverage.
- Scale for every item: 0 = not reported, 1 = partially reported, 2 = fully reported, NA = not applicable (reason required). Same 0/1/2 scale as MedCheck so core items stay comparable.
- Levels, named once and used everywhere: **NOT REPORTED** (0), **REPORTED** (1 or 2, documentary tier), **VERIFIED-BY-EXECUTION** (executed tier only: we reran the harness and the reported property held). A documentary 0 means the property is absent from every surface we checked. It never means the benchmark lacks the practice.
- Evidence surfaces, checked in this order before any 0: (S1) paper and appendix, (S2) repository README and docs, (S3) release notes or changelog, (S4) code, (S5) agent-visible surface (system prompt, tool descriptions, tool return strings). Each score records the surface and a quote of 25 words or fewer. Items A5 and A7 also record whether the disclosure reaches S5, because a disclosure to human readers does not reach the agent.
- Unit: one benchmark at one pinned version (paper version + repo commit). If the version is unpinnable, record the access date.
- Licence: our CC-BY release reproduces only the agent-module text and BetterBench items (CC BY 4.0). MedCheck and ABC items are referenced by id with a one-line paraphrase and citation; their text is not redistributed. (MedCheck has no rubric licence; ABC repo licence unchecked.)

## Core module (reused; 14 items)
| Id | Source | Construct | Item (paraphrase) |
|---|---|---|---|
| C1 | MedCheck 13 | h provenance | Original data sources stated with traceability (time frame, platform). |
| C2 | BetterBench J.3-11 | h provenance | Data origin, collection, provenance, licence compliance and consent documented. |
| C3 | MedCheck 16 | g subgroup | Representativeness of key patient features analysed against the target population. |
| C4 | MedCheck 12 | d safety | Dedicated tests for unsafe output and bias. |
| C5 | MedCheck 23 | f contamination | Developer-side contamination controls (gated access, canary, overlap checks). |
| C6 | ABC T.5 | f contamination | Agent isolated from ground-truth results. |
| C7 | ABC T.6 | b/h environment | Environment reproducible and frozen at release; no dynamic external dependence. |
| C8 | ABC T.9 | c grader | Oracle solver shows task configuration is solvable and correct. |
| C9 | ABC O.g.2 | c grader | State space includes irrelevant states, so out-of-scope side effects are detectable. |
| C10 | ABC O.g.3 | c grader | Random or trivial changes are unlikely to be graded correct. |
| C11 | ABC R.13 | c grader | Results of a trivial (do-nothing) agent reported. |
| C12 | BetterBench J.1-13 | c grader | Automatic evaluator's quality validated, results reported. |
| C13 | ABC O.f.2 | a reliability | Safeguards against non-determinism in the harness. |
| C14 | MedCheck 37 / ABC R.10 | e CI | Statistical significance or CIs for model comparisons. |

## Agent module (new; 11 items)
Anchors: 2 = all elements present; 1 = some present; 0 = none on any surface.

**A1 Run count per reported number (e).** Elements: (i) number of runs per task behind each headline score; (ii) seed or sampling policy; (iii) whether runs are independent.
**A2 Uncertainty with stated resampling unit (e).** Elements: (i) CI or SE on headline scores; (ii) the resampling or variance unit stated (task, patient, run); (iii) clustering of tasks within patients or templates addressed.
**A3 Action-level repeat-run reliability (a).** Elements: (i) agreement of tool actions or action sequences across identical reruns, or (ii) agreement of final environment state across reruns, or (iii) a pass^k-type all-runs metric. 2 = any metric at action or state level with its run count; 1 = score-level variance only; 0 = neither. (Score-level SD alone is C13/C14 territory, not A3.)
**A4 Model and harness pinning (a/e).** Elements: (i) exact model identifiers with version or date; (ii) decoding parameters; (iii) harness version or commit for reported results.
**A5 Tool contract specified (b).** Elements: (i) machine-readable schema for every tool; (ii) documented side effects per tool (reads vs writes); (iii) documented return semantics including error and failure returns. Record whether (ii) reaches S5.
**A6 Tool contract verified (b).** Elements: (i) tests or conformance checks that tools behave as documented; (ii) any simulated, stubbed or no-op tool behaviour disclosed; (iii) that disclosure reaches the agent-visible surface (S5). 2 needs (iii) when any simulation exists.
**A7 Write-action disclosure (d).** Elements: (i) which actions mutate state or are irreversible in the clinical frame (orders, prescriptions, notes, messages); (ii) whether writes are executed, simulated or sandboxed; (iii) whether unsafe or unnecessary writes are scored or penalised. Record S5 reach for (ii).
**A8 Grader reads state, or justifies transcript grading (c).** Elements: (i) grader input stated (end state, action log, transcript, or LLM judgement); (ii) if not end state, rationale given; (iii) grader validated against known state changes (injected correct and incorrect outcomes, with error rates). 2 needs (iii).
**A9 Agent-channel contamination (f).** Elements: (i) controls on answer leakage through tools, retrieval or web access during runs; (ii) held-out or private split; (iii) canary or provenance marker on released tasks.
**A10 Slice reporting (g).** Elements: (i) results per task family; (ii) results per patient subgroup where demographic fields exist; (iii) slice sizes reported with the slice results. NA for (ii) only when no demographic fields exist, stated.
**A11 Environment-state provenance (h).** Elements: (i) source of patient records or seed state stated as real de-identified, synthetic (with generator), or mixed; (ii) governance for real data (IRB, DUA, de-identification method); (iii) redistribution terms for environment data separate from code licence. Never infer "synthetic"; score only what the benchmark states.

## Open design questions (for Opus adjudication at pilot)
1. A4 overlaps BetterBench reproducibility items; keep only if pilot shows variance across benchmarks.
2. Whether to compare our C-module scores with MedCheck v2's per-benchmark scores on overlapping benchmarks (MedAgentBench, AgentClinic, MediQ, MedChain, MVME, MedAgentsBench, MedJourney) as a concurrent-validity check. Depends on MedCheck releasing per-benchmark scores (not found so far).
