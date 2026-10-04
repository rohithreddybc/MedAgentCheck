"""Perturbation under architecture v3: seeded cells, whole-packet single-item variants, mocked backends only."""
import json
import re
import shutil

import pytest

from agentaudit.backends import BackendAuthError, Response
from agentaudit.chunking import Source, wrap_long_lines
from agentaudit.items import ITEM_ORDER, load_items, load_perturbation_specs
from agentaudit.packet import load_sources, write_packet
from agentaudit.packet_score import score_packet
from agentaudit.perturb import (apply_variant, build_variants, cell_variant, estimate_cells, map_bench_dirs,
                                perturb_path, plan_packet_cells, run_perturb_packet, summarise, variant_packet)
from agentaudit.resolve import run_resolve
from agentaudit.sampling import build_perturbation_sample
from agentaudit.stats import wilson
from agentaudit.util import read_json

from conftest import make_sources
from test_packet_score import SPECS, PacketMock

FROZEN = [{"id": "arxiv:0001.00001", "benchmark_name": "Alpha"}, {"id": "arxiv:0002.00002", "benchmark_name": "Beta"},
          {"id": "arxiv:0003.00003", "benchmark_name": "Gamma"}]
A1_QUOTE = "Each task was run five times per model with independent seeds"


class PerturbMock:
    """Single-item mock: answers 2 with a verbatim quote when the item's inject or paraphrase text, or the base
    A1 sentence, is in the packet it was sent; otherwise 0. ``fabricate`` returns a quote that is not in the packet."""

    def __init__(self, model, fabricate=False, always=None):
        self.model, self.calls, self.fabricate, self.always = model, [], fabricate, always

    def complete(self, system, prompt, **kw):
        self.calls.append(prompt)
        ids = re.findall(r"^### Item (\w+):", prompt, re.M)
        assert len(ids) == 1, "single-item prompt expected"
        it = ids[0]
        pk = prompt.split("## Evidence packet", 1)[1].split("## Items to score", 1)[0]
        chunks = dict(re.findall(r"^### \[(S\d:[^\]]+)\] path=\S+\n(.*?)(?=\n\n### \[S\d:|\n\n## |\Z)", pk, re.S | re.M))
        spec = load_perturbation_specs()[it]
        cands = [spec["inject"].strip(), spec["paraphrase"].strip()] + ([A1_QUOTE] if it == "A1" else [])
        o = {"item": it, "score": 0, "elements": [False] * 3 if it.startswith("A") else [], "quotes": [],
             "contradicted": False, "contradiction_quotes": [], "s5_reach": None, "rationale": "searched: S1-S5"}
        if self.always is not None:  # a fixed score with a real verbatim quote from the first chunk
            cid0, t0 = next(iter(chunks.items()))
            o.update(score=self.always, quotes=[{"chunk_id": cid0, "text": t0[:80]}])
        for cid, t in chunks.items():
            hit = next((c for c in cands if c[:60] in t), None)
            if hit:
                q = hit[:110]
                if self.fabricate:
                    q = "completely different sentence that is nowhere in this packet at all"
                o.update(score=2, quotes=[{"chunk_id": cid, "text": q}])
                break
        return Response(json.dumps([o]), self.model, {"total_tokens": 5})


COD = {"sonnet": SPECS["sonnet"], "codex": SPECS["codex"], "gemini": SPECS["gemini"]}


@pytest.fixture(scope="module")
def base_run(tmp_path_factory):
    """Three packets named after frozen ids; base audit run with three families (A1 resolves to 2, rest 0)."""
    d = tmp_path_factory.mktemp("base")
    for r in FROZEN:
        write_packet(d, r["id"].replace(":", "_"), make_sources(), {"name": r["id"], "built_utc": "2026-01-01T00:00:00Z"})
        for c in COD:
            score_packet(d, r["id"].replace(":", "_"), c, COD[c], PacketMock(c), log=lambda *a: None)
    run_resolve(d, [r["id"].replace(":", "_") for r in FROZEN])
    return d


@pytest.fixture()
def run3(base_run, tmp_path):
    shutil.copytree(base_run, tmp_path / "run")
    return tmp_path / "run"


def sample_for(items):
    return build_perturbation_sample([r["id"] for r in FROZEN], items=items)


# ---- cell selection
def test_map_bench_dirs_and_cells_respect_base_eligibility(run3):
    assert map_bench_dirs(run3, FROZEN) == {r["id"]: r["id"].replace(":", "_") for r in FROZEN}
    cells = plan_packet_cells(run3, sample_for(["A1", "C1"]), FROZEN, ["A1", "C1"], n=8)
    by = {(c["item"], c["vtype"]): [] for c in cells}
    for c in cells:
        by[(c["item"], c["vtype"])].append(c)
    # A1 base is 2 in every benchmark: positives and decoy are uninformative and excluded; deletion has evidence
    assert [k for k in by if k[0] == "A1"] == [("A1", "deletion")]
    assert len(by[("A1", "deletion")]) == 3 and all(c["evidence"] for c in by[("A1", "deletion")])
    # C1 base is 0: all four non-deletion types, no deletion (nothing cited)
    assert {k[1] for k in by if k[0] == "C1"} == {"inject", "buried", "paraphrase", "decoy"}
    assert all(len(v) == 3 for k, v in by.items() if k[0] == "C1")  # only 3 benchmarks exist
    # buried: half (floor(3 / 2) = 1) carry the S4 comment
    assert sum(c["s4_comment"] for c in by[("C1", "buried")]) == 1
    # without base results: plain seeded draw, no deletion
    nb = plan_packet_cells(run3, sample_for(["A1"]), FROZEN, ["A1"], use_base=False)
    assert {c["vtype"] for c in nb} == {"inject", "buried", "paraphrase", "decoy"} and all(c["evidence"] == [] for c in nb)
    # n caps the draw
    assert len([c for c in plan_packet_cells(run3, sample_for(["C1"]), FROZEN, ["C1"], n=2) if c["vtype"] == "inject"]) == 2


def test_cell_without_base_results_is_not_eligible(tmp_path):
    write_packet(tmp_path, "arxiv_0001.00001", make_sources(), {"name": "x", "built_utc": "t"})
    assert plan_packet_cells(tmp_path, sample_for(["C1"]), FROZEN, ["C1"]) == []  # packet but no base audit
    assert plan_packet_cells(tmp_path, sample_for(["C1"]), FROZEN, ["C1"], use_base=False)  # plain draw works


# ---- buried: appendix block on S1 plus S4 code comment for half
def test_buried_s4_comment_variant_adds_synthetic_s4_source():
    src = make_sources()
    v = build_variants("A1", types=("buried",), s4_comment=True)[0]
    out = apply_variant(src, v)
    assert len(out) == len(src) + 1
    s4 = [s for s in out if s.path == "agent_eval/notes.py"][0]
    assert s4.surface == "S4" and s4.text.startswith("# " + v.text)
    s1 = next(s for s in out if s.surface == "S1").text
    assert s1.rstrip().endswith(v.text) and "Appendix Z" in s1  # appendix copy (label 2 rests on this)
    plain = apply_variant(src, build_variants("A1", types=("buried",))[0])
    assert len(plain) == len(src)
    # an existing synthetic path is not overwritten
    twice = apply_variant(out, v)
    assert len([s for s in twice if s.surface == "S4" and s.path.startswith("agent_eval/notes")]) == 2
    vp = variant_packet(src, v, 150000)
    assert vp["hit"] is True and vp["s4_hit"] is True
    assert "## S4" in vp["text"] and "agent_eval/notes.py" in vp["text"]


def test_variant_packet_keeps_cap_and_never_drops_s1():
    src = make_sources() + [Source("S4", "config/big.yaml", wrap_long_lines("\n".join(f"key{i}: value number {i}" * 3 for i in range(800))))]
    v = build_variants("A1", types=("inject",))[0]
    vp = variant_packet(src, v, 3000)
    assert vp["sel"]["dropped"] and all(d["id"].startswith("S4:") for d in vp["sel"]["dropped"])
    assert vp["hit"] is True


# ---- run: single-item whole-packet calls, three families
def test_run_perturb_packet_end_to_end(run3):
    items = ["A1", "C1"]
    cells = plan_packet_cells(run3, sample_for(items), FROZEN, items)
    mocks = {c: PerturbMock(c) for c in COD}
    mocks["gemini"] = PerturbMock("gemini", fabricate=True)  # quotes not in the packet: unsupported -> level 0
    s = run_perturb_packet(run3, cells, {c: (COD[c], mocks[c]) for c in COD})
    n_cells = len(cells)  # 3 deletion + 4 types x 3 benchmarks
    assert n_cells == 3 + 12 and s["done"] == 3 * n_cells and not s["failed"] and not s["blocked"]
    assert all(len(m.calls) == n_cells for m in mocks.values())  # one call per (cell, coder)
    # whole packet: S1 text far from the injection point is present in the prompt, and only the target item is asked
    assert "Filler paragraph 59" in mocks["sonnet"].calls[0] and "Item A1" in mocks["sonnet"].calls[0]
    rec = read_json(perturb_path(run3, "arxiv_0001.00001", "C1", "inject", "sonnet"))
    assert rec["status"] == "ok" and rec["mode"] == "packet_v3_single_item" and rec["variant_text_in_packet"] is True
    assert rec["verification"]["effective"] == 2 and rec["expected"] == 2 and rec["base_level"] == 0
    assert read_json(perturb_path(run3, "arxiv_0001.00001", "C1", "inject", "gemini"))["verification"]["effective"] == 0
    # deletion removes the cited chunk(s): the mock then finds nothing for A1
    d = read_json(perturb_path(run3, "arxiv_0001.00001", "A1", "deletion", "sonnet"))
    assert d["verification"]["effective"] == 0 and d["variant"]["removed_chunk_ids"] and d["base_level"] == 2
    # decoy on a base-0 item: the mock never answers above 0
    assert read_json(perturb_path(run3, "arxiv_0002.00002", "C1", "decoy", "codex"))["verification"]["effective"] == 0

    out = summarise(run3, [r["id"].replace(":", "_") for r in FROZEN])
    son, gem = out["by_coder"]["sonnet"], out["by_coder"]["gemini"]
    assert son["sensitivity"] == {"hits": 9, "n": 9, "rate": 1.0, "wilson95": list(wilson(9, 9))}
    assert son["specificity"]["hits"] == son["specificity"]["n"] == 6  # 3 deletion + 3 decoy
    assert gem["sensitivity"]["hits"] == 0 and gem["sensitivity"]["wilson95"][0] < 1e-9
    assert son["deletion_level_dropped"]["hits"] == 3  # level fell from base 2 to 0
    # resolved: sonnet and codex (two families) both reach 2, gemini's unsupported 0 is outvoted
    res = out["by_coder"]["RESOLVED"]
    assert res["sensitivity"]["hits"] == 9 and res["by_variant"]["buried"]["sensitivity"]["n"] == 3
    assert set(son["by_variant"]) == {"inject", "buried", "paraphrase", "deletion", "decoy"}
    assert set(son["by_item"]) == {"A1", "C1"} and "C1/inject" in son["by_item_variant"]
    assert (run3 / "perturb" / "summary.csv").exists()
    csv_head = (run3 / "perturb" / "summary.csv").read_text(encoding="utf-8").splitlines()[0]
    assert csv_head.startswith("scope,coder,item,vtype,metric,hits,n,rate,wilson_lo,wilson_hi")
    assert out["variant_text_in_packet"] == {"hits": 27, "n": 27}  # 9 cells x 3 coders, buried S1 copy included


def test_buried_s4_half_is_recorded_and_packet_contains_comment(run3):
    cells = plan_packet_cells(run3, sample_for(["C1"]), FROZEN, ["C1"], types=("buried",))
    mock = PerturbMock("m")
    run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], mock)})
    flags = [read_json(perturb_path(run3, c["bench"], "C1", "buried", "sonnet")) for c in cells]
    assert sorted(r["variant"]["s4_comment"] for r in flags) == [False, False, True]
    s4 = [r for r in flags if r["variant"]["s4_comment"]][0]
    assert s4["s4_comment_in_packet"] is True
    plain = [r for r in flags if not r["variant"]["s4_comment"]][0]
    assert plain["s4_comment_in_packet"] is None


def test_resume_dry_run_and_estimate(run3):
    cells = plan_packet_cells(run3, sample_for(["C1"]), FROZEN, ["C1"], types=("inject",))
    mock = PerturbMock("m")
    dry = run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], mock)}, dry_run=True)
    assert mock.calls == [] and dry["done"] == len(cells) and not (run3 / "perturb").exists()
    run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], mock)})
    n = len(mock.calls)
    again = run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], mock)})
    assert len(mock.calls) == n and again["skipped"] == len(cells)
    run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], mock)}, force=True)
    assert len(mock.calls) == 2 * n
    est = estimate_cells(run3, cells, {"sonnet": None, "mistral": 100000})
    tok = read_json(run3 / "packets" / "arxiv_0001.00001" / "manifest.json")["total_chunk_tokens"]
    assert est["sonnet"]["calls"] == len(cells) and est["sonnet"]["input_tokens_est"] == len(cells) * (tok + 2000)


def test_auth_error_blocks_and_parse_failure_is_recorded(run3):
    cells = plan_packet_cells(run3, sample_for(["C1"]), FROZEN, ["C1"], types=("inject",))

    class Bad:
        def complete(self, s, p, **kw):
            raise BackendAuthError("not logged in")

    s = run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], Bad())})
    assert s["blocked"] and "authentication" in s["blocked"]["reason"] and s["done"] == 0

    class Junk:
        def complete(self, s, p, **kw):
            return Response("not json", "m", {})

    s = run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], Junk())})
    assert len(s["failed"]) == len(cells)
    assert read_json(perturb_path(run3, cells[0]["bench"], "C1", "inject", "sonnet"))["status"] == "parse_error"
    assert summarise(run3, [c["bench"] for c in cells])["n_rows"] == 0  # failed cells never count


def test_cell_variant_labels():
    v = cell_variant({"item": "C1", "vtype": "decoy", "base_level": 1})
    assert v.expected == 1 and v.expectation == "at_most" and v.base_level == 1
    d = cell_variant({"item": "A1", "vtype": "deletion", "base_level": 2, "evidence": ["S1:p:1-3"]})
    assert d.expected == 0 and d.removed_chunk_ids == ["S1:p:1-3"] and d.base_level == 2
    b = cell_variant({"item": "A1", "vtype": "buried", "s4_comment": True})
    assert b.expected == 2 and b.s4_comment is True


def test_summary_counts_decoy_rise_as_specificity_miss(run3):
    cells = plan_packet_cells(run3, sample_for(["C1"]), FROZEN, ["C1"], types=("decoy",))
    run_perturb_packet(run3, cells, {"sonnet": (COD["sonnet"], PerturbMock("m", always=1))})
    out = summarise(run3, [c["bench"] for c in cells])
    assert out["by_coder"]["sonnet"]["specificity"] == {"hits": 0, "n": 3, "rate": 0.0, "wilson95": list(wilson(0, 3))}
