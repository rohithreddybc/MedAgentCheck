# Subagent transport for the Claude-family coder

Runs coder `sonnet` (groups=1, frozen 150,000-token cap) through a Claude Code subagent instead of the
logged-out `claude -p` CLI. Nothing under `scorer/agentaudit/` is edited; both scripts import it.

1. `python export_prompts.py [--bench NAME]` writes `prompts/<bench>/system.txt`, `user_part01.txt ...` and
   `meta.json`. The parts are the exact rendered user prompt split on chunk boundaries (a part never starts inside a chunk; <= 60,000 characters and
   <= 1,500 lines each unless one chunk is larger); concatenated in order they equal the prompt byte for byte. `meta.json` holds the prompt
   hashes, part list and the output schema.
2. A subagent reads the prompt and writes `responses/<bench>.json` (template below).
3. `python import_responses.py [--run DIR] [--bench NAME] [--force]` checks that the packet still renders the
   exported prompt, then calls the package's own `score_packet` with a replay backend. The answer is stored as
   `scoring/<bench>/sonnet/group1.json` (raw response, parsed by `parse_packet_response`), `results.json` and
   `coding/<bench>/<item>/sonnet.json`, and verified by `run_verify`. Model id recorded:
   `claude-sonnet-5-5 via Claude Code subagent`; transport: `subagent` (group record, attempt meta, coding records).
   `--run` defaults to `audit/`; point it at a copy for tests.

## Subagent instruction template

Replace `<bench>` and `<N>` (`n_parts` in `meta.json`). Use a Sonnet subagent, one bench per subagent, with the
Read tool only (no web, no shell commands needed for the reading).

```
You are an annotator applying a fixed coding manual to one benchmark's evidence packet. The complete task is stored
in files; you must read all of it before answering.

1. Read audit/transport/prompts/<bench>/system.txt with the Read tool. Those are your system instructions.
2. Read audit/transport/prompts/<bench>/user_part01.txt through user_part<NN>.txt IN ORDER, one Read call per file,
   reading each file completely (if a read is truncated, continue with offset/limit until the whole file is read).
   Together the parts are one user message. Ignore the line-number prefixes the Read tool adds. Do not skip, skim or
   summarise parts. Use no other source of information: no web, no repository access, no prior knowledge of the benchmark.
3. Follow the instructions in the prompt. Answer ONLY with the JSON array required by its output schema: 25 objects,
   items C1..C14 then A1..A11, quotes copied verbatim from the packet with their chunk ids. No prose, no code fence.
4. Write exactly that JSON array to audit/transport/responses/<bench>.json (Write tool), then reply "done <bench>" and
   nothing else.
```

Notes. The packet for `healthcraft` is over the cap even after the frozen drop rule (S2 alone exceeds it;
`over_cap` flag in `meta.json`) and is about 390k estimated tokens, beyond a 200k context. Estimates use the
package's 4 characters per token; real tokenization of code-heavy packets can be higher.

## Validation runs (gold, perturbation, retest)

`export_validation.py` and `import_validation.py` extend the transport to the three validation runs with the same
principles (frozen package renders the prompts, replay backend, model id and transport as above). Prompts go to
`prompts_gold_<set>/<bench>/`, `prompts_perturb/<variant>/`, `prompts_retest/<bench>/`; answers go to
`responses_gold_<set>/<bench>.json`, `responses_perturb/<variant>.json`, `responses_retest/<bench>.json`. The subagent
template above applies with the matching directory names.

    python export_validation.py gold --set abc|betterbench      # run dir audit/gold_abc | audit/gold_bb
    python export_validation.py perturb [--no-base]             # run dir audit/perturb
    python export_validation.py retest                          # run dir audit/retest (package layout under audit/)
    python import_validation.py --mode gold --set abc|betterbench
    python import_validation.py --mode perturb
    python import_validation.py --mode retest

Known limits. (1) Perturbation eligibility depends on base results (`resolved/`, `verified/` of the audit run); none
exist yet, so the current perturbation prompts are provisional (no deletion cells; `meta.json` says so) and must be
re-exported once the base run is resolved. (2) `map_bench_dirs` of the package finds only 34 of the 45 packets by the
audit slugs; `audit/perturb/packets` therefore uses the package's first candidate name for the other 11. For retest the
package's `plan_retest` maps 8 of the 10 drawn benchmarks; the transport maps all 10 through the manifests'
`frozen_list_id`, but `agentaudit retest` itself would skip the unmapped two. (3) Audit packets were curated after the
build (`privacy_exclusion`: patient-identifier data files removed from chunks.jsonl); variant packets are rebuilt from
sources, so those sources are dropped from the `audit/perturb` copy. One chunk differs from the audit packet as a result
(healthcare-ai-gym, `tasks.json:40-50`). (4) Gold packets for CyBench (ABC) and BIG-bench (BetterBench) were not built:
the repositories are 1.1 GB and 0.9 GB and need `--allow-large`.

Update 2026-10-06. Base results exist for 44 of 45 benchmarks, so `prompts_perturb/` was re-exported with eligibility from
`audit/resolved` and `audit/verified` (deletion cells included); the earlier export is kept in
`prompts_perturb_provisional/`. HealthCraft has no base result, so the package rule (`sampling.eligible`: no base level
means not eligible) drops all 20 cells of its variant v13; the variant is not scored and its (unperturbed) prompt is in
`prompts_perturb_skipped/v13/`, outside the import set.

Update 2026-10-06 (OpenAI coder). `run_codex_prompts.py` (perturbation) and `run_codex_retest.py` (the two retest benchmarks that the package's retest command skips, synthetic-hospital and diaggym-diagbench) send the exported prompts to the package's `CodexHeadlessBackend` (gpt-5.5, read-only sandbox) and store the answers in `responses_perturb_codex/` and `responses_retest_codex/`. `import_validation.py --mode perturb --coder codex` and `--mode retest --coder codex` score them with the package's own functions. Every retest import ends with `finalize_retest`: it resolves the retest run and rewrites `audit/retest/retest_agreement.json` for all 10 drawn benchmarks, mapping frozen ids to packet directories through the manifests (the package's `map_bench_dirs` is replaced in memory for that call only).
