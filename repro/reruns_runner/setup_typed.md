# Typed-action benchmarks: setup and smoke test (criterion v)

Date 2026-10-04. Benchmarks: AgentClinic, MedSP1000. Started 15:18 EDT, last action 17:58 EDT (2 h 40 min elapsed, most of it waiting on episodes).

## Result

| | AgentClinic | MedSP1000 |
|---|---|---|
| Setup effort (install + patch + adapter, excluding episode waits) | about 0.7 h | about 0.8 h |
| Install | pass | pass |
| One task end-to-end | **pass** (Groq-agent episode ran to the grader step; verdict "no_diagnosis") | **not shown**: episode 1 hit the Groq daily token cap at turn 4, episode 2 stalled in ollama at turn 6 and was killed |
| Criterion (v) | **pass** | **unresolved, blocked by compute, not by the code** |
| Local-default smoke episode (plan v2) | not completed (47 min, killed) | not run |

Caveat on AgentClinic: the doctor never emitted "DIAGNOSIS READY" within 20 turns, so the moderator (grader) was not reached in the episode. The grader route was checked separately with two direct `compare_results` calls (smoke/AgentClinic/moderator_check_calls.jsonl: correct text -> "yes", wrong text -> "no"). The benchmark scores a no-diagnosis episode as incorrect.

## Repos and environments

| | AgentClinic | MedSP1000 |
|---|---|---|
| Repo | SamuelSchmidgall/AgentClinic, branch main | MAGIC-AI4Med/MedSP1000, branch main |
| Commit | `b6fbe22300e99a267a7ac94eaa465ab552eef741` (2026-10-03) | `2806984cb331d6fedc2c0555e3c1c4a54171c77a` (2026-06-04) |
| Clone | `repos/AgentClinic` (depth 50) | `repos/MedSP1000` (depth 50) |
| Venv | `envs/AgentClinic`, Python 3.11.7 | `envs/MedSP1000`, Python 3.11.7 (repo asks 3.10; ran on 3.11) |
| Install | `pip install -r requirements.txt` (openai==0.28.0, replicate==0.23.1, regex, anthropic, transformers 5.3.0, datasets); no torch needed | `pip install openai==1.109.1 pyyaml==6.0.2 tenacity huggingface_hub`; pandas/numpy/matplotlib/flask skipped (analysis only) |
| Data | shipped jsonl (MedQA 107, MedQA_Ext 215) | `python scripts/download_data.py` (HF byrLLCC/MedSP1000, 9,961 files, about 10 min, rate-limited once); `subset.json` lists 100 scenarios; frozen rubrics ship in `rubrics/` |
| Run entry | adapter calls `agentclinic.main` unmodified | adapter builds `SimulationController` from `simulate.*` unmodified (shipped bash script not used) |

Note: the shipped `run_simulate_cases.sh` needs `scenario_directories_full.json` and a conda path; the adapter bypasses both. `docs/RUNNING.md` named in the README does not exist (docs/ is empty).

## Patches (model routing only), `patches/`

- `AgentClinic_routing.diff`: `query_model` accepts model strings `backend|model|temperature` (backends groq with env `GROQ_API_KEY`, ollama at `http://localhost:11434/v1`), via openai 0.28 `api_base`. Also: `max_tokens` 1500 instead of 200 (gpt-oss reasoning tokens count against it), `reasoning_effort="low"` for Groq and gpt-oss models, JSONL call log (env `AC_CALL_LOG`). Original temperature 0.05 is kept for the agent role; simulator and judge run at 0.
- `MedSP1000_routing.diff`: `LLMClient` accepts `backend:model@temperature` (same backends), temperature passed through, `reasoning_effort="low"` for Groq and gpt-oss, client `max_retries=8`, JSONL call log (env `MEDSP_CALL_LOG`). `patches/MedSP1000_config.yaml` is the base config; the adapter overwrites the four role models per episode.
- No committed key was used or found in either repo; keys come from env only.

Other deviations to disclose: the ollama tags actually served are derived tags (`gpt-oss-20b-ctx16k`, `llama3.1-8b-ctx16k`, `qwen3-4b-ctx16k`) created with `ollama create` from the pinned base models plus `num_ctx 16384` and `temperature 0`, because ollama's `/v1` endpoint cannot set `num_ctx` and the default 4096 would silently truncate MedSP1000 prompts (the environment prompt alone is about 3k tokens at turn 1 and grows). Weights are identical to the base.

## Pins (ollama)

| Tag | Digest |
|---|---|
| gpt-oss:20b | `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7` |
| llama3.1:8b-instruct-q4_K_M | `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e` |
| qwen3:4b-instruct-2507-q8_0 | `aa7252f68dda4d25dfffa65b3760af6d2c3231a140c0060c78d444686d98a374` |
| gpt-oss-20b-ctx16k (derived) | `5269c7fda101bb76612a7db5be7b39b35295e3874d5c017df54ddf5e6e45b0b9` |
| llama3.1-8b-ctx16k (derived) | `2b175d2e041c7108fcead7b5fe3a202d88ed24e8912c390dcc2f8a60f28b80ae` |
| qwen3-4b-ctx16k (derived) | `175cbe4a2b73ba55a2d3b8f59c0eaf2a4537145d9071836b5495dcf754975f22` |

`ollama` 0.35.1. Groq `system_fingerprint` varies per call (19 distinct values in one 20-call episode), so it cannot pin the served model; log it but do not rely on it.

## Runners, `runners/`

`AgentClinic_runner.py` and `MedSP1000_runner.py` (each documents its canonicalisation function in the docstring), plus `runner_config.json` (per-role backend, model, temperature; defaults = plan v2: agent ollama gpt-oss:20b, replication qwen3:4b-instruct-2507-q8_0, simulator and judge ollama llama3.1:8b-instruct-q4_K_M at 0; benchmark default agent temperature 0.05 for AgentClinic, 0 for MedSP1000) and `runner_common.py`. CLI: `--task --repeat --out [--config --model --backend --replication --temperature]`. Output JSON: task_id, condition, repeat, model_ids, role_config (with live ollama digests), timestamps, actions, final_state, verdict, usage, raw_log_path. Groq calls are throttled to 7,000 tokens per minute per model inside the adapter.

- AgentClinic task id `MedQA:<i>` or `MedQA_Ext:<i>`. Actions: `ASK`, `REQUEST_TEST:<name>`, `DIAGNOSIS:<text>` (plus `actions_strict` with the question text). `final_state` is null: no environment state exists. Verdict: correct, incorrect, no_diagnosis or error.
- MedSP1000 task id `mededportal_NNNNN/scenarioK`. Actions: the environment controller's canonical action id per raw action, `UNSUPPORTED:<raw>` otherwise, `EOS` (plus `actions_raw_norm`). `final_state` is observable (progress index, state label, patient status, completion reason). Verdict is a rubric score with items true and total; the benchmark defines no binary pass, so one must be fixed before the pass^k analysis. Canonical ids come from an LLM environment controller, so action divergence on MedSP1000 includes simulator noise; the raw-normalised list gives a simulator-independent sensitivity check.

## Episodes run (quota: 2 per benchmark; MedSP1000 used 3 attempts, AgentClinic 2)

| Episode | Config | Outcome | Wall time | Calls | Tokens (prompt / completion) |
|---|---|---|---|---|---|
| AgentClinic MedQA:0 `smoke/AgentClinic/ep0` | doctor Groq gpt-oss-20b at 0.05; patient, measurement ollama gpt-oss (ctx16k) at 0; moderator Groq 120b not reached | complete, no_diagnosis after 20 turns (19 ASK, 1 REQUEST_TEST); [reference diagnosis removed from this released copy] | 826 s (684 s of it ollama) | 40 (20 Groq, 20 ollama) | Groq 23,748 / 1,887; ollama 25,497 / 1,196; moderator about 0.3k |
| AgentClinic MedQA:1 `smoke/AgentClinic/local_ep0` | plan-v2 defaults (gpt-oss agent, llama3.1 simulator and judge) | killed after 47 min, 2 successful calls | not completed | 2 ok, 3 read timeouts at 600 s | n/a |
| MedSP1000 stroke-code `smoke/MedSP1000/ep0` | examinee Groq gpt-oss-20b at 0; sp, environment ollama gpt-oss | failed at turn 4: Groq 429 on tokens per day (limit 200,000, used 199,340) | 1,368 s | 9 | Groq 3,284 / 543; ollama 27,291 / 3,081 |
| MedSP1000 stroke-code `smoke/MedSP1000/ep1` | examinee Groq qwen3.8-27b at 0; sp, environment ollama gpt-oss | killed at turn 6: one SP call stalled about 30 min behind another session on ollama; no result.json | about 62 min | 16 | Groq 12,488 / 4,100; ollama 59,738 / 4,888 |

What the partial MedSP1000 episodes do show: routing, JSON parsing, role loops, and canonical action extraction work (4 turns produced 22 environment-mapped actions). They do not show the evaluator or a final verdict.

## Sizing for the full run

- AgentClinic, one episode (20 turns, Groq agent): about 21 Groq calls, about 25.6k Groq-agent tokens, 20 ollama calls with about 26.7k tokens. Groq free tier caps **200,000 tokens per day per model** (read from the 429 message; plan v1 assumed only the 8k/min and 1k/day request limits). At 25.6k tokens that is 7 episodes per day on the 20b; 225 episodes would take about 32 days. This is why plan v2 goes local.
- MedSP1000, one episode (12 turns max): ollama prompt tokens grow to about 12k per turn by turn 5 (SP prompt about 4.5k, environment about 7k), so roughly 150k to 200k local prompt tokens per episode; Groq agent about 40k tokens plus the evaluator.
- Local speed on this machine (RTX 4050 6 GB, 14 GB RAM): gpt-oss:20b is 71 to 76 percent CPU. Uncontended, one gpt-oss ollama call is 12 to 70 s for AgentClinic-size prompts and 110 to 430 s for MedSP1000-size prompts (stalled prefill measured at about 6 tokens per second under memory pressure). Estimated uncontended episode time: AgentClinic about 14 min (Groq doctor) or about 20 min (all local); MedSP1000 about 90 min or more. 225 MedSP1000 episodes would be 14 days or more; 225 AgentClinic episodes about 75 hours.

## Blockers and risks

1. **Local plan v2 as specified will thrash.** gpt-oss:20b is 14 GB and the machine has 14 GB RAM, so it cannot stay loaded beside llama3.1:8b (4.9 GB); every agent/simulator alternation forces a model reload. Observed: 3 read timeouts of 600 s in the local episode. Recommended fix: use one resident model for all roles in an episode (agent and simulator and judge all gpt-oss:20b, as in the 14-minute episode), or run an agent and simulator pair whose combined size fits (for example qwen3:4b plus llama3.1:8b). This is a config change in `runner_config.json`, no code change.
2. **Ollama is shared.** Other sessions (smoke/CP_ENV, RadABench, synthetic_hospital) use the same ollama and Groq quota at the same time. Wall-clock numbers above are therefore noisy, and the 200k daily Groq cap is shared (my own earlier bug, a relative log path that made the patch raise and the benchmark's silent 30-retry loop re-call Groq about 100 times, burned a large share before it was fixed). Full runs need an exclusive window or a lock.
3. AgentClinic's own `query_model` swallows every exception and retries 30 times with a 20 s sleep. A full run needs a wrapper that fails fast on auth, quota and timeout errors; calls.jsonl logs each error.
4. gpt-oss-20b at `reasoning_effort=low` ignored the AgentClinic instruction to emit one dialogue turn: it often emits several "Doctor:" lines per reply and did not diagnose in 20 turns on MedQA:0. Expect a high no_diagnosis rate; decide whether that counts as incorrect (the benchmark does) before the run.
5. MedSP1000 judge default in the repo is DeepSeek (`--eval-model deepseek-v4-pro` for rescoring only); here the judge is the configured judge role. Judge and agent can share a model family.
6. Temperature: AgentClinic specifies 0.05 for all roles; simulator and judge are 0 here (deviation). MedSP1000 specifies none (provider default); 0 is used.
