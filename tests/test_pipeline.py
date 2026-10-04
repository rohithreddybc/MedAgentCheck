"""End-to-end with mock backends: code -> verify -> resolve -> agree -> report -> perturb. No network."""
import json
import re

from agentaudit.agree import run_agree
from agentaudit.backends import Response
from agentaudit.coding import parse_result, run_coding
from agentaudit.items import load_items
from agentaudit.perturb import run_perturb, summarise
from agentaudit.report import run_report
from agentaudit.resolve import run_resolve
from agentaudit.retrieve import run_retrieval
from agentaudit.throttle import DailyLimitReached
from agentaudit.verify import run_verify


class MockBackend:
    """Scores 2 and quotes the first line of the first excerpt that mentions 'five times'; else 0."""

    def __init__(self, model="mock", fabricate=False, fail_after=None):
        self.model, self.fabricate, self.n, self.fail_after = model, fabricate, 0, fail_after
        self.prompts = []

    def complete(self, system, prompt):
        if self.fail_after is not None and self.n >= self.fail_after:
            raise DailyLimitReached(1e12)
        self.n += 1
        self.prompts.append(prompt)
        blocks = re.findall(r"### \[(.*?)\] surface=\S+(?: agent_visible)? path=\S+\n(.*?)(?=\n\n### \[|\Z)", prompt, re.S)
        for cid, text in blocks:
            if "five times" in text and "## Item A1" in prompt:
                q = "Each task was run five times per model with independent seeds"
                if self.fabricate:
                    q = "Each task was run fifty times"
                body = {"score": 2, "elements": [True, False, False], "quotes": [{"chunk_id": cid, "text": q}],
                        "contradicted": False, "contradiction_quotes": [], "rationale": "ok"}
                return Response("```json\n" + json.dumps(body) + "\n```", self.model, {"total_tokens": 10})
        body = {"score": 0, "elements": [False, False, False], "quotes": [], "contradicted": False,
                "contradiction_quotes": [], "rationale": "searched: S1, S2"}
        return Response(json.dumps(body), self.model, {})


SPEC_OSS = {"backend": "openai", "model": "mock-oss", "family": "openai-oss"}
SPEC_CL = {"backend": "claude", "model": "mock-claude", "family": "claude"}


def test_parse_result_variants():
    it = load_items()["A1"]
    p = parse_result('noise {"score": "2", "elements": [true,false,true], "quotes": [{"chunk_id": "x", "text": "t"}]} tail', it)
    assert p["score"] == 2 and p["elements"] == [True, False, True] and p["contradicted"] is False
    assert parse_result('{"score": "na"}', load_items()["A5"])["score"] == "NA"
    assert parse_result('{"score": 1, "elements": [1]}', it)["elements"] is None


def test_full_pipeline_with_mocks(run_dir, tmp_path):
    run = run_dir
    run_retrieval(run, "toy", ["A1", "C6"])
    out = {}
    for name, spec, be in [("gpt-oss-120b", SPEC_OSS, MockBackend("oss")), ("sonnet", SPEC_CL, MockBackend("s")),
                           ("opus", SPEC_CL, MockBackend("o", fabricate=True))]:
        out[name] = run_coding(run, "toy", name, spec, be, ["A1", "C6"], log=lambda *_: None)
        assert len(out[name]["done"]) == 2
    # resume: nothing is recoded
    be = MockBackend()
    again = run_coding(run, "toy", "sonnet", SPEC_CL, be, ["A1", "C6"], log=lambda *_: None)
    assert again["skipped"] == ["A1", "C6"] and be.n == 0
    rec = json.loads((run / "coding" / "toy" / "A1" / "sonnet.json").read_text(encoding="utf-8"))
    assert rec["prompt_sha256"] and rec["model_id"] == "s" and rec["attempts"][0]["raw_response"]
    # identical inputs: same prompt for every coder
    assert be.prompts == []
    # verify: opus fabricated its quote -> unsupported
    vs = run_verify(run, "toy")
    by = {(v["item"], v["coder"]): v for v in vs}
    assert by[("A1", "sonnet")]["effective"] == 2 and by[("A1", "gpt-oss-120b")]["effective"] == 2
    assert by[("A1", "opus")]["effective"] == 0 and "unsupported" in by[("A1", "opus")]["flags"]
    s = run_resolve(run, ["toy"])
    cells = json.loads((run / "resolved" / "toy.json").read_text(encoding="utf-8"))["cells"]
    assert cells["A1"]["final"] == 2 and cells["A1"]["status"] == "resolved"
    assert cells["C6"]["final"] == 0 and cells["C6"]["status"] == "established_zero"
    assert s["fallback_cells"] == 0
    ag = run_agree(run, ["toy"], n_boot=20)
    assert any(k.startswith("cross-family:") for k in ag["sets"])
    md = run_report(run, ["toy"])[0].read_text(encoding="utf-8")
    assert "Score card: toy" in md and "A1" in md and "never means" in md


def test_daily_limit_stops_cleanly_and_resumes(run_dir):
    run = run_dir
    run_retrieval(run, "toy", ["A1", "C6", "C1"])
    be = MockBackend(fail_after=1)
    s = run_coding(run, "toy", "gpt-oss-120b", SPEC_OSS, be, ["A1", "C6", "C1"], log=lambda *_: None)
    assert s["done"] == ["A1"] and s["blocked"]["item"] == "C6"
    s2 = run_coding(run, "toy", "gpt-oss-120b", SPEC_OSS, MockBackend(), ["A1", "C6", "C1"], log=lambda *_: None)
    assert s2["skipped"] == ["A1"] and s2["done"] == ["C6", "C1"]


def test_prompt_embeds_manual_text_verbatim(run_dir):
    run = run_dir
    run_retrieval(run, "toy", ["A5"])
    be = MockBackend()
    run_coding(run, "toy", "sonnet", SPEC_CL, be, ["A5"], log=lambda *_: None)
    items = load_items()
    p = be.prompts[0]
    for needle in (items["A5"].anchors, items["A5"].item_text, items["A5"].na_clause):
        assert needle in p
    assert "G7 NA." in p and "agent_visible" in p and "s5_reach" in p


def test_perturb_end_to_end(run_dir):
    run = run_dir
    run_retrieval(run, "toy", ["A1"])
    for name, spec in (("gpt-oss-120b", SPEC_OSS), ("sonnet", SPEC_CL)):
        run_coding(run, "toy", name, spec, MockBackend(name), ["A1"], log=lambda *_: None)
    run_verify(run, "toy")
    run_resolve(run, ["toy"])

    class Echo(MockBackend):  # scores 2 whenever the canonical injected sentence is in the prompt
        def complete(self, system, prompt):
            self.n += 1
            m = re.search(r"### \[(.*?)\] surface=\S+ path=\S+\n(?:(?!### ).)*?(run five times|Each task was run five times)", prompt, re.S)
            return super().complete(system, prompt)

    cb = {"gpt-oss-120b": (SPEC_OSS, MockBackend("oss")), "sonnet": (SPEC_CL, MockBackend("s"))}
    s = run_perturb(run, "toy", ["A1"], cb, log=lambda *_: None)
    assert s["done"] > 0 and not s["failed"]
    summ = summarise(run, ["toy"])
    assert summ["by_coder"]["RESOLVED"] and summ["by_coder"]["sonnet"]["sensitivity"]["n"] >= 1
    # deletion removed the evidence the base coding cited, so the mock must now answer 0 there
    rows = [r for r in summ["rows"] if r["vtype"] == "deletion" and r["coder"] == "sonnet"]
    assert rows and rows[0]["level"] == 0 and rows[0]["ok"]
