"""Shared helpers for the per-benchmark runners: role config, model strings, ollama digest lookup."""
import json
import urllib.request
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent / "runner_config.json"


def load_config(path=None):
    return json.loads(Path(path or DEFAULT_CONFIG).read_text(encoding="utf-8"))


def resolve_roles(cfg, benchmark, agent_model=None, agent_backend=None, temperature=None, replication=False):
    """Return {'agent','simulator','judge'} dicts with backend, model, temperature filled in."""
    roles = {k: dict(v) for k, v in cfg["roles"].items()}
    if replication:
        roles["agent"].update(cfg["replication_agent"])
    if agent_backend:
        roles["agent"]["backend"] = agent_backend
    if agent_model:
        roles["agent"]["model"] = agent_model
    if temperature is not None:
        roles["agent"]["temperature"] = temperature
    if roles["agent"].get("temperature") is None:
        roles["agent"]["temperature"] = cfg["benchmark_default_agent_temperature"][benchmark]
    return roles


def ollama_digests():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=10) as r:
            return {m["name"].replace(":latest", ""): m["digest"] for m in json.load(r)["models"]}
    except Exception:  # noqa: BLE001
        return {}


def describe(roles, digests):
    out = {}
    for name, r in roles.items():
        d = dict(r)
        if r["backend"] == "ollama":
            d["live_digest"] = digests.get(r["model"])
        out[name] = d
    return out
