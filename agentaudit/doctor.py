"""``agentaudit doctor``: which scoring backends are live, without spending quota.

Default checks cost nothing: ``claude auth status``, ``codex login status``, and for the two HTTP APIs the
key variable plus a model-list request (no generation, no quota). ``--ping`` adds a 1-token generation
request for each backend that passed its free check.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

BACKENDS = [("claude", "anthropic"), ("codex", "openai"), ("gemini", "google"), ("mistral", "mistral")]


def _run(runner, cmd, timeout=60):
    try:
        p = runner(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "not found"
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def check_claude(runner=subprocess.run, which=shutil.which) -> dict:
    exe = which("claude")
    if not exe:
        return {"live": False, "detail": "claude CLI not installed"}
    rc, out = _run(runner, [exe, "auth", "status"])
    try:
        j = json.loads(out)
        logged = bool(j.get("loggedIn"))
        return {"live": logged, "detail": f"loggedIn={logged}, authMethod={j.get('authMethod')}"
                + ("" if logged else "; run `claude auth login`")}
    except ValueError:
        return {"live": rc == 0, "detail": out.strip()[:200]}


def check_codex(runner=subprocess.run, which=shutil.which) -> dict:
    exe = which("codex")
    if not exe:
        return {"live": False, "detail": "codex CLI not installed (npm i -g @openai/codex), then `codex login`"}
    rc, out = _run(runner, [exe, "login", "status"])
    low = out.lower()
    logged = rc == 0 and "not logged" not in low
    _, hlp = _run(runner, [exe, "exec", "--help"])
    flags = [f for f in ("--sandbox", "--output-last-message", "--skip-git-repo-check", "--ephemeral", "--model")
             if f in hlp]
    return {"live": logged, "detail": out.strip()[:200] or f"exit {rc}", "exec_flags_present": flags}


def check_gemini(session=None, env=os.environ, base="https://generativelanguage.googleapis.com/v1beta") -> dict:
    key = env.get("GEMINI_API_KEY")
    if not key:
        return {"live": False, "detail": "GEMINI_API_KEY not set"}
    import requests

    s = session or requests.Session()
    try:
        r = s.get(f"{base}/models", params={"pageSize": 1}, headers={"x-goog-api-key": key}, timeout=30)
    except Exception as e:  # noqa: BLE001
        return {"live": False, "detail": f"request failed: {e}"}
    return {"live": r.status_code == 200, "detail": f"model list HTTP {r.status_code}"}


def check_mistral(session=None, env=os.environ, base="https://api.mistral.ai/v1") -> dict:
    key = env.get("MISTRAL_API_KEY")
    if not key:
        return {"live": False, "detail": "MISTRAL_API_KEY not set"}
    import requests

    s = session or requests.Session()
    try:
        r = s.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    except Exception as e:  # noqa: BLE001
        return {"live": False, "detail": f"request failed: {e}"}
    return {"live": r.status_code == 200, "detail": f"model list HTTP {r.status_code}"}


def ping(name: str) -> dict:
    """1-token generation request through the real backend. Returns {ok, detail, model_id}."""
    from .coders import load_coders, make_backend

    spec = load_coders()[{"claude": "sonnet"}.get(name, name)]
    try:
        be = make_backend(spec)
        if name == "gemini":
            r = be.complete("Reply with one word.", "ok", max_output_tokens=64)  # thinking tokens count too
        else:
            r = be.complete("Reply with one word.", "Reply with the single word ok.")
        return {"ok": True, "model_id": r.model_id, "detail": f"reply {r.text.strip()[:20]!r}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": f"{type(e).__name__}: {str(e)[:200]}"}


def run_doctor(do_ping: bool = False) -> list[dict]:
    checks = {"claude": check_claude, "codex": check_codex, "gemini": check_gemini, "mistral": check_mistral}
    rows = []
    for name, fam in BACKENDS:
        r = checks[name]()
        row = {"backend": name, "family": fam, **r}
        if do_ping and r["live"]:
            pr = ping(name)
            row["ping"] = pr
            row["live"] = pr["ok"]
        rows.append(row)
    return rows
