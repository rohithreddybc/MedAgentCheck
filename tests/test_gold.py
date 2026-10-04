"""Published-human-gold validation: instruments, gold mapping, scoring and agreement with mocked backends."""
import csv
import json
import re

import pytest

from agentaudit import gold as G
from agentaudit.backends import BackendAuthError, Response
from agentaudit.chunking import Source, wrap_long_lines
from agentaudit.cli import main as cli_main
from agentaudit.gold import (agreement_stats, build_gold_packets, estimate_gold, github_pin, arxiv_pin,
                             gold_agreement, gold_run_dir, items_for_set, load_gold, load_instrument,
                             manifest_for, parse_gold_response, parse_github_url, render_gold_prompt,
                             run_gold_agree, score_gold)
from agentaudit.packet import write_packet
from agentaudit.stats import cohen_kappa, weighted_kappa
from agentaudit.util import read_json

ABC_ITEMS = [("T.1", "For self-hosted tools, the prompt explicitly states the correct tool or package versions."),
             ("T.9", "An automatic oracle solver demonstrates the task configuration is correct."),
             ("T.10", "Outliers in pilot experiments are inspected to find bugs (impossible tasks, shortcuts)."),
             ("R.1", "Benchmark is fully or at least partially open-sourced."),
             ("R.13", "Reports results of trivial agents (e.g., one that does nothing)."),
             ("O.a.1", "Ground truth accounts for semantically equivalent expressions."),
             ("T.7", "Correctness of ground-truth annotation is verified. [T.7/T.8 split inferred from order]")]
BB_ITEMS = [("J.1-1", "Developers state and define the capability. [App. J title: Definition of tested capability]"),
            ("J.1-4", "Benchmark specifies use cases and user personas; n/a for systems without human interaction. [App. J title: Use cases]"),
            ("J.3-11", "Documents data origins and consent where applicable. [App. J title: Documentation of data sources (if applicable)]"),
            ("J.2-1", "Code to evaluate other models is available. [App. J title: Availability of evaluation code]")]
PAPER_NAMES = ["Alpha Bench", "Beta Bench"]


def wcsv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


@pytest.fixture()
def rdir(tmp_path, monkeypatch):
    r = tmp_path / "research"
    f = ["source", "item_id", "stage_or_category", "item_text", "scoring_scale", "source_location", "verbatim_anchor"]
    wcsv(r / "instruments" / "abc_items.csv", [{"item_id": i, "item_text": t} for i, t in ABC_ITEMS], f)
    wcsv(r / "instruments" / "betterbench_items.csv", [{"item_id": i, "item_text": t} for i, t in BB_ITEMS], f)
    # gold: ABC binary on the 4 included items (T.9, T.1, R.1, R.13); T.10 and O.a.1 deliberately present too
    abc_gold = {("Alpha Bench", "T.1"): 1, ("Alpha Bench", "T.9"): 0, ("Alpha Bench", "R.1"): 1, ("Alpha Bench", "R.13"): 0,
                ("Beta Bench", "T.1"): 0, ("Beta Bench", "T.9"): 1, ("Beta Bench", "R.1"): 1, ("Beta Bench", "R.13"): 0,
                ("Alpha Bench", "T.10"): 1, ("Alpha Bench", "O.a.1 [x]"): 1}
    wcsv(r / "gold" / "abc_scores.csv", [{"benchmark": b, "item_id": i, "score": s, "app_d_check_text": "SECRET CHECK TEXT"}
                                          for (b, i), s in abc_gold.items()], ["benchmark", "item_id", "score", "app_d_check_text"])
    wcsv(r / "gold" / "abc_benchmarks.csv",
         [{"benchmark": "Alpha Bench", "paper_url": "https://arxiv.org/pdf/2310.06770", "repo_url_of_benchmark": "https://github.com/o/alpha"},
          {"benchmark": "Beta Bench", "paper_url": "https://arxiv.org/pdf/2502.12115", "repo_url_of_benchmark": "https://huggingface.co/beta"}],
         ["benchmark", "paper_url", "repo_url_of_benchmark"])
    bb_gold = {("Alpha Bench", "J.1-1"): "15", ("Alpha Bench", "J.1-4"): "NA", ("Alpha Bench", "J.2-1"): "0", ("Alpha Bench", "J.3-11"): "5",
               ("Beta Bench", "J.1-1"): "10", ("Beta Bench", "J.1-4"): "5", ("Beta Bench", "J.2-1"): "15", ("Beta Bench", "J.3-11"): "NA"}
    wcsv(r / "gold" / "betterbench_scores.csv", [{"benchmark": b, "criterion_id": c, "score": s} for (b, c), s in bb_gold.items()],
         ["benchmark", "criterion_id", "score"])
    wcsv(r / "gold" / "betterbench_benchmarks.csv",
         [{"benchmark": n, "repo_url": "https://github.com/o/x", "arxiv_id_if_in_betterbench_reference": ""} for n in PAPER_NAMES],
         ["benchmark", "repo_url", "arxiv_id_if_in_betterbench_reference"])
    s = tmp_path / "samples"
    wcsv(s / "abc.csv", [{"item_id": i, "included": "yes" if i in ("T.1", "T.9", "R.1", "R.13") else "no", "reason": "x"}
                         for i in ("T.1", "T.9", "T.10", "R.1", "R.13", "O.a.1", "T.7")], ["item_id", "included", "reason"])
    wcsv(s / "bb.csv", [{"criterion_id": c, "selected": "yes"} for c in ("J.1-1", "J.1-4", "J.3-11", "J.2-1")], ["criterion_id", "selected"])
    wcsv(s / "papers.csv", [{"set": "betterbench", "benchmark": n, "arxiv_id": "2110.08193"} for n in PAPER_NAMES],
         ["set", "benchmark", "arxiv_id"])
    monkeypatch.setattr(G, "ABC_ITEMS_PATH", s / "abc.csv")
    monkeypatch.setattr(G, "BB_CRITERIA_PATH", s / "bb.csv")
    monkeypatch.setattr(G, "PAPERS_PATH", s / "papers.csv")
    return r


# ---- instruments and gold
def test_instrument_cleaning_and_na_rule(rdir):
    abc = load_instrument("abc", rdir)
    assert abc["T.7"].text == "Correctness of ground-truth annotation is verified."  # CSV note stripped
    assert abc["T.1"].title == "" and not abc["T.1"].na_allowed
    bb = load_instrument("betterbench", rdir)
    assert bb["J.1-1"].title == "Definition of tested capability" and bb["J.1-1"].text.endswith("capability.")
    assert bb["J.1-4"].na_allowed and bb["J.3-11"].na_allowed and not bb["J.1-1"].na_allowed
    assert items_for_set("abc") == ["T.1", "T.9", "R.1", "R.13"] and items_for_set("betterbench") == ["J.1-1", "J.1-4", "J.3-11", "J.2-1"]


def test_gold_scale_mapping_and_id_normalisation(rdir):
    a = load_gold("abc", rdir)
    assert a[("Alpha_Bench", "T.1")] == 1 and a[("Alpha_Bench", "O.a.1")] == 1  # "O.a.1 [x]" -> "O.a.1"
    b = load_gold("betterbench", rdir)
    assert [b[("Alpha_Bench", c)] for c in ("J.1-1", "J.1-4", "J.2-1", "J.3-11")] == [3, "NA", 0, 1]
    assert b[("Beta_Bench", "J.1-1")] == 2 and b[("Beta_Bench", "J.2-1")] == 3


def test_prompt_renders_source_items_and_scale(rdir):
    instr = load_instrument("betterbench", rdir)
    p = render_gold_prompt("betterbench", ["J.1-1", "J.1-4"], instr, "PACKET-TEXT")
    assert "PACKET-TEXT" in p and "{{" not in p and "BetterBench" in p
    assert "### Criterion J.1-1: Definition of tested capability" in p and "5 points" in p and "15 points" in p
    assert "NA is allowed for this criterion" in p and "NA is not allowed for this criterion" in p
    assert '0 | 1 | 2 | 3 | "NA"' in p and "2024-11-21" in p and "Do not use prior knowledge" in p
    q = render_gold_prompt("abc", ["T.1"], load_instrument("abc", rdir), "PK")
    assert "Binary" in q and "ABC" in q and '"score": 0 | 1,' in q and "NA is not allowed" in q and "2025-07-10" in q
    assert "SECRET CHECK TEXT" not in q and "Anchors" not in q  # no checklist anchors, no gold wording


def test_parse_gold_response_scales_and_errors():
    arr = [{"item": "J.1-1", "score": 15, "quotes": [{"chunk_id": "[S1:p:1-2]", "text": "abc"}]},
           {"item": "J.1-4", "score": "NA"}, {"item": "J.2-1", "score": 2}, {"item": "J.3-11", "score": 7}]
    ok, err = parse_gold_response(json.dumps(arr), ["J.1-1", "J.1-4", "J.2-1", "J.3-11", "J.4-1"], "betterbench")
    assert ok["J.1-1"]["score"] == 3 and ok["J.1-1"]["quotes"][0]["chunk_id"] == "S1:p:1-2"  # points mapped, brackets stripped
    assert ok["J.1-4"]["score"] == "NA" and ok["J.2-1"]["score"] == 2
    assert "bad score" in err["J.3-11"] and err["J.4-1"] == "missing from response"
    ok, err = parse_gold_response(json.dumps({"results": [{"item": "T.1", "score": 1}, {"item": "R.1", "score": 2}, {"item": "R.2", "score": "NA"}]}),
                                  ["T.1", "R.1", "R.2"], "abc")
    assert list(ok) == ["T.1"] and set(err) == {"R.1", "R.2"}  # binary: 2 and NA are rejected


# ---- scoring and agreement (mock backends)
class GoldMock:
    """Answers each criterion from answers[bench][item] (a score) with a real quote from the packet. ``fabricate``
    uses a quote that is not in the packet."""

    def __init__(self, model, answers, fabricate=False):
        self.model, self.answers, self.fabricate, self.calls = model, answers, fabricate, []

    def complete(self, system, prompt, **kw):
        self.calls.append(prompt)
        bench = re.search(r"Paper of (\w+) and its", prompt).group(1)
        ids = re.findall(r"^### Criterion ([\w.\-]+)", prompt, re.M)
        cid = re.search(r"^### \[(S1:[^\]]+)\]", prompt, re.M).group(1)
        out = []
        for i in ids:
            sc = self.answers[bench][i]
            q = []
            if sc not in (0, "NA"):
                q = [{"chunk_id": cid, "text": "Nothing like this is in the packet at all, honestly" if self.fabricate
                      else f"Paper of {bench} and its evaluation harness"}]
            out.append({"item": i, "score": sc, "quotes": q, "rationale": "searched: S1"})
        return Response(json.dumps(out), self.model, {"total_tokens": 7})


SPEC = {"sonnet": {"backend": "claude", "model": "m", "family": "anthropic"},
        "codex": {"backend": "codex", "model": None, "family": "openai"},
        "gemini": {"backend": "gemini", "model": "g", "family": "google"}}


def make_packets(run, set_name):
    grun = gold_run_dir(run, set_name)
    for k in ("Alpha_Bench", "Beta_Bench"):
        text = wrap_long_lines(f"Paper of {k} and its evaluation harness\n" + "\n".join(f"Filler line {i} about the benchmark." for i in range(40)))
        write_packet(grun, k, [Source("S1", "paper.txt", text), Source("S2", "README.md", "# readme")], {"name": k, "built_utc": "t"})


def test_abc_end_to_end_agreement_and_no_gold_in_outputs(tmp_path, rdir):
    run = tmp_path / "run"
    make_packets(run, "abc")
    instr, ids = load_instrument("abc", rdir), items_for_set("abc")
    gold = {"Alpha_Bench": {"T.1": 1, "T.9": 0, "R.1": 1, "R.13": 0}, "Beta_Bench": {"T.1": 0, "T.9": 1, "R.1": 1, "R.13": 0}}
    codex = {b: dict(d) for b, d in gold.items()}
    codex["Alpha_Bench"]["T.1"] = 0  # one miss
    ans = {"sonnet": gold, "codex": codex, "gemini": {b: {i: 1 for i in d} for b, d in gold.items()}}
    mocks = {"sonnet": GoldMock("s", ans["sonnet"]), "codex": GoldMock("c", ans["codex"]),
             "gemini": GoldMock("g", ans["gemini"], fabricate=True)}  # all 1s but no verifiable quote -> effective 0
    for c, m in mocks.items():
        for k in ("Alpha_Bench", "Beta_Bench"):
            s = score_gold(run, "abc", k, c, SPEC[c], m, ids, instr, log=lambda *a: None)
            assert s["status"] == "ok" and s["items"] == 4
        assert len(m.calls) == 2  # one call per (benchmark, coder), all items together
    rec = read_json(gold_run_dir(run, "abc") / "gold_scoring" / "Alpha_Bench" / "gemini.json")
    assert rec["items"]["T.1"]["verification"]["effective"] == 0 and "unsupported" in rec["items"]["T.1"]["verification"]["flags"]
    res = gold_agreement(run, "abc", rdir, n_boot=50)
    s, c, g = res["by_coder"]["sonnet"], res["by_coder"]["codex"], res["by_coder"]["gemini"]
    assert s["n_cells"] == 8 and s["raw_agreement"]["rate"] == 1.0 and s["cohen_kappa"] == 1.0
    assert abs(c["raw_agreement"]["rate"] - 7 / 8) < 1e-12 and abs(c["cohen_kappa"] - 0.75) < 1e-12
    assert abs(g["raw_agreement"]["rate"] - 0.5) < 1e-12 and abs(g["cohen_kappa"]) < 1e-12
    assert s["confusion"] == {"0": {"0": 4, "1": 0}, "1": {"0": 0, "1": 4}}
    # resolved: the cell whose only 1 vote comes from sonnet (codex flipped it) is not established -> 0
    r = res["resolved"]
    assert r["n_cells"] == 8 and abs(r["raw_agreement"]["rate"] - 7 / 8) < 1e-12 and r["fallback_cells"] >= 1
    assert res["items"] == ["R.1", "R.13", "T.1", "T.9"]  # T.10 and O.a.1 never scored
    assert "n_cells" in res["by_coder"]["sonnet"] and "T.10" not in json.dumps(res)
    # ABC outputs carry statistics only
    files = G.write_agreement(run, "abc", res)
    names = sorted(p.name for p in files)
    assert names == ["agreement.csv", "agreement.json"]
    allout = "".join(p.read_text(encoding="utf-8") for p in (gold_run_dir(run, "abc") / "agreement").iterdir())
    assert "cells_with_gold" not in allout and "SECRET CHECK TEXT" not in allout
    parsed = json.loads((gold_run_dir(run, "abc") / "agreement" / "agreement.json").read_text(encoding="utf-8"))
    assert "_cells" not in parsed and not any(k in parsed for k in ("cells", "gold_scores"))
    # resume: nothing is called again
    n = len(mocks["sonnet"].calls)
    assert score_gold(run, "abc", "Alpha_Bench", "sonnet", SPEC["sonnet"], mocks["sonnet"], ids, instr)["status"] == "already_done"
    assert len(mocks["sonnet"].calls) == n
    assert score_gold(run, "abc", "Alpha_Bench", "sonnet", SPEC["sonnet"], mocks["sonnet"], ids, instr, dry_run=True, force=True)["status"] == "dry_run"
    assert len(mocks["sonnet"].calls) == n


def test_betterbench_ordinal_agreement_na_handling_and_cells_file(tmp_path, rdir):
    run = tmp_path / "run"
    make_packets(run, "betterbench")
    instr, ids = load_instrument("betterbench", rdir), items_for_set("betterbench")
    gold = {"Alpha_Bench": {"J.1-1": 3, "J.1-4": "NA", "J.2-1": 0, "J.3-11": 1},
            "Beta_Bench": {"J.1-1": 2, "J.1-4": 1, "J.2-1": 3, "J.3-11": "NA"}}
    pred = {"Alpha_Bench": {"J.1-1": 2, "J.1-4": 1, "J.2-1": 0, "J.3-11": 1},   # one near miss, one NA-vs-score
            "Beta_Bench": {"J.1-1": 2, "J.1-4": 1, "J.2-1": 1, "J.3-11": 2}}    # one far miss, one score-vs-NA
    for c in ("sonnet", "codex"):
        for k in gold:
            score_gold(run, "betterbench", k, c, SPEC[c], GoldMock(c, pred), ids, instr, log=lambda *a: None)
    res = gold_agreement(run, "betterbench", rdir, n_boot=50)
    s = res["by_coder"]["sonnet"]
    # cells compared: 8 minus the two gold NAs
    assert s["n_cells"] == 6 and s["n_gold_na"] == 2 and s["n_pred_na_where_gold_scored"] == 0
    gs, ps = [3, 0, 1, 2, 1, 3], [2, 0, 1, 2, 1, 1]
    assert abs(s["weighted_kappa_quadratic"] - weighted_kappa(gs, ps, [0, 1, 2, 3], "quadratic")) < 1e-12
    assert abs(s["weighted_kappa_linear"] - weighted_kappa(gs, ps, [0, 1, 2, 3], "linear")) < 1e-12
    assert abs(s["cohen_kappa"] - cohen_kappa(gs, ps)) < 1e-12
    assert s["raw_agreement"]["agree"] == 4 and s["within_one_level"]["hits"] == 5
    assert s["primary_statistic"] == "weighted_kappa_quadratic" and s["primary_value"] == s["weighted_kappa_quadratic"]
    # both coders (two families) answer alike, so the resolved scores equal the coders' scores
    assert res["resolved"]["n_cells"] == 6 and res["resolved"]["raw_agreement"] == s["raw_agreement"]
    assert res["resolved"]["status_counts"]["resolved"] == 7 and res["resolved"]["fallback_cells"] == 0
    files = G.write_agreement(run, "betterbench", res)
    assert "cells_with_gold.csv" in {p.name for p in files}  # BetterBench is CC BY 4.0: per-cell file allowed
    rows = list(csv.DictReader(open(gold_run_dir(run, "betterbench") / "agreement" / "cells_with_gold.csv", encoding="utf-8")))
    assert {r["coder"] for r in rows} == {"sonnet", "codex", "RESOLVED"}


def test_agreement_stats_na_pred_and_degenerate_kappa():
    cfg = G.SETS["betterbench"]
    pairs = [("b1", "J.1-1", 2, "NA"), ("b1", "J.1-2", "NA", "NA"), ("b2", "J.1-1", 1, 1)]
    st = agreement_stats(pairs, cfg, 20, 1)
    assert st["n_cells"] == 1 and st["n_pred_na_where_gold_scored"] == 1 and st["n_both_na"] == 1
    assert st["cohen_kappa"] is None  # one cell: chance agreement 1
    assert agreement_stats([("b", "x", "NA", 1)], cfg, 20, 1) == {"n_cells": 0, "n_gold_na": 1,
                                                               "n_pred_na_where_gold_scored": 0, "n_both_na": 0}


def test_blocked_backend_is_reported_not_raised(tmp_path, rdir):
    run = tmp_path / "run"
    make_packets(run, "abc")

    class Bad:
        def complete(self, s, p, **kw):
            raise BackendAuthError("not logged in")

    s = score_gold(run, "abc", "Alpha_Bench", "sonnet", SPEC["sonnet"], Bad(), items_for_set("abc"), load_instrument("abc", rdir))
    assert s["status"] == "blocked" and "authentication" in s["reason"]
    assert not (gold_run_dir(run, "abc") / "gold_scoring").exists()


# ---- pins and packets
class R:
    def __init__(self, code=200, body=None, text="", headers=None):
        self.status_code, self._b, self.text, self.headers = code, body, text, headers or {}

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Sess:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        for k, v in self.routes:
            if k in url:
                return v(params or {}) if callable(v) else v
        return R(404)


def commit(sha, date):
    return {"sha": sha, "commit": {"committer": {"date": date}}}


def test_github_pin_last_commit_on_or_before_cutoff_and_fallbacks():
    meta = R(200, {"full_name": "o/r", "default_branch": "main", "size": 12, "archived": False})
    s = Sess([("/commits", lambda p: R(200, [commit("abc123", "2025-07-09T10:00:00Z")]) if "until" in p else R(200, [])),
              ("api.github.com/repos/o/r", meta)])
    pin = github_pin(s, "o", "r", "2025-07-10T23:59:59Z", token="t")
    assert pin["status"] == "ok" and pin["commit"] == "abc123" and pin["flag"] is None and pin["size_kb"] == 12
    assert s.calls[1][1] == {"until": "2025-07-10T23:59:59Z", "per_page": 1}
    # no commit before the cutoff: the first commit is used and flagged
    s2 = Sess([("/commits", lambda p: R(200, []) if "until" in p else
                (R(200, [commit("first", "2025-08-01T00:00:00Z")]) if p.get("page") == "9" else
                 R(200, [commit("tip", "2026-01-01T00:00:00Z")], headers={"Link": '<https://x/commits?per_page=1&page=9>; rel="last"'}))),
               ("api.github.com/repos/o/r", meta)])
    p2 = github_pin(s2, "o", "r", "2025-07-10T23:59:59Z")
    assert p2["commit"] == "first" and "first commit" in p2["flag"]
    assert github_pin(Sess([("api.github.com/repos/o/r", R(451))]), "o", "r", "x")["status"] == "unavailable"
    assert github_pin(Sess([("api.github.com/repos/o/r", R(500))]), "o", "r", "x")["status"] == "error"


def test_arxiv_pin_picks_last_version_on_or_before_cutoff():
    html = ('<strong><a href="/abs/1v1" rel="nofollow">[v1]</a></strong>\n Fri, 15 Oct 2021 16:43:46 UTC (1,587 KB)<br/>\n'
            '<strong><a href="/abs/1v2" rel="nofollow">[v2]</a></strong>\n Mon, 14 Jul 2025 01:00:00 UTC (1 KB)<br/>\n'
            '<strong>[v3]</strong> Tue, 12 Aug 2025 09:00:00 UTC (1 KB)<br/>')
    s = Sess([("arxiv.org/abs/", R(200, text=html))])
    p = arxiv_pin(s, "2110.08193", "2025-07-10T23:59:59Z")
    assert p["version"] == "v1" and p["n_versions"] == 3 and p["flag"] is None
    assert arxiv_pin(s, "2110.08193", "2025-07-14T23:59:59Z")["version"] == "v2"
    late = arxiv_pin(s, "2110.08193", "2020-01-01T00:00:00Z")
    assert late["version"] == "v1" and "later than the cutoff" in late["flag"]
    assert arxiv_pin(Sess([("arxiv.org/abs/", R(200, text="nothing"))]), "x", "2025-07-10T23:59:59Z")["status"] == "error"


def test_parse_github_url_variants():
    assert parse_github_url("https://github.com/openai/SWELancer-Benchmark?tab=readme-ov-file") == ("openai", "SWELancer-Benchmark", None)
    assert parse_github_url("https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird") == ("AlibabaResearch", "DAMO-ConvAI", "bird")
    assert parse_github_url("https://github.com/sylinrl/TruthfulQA/blob/main/truthfulqa/evaluate.py") == ("sylinrl", "TruthfulQA", None)
    assert parse_github_url("https://github.com/x/y.git") == ("x", "y", None)
    assert parse_github_url("https://huggingface.co/gaia-benchmark") is None


def test_pin_set_records_cutoff_and_handles_non_github(rdir):
    meta = R(200, {"full_name": "o/alpha", "default_branch": "main", "size": 5})
    html = '<strong><a href="/abs/1" rel="nofollow">[v1]</a></strong> Mon, 1 Jan 2024 00:00:00 UTC (1 KB)<br/>'
    s = Sess([("/commits", R(200, [commit("sha1", "2025-07-01T00:00:00Z")])), ("api.github.com/repos/o/alpha", meta),
              ("arxiv.org/abs/", R(200, text=html))])
    pins = G.pin_set("abc", rdir, session=s, log=lambda *a: None)
    a, b = pins["Alpha_Bench"], pins["Beta_Bench"]
    assert a["cutoff"] == "2025-07-10T23:59:59Z" and a["repo"]["commit"] == "sha1" and a["arxiv"]["version"] == "v1"
    assert b["repo"]["status"] == "none" and "paper only" in b["repo"]["flag"]
    assert manifest_for("Alpha_Bench", a) == {"name": "Alpha_Bench", "arxiv": {"id": "2310.06770", "version": "v1"},
                                              "repo": {"url": "https://github.com/o/alpha", "commit": "sha1"}}
    assert manifest_for("Beta_Bench", b)["arxiv"]["id"] == "2502.12115" and "repo" not in manifest_for("Beta_Bench", b)


def test_shipped_pins_cover_every_gold_benchmark_with_commit_not_after_cutoff():
    pins = G.load_pins()
    assert set(pins["sets"]) == {"abc", "betterbench"} and pins["seed"] == 20261004
    assert len(pins["sets"]["abc"]) == 10 and len(pins["sets"]["betterbench"]) == 23
    for st, d in pins["sets"].items():
        cut = G.SETS[st]["cutoff"]
        for k, r in d.items():
            assert r["cutoff"] == cut
            if r["repo"].get("status") == "ok":
                assert r["repo"]["commit"] and (r["repo"]["flag"] or r["repo"]["commit_date"] <= cut), k
            else:
                assert r["repo"]["status"] in ("none", "unavailable"), k
            assert r["arxiv"].get("status") == "ok" and r["arxiv"]["version"].startswith("v"), k


def test_build_gold_packets_uses_pinned_versions_and_skips_existing(tmp_path, monkeypatch):
    seen = []

    def fake_build(man, grun, cache, session=None):
        seen.append(man)
        write_packet(grun, man["name"], [Source("S1", "p", "text")], {"name": man["name"], "built_utc": "t"})

    monkeypatch.setattr("agentaudit.packet.build_packet", fake_build)
    pins = {"sets": {"abc": {
        "A": {"repo": {"status": "ok", "repo": "o/a", "commit": "c1", "size_kb": 10, "subpath": "bird"}, "arxiv": {"status": "ok", "id": "1", "version": "v2"}},
        "B": {"repo": {"status": "ok", "repo": "o/b", "commit": "c2", "size_kb": 900_000}, "arxiv": {"status": "none"}},
        "C": {"repo": {"status": "unavailable"}, "arxiv": {"status": "none"}}}}}
    r = build_gold_packets(tmp_path, "abc", pins, log=lambda *a: None)
    assert r["built"] == ["A"] and set(r["failed"]) == {"B", "C"} and "allow-large" in r["failed"]["B"]
    assert seen[0] == {"name": "A", "arxiv": {"id": "1", "version": "v2"},
                       "repo": {"url": "https://github.com/o/a", "commit": "c1", "subpath": "bird"}}
    assert build_gold_packets(tmp_path, "abc", pins, only=["A"], log=lambda *a: None)["skipped"] == ["A"]
    assert build_gold_packets(tmp_path, "abc", pins, allow_large=True, log=lambda *a: None)["built"] == ["B"]


def test_estimate_and_cli_dry_run(tmp_path, rdir, capsys):
    run = tmp_path / "run"
    make_packets(run, "abc")
    pins = {"sets": {"abc": {"Alpha_Bench": {}, "Beta_Bench": {}, "Gamma_Bench": {}}}}
    est = estimate_gold(run, "abc", pins, {"sonnet": None, "mistral": 100_000})
    assert est["sonnet"]["calls"] == 3 and est["sonnet"]["packets_built"] == 2
    pf = tmp_path / "pins.json"
    pf.write_text(json.dumps({"seed": 1, "sets": {"abc": {"Alpha_Bench": {}, "Beta_Bench": {}}}}), encoding="utf-8")
    rc = cli_main(["gold", "--set", "abc", "--out", str(run), "--research-dir", str(rdir), "--pins", str(pf),
                   "--score", "--dry-run", "--coder", "sonnet"])
    out = capsys.readouterr().out
    assert rc == 0 and '"estimate_per_coder"' in out and '"status": "dry_run"' in out
    assert not (gold_run_dir(run, "abc") / "gold_scoring").exists()  # no calls, nothing written
