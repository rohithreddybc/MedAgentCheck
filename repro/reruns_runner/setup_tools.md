# Setup and smoke test (criterion v): RadA-BenchPlat, CP-Env, Synthetic Hospital

Written 2026-10-04 (Sonnet subagent). Clock: setup started 15:19, last update 18:05 (about 2 h 45 min elapsed, all three benchmarks interleaved; per-benchmark effort below). No benchmark hit the 4 h limit.

## Commits (default branch, cloned 2026-10-04)
| Benchmark | Repo | Commit | Licence |
|---|---|---|---|
| RadA-BenchPlat | MAGIC-AI4Med/RadABench | ee45eb2ffa65541b5deb013135caf825e471ac53 | MIT |
| CP-Env | SPIRAL-MED/CP_ENV | 6c33121d96baf610c9c5b15bf3429129555e5acb | MIT |
| Synthetic Hospital | sparkcpark/synthetic_hospital | 911f34c4ac65a508543c4b3b90c373a0cd16534d | MIT |

## Models and digests
ollama gpt-oss:20b `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7`; qwen3:4b-instruct-2507-q8_0 `aa7252f6...a374`; llama3.1:8b-instruct-q4_K_M `46e0c10c...c66e`. Full digests in `runners/roles.json`. Because the OpenAI endpoint of ollama cannot set num_ctx, local runs use derived tags `*-ctx32k` created with `ollama create` (FROM the pinned tag, PARAMETER num_ctx 32768; same weights blob; Modelfiles in `ollama_modelfiles/`, their digests in roles.json). A default 4096 context would silently truncate these prompts. The Groq smoke runs used gpt-oss-20b-ctx16k (created by another session) as simulator.

## Install
- RadABench: venv `envs/RadABench` (Python 3.11.7), requirements.txt minus torch/transformers/matplotlib/sentence_transformers (only local_hf backends and figures need them; list in `envs/RadABench_requirements_used.txt`), plus nltk punkt/punkt_tab data (the scorer calls word_tokenize). About 10 min.
- CP-Env: venv `envs/CP_ENV`, requirements.txt (freeze: `envs/CP_ENV_freeze.txt`). requirements.txt omits packages the tools import: **langchain-community, wikipedia, xmltodict** must be added. Dataset SII-SPIRAL-MED/DiagnosisArena (915 test rows) from Hugging Face; Hugging Face answered 429 to repeated HEAD requests, so runs read the local cache.
- Synthetic Hospital: Docker Desktop 29.7.2 was installed but would not start (stale AF_UNIX socket files in `%LOCALAPPDATA%\Docker\run` and `...\docker-secrets-engine` that Windows cannot delete). Fixed by renaming those two directories (`run_stale_20261004`, `docker-secrets-engine.stale_20261004`; delete them whenever convenient). Then `docker compose up -d --build` with APP_PORT=58000 POSTGRES_PORT=55432 REDIS_PORT=56379 (postgres:16-alpine, redis:7-alpine, python:3.12-slim app; images well under 20 GB). The first clone had CRLF line endings that broke `docker/entrypoint.sh` in the Linux image ("exec ... no such file or directory"), so the repo was re-cloned with core.autocrlf=false (clone-local; user git config untouched). Server health: `http://localhost:58000/health`; 1,268 patients load at boot. Host venv `envs/synthetic_hospital` (openai, httpx only; scoring runs server-side). Terminology tables (SNOMED/LOINC) are not loaded; not needed for patient_diagnosis scoring.

## Patches (`patches/`)
- RadABench_routing.diff: two aliases in EvalPlat/Configs/models.yaml (Groq gpt-oss-20b, qwen3.8-27b). The runner now injects the per-role route into the benchmark registry in memory, so this diff is only needed for the Groq smoke.
- CP_ENV_routing.diff, synthetic_hospital_routing.diff: no repo change (comment-only files). Routing is by the benchmarks' own arguments; temperature, timeouts and logging are a runner hook.
- Environment deviation, CP-Env: Wikimedia returns 403 to the `wikipedia` package's default User-Agent, which crashed the first CP-Env episode. The runner sets a descriptive UA (`wikipedia.wikipedia.USER_AGENT`). Recorded in each result JSON.
- Never used: any key committed to a repo. Keys come from the environment (GROQ_API_KEY); ollama gets a dummy key. Synthetic Hospital's local scorer token is the repo's own dev default.

## Runners (`runners/`) and config
`roles.json` maps roles (agent, agent_replication, simulator, judge) to base URL, model, key env var per profile (`local` default, `groq`). Flags: `--profile`, `--agent-role`, `--temperature`, `--repeat`, `--task-id`, `--out-dir`. Each file documents its canonicalisation in the docstring. Output JSON has task_id, condition, repeat, model_ids, timestamps, actions, final_state, verdict, raw_log_path (+ usage, calls, errors).
- RadABench `0:012` style ids (case:QA chain). Actions = TOOLn + sorted Input variables. Environment seed derived from task id only (tool set is built with random.sample). Verdict = benchmark metrics (win_rate, milestone, f1, bleu, rouge); `pass` = milestone and no error is OUR derived binary. final_state = memory bank from the log; the benchmark's pickled tool manager is saved.
- CP_ENV ids = DiagnosisArena id. Actions from the doctor's tool_calls (attempted calls count). Verdict = MedicalEvaluator scores; `pass` = process_success and exact diagnosis (derived).
- synthetic_hospital `patient_diagnosis:<gt_id>`. The repo ships no model policy loop for its /env API (the paper harness leaks the problem list, per README), so the runner supplies one using the server's own prompt and tool schemas. final_state = /env/state trace and reward, the ground truth read from benchmark_v1.3.db, and an independent exact-ICD-10 overlap (`state_check`) for the grader-versus-state comparison.
- `runs/driver.py`: resumable full-run driver (see its docstring). **Not launched**, see blockers.

## Smoke results
| Benchmark | Run | Outcome | Calls / tokens | Wall clock |
|---|---|---|---|---|
| RadABench 0:012 | Groq gpt-oss-20b T0, r0 | Completed. Actions TOOL1, 3, 4, 6, 11. win_rate 0.667, milestone true, F1 0.23, BLEU 0.17 | 7 calls, 35,552 prompt + 2,162 completion | 3 min 51 s (throttled to 6,500 TPM) |
| RadABench 0:012 | Groq r1 | Aborted by Groq 429 (daily token cap) after 2 tools (same first two actions as r0) | 3 ok, 6 errors | 1.5 min |
| RadABench 0:012 | local gpt-oss-20b-ctx32k | Not finished (see blockers); still running at last check | | >1 h 20 min so far |
| CP-Env id 4 | Groq attempt 1 | Reached specialist consultation; crashed on Wikipedia 403 (UA). Raw log was overwritten by me when re-running; numbers from the console: agent 5 calls / 4,502 tokens, simulator 3 calls / 2,208 | | 3 min |
| CP-Env id 4 | Groq attempt 2 (UA fixed) | Failed in registration: Groq returned 400 "Tool choice is none, but model called a tool" (gpt-oss-20b emitted an unrequested tool call; 8 identical retries) | agent 2 ok calls / 1,151 tokens; 8 errors | 2.3 min |
| CP-Env | local / judge path | Not exercised end to end; the Groq judge path is untested | | |
| Synthetic Hospital patient_diagnosis:7006 | Groq attempt 1 | Aborted: 429 daily token cap after open_chart | 1 ok | 0.7 min |
| Synthetic Hospital | Groq attempt 2 | Waited out the cap; was still running (about 6 env steps in 70 min) at last check; result file not yet written | | >1 h |
| Synthetic Hospital | local | Not run | | |
Up to three overlapping launches of CP-Env id 4/0 were killed within about 2 minutes while retrying the Hugging Face 429; they may have made a few calls.

## Criterion (v)
- RadABench: **pass** (one task completed end to end, 15 min active setup, about 4 min run). Caveat: the repo's scorer script has placeholder paths and a README flag (`--logs`) that does not exist; the runner calls its `analyze_output()` directly.
- CP-Env: **not yet demonstrated.** Install and pipeline work; no episode completed and the evaluator path is unexercised. Two environment failure modes found (Wikipedia 403; Groq 400 on unrequested tool calls). About 45 min of setup effort.
- Synthetic Hospital: **not yet demonstrated.** Server, scorer endpoint and /env reset/step work (verified with a model-free reset/step/close); no model episode has completed. About 60 min setup effort including the Docker repair.
Environment-drift risk (CP-Env): the Wikipedia and PubMed tools hit live APIs; the Wikipedia policy change above is an example that broke the benchmark between its release (Dec 2025) and now. Raw payloads are logged per episode (`web_tool_payloads.json`). RadABench tool outputs are simulated; its toolset is random-seeded.

## Blockers and findings that change the plan
1. **Groq cap.** The free tier allows 200,000 tokens per day per model (error text), plus 8,000 tokens per minute and 1,000 requests per day. One RadABench episode costs about 38k tokens, so the cap is shared by all sessions and exhausted within a day. Synthetic Hospital resends a growing chart each step; a single request may exceed 8,000 tokens (not yet observed).
2. **Local throughput.** ollama gpt-oss on this laptop (RTX 4050 6 GB, about 75% of the model on CPU) logged prompt processing of 5 to 6 tokens per second while three sessions shared it, with 5 to 18 minute requests and repeated 499/500 responses. A RadABench episode (about 35k prompt tokens) therefore takes hours, not minutes, under contention; the full 225-episode design per benchmark is not feasible at this speed. Different ctx tags of the same weights are separate loaded models, which makes sessions evict each other. Uncontended speed was not measured.
3. Tool-call support (ollama capability list): gpt-oss:20b, qwen3:4b-instruct-2507-q8_0 and llama3.1:8b all report "tools". An actual tool-call probe of the two smaller models was queued behind the GPU and had not returned at last check; `driver.py` probes before CP-Env and Synthetic Hospital and skips a condition that cannot emit tool calls.
4. Local smoke not passed for any benchmark, so the full run was NOT launched (precondition in the coordinator's instruction). To launch once a local smoke passes: `nohup envs/RadABench/Scripts/python runs/driver.py > runs/driver.log 2>&1 &` from this folder (any python with pandas and huggingface_hub works for the driver itself); it takes `runs/gpu.lock`. At the measured contended speed expect weeks; uncontended it is unmeasured.
5. Docker Desktop on this machine has repeatedly broken the same way (`run.broken-*` folders from earlier dates exist), so the compose stack may need the same directory rename after a reboot.
