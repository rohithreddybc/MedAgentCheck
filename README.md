# MedAgentCheck

An agent-specific validity and reliability checklist for benchmarks of action-taking medical and clinical AI agents, plus `agentaudit`, a quote-verified automated scorer. MedAgentCheck extends MedCheck ("Beyond the Leaderboard: Rethinking Medical Benchmarks for Large Language Models", ACL 2026; arXiv 2508.04325) to agentic benchmarks; it is an independent project, not affiliated with the MedCheck authors.

## agentaudit

`agentaudit` scores a benchmark against a 25-item documentary checklist (14 reused core items, 11 agent-specific items; rubric v1 and coding manual v1.0 in `rubric/`) using only evidence that can be quoted. Every score of 1 or 2 must carry a verbatim quote that the tool checks against the evidence packet; coders from different model families score the same packet, and a level is accepted only when coders from at least two families agree on it with verified quotes. The tool is the method behind the study in `protocol/protocol-v1.md` (clinical agent benchmarks, 45 benchmarks listed in `eligibility/frozen_list_v1.csv`).

Authors: Rohith Reddy Bellibatlu (rohithreddybc@gmail.com) and Manpreet Singh.

## Status of this repository

Status: audit run 2026-10-05/06; results in `results/`. The protocol was frozen at commit 713d078 before any item was coded. The scorer at 713d078 is frozen: the files listed in `FREEZE_MANIFEST.json` are unchanged and `agentaudit freeze --verify .` still passes. Later commits touch only this README, the citation metadata and new folders, and those folders are post-freeze outputs, not part of the method:

- `results/`: resolved cells with verified quotes and flags, per-benchmark score cards (`results/scorecards/`), raw coder responses with model ids and timestamps, agreement with the published expert scores (statistics only), perturbation and retest outputs, analysis outputs. See `results/README.md`.
- `transport/`: the Claude Code subagent transport scripts and protocol, and the coder isolation audit.
- `reruns/`: per-episode metrics, canonical action sequences, verdicts, model digests and timestamps of the executed reruns (no transcripts or task texts).
- `analysis/`: the analysis scripts used for the paper (new files, and `postfreeze/` versions of two frozen scripts) and `analysis/out/RESULTS_SUMMARY.md`.

Not released: evidence packets and their sources, paper full texts, benchmark repository files, task or case texts, patient-like records, rerun transcripts, and the published expert scores of ABC and BetterBench (agreement statistics only). Quotes of at most 25 words from the audited benchmarks are kept so that each score can be checked. Score cards are offered to the benchmarks' maintainers; corrections are welcome as GitHub issues on this repository.

`FREEZE_MANIFEST.json` lists the SHA-256 of every file that defines the method: the protocol, the rubric and coding manual, the item definitions, the prompts, the perturbation and decoy texts, the seeded samples (perturbation sample, ABC and BetterBench item lists, gold version pins), the frozen benchmark list, and the code of packet building, scoring, quote verification, resolution, perturbation and gold validation. Check a checkout with

    agentaudit freeze --verify .

The manifest also lists, by hash only, the inputs that are used but not redistributed here: the ABC and BetterBench item texts and the published gold scores. ABC's repository has no licence and MedCheck has no rubric licence, so their texts are referenced by id and paraphrased, never reproduced. Pilot transcripts and benchmark data are not part of this repository; the run outputs of the audit are in `results/`.

## Reproduce

1. Check the frozen method: `agentaudit freeze --verify .`.
2. Rebuild the score cards from the released cells: `python analysis/make_scorecards.py` (needs only `results/`).
3. Rerun the audit: build packets from `results/manifests/*.yaml` at the pinned paper version and repository commit (`agentaudit packet`), score them with your own coder backends (`agentaudit score-packet`), then `resolve`, `agree`, `report`. `results/packet_manifests/` gives the file hashes and the packet hash to compare against. Our coders were hosted models without temperature control (gpt-5.5 through the Codex CLI; claude-sonnet-5-5 through Claude Code subagents, see `transport/README.md`), so levels may differ from ours; the released raw responses are the record of what we obtained.
4. Validation runs: `agentaudit perturb` and `agentaudit gold` as described below. The published scores of ABC (arXiv 2507.02825v5) and BetterBench are not redistributed; obtain them from the sources, check them against the hashes in `FREEZE_MANIFEST.json` (`inputs_not_shipped`) and pass `--research-dir`.
5. Analysis: the scripts in `analysis/` read the authors' working-tree layout (see `analysis/README.md`); their outputs are in `analysis/out/RESULTS_SUMMARY.md` and `results/analysis_out/`. The grader-versus-state and judge re-run analyses need rerun transcripts and final states, which are not released.

## Install

Python 3.10 or later.

    pip install .            # from a clone of this repository
    pip install ".[test]" && pytest

## Use

The audit of 2026-10-05/06 used two coders, `sonnet` (claude-sonnet-5-5, through Claude Code subagents) and `codex` (gpt-5.5, through the Codex CLI); the Gemini and Mistral backends and the `--coder gemini` examples below were implemented but not run, so the audit's resolution rule had two families. The backends are your own: the Claude CLI (`claude auth login`), the Codex CLI (`codex login`), a Gemini API key (`GEMINI_API_KEY`), optionally a Mistral key (`MISTRAL_API_KEY`). `agentaudit doctor` reports which are live. Model identifiers are recorded in every result file.

    agentaudit packet manifest.yaml --out runs/x          # evidence packet at a pinned paper version and repo commit
    agentaudit score-packet --out runs/x --coder sonnet --coder codex --coder gemini
    agentaudit resolve --out runs/x                       # two-family resolution rule
    agentaudit agree   --out runs/x                       # Krippendorff alpha, per item and overall
    agentaudit report  --out runs/x                       # score cards

A manifest names the benchmark, its arXiv id and version, and the repository commit:

    name: agentclinic
    arxiv: {id: "2405.07960", version: v5}
    repo: {url: https://github.com/SamuelSchmidgall/AgentClinic, commit: b6fbe22300e99a267a7ac94eaa465ab552eef741}

### Validation

    agentaudit perturb --out runs/x --frozen-list eligibility/frozen_list_v1.csv --plan-only
    agentaudit perturb --out runs/x --frozen-list eligibility/frozen_list_v1.csv --coder sonnet --coder codex --coder gemini
    agentaudit perturb --out runs/x --summarise

The perturbation suite uses 40 variant packets drawn with seed 20261004 from the 45 listed benchmarks. In each variant every item receives exactly one perturbation (inject, buried, paraphrase, deletion or decoy), assigned so that each item and type occurs exactly 8 times, which gives 1,000 labelled cells; a variant is scored once with the normal 25-item call, so a coder needs 40 calls. Buried texts go to a late S1 appendix; half of the decoys are the full level-2 text placed only in an S4 code comment, which tests that code never counts as reporting (coding manual G1a). Cells that the base audit makes uninformative are dropped and counted. Labels are fixed by construction; the summary gives sensitivity and specificity with Wilson 95% intervals per item, per variant type, per coder and for the resolved score. Perturbation texts for different items share a packet, so a cell's label holds for its target item only (for example, the text injected for A1 mentions temperature, which C13 and A4 also read); scores of the unlabelled items are stored for every variant so that this interference can be measured. It measures validity under perturbation, not agreement with ground truth.

    agentaudit gold --set betterbench --out runs/x --research-dir <dir with gold/ and instruments/> --coder sonnet --coder codex --coder gemini
    agentaudit gold --set abc ...

The gold mode scores the benchmarks that ABC (10 benchmarks) and BetterBench (23 benchmarks) had experts assess, with each source's own item texts and scale, and reports agreement with the published scores (Cohen's kappa for ABC, weighted kappa for BetterBench, raw agreement), per coder and resolved. The gold data are not part of this repository; obtain them from the sources and pass `--research-dir`. Outputs for ABC contain statistics only.

`agentaudit --help` lists every stage. The BM25 retrieval and tagging stages (`retrieve`, `tag`, `code`) are kept as an ablation of the retired retrieval design.

## Licences

Code: MIT (`LICENSE`), copyright Rohith Reddy Bellibatlu and Manpreet Singh. Data: the checklist and the audit results (`results/`, `reruns/`) are CC BY 4.0 (`LICENSE-checklist`, `results/LICENSE`); quoted passages of at most 25 words remain the work of their authors. Checklist text (the files in `rubric/`, and the item and anchor text in `agentaudit/items.yaml`): CC BY 4.0 (`LICENSE-checklist`). The protocol and eligibility files (`protocol/`, `eligibility/`) are also CC BY 4.0 (`LICENSE-checklist`).

## How to cite

Placeholder, to be filled when a DOI exists. No DOI has been issued.

    Bellibatlu, R. R., and Singh, M. agentaudit: a quote-verified, cross-family scorer for agentic benchmark documentation. Version 0.1.0. [DOI to be added]
