"""On-disk TPM/RPD throttle so runs resume across minutes and days.

State file: {"events": [[ts, tokens], ...], "blocked_until": ts}. TPM is the sum
of tokens in the last 60 s; RPD is the number of requests in the last 24 h.
Clock and sleep are injectable for tests.
Optional ``rpm`` adds a requests-per-minute limit (Gemini free tier).
Optional ``rpm`` adds a requests-per-minute limit (Gemini free tier, Mistral).
Optional ``tpd`` adds a rolling 24 h token limit (Groq free tier: 200,000 for gpt-oss-120b), counted from
this state file only; usage by other programs on the same key is not visible here and shows up as a 429.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


class DailyLimitReached(Exception):
    def __init__(self, next_available: float, msg: str = ""):
        super().__init__(msg or f"daily request limit reached; next slot at {next_available:.0f} (unix)")
        self.next_available = next_available


class RequestTooLarge(Exception):
    pass


class Throttle:
    def __init__(self, state_path: Path | None, tpm: int = 8000, rpd: int = 1000,
                 clock=time.time, sleep=time.sleep, tpd: int | None = None, rpm: int | None = None):
        self.path = Path(state_path) if state_path else None
        self.tpm, self.rpd, self.tpd, self.rpm = tpm, rpd, tpd, rpm
        self.clock, self.sleep = clock, sleep
        self._mem = {"events": [], "blocked_until": 0.0}

    # -- state io
    def _load(self) -> dict:
        if self.path is None:
            return self._mem
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"events": [], "blocked_until": 0.0}

    def _save(self, st: dict) -> None:
        if self.path is None:
            self._mem = st
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st), encoding="utf-8")
        tmp.replace(self.path)

    # -- api
    def acquire(self, est_tokens: int) -> float:
        """Block until a request of est_tokens fits; record it; return its event timestamp."""
        if est_tokens > self.tpm:
            raise RequestTooLarge(f"estimated request of {est_tokens} tokens exceeds the TPM limit {self.tpm}")
        while True:
            now = self.clock()
            st = self._load()
            st["events"] = [e for e in st["events"] if now - e[0] < 86400]
            if st.get("blocked_until", 0) > now:
                self._save(st)
                raise DailyLimitReached(st["blocked_until"], "blocked by an earlier rate-limit response")
            if len(st["events"]) >= self.rpd:
                oldest = min(e[0] for e in st["events"])
                self._save(st)
                raise DailyLimitReached(oldest + 86400)
            if self.tpd:  # tokens per day over the last 24 h (this machine's own events only)
                day = sorted(st["events"], key=lambda e: e[0])
                used = sum(e[1] for e in day)
                if used + est_tokens > self.tpd:
                    freed, nxt = 0, day[-1][0] + 86400
                    for e in day:
                        freed += e[1]
                        if used - freed + est_tokens <= self.tpd:
                            nxt = e[0] + 86400
                            break
                    self._save(st)
                    raise DailyLimitReached(nxt, f"daily token limit ({self.tpd}) would be exceeded")
            window = sorted((e for e in st["events"] if now - e[0] < 60), key=lambda e: e[0])
            total = sum(e[1] for e in window)
            if self.rpm and len(window) >= self.rpm:  # requests per minute
                wait_until = window[len(window) - self.rpm][0] + 60
                self._save(st)
                self.sleep(max(0.05, wait_until - now) + 0.05)
                continue
            if total + est_tokens <= self.tpm:
                ts = now
                while any(e[0] == ts for e in st["events"]):
                    ts += 1e-6
                st["events"].append([ts, int(est_tokens)])
                self._save(st)
                return ts
            need = total + est_tokens - self.tpm
            freed, wait_until = 0, now + 60
            for e in window:
                freed += e[1]
                if freed >= need:
                    wait_until = e[0] + 60
                    break
            self._save(st)
            self.sleep(max(0.05, wait_until - now) + 0.05)

    def settle(self, ts: float, actual_tokens: int) -> None:
        """Replace the estimate for an event with the reported token usage."""
        st = self._load()
        for e in st["events"]:
            if e[0] == ts:
                e[1] = int(actual_tokens)
        self._save(st)

    def block_until(self, ts: float) -> None:
        st = self._load()
        st["blocked_until"] = ts
        self._save(st)
