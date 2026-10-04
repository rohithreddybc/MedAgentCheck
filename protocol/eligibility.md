# Eligibility criteria (v1, Opus, 2026-10-04) — applied at full-text stage

Search window: first public release 2024-01-01 to 2026-10-03 (search run 2026-10-03). Sources: arXiv, PubMed, ACL Anthology, backward chaining (Gong JMIR 2025; Xu JBI 2026 + repo; Gridach CSUR 2026, partial). See `research/search/log.md`.

## Definition (stated once; every later use means this)
An **action-taking clinical agent benchmark** is a released evaluation resource in which an LLM-based agent, in a clinical-care setting, issues actions through a defined action interface (tool or function calls, API or FHIR requests, GUI operations, code execution, or discrete order/test actions in an environment), and the benchmark observes or grades the results of those actions.

## Include (all must hold)
E1. Primary contribution is a benchmark, environment, or evaluation suite (not a method evaluated on someone else's benchmark).
E2. Meets the definition above: at least one task type requires actions through a defined action interface.
E3. Clinical-care setting: patient care, clinical documentation, ordering, EHR work, triage, clinical decision support, or clinician-facing workflow.
E4. Released or publicly described 2024-01-01 to 2026-10-03.
E5. Enough public documentation to code (paper or technical report; repo optional).

## Exclude (record the first that applies)
X1 NOT_BENCHMARK. X2 DIALOGUE_ONLY: the only agent action is conversational turns (e.g., asking a simulated patient questions) with no defined action interface. X3 STATIC_QA: no interaction. X4 NOT_CLINICAL_CARE: biomedical research, ML engineering, drug discovery, education-only. X5 OUT_OF_DATE. X6 PAYER_OUT_OF_SCOPE: prior authorization, utilization review, claims, Medicaid managed care; listed as "out of scope pending review", never scored. X7 DUPLICATE or superseded version (score the latest version; versions of one benchmark, e.g. MedAgentBench v1/v2, MedBench v4/v5, are separate units only if they have separate task sets and papers). X8 NO_DOCUMENTATION.

Borderline rule: dialogue benchmarks where test ordering or examination is a discrete, enumerated action that the environment answers (AgentClinic-style) meet E2. Free-text requests for information inside dialogue do not.

Dialogue-only (X2) count is reported in the flow diagram, so a reader sees the size of the excluded neighbour class.
## Clarifications added 2026-10-04 (before any coding)
- **R1 Co-primary resource.** A paper that proposes a method AND releases a named benchmark or environment with its own tasks meets E1. A training environment evaluated only on pre-existing benchmarks does not (X1).
- **R2 Interface ownership.** If the action interface belongs only to the authors' agent and the benchmark itself is a static dataset, the benchmark fails E2 (X3).
- **R3 Non-LLM agents.** Environments evaluated only with non-LLM policies (RL policies, small transformers) fail the definition. New code **X9 NOT_LLM_AGENT**.
- **R4 Typed actions.** A typed action channel answered by the environment (enumerated or typed action names, even with free-text arguments) meets E2. Free-text requests inside dialogue do not (X2, per the borderline rule).
- **R5 Offline action prediction.** Actions predicted against recorded screens or logs and graded against annotations, with no environment executing them, fail E2 (X3).
- **R6 Clinical-care scope.** E3 needs a patient case or a care workflow (including hospital administration that is not payer-side, and patient education). Clinical data science or research analysis over EHR datasets, consumer wearables, and literature or fact retrieval without a patient are X4.
- **R7 Mixed suites.** Only the agentic component is scored. The action interface must be verifiable from public documentation; if not, X8.

- **R6a EHR querying vs research analytics (2026-10-04).** Agents that retrieve or act on records as part of care or hospital operations, including database question answering posed by clinical staff, meet E3. Benchmarks whose goal is cohort-level research analytics, report generation or study reproduction are X4. A suite mixing both is included under R7 and scored on its care component. Applied: EHR-ChatQA, EHR-RobustGym, EHR-Complex stay INCLUDE; ClinLens, MedAgentBoard, RWE-bench stay X4.
