# results/

Post-freeze outputs of the audit run of 2026-10-05 and 2026-10-06. Nothing here is part of the frozen method (`FREEZE_MANIFEST.json` covers the files at commit 713d078 only). Licence: CC BY 4.0 (`LICENSE`, `../LICENSE-checklist`), except for the quoted passages described below.

| Folder | Content |
|---|---|
| `resolved/` | One JSON per benchmark (45; `healthcraft` has no cells because its packet exceeds the frozen 150,000-token cap even after the drop rule). Each of the 25 cells holds the resolved level, status, fallback flag, majority level, the two coders' raw and effective scores, verified quotes with chunk ids, contradiction flags and quotes, element flags, coder rationale, model id, timestamp and prompt and packet hashes. `resolved.csv` and `summary.json` are the flat tables. |
| `scorecards/` | `<bench>.md` per benchmark, `scorecards.csv` (1,100 benchmark-item rows), `benchmarks.csv`. Generated from `resolved/` by `analysis/make_scorecards.py`. A 0 means not reported on the surfaces checked; contradiction flags are candidates only. |
| `coder_responses/base/` | Per benchmark and coder: `group1.json` (raw response, model id, timestamps, attempt metadata, prompt hashes), `results.json` (parsed), `packet_manifest.json` (chunk ids sent, cap, drops). Coders: `claude-sonnet-5-5 via Claude Code subagent` and `gpt-5.5` (codex exec). |
| `coder_responses/sonnet_subagent_raw_*`, `codex_raw_perturb`, `codex_raw_retest` | The raw JSON arrays that the Claude subagents and the Codex CLI returned, for the audit, perturbation and retest runs. |
| `manifests/`, `packet_manifests/` | Benchmark manifests (paper version, repository commit) and packet manifests (file list with SHA-256 hashes, token counts, packet hash). The packets themselves are not released. |
| `gold/abc/`, `gold/betterbench/` | Agreement with the published expert scores: statistics only (Cohen's kappa, weighted kappa, raw agreement, per-item agreement, bootstrap intervals). The published scores are not redistributed. |
| `perturbation/` | Final perturbation run: `plan.json`, `summary.json`, `summary.csv` and per-variant coder outputs (39 of 40 variants ran; the missing one is built on HealthCraft). The perturbation texts in `plan.json` and the variant records are the frozen package texts. Variant packets are not released. |
| `retest/` | Retest run on 10 benchmarks: coding, resolved cells, verified quotes, scoring, agreement. Retest packets are not released. |
| `analysis_out/` | Agreement, summary and table outputs of the analysis scripts (CSV and JSON), including the `provisional/` pre-final runs. |

## What was removed or changed

- Evidence packets, packet sources, paper full texts, repository files, benchmark task or case texts, patient-like records and the prompts that embed packets are not released. Packet manifests keep file paths, URLs, hashes and counts; the names of files removed for patient-identifier fields (privacy exclusion of 2026-10-05) are replaced by a count.
- Coder quotes are kept at 25 words or fewer. 38 quotes of 26 to 52 words were cut to 25 words and marked `"truncated": true` with the original word count and SHA-256; raw responses that held such quotes were re-serialised with the same cut. No other field was altered.
- Local file paths (user name, temporary directories) are replaced by `<local-path>`.
- Quoted passages are third-party text, included for verification of a score and not relicensed.

## Reading the data

The final level of a cell is `final`; `status` is `resolved` (two families agree with verified quotes), `established_zero`, `not_established` (falls back to 0) or `na_rejected_as_zero`. `effective` is the coder's score after quote verification (a 1 or 2 without a verified quote counts as 0). Coder scores are model outputs from hosted models without temperature control, so a rerun may differ. Gold-set coder responses and the ABC and BetterBench item and score files are not included.
