import json

import pytest

from agentaudit.backends import (BackendAuthError, BackendError, ClaudeHeadlessBackend, OpenAICompatBackend,
                                 parse_retry_after)
from agentaudit.throttle import DailyLimitReached, RequestTooLarge, Throttle


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


class FakeResp:
    def __init__(self, status=200, body=None, headers=None, text=""):
        self.status_code, self._b, self.headers, self.text = status, body, headers or {}, text or json.dumps(body or {})

    def json(self):
        return self._b


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append(json.loads(data))
        return self.responses.pop(0)


OK = {"model": "m", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {"total_tokens": 900}}


def backend(responses, clk, th=None, **kw):
    th = th or Throttle(None, tpm=8000, rpd=1000, clock=clk.now, sleep=clk.sleep)
    return OpenAICompatBackend("m", "http://x/v1", throttle=th, session=FakeSession(responses), sleep=clk.sleep,
                               clock=clk.now, api_key="k", max_tokens=1000, **kw), th


def test_retry_after_honoured_on_429():
    clk = Clock()
    b, _ = backend([FakeResp(429, headers={"retry-after": "7"}), FakeResp(200, OK)], clk)
    r = b.complete("sys", "hello")
    assert r.text == "{}" and r.meta["attempts"] == 2
    assert any(abs(s - 7.5) < 1e-6 for s in clk.slept)


def test_exponential_backoff_without_retry_after_and_5xx():
    clk = Clock()
    b, _ = backend([FakeResp(429), FakeResp(500), FakeResp(200, OK)], clk)
    b.complete("sys", "hello")
    assert clk.slept[0] == 5.5 and clk.slept[1] == 10


def test_long_retry_after_is_a_daily_limit_and_blocks_state(tmp_path):
    clk = Clock()
    th = Throttle(tmp_path / "st.json", clock=clk.now, sleep=clk.sleep)
    b, _ = backend([FakeResp(429, headers={"retry-after": "40000"})], clk, th)
    with pytest.raises(DailyLimitReached):
        b.complete("sys", "hello")
    # a fresh process with the same state file is still blocked, then free after the wait
    th2 = Throttle(tmp_path / "st.json", clock=clk.now, sleep=clk.sleep)
    with pytest.raises(DailyLimitReached):
        th2.acquire(100)
    clk.t += 40001
    th2.acquire(100)


def test_other_errors():
    clk = Clock()
    with pytest.raises(BackendAuthError):
        backend([FakeResp(401, text="bad key")], clk)[0].complete("s", "p")
    with pytest.raises(BackendError):
        backend([FakeResp(400, text="bad request")], clk)[0].complete("s", "p")
    b, _ = backend([FakeResp(500)] * 3, clk, max_retries=2)
    with pytest.raises(BackendError):
        b.complete("s", "p")


def test_payload_is_deterministic_json_mode():
    clk = Clock()
    b, _ = backend([FakeResp(200, OK)], clk, extra_params={"reasoning_effort": "low"})
    b.complete("sys", "hello")
    p = b.session.calls[0]
    assert p["temperature"] == 0.0 and p["response_format"] == {"type": "json_object"}
    assert p["reasoning_effort"] == "low" and p["messages"][0]["role"] == "system"


def test_tpm_throttle_waits_and_persists_state(tmp_path):
    clk = Clock()
    path = tmp_path / "state.json"
    th = Throttle(path, tpm=8000, rpd=1000, clock=clk.now, sleep=clk.sleep)
    th.acquire(6000)
    t0 = clk.t
    th2 = Throttle(path, tpm=8000, rpd=1000, clock=clk.now, sleep=clk.sleep)  # new process, same state
    th2.acquire(6000)
    assert clk.t - t0 >= 59  # had to wait for the first event to leave the 60 s window
    with pytest.raises(RequestTooLarge):
        th.acquire(9000)


def test_settle_replaces_estimate(tmp_path):
    clk = Clock()
    th = Throttle(tmp_path / "s.json", tpm=8000, clock=clk.now, sleep=clk.sleep)
    ts = th.acquire(7000)
    th.settle(ts, 1000)
    t0 = clk.t
    th.acquire(6500)
    assert clk.t == t0  # no wait: actual usage was only 1000


def test_rpd_limit_resumes_next_day(tmp_path):
    clk = Clock()
    th = Throttle(tmp_path / "s.json", tpm=10**9, rpd=3, clock=clk.now, sleep=clk.sleep)
    for _ in range(3):
        th.acquire(10)
        clk.t += 1
    with pytest.raises(DailyLimitReached) as e:
        th.acquire(10)
    assert e.value.next_available == pytest.approx(1000.0 + 86400)
    clk.t = 1000.0 + 86400 + 1
    th.acquire(10)


def test_parse_retry_after():
    assert parse_retry_after({"retry-after": "3"}) == 3.0
    assert parse_retry_after({}) is None
    assert parse_retry_after({"Retry-After": "x"}) is None


class FakeProc:
    def __init__(self, out, code=0, err=""):
        self.stdout, self.returncode, self.stderr = out, code, err


def test_claude_command_disables_tools_and_uses_stdin():
    seen = {}

    def runner(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return FakeProc(json.dumps({"result": "{\"score\": 0}", "usage": {"input_tokens": 5},
                                    "modelUsage": {"claude-sonnet-5-5": {}}, "total_cost_usd": 0.01, "is_error": False}))

    b = ClaudeHeadlessBackend("claude-sonnet-5-5", claude_bin="claude", runner=runner)
    r = b.complete("SYS", "PROMPT BODY")
    cmd = seen["cmd"]
    assert cmd[:2] == ["claude", "-p"] and cmd[cmd.index("--model") + 1] == "claude-sonnet-5-5"
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[cmd.index("--tools") + 1] == ""  # all tools disabled
    assert "--safe-mode" in cmd and "--strict-mcp-config" in cmd and "--no-session-persistence" in cmd
    assert "PROMPT BODY" not in cmd and seen["kw"]["input"] == "PROMPT BODY"  # prompt only via stdin
    assert r.text == '{"score": 0}' and r.model_id == "claude-sonnet-5-5"


def test_claude_auth_error_is_fatal_not_retried():
    calls = []

    def runner(cmd, **kw):
        calls.append(1)
        return FakeProc(json.dumps({"is_error": True, "result": "Failed to authenticate: OAuth session expired"}))

    with pytest.raises(BackendAuthError):
        ClaudeHeadlessBackend("m", claude_bin="claude", runner=runner).complete("s", "p")
    assert len(calls) == 1


def test_tpd_429_body_stops_even_with_short_retry_after():
    clk = Clock()
    body = '{"error":{"message":"Rate limit reached ... on tokens per day (TPD): Limit 200000, Used 197455"}}'
    b, th = backend([FakeResp(429, headers={"retry-after": "879"}, text=body)], clk)
    with pytest.raises(DailyLimitReached) as ei:
        b.complete("sys", "hello")
    assert abs(ei.value.next_available - (clk.t + 879)) < 1e-6 and not clk.slept


def test_throttle_tpd_blocks_when_rolling_day_total_would_be_exceeded():
    clk = Clock()
    th = Throttle(None, tpm=8000, rpd=1000, tpd=10000, clock=clk.now, sleep=clk.sleep)
    th.acquire(6000)
    clk.t += 61
    with pytest.raises(DailyLimitReached) as ei:
        th.acquire(5000)
    assert abs(ei.value.next_available - (1000.0 + 86400)) < 1e-6
    clk.t += 86400
    th.acquire(5000)  # the first event has aged out
