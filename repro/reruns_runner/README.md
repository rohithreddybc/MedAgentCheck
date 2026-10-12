# repro/reruns_runner/

Our own code and configuration for the executed reruns of three benchmarks (AgentClinic, RadA-BenchPlat, Synthetic Hospital; run design v3: 10 tasks, 2 temperature conditions, 5 repeats, 100 episodes per benchmark). The per-episode records these scripts produced are in `../../reruns/`; `../reproduce_reruns.py` recomputes the paper's rerun metrics from them. Post-freeze, like everything under `repro/`: nothing here is part of the frozen method and `FREEZE_MANIFEST.json` does not cover it.

The folder keeps the layout of the authors' `research/executed/` so that the scripts find each other (`runs/driver_v3.py` resolves `runners/`, `repos/` and `envs/` relative to its parent folder).

| Path | What it is |
|---|---|
| `runs/driver_v3.py`, `runs/v3_config.json` | Resumable driver for run design v3 (seeded task sample, conditions A and B, 5 repeats, 90 min cap per episode) and the role/model routing config it passes to the runners (agent `qwen3-4b-ctx16k`; simulator and judge `llama3.1-8b-ctx16k` at temperature 0; ollama base digests). |
| `runners/*_runner.py`, `runner_common.py`, `roles.json`, `runner_config.json` | Per-benchmark episode adapters. Each drives the benchmark's own entry point and writes one result JSON (task id, condition, repeat, model ids, timestamps, canonical action sequence, verdict). The canonicalisation of actions is documented in each docstring. `CP_ENV_runner.py` and `MedSP1000_runner.py` belong to the earlier design (v2) and were not used for the v3 data; they are kept because the setup notes refer to them. |
| `patches/` | Model-routing diffs against the benchmark repositories (routing, temperature and call logging only; `CP_ENV_routing.diff` and `synthetic_hospital_routing.diff` are comment-only files because no repository file was patched). |
| `ollama_modelfiles/` | `*.Modelfile`: derived ollama tags (pinned base weights plus `num_ctx`). The `ctx16k` files were written for this release from `ollama show --parameters` of the tags used in v3 (same parameter set, compared; the tag digest differs because it covers the manifest and its metadata, so pin by the base digests in `runs/v3_config.json`). The `ctx32k` files are the v2 originals. |
| `setup_tools.md`, `setup_typed.md`, `setup_v3.md` | Setup and smoke-test notes (commits, licences, install steps, deviations, blockers). One reference diagnosis of a benchmark case that the original notes quoted was replaced by "[reference diagnosis removed from this released copy]"; nothing else was changed. |

## What to obtain yourself

The benchmark repositories, their data and the model weights are not redistributed. Clone each repository into `repos/` at the commit named in the setup notes (`setup_tools.md`: RadABench `ee45eb2f...`, Synthetic Hospital `911f34c4...`; `setup_typed.md`: AgentClinic `b6fbe223...`), apply `patches/*.diff` where a diff is not comment-only (`git apply`), create one virtual environment per benchmark in `envs/<name>/` (the driver calls `envs/<name>/Scripts/python.exe`, i.e. the Windows layout; adjust `command()` and `py` in `driver_v3.py` for other systems), pull the ollama base models (digests in `runs/v3_config.json`), create the derived tags with `ollama create <tag> -f ollama_modelfiles/<tag>.Modelfile`, start the Synthetic Hospital stack (`docker compose up -d` with the ports named in `setup_tools.md`), then, from this folder:

    python runs/driver_v3.py --bench AgentClinic RadABench synthetic_hospital

Episodes are appended to `runs/v3/<bench>/episodes.jsonl`. Local models served by ollama give no determinism guarantee; the released episode records, not a fresh run, are what the paper's numbers come from.

## Licensing and credentials

- The runners, driver and configs are the authors' code (MIT, as the repository). The patches contain a few unchanged lines of context from the upstream files; those lines stay under the upstream licences, all MIT: AgentClinic (Samuel Schmidgall), RadABench (MAGIC-AI4Med), Synthetic Hospital (sparkcpark), MedSP1000 (MAGIC-AI4Med; its licence file leaves the year and holder as a template), CP_ENV (SPIRAL-MED).
- No benchmark repository file, dataset, task text, case, reference answer or transcript is included. The driver draws task ids from the benchmark data at run time (seed 20261004); the sampled ids are in `../../reruns/`.
- No API key, token or credential is included; keys are read from the environment (`GROQ_API_KEY`, used only in the v2 smoke tests; ollama needs none). `runners/synthetic_hospital_runner.py` reads the scorer token of the local Synthetic Hospital server from `SYNTHETIC_HOSPITAL_TOKEN` (or the upstream name `EPIC_SIM_SCORER_TOKEN`) and stops with an error if neither is set. The reruns used the upstream repository's default development token; where it is defined is stated in `../README_REPRO.md`, section Credentials. The released runner differs from the file that produced the data only in this token handling (the literal fallback was replaced by the environment read).
- The Groq profile in `roles.json` and `runner_config.json` names an endpoint and an environment variable only.
