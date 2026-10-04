"""Model backends: OpenAI-compatible (Groq by default) and Claude headless."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from .throttle import DailyLimitReached, Throttle
from .util import est_tokens


class BackendError(Exception):
    pass


class BackendAuthError(BackendError):
    pass


@dataclass
class Response:
    text: str
    model_id: str
    usage: dict = field(default_factory=dict)
    raw: Any = None
    meta: dict = field(default_factory=dict)


def parse_retry_after(headers) -> float | None:
    v = None
    for k in ("retry-after", "Retry-After"):
        if k in headers:
            v = headers[k]
            break
    if v is None:
        return None
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return None


class OpenAICompatBackend:
    """Chat-completions client with throttle, 429 backoff honouring retry-after, 5xx retry."""

    def __init__(self, model: str, base_url: str, api_key_env: str = "GROQ_API_KEY",
                 throttle: Throttle | None = None, max_tokens: int = 1500, temperature: float = 0.0,
                 extra_params: dict | None = None, json_mode: bool = True, session=None,
                 max_retries: int = 8, sleep=time.sleep, clock=time.time,
                 daily_wait_threshold: float = 900.0, timeout: float = 180.0, api_key: str | None = None):
        import requests

        self.model, self.base_url = model, base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._api_key = api_key
        self.throttle = throttle or Throttle(None)
        self.max_tokens, self.temperature = max_tokens, temperature
        self.extra_params = dict(extra_params or {})
        self.json_mode = json_mode
        self.session = session or requests.Session()
        self.max_retries, self.sleep, self.clock = max_retries, sleep, clock
        self.daily_wait_threshold, self.timeout = daily_wait_threshold, timeout
        self.log: list[dict] = []

    def _key(self) -> str:
        k = self._api_key or os.environ.get(self.api_key_env)
        if not k:
            raise BackendAuthError(f"environment variable {self.api_key_env} is not set")
        return k

    def build_payload(self, system: str, prompt: str) -> dict:
        p = {"model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
             "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if self.json_mode:
            p["response_format"] = {"type": "json_object"}
        p.update(self.extra_params)
        return p

    def complete(self, system: str, prompt: str) -> Response:
        payload = self.build_payload(system, prompt)
        est = est_tokens(system) + est_tokens(prompt) + self.max_tokens
        headers = {"Authorization": f"Bearer {self._key()}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"
        last = ""
        for attempt in range(self.max_retries + 1):
            ts = self.throttle.acquire(est)
            try:
                r = self.session.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
            except Exception as e:  # connection problems
                last = f"connection error: {e}"
                self.log.append({"attempt": attempt, "error": last})
                self.sleep(min(120, 5 * 2 ** attempt))
                continue
            if r.status_code == 429:
                ra = parse_retry_after(r.headers)
                delay = ra if ra is not None else min(120.0, 5.0 * 2 ** attempt)
                last = f"429: {r.text[:300]}"
                self.log.append({"attempt": attempt, "status": 429, "retry_after": ra, "delay": delay})
                daily_body = "tokens per day" in r.text.lower() or "(tpd)" in r.text.lower()
                if daily_body or delay > self.daily_wait_threshold:
                    until = self.clock() + delay
                    self.throttle.block_until(until)
                    raise DailyLimitReached(until, f"429 with retry-after {delay:.0f}s: {r.text[:200]}")
                self.sleep(delay + 0.5)
                continue
            if r.status_code >= 500:
                last = f"{r.status_code}: {r.text[:300]}"
                self.log.append({"attempt": attempt, "status": r.status_code})
                self.sleep(min(120, 5 * 2 ** attempt))
                continue
            if r.status_code in (401, 403):
                raise BackendAuthError(f"{r.status_code}: {r.text[:300]}")
            if r.status_code != 200:
                raise BackendError(f"{r.status_code}: {r.text[:500]}")
            j = r.json()
            usage = j.get("usage") or {}
            if usage.get("total_tokens"):
                self.throttle.settle(ts, usage["total_tokens"])
            try:
                ch = j["choices"][0]
                text = ch["message"].get("content") or ""
            except (KeyError, IndexError) as e:
                raise BackendError(f"malformed response: {str(j)[:300]}") from e
            return Response(text=text, model_id=j.get("model", self.model), usage=usage, raw=j,
                            meta={"finish_reason": ch.get("finish_reason"), "attempts": attempt + 1})
        raise BackendError(f"gave up after {self.max_retries + 1} attempts; last: {last}")


class ClaudeHeadlessBackend:
    """claude -p headless. Built-in tools are disabled (--tools with an empty string), all
    customisations are off (--safe-mode), no MCP servers, no slash commands, no session
    persistence. The prompt goes through stdin and the process runs in an empty temporary
    directory. The model sees only the prompt."""

    def __init__(self, model: str, claude_bin: str | None = None, timeout: float = 900.0,
                 runner=subprocess.run, max_retries: int = 2, sleep=time.sleep):
        self.model = model
        self.claude_bin = claude_bin or shutil.which("claude") or "claude"
        self.timeout, self.runner, self.max_retries, self.sleep = timeout, runner, max_retries, sleep
        self.log: list[dict] = []

    def build_cmd(self, system: str) -> list[str]:
        return [self.claude_bin, "-p", "--model", self.model, "--output-format", "json",
                "--tools", "", "--safe-mode", "--disable-slash-commands", "--strict-mcp-config",
                "--no-session-persistence", "--system-prompt", system]

    def complete(self, system: str, prompt: str) -> Response:
        cmd = self.build_cmd(system)
        last = ""
        for attempt in range(self.max_retries + 1):
            with tempfile.TemporaryDirectory(prefix="agentaudit_claude_") as cwd:
                try:
                    p = self.runner(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                    timeout=self.timeout, cwd=cwd)
                except subprocess.TimeoutExpired:
                    last = "timeout"
                    self.log.append({"attempt": attempt, "error": last})
                    continue
            out = (p.stdout or "").strip()
            try:
                obj = json.loads(out.splitlines()[-1] if out else "")
            except ValueError:
                last = f"unparseable output (exit {p.returncode}): {out[:300]} {(p.stderr or '')[:300]}"
                self.log.append({"attempt": attempt, "error": last})
                self.sleep(5 * 2 ** attempt)
                continue
            if obj.get("is_error"):
                msg = str(obj.get("result", ""))
                low = msg.lower()
                if "authenticate" in low or "oauth" in low or "login" in low:
                    raise BackendAuthError(msg)
                last = msg
                self.log.append({"attempt": attempt, "error": msg[:300]})
                self.sleep(5 * 2 ** attempt)
                continue
            mu = obj.get("modelUsage") or {}
            model_id = next(iter(mu), self.model)
            return Response(text=str(obj.get("result", "")), model_id=model_id, usage=obj.get("usage") or {},
                            raw=obj, meta={"total_cost_usd": obj.get("total_cost_usd"),
                                           "session_id": obj.get("session_id"), "attempts": attempt + 1})
        raise BackendError(f"claude headless failed after {self.max_retries + 1} attempts; last: {last}")


class ModelUnavailable(BackendError):
    pass


class CodexHeadlessBackend:
    """Codex CLI non-interactive mode (``codex exec``). Read-only sandbox (which also blocks network
    access by default), prompt on stdin (``-``), final message captured with ``--output-last-message``,
    run in an empty temporary directory. The CLI has no flag that removes its shell tool, so the
    read-only sandbox, the empty directory and the system text are what keep the model on the prompt.
    Optional flags are used only if ``codex exec --help`` lists them. The model id the CLI reports
    (header line ``model: ...`` on stderr) is recorded; when none is reported the id is
    "codex-default (not reported)". Flags were written from the documented CLI and checked against
    --help at run time; they were not exercised live on the machine where this was developed."""

    OPTIONAL_FLAGS = ("--skip-git-repo-check", "--ephemeral", "--color")

    def __init__(self, model: str | None = None, codex_bin: str | None = None, timeout: float = 1800.0,
                 runner=subprocess.run, max_retries: int = 2, sleep=time.sleep):
        self.model = model
        self.codex_bin = codex_bin or shutil.which("codex") or "codex"
        self.timeout, self.runner, self.max_retries, self.sleep = timeout, runner, max_retries, sleep
        self.log: list[dict] = []
        self._help: str | None = None

    def help_text(self) -> str:
        if self._help is None:
            try:
                p = self.runner([self.codex_bin, "exec", "--help"], capture_output=True, text=True,
                                encoding="utf-8", timeout=60)
                self._help = (p.stdout or "") + (p.stderr or "")
            except Exception:  # noqa: BLE001
                self._help = ""
        return self._help

    def build_cmd(self, out_file: str, cwd: str) -> list[str]:
        h = self.help_text()
        cmd = [self.codex_bin, "exec", "--sandbox", "read-only", "--output-last-message", out_file, "-C", cwd]
        if self.model:
            cmd += ["--model", self.model]
        for fl in self.OPTIONAL_FLAGS:
            if fl in h:
                cmd += [fl, "never"] if fl == "--color" else [fl]
        return cmd + ["-"]

    @staticmethod
    def reported_model(stderr: str, stdout: str = "") -> str | None:
        import re

        for blob in (stderr, stdout):
            m = re.search(r"^\s*model:\s*([\w.\-:/]+)", blob or "", re.M | re.I)
            if m:
                return m.group(1)
        return None

    def complete(self, system: str, prompt: str) -> Response:
        full = f"{system}\n\n{prompt}"
        last = ""
        for attempt in range(self.max_retries + 1):
            with tempfile.TemporaryDirectory(prefix="agentaudit_codex_") as cwd:
                out_file = os.path.join(cwd, "last_message.txt")
                cmd = self.build_cmd(out_file, cwd)
                try:
                    p = self.runner(cmd, input=full, capture_output=True, text=True, encoding="utf-8",
                                    timeout=self.timeout, cwd=cwd)
                except subprocess.TimeoutExpired:
                    last = "timeout"
                    self.log.append({"attempt": attempt, "error": last})
                    continue
                msg = ""
                if os.path.exists(out_file):
                    with open(out_file, encoding="utf-8") as fh:
                        msg = fh.read()
            err = p.stderr or ""
            if p.returncode != 0 or not msg.strip():
                low = (err + (p.stdout or "")).lower()
                if "not logged in" in low or "codex login" in low or "401" in low:
                    raise BackendAuthError((err or p.stdout or "")[:300])
                last = f"exit {p.returncode}: {err[-300:]}"
                self.log.append({"attempt": attempt, "error": last})
                self.sleep(5 * 2 ** attempt)
                continue
            mid = self.reported_model(err, p.stdout) or "codex-default (not reported)"
            return Response(text=msg, model_id=mid, raw=None,
                            meta={"attempts": attempt + 1, "requested_model": self.model, "cmd": cmd[:-1]})
        raise BackendError(f"codex headless failed after {self.max_retries + 1} attempts; last: {last}")


class GeminiBackend:
    """Gemini REST (generativelanguage.googleapis.com v1beta generateContent). The API key goes in the
    ``x-goog-api-key`` header (never the URL). Temperature 0, JSON mime type. Each model has its own
    on-disk throttle (RPM/TPM/RPD). When the primary model hits a daily quota, or is unavailable
    (404), the fallback model is used and recorded in the response model id."""

    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, model: str = "gemini-2.5-pro", fallback_model: str | None = "gemini-2.5-flash",
                 throttles: dict[str, Throttle] | None = None, api_key_env: str = "GEMINI_API_KEY",
                 api_key: str | None = None, max_output_tokens: int = 65536, session=None, max_retries: int = 6,
                 sleep=time.sleep, clock=time.time, timeout: float = 900.0, base_url: str | None = None):
        import requests

        self.model, self.fallback_model = model, fallback_model
        self.throttles = throttles if throttles is not None else {}
        self.api_key_env, self._api_key = api_key_env, api_key
        self.max_output_tokens = max_output_tokens
        self.session = session or requests.Session()
        self.max_retries, self.sleep, self.clock, self.timeout = max_retries, sleep, clock, timeout
        self.base = (base_url or self.BASE).rstrip("/")
        self.log: list[dict] = []

    def _key(self) -> str:
        k = self._api_key or os.environ.get(self.api_key_env)
        if not k:
            raise BackendAuthError(f"environment variable {self.api_key_env} is not set")
        return k

    def build_payload(self, system: str, prompt: str, max_output_tokens: int | None = None) -> dict:
        return {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                     "maxOutputTokens": max_output_tokens or self.max_output_tokens}}

    @staticmethod
    def retry_delay(body: dict) -> float | None:
        for d in (body.get("error", {}) or {}).get("details", []) or []:
            rd = d.get("retryDelay")
            if rd:
                try:
                    return float(str(rd).rstrip("s"))
                except ValueError:
                    pass
        return None

    def _one(self, model: str, system: str, prompt: str, max_output_tokens: int | None = None) -> Response:
        th = self.throttles.get(model)
        if th is None:
            th = self.throttles[model] = Throttle(None, tpm=250000, rpd=100, rpm=5)
        est = est_tokens(system) + est_tokens(prompt) + (max_output_tokens or 8000)
        url = f"{self.base}/models/{model}:generateContent"
        headers = {"x-goog-api-key": self._key(), "Content-Type": "application/json"}
        data = json.dumps(self.build_payload(system, prompt, max_output_tokens))
        last = ""
        for attempt in range(self.max_retries + 1):
            ts = th.acquire(est)
            try:
                r = self.session.post(url, headers=headers, data=data, timeout=self.timeout)
            except Exception as e:  # noqa: BLE001
                last = f"connection error: {e}"
                self.log.append({"model": model, "attempt": attempt, "error": last})
                self.sleep(min(120, 5 * 2 ** attempt))
                continue
            if r.status_code == 429:
                try:
                    body = r.json()
                except ValueError:
                    body = {}
                ra = self.retry_delay(body)
                low = r.text.lower().replace(" ", "").replace("_", "")
                last = f"429: {r.text[:300]}"
                self.log.append({"model": model, "attempt": attempt, "status": 429, "retry_after": ra})
                if "perday" in low:
                    until = self.clock() + (ra if ra and ra > 900 else 86400)
                    th.block_until(until)
                    raise DailyLimitReached(until, f"{model}: daily quota: {r.text[:200]}")
                self.sleep((ra if ra is not None else min(120.0, 15.0 * 2 ** attempt)) + 0.5)
                continue
            if r.status_code >= 500:
                last = f"{r.status_code}: {r.text[:300]}"
                self.log.append({"model": model, "attempt": attempt, "status": r.status_code})
                self.sleep(min(120, 5 * 2 ** attempt))
                continue
            if r.status_code in (401, 403) or (r.status_code == 400 and "api key" in r.text.lower()):
                raise BackendAuthError(f"{r.status_code}: {r.text[:300]}")
            if r.status_code == 404:
                raise ModelUnavailable(f"{model}: {r.text[:300]}")
            if r.status_code != 200:
                raise BackendError(f"{r.status_code}: {r.text[:500]}")
            j = r.json()
            um = j.get("usageMetadata") or {}
            if um.get("totalTokenCount"):
                th.settle(ts, um["totalTokenCount"])
            try:
                cand = j["candidates"][0]
                text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
            except (KeyError, IndexError, TypeError) as e:
                raise BackendError(f"malformed or blocked response: {str(j)[:300]}") from e
            fin = cand.get("finishReason")
            if fin == "MAX_TOKENS":
                raise BackendError("output truncated (MAX_TOKENS); rerun with more item groups (--groups)")
            return Response(text=text, model_id=j.get("modelVersion", model), usage=um, raw=None,
                            meta={"finish_reason": fin, "attempts": attempt + 1, "requested_model": model})
        raise BackendError(f"gave up after {self.max_retries + 1} attempts; last: {last}")

    def complete(self, system: str, prompt: str, max_output_tokens: int | None = None) -> Response:
        try:
            return self._one(self.model, system, prompt, max_output_tokens)
        except (DailyLimitReached, ModelUnavailable) as e:
            if not self.fallback_model:
                raise
            self.log.append({"fallback": self.fallback_model, "reason": str(e)[:200]})
            r = self._one(self.fallback_model, system, prompt, max_output_tokens)
            r.meta["fallback_from"] = self.model
            return r
