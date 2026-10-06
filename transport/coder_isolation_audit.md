# Coder isolation audit (Claude Sonnet subagent coder)

Source: `<local-path> (193 transcripts scanned, streamed). Script: `analysis/coder_isolation_audit.py`.

A coder run is a subagent whose first prompt contains the annotator template. In scope: Read of the assigned `prompts*/<bench>/` files (system, meta.json, user parts) and Write of the assigned `responses*/<bench>.json`. Bash/Grep/Edit calls are reported separately as scoped when every path they touch is the run's own prompt directory or response file and they reference no gold, pilot, resolved, verified, scoring, paper, analysis or web target. Anything else (another Read or Write target, another bench's files, any other path, web) is out of scope. The tool-call total includes one SubagentHandback call per run. Only session b70619cc exists in the project transcript folder (192 subagent transcripts, 124 of them coder runs; the rest are build, analysis and review subagents).

## Summary

- Coder subagent runs: 124
- Tool calls in those runs: 1486
- Bash/Grep/Edit calls confined to the assigned prompt dir or response file (see below): 52
- Out-of-scope calls: 0
- Runs with at least one out-of-scope call: 0
- Runs whose prompt carries the isolation instruction: 124 of 124

- Model ids (assistant message.model, count of messages): `claude-sonnet-5-5` x1947


## Counts per run type

| Run type | Runs | Tool calls | Read | Write | Bash | Grep | Other | Out of scope |
|---|---|---|---|---|---|---|---|---|
| main | 44 | 535 | 422 | 44 | 12 | 11 | 46 | 0 |
| gold | 31 | 350 | 288 | 31 | 0 | 0 | 31 | 0 |
| perturb | 39 | 487 | 383 | 39 | 14 | 8 | 43 | 0 |
| retest | 10 | 114 | 93 | 10 | 1 | 0 | 10 | 0 |

Gold runs by prompt directory: gold_abc: 9, gold_betterbench: 22


## Isolation instruction in the prompt (quote)

- (53 runs) "Use no other information source (no web, no repos, no prior knowledge).
3."
- (39 runs) "Use no other information source; do not open any other file in the folder.
3."
- (22 runs) "Use no other information source.
3."
- (10 runs) "Use no other information source. Do not look at any other file in the folder."

## Out-of-scope accesses

None.

## Context injected by the harness (attachment records in coder transcripts)

Attachment types: total_tokens_reminder x1195, prompt_snapshot x248, deferred_tools_delta x124, environment x124, model x124, skill_listing x124, instructions x124, session_context x124, date x124, credential_org x124, agent_listing_delta x124, mcp_instructions_delta x124, read_truncation_notice x71, deferred_tools_record x5, edited_text_file x1. These are harness-supplied (instructions, skill/agent listings, environment, token reminders), not files read by the subagent. Claude Code loads the project CLAUDE.md into every subagent; that is context the OpenAI coder did not have. It holds no benchmark gold or pilot content, but it is a difference between transports.


## Scoped Bash/Grep/Edit calls (confined to the run's own prompt directory or response file)

They search or count inside the run's own prompt parts, or validate/repair quotes in its own response file. No other path, no gold/pilot/resolved/other-bench path, no web. Count per transcript and tool:

- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a09dbe96b8e8ede24.jsonl: Edit x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2f75027c78909179.jsonl: Edit x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a563c3bb1807ea2e6.jsonl: Bash x4
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a563c3bb1807ea2e6.jsonl: Grep x5
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8d3c742b9193a729.jsonl: Bash x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8d3c742b9193a729.jsonl: Edit x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a918b8c5d13602851.jsonl: Bash x4
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a918b8c5d13602851.jsonl: Grep x3
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a99a387b35955d095.jsonl: Bash x2
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a99a387b35955d095.jsonl: Grep x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa205e1caa56cd96e.jsonl: Bash x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa2aacb257531d5e7.jsonl: Bash x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aabbdf3fd284c3880.jsonl: Grep x2
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ab51e4e24983e6d20.jsonl: Grep x5
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-acfc4583d85481d48.jsonl: Bash x14
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-acfc4583d85481d48.jsonl: Grep x3
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-adf212b102aae133e.jsonl: Edit x1
- b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-af6a43a0da9992cdd.jsonl: Edit x2

## Per-run listing

| Transcript | Type | Bench/variant | Model(s) | Calls | Out of scope |
|---|---|---|---|---|---|
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a067a81730f5f2d35.jsonl | main | vivabench | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a08f00cfeef0de2f3.jsonl | main | clinenv | claude-sonnet-5-5 | 11 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a090671f51f737ea2.jsonl | main | cp-env | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a09dbe96b8e8ede24.jsonl | perturb | v19 | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a0c41403403415377.jsonl | gold | kernelbench | claude-sonnet-5-5 | 10 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a0c9e590929a1a745.jsonl | main | diaggym-diagbench | claude-sonnet-5-5 | 25 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a0f2b890a00b1b971.jsonl | main | rada-benchplat | claude-sonnet-5-5 | 15 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a0f3f948376c3620c.jsonl | retest | clinenv | claude-sonnet-5-5 | 11 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a10eb16c210b3dbdd.jsonl | gold | arc-challenge | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a1692b2e35a2a593c.jsonl | perturb | v07 | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a1cd38b9158892e4e.jsonl | main | rha-safety | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a20e7feaca2c92ef6.jsonl | perturb | v33 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2181adb3d590177a.jsonl | retest | cp-env | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2384d6831cd21157.jsonl | gold | swe-bench_verified | claude-sonnet-5-5 | 14 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2611356df169aa41.jsonl | perturb | v23 | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2d041487989ed0b8.jsonl | gold | truthfulqa | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2e1929532c0ce562.jsonl | main | art | claude-sonnet-5-5 | 4 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a2f75027c78909179.jsonl | main | medagentbench-v1 | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a309e5ddf54f131d1.jsonl | main | clinicare-bench | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a319a0b13d46a75dd.jsonl | gold | swe-lancer | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a322026a7b05768e3.jsonl | main | fhir-agenteval | claude-sonnet-5-5 | 5 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a33d840fb848d7107.jsonl | gold | ale | claude-sonnet-5-5 | 19 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a33edfe99a72e2e12.jsonl | perturb | v17 | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a37274178ed1aca24.jsonl | perturb | v18 | claude-sonnet-5-5 | 11 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a37a59c18441205af.jsonl | perturb | v21 | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a3bcb9d6641386ab6.jsonl | perturb | v35 | claude-sonnet-5-5 | 15 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a3bd255299ae4fb62.jsonl | main | clinicalagent-bench | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a3dfeb6dde7119d5f.jsonl | main | ehr-chatqa | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a42b33fa4cf5c9bc3.jsonl | gold | bird-bench | claude-sonnet-5-5 | 12 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a438807c7886ca983.jsonl | main | ehr-complex | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a44cb3a80351be7c2.jsonl | perturb | v15 | claude-sonnet-5-5 | 10 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a452e19c5d28867f8.jsonl | main | medagentbench-v2 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a4620a8487c6e767d.jsonl | perturb | v16 | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a4dfe79b62b3dfb8b.jsonl | gold | gaia | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a4e66098c2431b667.jsonl | perturb | v02 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a4f4bdd530886f8bd.jsonl | main | medimageedu | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a4f678dcb5d2b03ab.jsonl | perturb | v12 | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a523a7cf5a43a7550.jsonl | main | synthetic-hospital | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a529f5c5597704152.jsonl | perturb | v01 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a532cf8c8e09b325e.jsonl | perturb | v05 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a53c038a6d56d6a28.jsonl | retest | h-adminsim | claude-sonnet-5-5 | 14 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a563c3bb1807ea2e6.jsonl | main | medcta | claude-sonnet-5-5 | 34 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a58adaa1ebb2a517d.jsonl | perturb | v32 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a590a5b303934293c.jsonl | gold | safebench | claude-sonnet-5-5 | 25 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a609ef3ecb889eae9.jsonl | gold | procgen | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a625565021705f4a2.jsonl | main | medflowbench | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a625f56ffa9548a2a.jsonl | gold | bold | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a62e093cb3e2deb5a.jsonl | perturb | v40 | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a6361c6c92349c7da.jsonl | gold | tau-bench | claude-sonnet-5-5 | 15 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a6436cd12fab5c94b.jsonl | gold | osworld | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a69403482ff04c32c.jsonl | gold | gpqa | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a695fc0415f7dc6ca.jsonl | gold | humaneval | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a6d90b96c8e25344f.jsonl | perturb | v28 | claude-sonnet-5-5 | 5 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a6dd0dc898a0a90a0.jsonl | main | h-adminsim | claude-sonnet-5-5 | 14 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a6f3f6fa12ca98e65.jsonl | retest | medimageedu | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a73d10bc01bbcc620.jsonl | main | clindef | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a77f0d602c589230e.jsonl | perturb | v06 | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a7955ba8b6e704783.jsonl | main | evimed | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a7a2c332fab76e592.jsonl | main | mentalhospital | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a816dda5784835a86.jsonl | main | med-inquire | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a81ae7a0ef0996172.jsonl | retest | medsp1000 | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8405cd3c8b74f6e8.jsonl | main | klinikebench | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a84749ad32dec3e13.jsonl | main | codeclinic | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a852da9f48f0e0eaf.jsonl | main | gpagentbench-2k | claude-sonnet-5-5 | 8 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a89107b500f7b9830.jsonl | gold | gsm8k | claude-sonnet-5-5 | 5 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8a97e44186ec5076.jsonl | perturb | v27 | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8cac9fa70240b4c1.jsonl | gold | mmlu | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8cc8387a738fb887.jsonl | perturb | v30 | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8d3c742b9193a729.jsonl | main | physicianbench | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8ef62b4b1d6c1f9b.jsonl | gold | medmnist_v2 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a8f876c6f7dccbf61.jsonl | main | medcua-bench | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a917f93c477eccccb.jsonl | main | ehr-robustgym | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a918b8c5d13602851.jsonl | main | mtbbench | claude-sonnet-5-5 | 24 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a932a362ae5d3b3ca.jsonl | gold | mlcommons_ai_safety_v0.5 | claude-sonnet-5-5 | 12 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a9708c9e383d00c9b.jsonl | perturb | v03 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a99a387b35955d095.jsonl | main | medagentsim | claude-sonnet-5-5 | 22 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a9abd56dad6cf4246.jsonl | retest | medagentsim | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a9be31f20b2707b4a.jsonl | perturb | v24 | claude-sonnet-5-5 | 29 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-a9cba38d3abfa82d4.jsonl | gold | mle-bench | claude-sonnet-5-5 | 10 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa1e39359cca0a439.jsonl | gold | agentbench | claude-sonnet-5-5 | 27 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa205e1caa56cd96e.jsonl | retest | synthetic-hospital | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa26057849e80905b.jsonl | main | fhir-agentbench | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa2aacb257531d5e7.jsonl | main | physassistbench | claude-sonnet-5-5 | 19 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa3ea979f20e224d4.jsonl | perturb | v14 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa6810ef9a0231309.jsonl | perturb | v25 | claude-sonnet-5-5 | 14 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aa80464163ebcde5b.jsonl | perturb | v11 | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aabbdf3fd284c3880.jsonl | main | openhospital | claude-sonnet-5-5 | 20 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aad3227fd897962c8.jsonl | main | medmcp-calc | claude-sonnet-5-5 | 11 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aafa25fa1e50d428e.jsonl | main | medsp1000 | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aafcff4168cff35df.jsonl | main | abra | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ab2173a7f98ea22cb.jsonl | perturb | v08 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ab2b7abeee217e261.jsonl | gold | rl_unplugged | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ab51e4e24983e6d20.jsonl | perturb | v31 | claude-sonnet-5-5 | 20 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ab9e19b6f89e428eb.jsonl | main | agentclinic | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-abd83ecb286b95066.jsonl | perturb | v20 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-abf0c592257687025.jsonl | main | patientagentbench | claude-sonnet-5-5 | 15 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ac22f87ffb51e0e86.jsonl | main | healthagentbench | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ac533105087657b34.jsonl | gold | bbq | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ac535ce60da50f1d4.jsonl | perturb | v37 | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-acc1d4acad33f59e4.jsonl | gold | finrl-meta | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-acfc4583d85481d48.jsonl | perturb | v36 | claude-sonnet-5-5 | 38 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-acff8867c2da69cab.jsonl | retest | diaggym-diagbench | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ad128d876262e4fe5.jsonl | retest | klinikebench | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ad4d558a7dbd8a5af.jsonl | main | healthcare-ai-gym | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ad96659308ffb8073.jsonl | gold | machiavelli | claude-sonnet-5-5 | 9 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ad9caf7dd6130e54a.jsonl | gold | decodingtrust | claude-sonnet-5-5 | 25 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-adb87be8a70dc4135.jsonl | gold | webarena | claude-sonnet-5-5 | 12 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-adf212b102aae133e.jsonl | perturb | v09 | claude-sonnet-5-5 | 18 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-adf953545e8eb3e7e.jsonl | gold | winogrande | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ae1fec726a7fdf2c3.jsonl | gold | hellaswag | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ae39753b72a00e1a0.jsonl | main | ecg-scroll | claude-sonnet-5-5 | 14 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ae5641242be4751e9.jsonl | main | medevoeval | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ae81aa325e556536c.jsonl | gold | wordcraft | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-ae8dcdf2abc3b47da.jsonl | perturb | v22 | claude-sonnet-5-5 | 23 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aeb9e99a3b24f2cb2.jsonl | perturb | v29 | claude-sonnet-5-5 | 15 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aebecf8f172401265.jsonl | perturb | v04 | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aed9ed0cc631691b4.jsonl | retest | fhir-agenteval | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aeeb614109d0e7fc5.jsonl | main | deeptumorvqa | claude-sonnet-5-5 | 23 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-af1ac0b5da512876e.jsonl | perturb | v38 | claude-sonnet-5-5 | 7 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-af6a43a0da9992cdd.jsonl | perturb | v26 | claude-sonnet-5-5 | 17 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-af9316bea5768fca1.jsonl | perturb | v34 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-afa3fb03fa2915c88.jsonl | perturb | v10 | claude-sonnet-5-5 | 6 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-afc604d9f7d4151a7.jsonl | perturb | v39 | claude-sonnet-5-5 | 16 | 0 |
| b70619cc-e61f-44f3-8789-37cb3d4bacd8\subagents\agent-aff138732e531098c.jsonl | gold | pdebench | claude-sonnet-5-5 | 15 | 0 |
