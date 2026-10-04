# Study protocol v1 (supersedes osf-protocol-v0.md). DRAFT; frozen by hash and public commit before any audit coding

**Working title:** Can Medical AI Agent Benchmarks Be Trusted? A Validity and Reliability Audit
**Authors:** Rohith Reddy Bellibatlu (Independent Researcher, rohithreddybc@gmail.com, ORCID 0009-0003-6083-0364); Manpreet Singh (Boston University).
**Freeze:** the SHA-256 manifest of this file, `rubric/`, `scorer/` (prompts, items.yaml, queries.yaml, retrieval parameters, resolution rule) and `research/eligibility/frozen_list_v1.csv`, committed to a public repository. The commit timestamp precedes all audit coding, and publishing needs Rohith's approval. The paper says "protocol frozen before coding", never "pre-registered".

## 1. Questions
- **RQ1 Reporting.** For the 45 action-taking clinical agent benchmarks released 2024-01-01 to 2026-10-03, what share report each agent-specific property (A1-A11) and each reused core property (C1-C14)?
- **RQ2 Can the audit be automated reliably?** How far do independent coders from two model families agree when they score identical evidence (Krippendorff's alpha, cross-family pair as the primary figure)? How sensitive and specific is the full pipeline, retrieval plus coding, under known-answer perturbations?
- **RQ3 Executed behaviour.** On 5 runnable benchmarks not executed by papers 20 or 21, how stable are agent actions and grader verdicts across 5 identical reruns, how wide are headline-score intervals at 1 run versus 5, and, where state is observable, how often does the grader disagree with the end state?
- Exploratory, labelled as such: reporting by interface type and release year.

## 2. Population
Defined in `protocol/eligibility.md` (E1-E5, X1-X9, R1-R7, R6a). The search ran 2026-10-03 over arXiv, PubMed, the ACL Anthology and backward chaining. 7,233 unique records; 186 assessed in full text; 45 included. The flow is machine-computed in `research/eligibility/flow_counts.md`. Screening and eligibility were LLM-assisted (Claude Sonnet), with Opus adjudicating 67 uncertain calls under rules written down before any coding. One merge defect was found and corrected (20 records rescreened), and it is reported.

## 3. Instrument
Item list in `rubric/rubric-v1.md`; anchors and global rules G1-G7 in `rubric/coding-manual-v1.0.md`. Anchors were developed in two pilot rounds on five benchmarks; agreement between two Sonnet coders was 63/75, then 46/50. The pilot sheets are development data only and are discarded. The five pilot benchmarks are re-coded by the frozen pipeline.

## 4. Automated audit (`scorer/ARCHITECTURE.md`)
Steps (architecture v3): evidence packets at pinned versions, capped at 150k tokens by a deterministic S4 truncation rule; whole-packet scoring with no retrieval step, so every coder reads the identical packet. Coders from three families score all 25 items per benchmark in one call (or fixed item groups): Anthropic claude-sonnet-5-5 (Claude CLI), OpenAI via Codex CLI (model ID recorded at run time), and Google Gemini (free API; model ID recorded). Mistral (mistral-large-latest) is an optional fourth family. Temperature 0 where the backend allows it. Then verbatim quote verification and resolution. BM25 retrieval and exhaustive tagging are reported only as an ablation (dev-set recall 34-53%).
**Resolution rule:** the final level is the highest s that coders from at least two distinct families assign at s or above, each with verified quotes. Otherwise the cell is "not established" and scores 0. NA requires coders from at least two families. Reported: the share of cells resolved by fallback, and a majority-rule sensitivity analysis.
**Agreement:** ordinal Krippendorff's alpha per item and overall; NA counts as missing; bootstrap CIs over benchmarks. Cross-family pairs are primary; the all-three figure is secondary.
**Contradiction flags (G2):** reported only after a check against the benchmark's own documentation and a right-of-reply offer.

## 5. Validation without human coders
**Perturbation suite:** for each item, packet variants with labels fixed by construction: easy injection, buried, paraphrase, deletion and decoy near-miss. Sample: 8 variants per item per type, drawn by seed 20261004 across the 45 benchmarks. Reported: sensitivity and specificity per item and per variant type, with Wilson 95% CIs, for each coder and for the resolved pipeline. Described as validity under perturbation, not as ground truth.
**Published-human-gold check (no new human coding):** the closest automated-coding work validates against human labels (Rystrom 2601.20617; Kunilovskaya 2606.02255). We use human scores that are already published.
(a) ABC (2507.02825, App. D) gives binary expert assessments of 10 agentic benchmarks. The pipeline scores those benchmarks on the ABC-derived items (C6-C11, plus the other ABC items whose assessments are reported), with the item text adapted only to ABC's binary scale.
(b) BetterBench (2411.12990) released per-criterion expert scores for 24 benchmarks, of which 23 are obtainable (MMMU is missing from the released data) (CC BY 4.0). The pipeline scores them on BetterBench's own items, using a seeded sample of 20 items × 23 benchmarks.
Reported: agreement with the published scores (Cohen's kappa or weighted kappa, raw agreement), per coder and resolved. Caveat: those scores refer to the benchmark versions available when ABC and BetterBench scored them, so we pin the nearest version by date.
**External check:** maintainer right of reply on their own scores. Reported: the response rate, and corrections in each direction (score raised or lowered), with the evidence surface each correction cites.

## 6. Executed scoring
As in `research/executed/plan-v1.md` (run design v2): the selection rule with its amendments; 15 seeded tasks × 5 repeats × 3 conditions per benchmark; all roles run locally on ollama, pinned by digest (agent gpt-oss:20b primary and qwen3:4b-instruct-2507-q8_0 replication; simulator and judge llama3.1:8b-instruct-q4_K_M at temperature 0). Operational metrics: action divergence, verdict instability, pass^k with cluster bootstrap CIs, CI width at 1 versus 5 runs, and grader-versus-state disagreement. Results are per-benchmark, never population rates. No MedAgentBench (v1 or v2), tau2-bench, AgentDojo or MM-ToolSandbox execution. No benchmark data redistributed.

## 7. Analysis
RQ1: per-item share REPORTED (score of 1 or more) and fully reported (2), with Wilson 95% CIs, from the resolved scores. RQ2 and RQ3 as above. No confirmatory hypothesis tests.

## 8. Disclosure
Every model, ID, access date and prompt is listed in Methods and released (IEEE generative-AI policy). LLM-assisted search, screening, eligibility, coding and drafting support are all disclosed.

## 9. Deviations
Logged in `decisions/decision-log.md` with their dates and reported in the paper.
