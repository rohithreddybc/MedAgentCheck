"""Coder registry: name -> backend recipe and model family."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from .backends import ClaudeHeadlessBackend, CodexHeadlessBackend, GeminiBackend, OpenAICompatBackend
from .throttle import Throttle

GROQ_BASE = "https://api.groq.com/openai/v1"
MISTRAL_BASE = "https://api.mistral.ai/v1"  # endpoint and key variable as in ff_gateway.py

DEFAULT_CODERS = {
    "gpt-oss-120b": {"backend": "openai", "model": "openai/gpt-oss-120b", "base_url": GROQ_BASE,
                     "api_key_env": "GROQ_API_KEY", "family": "openai-oss", "tpm": 8000, "rpd": 1000, "tpd": 200000,
                     "max_tokens": 1500, "temperature": 0.0, "json_mode": True,
                     "extra_params": {"reasoning_effort": "low"}},
    "sonnet": {"backend": "claude", "model": "claude-sonnet-5-5", "family": "anthropic"},
    "opus": {"backend": "claude", "model": "claude-opus-5-5", "family": "anthropic"},
    # v3 whole-packet coders. codex: model None = the CLI's configured default; its reported id is recorded.
    "codex": {"backend": "codex", "model": None, "family": "openai"},
    # Gemini free-tier limits as published for 2.5 Pro / 2.5 Flash (override with --coders-file).
    "gemini": {"backend": "gemini", "model": "gemini-2.5-pro", "fallback_model": "gemini-2.5-flash",
               "family": "google", "limits": {"gemini-2.5-pro": {"rpm": 5, "tpm": 250000, "rpd": 100},
                                              "gemini-2.5-flash": {"rpm": 10, "tpm": 250000, "rpd": 250}}},
    # Optional 4th coder. mistral-large-latest has a 128k-token context, so its packet cap is lower.
    "mistral": {"backend": "openai", "model": "mistral-large-latest", "base_url": MISTRAL_BASE,
                "api_key_env": "MISTRAL_API_KEY", "family": "mistral", "tpm": 500000, "rpd": 1000, "rpm": 1,
                "max_tokens": 16000, "temperature": 0.0, "json_mode": True, "max_packet_tokens": 100000},
}


def load_coders(coders_file: str | None = None) -> dict[str, dict]:
    coders = {k: dict(v) for k, v in DEFAULT_CODERS.items()}
    if coders_file:
        extra = yaml.safe_load(Path(coders_file).read_text(encoding="utf-8")) or {}
        coders.update(extra.get("coders", extra))
    return coders


def make_backend(spec: dict, state_dir: Path | None = None, throttle_state: str | None = None,
                 base_url: str | None = None):
    if spec["backend"] == "claude":
        return ClaudeHeadlessBackend(spec["model"])
    if spec["backend"] == "codex":
        return CodexHeadlessBackend(spec.get("model"))
    if spec["backend"] == "gemini":
        ths = {}
        for m in [spec["model"], spec.get("fallback_model")]:
            if not m:
                continue
            lim = (spec.get("limits") or {}).get(m, {"rpm": 5, "tpm": 250000, "rpd": 100})
            d = Path(state_dir) if state_dir else None
            sp = str(d / f"throttle-gemini-{m}.json") if d else None
            ths[m] = Throttle(sp, tpm=int(lim["tpm"]), rpd=int(lim["rpd"]), rpm=int(lim["rpm"]))
        return GeminiBackend(spec["model"], spec.get("fallback_model"), throttles=ths,
                             max_output_tokens=int(spec.get("max_output_tokens", 65536)))
    if spec["backend"] == "openai":
        sp = throttle_state or (str(Path(state_dir) / f"throttle-{spec['model'].replace('/', '_')}.json")
                                if state_dir else None)
        th = Throttle(sp, tpm=int(spec.get("tpm", 8000)), rpd=int(spec.get("rpd", 1000)),
                      tpd=int(spec["tpd"]) if spec.get("tpd") else None,
                      rpm=int(spec["rpm"]) if spec.get("rpm") else None)
        return OpenAICompatBackend(
            spec["model"], base_url or os.environ.get("AGENTAUDIT_BASE_URL") or spec["base_url"],
            api_key_env=spec.get("api_key_env", "GROQ_API_KEY"), throttle=th,
            max_tokens=int(spec.get("max_tokens", 1500)), temperature=float(spec.get("temperature", 0.0)),
            extra_params=spec.get("extra_params"), json_mode=bool(spec.get("json_mode", True)))
    raise ValueError(f"unknown backend {spec['backend']}")
