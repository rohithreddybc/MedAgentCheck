import json
import re
import subprocess

import pytest

from agentaudit.agree import run_agree
from agentaudit.backends import (BackendAuthError, BackendError, CodexHeadlessBackend, GeminiBackend,
                                 OpenAICompatBackend, Response)
from agentaudit.chunking import Chunk
from agentaudit.coders import load_coders, make_backend
from agentaudit.doctor import check_claude, check_codex, check_gemini, check_mistral
from agentaudit.items import ITEM_ORDER, load_items
from agentaudit.packet_score import (GROUP_PLANS, extract_array, parse_packet_response, render_packet,
                                     render_packet_prompt, score_packet, select_packet)
from agentaudit.resolve import run_resolve
from agentaudit.throttle import DailyLimitReached, Throttle
from agentaudit.util import read_json


def mk(surface, path, start, text, s5=False):
    return Chunk(f"{surface}:{path}:{start}-{start + 1}", surface, path, start, start + 1, text, s5,
                 len(text) // 4, "h")


# ---- packet cap
def test_cap_drops_s4_non_s5_largest_file_first_and_never_others():
    big = "x" * 4000
    cs = [mk("S1", "paper", 1, big), mk("S2", "README.md", 1, "r" * 400), mk("S4", "a/small.py", 1, "s" * 400),
          mk("S4", "b/big.py", 1, big), mk("S4", "b/big.py", 3, big), mk("S4", "c/mid.py", 1, "m" * 2000),
          mk("S4", "prompts.py", 1, "p" * 400, s5=True)]
    sel = select_packet(cs, cap_tokens=1000 + 1000)  # chunk text ~ 3.5k tokens before the cap
    ids = [d["id"] for d in sel["dropped"]]
    assert ids[0].startswith("S4:b/big.py") and ids[1].startswith("S4:b/big.py")  # largest file first
    assert not sel["over_cap"] and sel["tokens"] <= sel["cap_tokens"]
    kept = {c.id for c in sel["kept"]}
    assert "S1:paper:1-2" in kept and "S4:prompts.py:1-2" in kept and "S2:README.md:1-2" in kept
    # deterministic
    assert [d["id"] for d in select_packet(cs, 2000)["dropped"]] == ids


def test_cap_not_reached_keeps_everything_and_over_cap_flag():
    cs = [mk("S1", "p", 1, "a" * 400)]
    assert select_packet(cs, 150000)["dropped"] == []
    assert select_packet([mk("S1", "p", 1, "a" * 40000)], 1000)["over_cap"] is True


def test_render_groups_by_surface_with_s5_separate():
    cs = [mk("S4", "t.py", 1, "code"), mk("S4", "p.py", 1, "prompt", s5=True), mk("S1", "paper", 1, "text")]
    t = render_packet(cs)
    assert t.index("## S1") < t.index("## S2") < t.index("## S4") < t.index("## S5")
    assert t.index("[S4:p.py:1-2]") > t.index("## S5") and t.index("[S4:t.py:1-2]") < t.index("## S5")


def test_prompt_contains_items_anchors_na_and_g_rules():
    items = load_items()
    p = render_packet_prompt("PACKET", ["C1", "A5"], items)
    assert "Item C1" in p and "Item A5" in p and "PACKET" in p and "Global rules" in p
    assert items["A5"].anchors in p and "NA clause" in p and "s5_reach" in p
    assert "{{" not in p


def test_group_plans_partition_all_items():
    for n, plan in GROUP_PLANS.items():
        flat = [i for g in plan for i in g]
        assert flat == ITEM_ORDER or sorted(flat) == sorted(ITEM_ORDER)
        assert len(plan) == n


# ---- parsing
def obj(i, score=0, **kw):
    d = {"item": i, "score": score, "elements": [False] * 3 if i.startswith("A") else [], "quotes": [],
         "contradicted": False, "contradiction_quotes": [], "s5_reach": None, "rationale": "searched: S1"}
    d.update(kw)
    return d


def test_parse_array_wrapped_and_keyed_forms():
    items = load_items()
    g = ["C1", "A1"]
    arr = [obj("C1"), obj("A1", 1)]
    for text in [json.dumps(arr), "```json\n" + json.dumps(arr) + "\n```", json.dumps({"results": arr}),
                 "noise " + json.dumps(arr) + " tail", json.dumps({"C1": arr[0], "A1": arr[1]})]:
        ok, err = parse_packet_response(text, g, items)
        assert set(ok) == set(g) and not err
    ok, err = parse_packet_response(json.dumps([obj("C1")]), g, items)
    assert err == {"A1": "missing from response"}
    with pytest.raises(Exception):
        extract_array("no json here")


# ---- mocked whole-packet scoring
class PacketMock:
    """Reads chunk headers from the prompt; answers every item in the prompt."""

    def __init__(self, model, quote_for_a1=None, fabricate=False, score_a1=2):
        self.model, self.calls, self.fabricate, self.score_a1 = model, [], fabricate, score_a1

    def complete(self, system, prompt, **kw):
        self.calls.append(prompt)
        ids = re.findall(r"^### Item (\w+):", prompt, re.M)
        pk = prompt.split("## Evidence packet", 1)[1].split("## Items to score", 1)[0]
        chunks = dict(re.findall(r"^### \[(S\d:[^\]]+)\] path=\S+\n(.*?)(?=\n\n### \[S\d:|\n\n## |\Z)", pk,
                                 re.S | re.M))
        out = []
        for i in ids:
            o = obj(i)
            if i == "A1":
                cid = next(c for c, t in chunks.items() if "five times" in t)
                q = "Each task was run five times per model with independent seeds"
                if self.fabricate:
                    q = "Each task was run fifty times per model with fresh seeds"
                o.update(score=self.score_a1, elements=[True, False, False], quotes=[{"chunk_id": cid, "text": q}])
            out.append(o)
        return Response(json.dumps(out), self.model, {"total_tokens": 5})


SPECS = {"sonnet": {"backend": "claude", "model": "m-a", "family": "anthropic"},
         "codex": {"backend": "codex", "model": None, "family": "openai"},
         "gemini": {"backend": "gemini", "model": "g", "family": "google"}}


def test_score_packet_end_to_end_three_families(run_dir):
    run = run_dir
    summ = {}
    mocks = {"sonnet": PacketMock("claude-sonnet-5-5"), "codex": PacketMock("gpt-x"), "gemini": PacketMock("gemini-2.5-pro-001", fabricate=True)}
    for c, be in mocks.items():
        summ[c] = score_packet(run, "toy", c, SPECS[c], be)
        assert len(be.calls) == 1  # one call for all 25 items
        assert len(summ[c]["done"]) == 25
    arr = read_json(run / "scoring" / "toy" / "sonnet" / "results.json")
    assert [o["item"] for o in arr] == ITEM_ORDER
    assert set(arr[0]) == {"item", "score", "elements", "quotes", "contradicted", "contradiction_quotes", "s5_reach", "rationale"}
    assert summ["sonnet"]["verification"]["quote_verification_rate"] == 1.0
    assert summ["gemini"]["verification"]["quote_verification_rate"] == 0.0  # fabricated quote
    man = read_json(run / "scoring" / "toy" / "sonnet" / "packet_manifest.json")
    assert man["dropped"] == [] and man["tokens_sent"] > 0
    res = run_resolve(run, ["toy"])
    cell = read_json(run / "resolved" / "toy.json")["cells"]["A1"]
    # sonnet + codex verified at 2 (two families); gemini unsupported -> effective 0
    assert cell["final"] == 2 and cell["status"] == "resolved" and set(cell["supporters"]) == {"sonnet", "codex"}
    assert res["total_cells"] == 25
    ag = run_agree(run, ["toy"], n_boot=10)
    assert "cross-family:codex|gemini" in ag["sets"] and "cross-family:codex|sonnet" in ag["sets"]
    assert any(k.startswith("all:") for k in ag["sets"])


def test_two_distinct_families_needed_not_two_coders(run_dir):
    run = run_dir
    for c in ("sonnet", "codex"):  # both anthropic family for this test
        spec = dict(SPECS["sonnet"])
        score_packet(run, "toy", c, spec, PacketMock("m"))
    run_resolve(run, ["toy"])
    cell = read_json(run / "resolved" / "toy.json")["cells"]["A1"]
    assert cell["final"] == 0 and cell["status"] == "not_established"
    assert cell["majority_final"] == 2  # sensitivity variant


def test_groups_and_resume(run_dir):
    be = PacketMock("m")
    s = score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], be, groups=3)
    assert len(be.calls) == 3 and len(s["done"]) == 25
    assert all(f"Item {i}:" in be.calls[1] for i in GROUP_PLANS[3][1])
    be2 = PacketMock("m")
    score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], be2, groups=3)
    assert be2.calls == []  # resumed: nothing recalled
    score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], be2, groups=3, force=True)
    assert len(be2.calls) == 3


def test_cap_applied_and_recorded_in_manifest(run_dir):
    from agentaudit.chunking import Source
    from agentaudit.packet import write_packet
    from conftest import make_sources

    src = make_sources() + [Source("S4", "config/big.yaml", chr(10).join(f"key{i}: value number {i}" * 3 for i in range(400)))]
    write_packet(run_dir, "toy", src, {"name": "toy", "built_utc": "2026-01-01T00:00:00Z"})
    be = PacketMock("m")
    score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], be, cap_tokens=3000)
    man = read_json(run_dir / "scoring" / "toy" / "sonnet" / "packet_manifest.json")
    assert man["n_dropped"] >= 1 and all(d["id"].startswith("S4:") for d in man["dropped"])
    assert not any(d["id"] in man["kept_ids"] for d in man["dropped"])


def test_partial_response_is_retried_then_recorded(run_dir):
    class Short(PacketMock):
        def complete(self, system, prompt, **kw):
            r = super().complete(system, prompt)
            arr = json.loads(r.text)[:20]
            return Response(json.dumps(arr), r.model_id, {})

    s = score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], Short("m"))
    assert len(s["done"]) == 20 and len(s["failed"]) == 5
    assert read_json(run_dir / "scoring" / "toy" / "sonnet" / "group1.json")["status"] == "partial"


def test_auth_error_blocks_cleanly(run_dir):
    class Bad:
        def complete(self, s, p, **kw):
            raise BackendAuthError("not logged in")

    s = score_packet(run_dir, "toy", "sonnet", SPECS["sonnet"], Bad())
    assert s["blocked"] and "authentication" in s["blocked"]["reason"] and not s["done"]


# ---- backends
def test_codex_backend_command_and_model_id(tmp_path):
    calls = []

    def runner(cmd, **kw):
        calls.append((cmd, kw))
        if cmd[1:3] == ["exec", "--help"]:
            return subprocess.CompletedProcess(cmd, 0, "--sandbox --output-last-message --skip-git-repo-check --ephemeral", "")
        out = cmd[cmd.index("--output-last-message") + 1]
        open(out, "w", encoding="utf-8").write('[{"item": "C1"}]')
        return subprocess.CompletedProcess(cmd, 0, "", "OpenAI Codex v9\nmodel: gpt-5-codex\nprovider: openai\n")

    b = CodexHeadlessBackend(None, codex_bin="codex", runner=runner)
    r = b.complete("sys", "prompt")
    cmd, kw = calls[-1]
    assert r.text == '[{"item": "C1"}]' and r.model_id == "gpt-5-codex"
    assert cmd[cmd.index("--sandbox") + 1] == "read-only" and cmd[-1] == "-" and "--ephemeral" in cmd
    assert "--model" not in cmd and "sys" in kw["input"] and "prompt" in kw["input"]
    b2 = CodexHeadlessBackend("gpt-x", codex_bin="codex", runner=runner)
    assert "--model" in b2.build_cmd("o", "d")


def test_codex_unsupported_optional_flags_skipped_and_auth_error():
    def runner(cmd, **kw):
        if cmd[1:3] == ["exec", "--help"]:
            return subprocess.CompletedProcess(cmd, 0, "--sandbox", "")
        return subprocess.CompletedProcess(cmd, 1, "", "Error: not logged in. Run codex login")

    b = CodexHeadlessBackend(None, codex_bin="codex", runner=runner)
    assert "--ephemeral" not in b.build_cmd("o", "d")
    with pytest.raises(BackendAuthError):
        b.complete("s", "p")


class FakeResp:
    def __init__(self, status=200, body=None, text=None):
        self.status_code, self._b = status, body or {}
        self.text = text if text is not None else json.dumps(self._b)
        self.headers = {}

    def json(self):
        return self._b


class FakeSession:
    def __init__(self, responses):
        self.r, self.calls = list(responses), []

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append((url, headers, json.loads(data)))
        return self.r.pop(0)


def gem_ok(model="gemini-2.5-pro-001", finish="STOP"):
    return {"candidates": [{"content": {"parts": [{"text": "[]"}]}, "finishReason": finish}],
            "usageMetadata": {"totalTokenCount": 1234}, "modelVersion": model}


def test_gemini_request_shape_key_in_header_and_model_id():
    sess = FakeSession([FakeResp(200, gem_ok())])
    b = GeminiBackend(api_key="K", session=sess, sleep=lambda s: None)
    r = b.complete("sys", "hello")
    url, headers, payload = sess.calls[0]
    assert url.endswith("/models/gemini-2.5-pro:generateContent") and "K" not in url
    assert headers["x-goog-api-key"] == "K"
    gc = payload["generationConfig"]
    assert gc["temperature"] == 0 and gc["responseMimeType"] == "application/json"
    assert payload["systemInstruction"]["parts"][0]["text"] == "sys"
    assert r.model_id == "gemini-2.5-pro-001"


def test_gemini_daily_quota_falls_back_and_blocks_primary_state(tmp_path):
    quota = {"error": {"code": 429, "message": "Quota exceeded for metric GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                       "details": []}}
    sess = FakeSession([FakeResp(429, quota), FakeResp(200, gem_ok("gemini-2.5-flash-002"))])
    th = {"gemini-2.5-pro": Throttle(tmp_path / "p.json", tpm=250000, rpd=100, rpm=5),
          "gemini-2.5-flash": Throttle(tmp_path / "f.json", tpm=250000, rpd=250, rpm=10)}
    b = GeminiBackend(api_key="K", session=sess, throttles=th, sleep=lambda s: None)
    r = b.complete("s", "p")
    assert sess.calls[1][0].find("gemini-2.5-flash") > 0 and r.meta["fallback_from"] == "gemini-2.5-pro"
    with pytest.raises(DailyLimitReached):  # primary stays blocked on disk (resumable)
        th["gemini-2.5-pro"].acquire(10)
    # with no fallback the quota error surfaces
    b2 = GeminiBackend(fallback_model=None, api_key="K", session=FakeSession([FakeResp(429, quota)]), sleep=lambda s: None)
    with pytest.raises(DailyLimitReached):
        b2.complete("s", "p")


def test_gemini_retry_delay_truncation_and_auth():
    rl = {"error": {"details": [{"retryDelay": "7s"}]}}
    slept = []
    sess = FakeSession([FakeResp(429, rl), FakeResp(200, gem_ok())])
    GeminiBackend(api_key="K", session=sess, sleep=slept.append).complete("s", "p")
    assert any(abs(x - 7.5) < 1e-6 for x in slept)
    with pytest.raises(BackendError, match="MAX_TOKENS"):
        GeminiBackend(api_key="K", session=FakeSession([FakeResp(200, gem_ok(finish="MAX_TOKENS"))])).complete("s", "p")
    with pytest.raises(BackendAuthError):
        GeminiBackend(api_key="K", session=FakeSession([FakeResp(403, {}, "denied")])).complete("s", "p")
    with pytest.raises(BackendAuthError):
        GeminiBackend(api_key=None, api_key_env="AGENTAUDIT_NO_SUCH_VAR", session=FakeSession([])).complete("s", "p")


def test_rpm_throttle_waits():
    t = {"v": 1000.0}
    slept = []

    def sleep(s):
        slept.append(s)
        t["v"] += s

    th = Throttle(None, tpm=10**6, rpd=100, rpm=2, clock=lambda: t["v"], sleep=sleep)
    th.acquire(10)
    th.acquire(10)
    assert slept == []
    th.acquire(10)
    assert slept and 59 < sum(slept) < 62


def test_mistral_spec_and_gemini_spec_in_registry(tmp_path):
    c = load_coders()
    assert c["mistral"]["family"] == "mistral" and c["mistral"]["model"] == "mistral-large-latest"
    assert c["gemini"]["family"] == "google" and c["codex"]["family"] == "openai" and c["sonnet"]["family"] == "anthropic"
    assert c["sonnet"]["model"] == "claude-sonnet-5-5"
    b = make_backend(c["mistral"], state_dir=tmp_path)
    assert isinstance(b, OpenAICompatBackend) and b.base_url == "https://api.mistral.ai/v1"
    assert b.api_key_env == "MISTRAL_API_KEY" and b.temperature == 0.0 and b.json_mode
    pl = b.build_payload("s", "p")
    assert pl["response_format"] == {"type": "json_object"} and pl["temperature"] == 0.0
    assert b.throttle.path == tmp_path / "throttle-mistral-large-latest.json"
    g = make_backend(c["gemini"], state_dir=tmp_path)
    assert isinstance(g, GeminiBackend) and set(g.throttles) == {"gemini-2.5-pro", "gemini-2.5-flash"}
    assert isinstance(make_backend(c["codex"]), CodexHeadlessBackend)


def test_mistral_four_families_resolution_generalises():
    from agentaudit.resolve import resolve_cell

    v = {c: {"raw": 1, "effective": 1, "family": f} for c, f in
         [("sonnet", "anthropic"), ("codex", "openai"), ("gemini", "google"), ("mistral", "mistral")]}
    v["gemini"].update(raw=0, effective=0)
    v["mistral"].update(raw=0, effective=0)
    assert resolve_cell(v)["final"] == 1  # anthropic + openai


# ---- doctor
def test_doctor_checks_with_fakes():
    def r(out, rc=0):
        return lambda cmd, **kw: subprocess.CompletedProcess(cmd, rc, out, "")

    assert check_claude(r('{"loggedIn": true, "authMethod": "oauth"}'), lambda n: "claude")["live"] is True
    assert check_claude(r('{"loggedIn": false}'), lambda n: "claude")["live"] is False
    assert check_claude(r(""), lambda n: None)["live"] is False
    assert check_codex(r("Logged in using ChatGPT"), lambda n: "codex")["live"] is True
    assert check_codex(r("Not logged in", 1), lambda n: "codex")["live"] is False
    assert check_codex(r(""), lambda n: None)["live"] is False
    assert check_gemini(env={})["live"] is False and check_mistral(env={})["live"] is False

    class S:
        def __init__(self, code):
            self.code, self.seen = code, []

        def get(self, url, params=None, headers=None, timeout=None):
            self.seen.append((url, params, headers))
            return FakeResp(self.code)

    s = S(200)
    assert check_gemini(s, {"GEMINI_API_KEY": "k"})["live"] is True and "k" not in s.seen[0][0]
    assert check_mistral(S(401), {"MISTRAL_API_KEY": "k"})["live"] is False
