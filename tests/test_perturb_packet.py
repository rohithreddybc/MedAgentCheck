"""Perturbation under architecture v3, multiplexed: 40 variant packets, every item perturbed once per variant,
one whole-packet 25-item call per variant and coder. Mocked backends only."""
import json
import re
import shutil
from collections import Counter

import pytest

from agentaudit.backends import BackendAuthError, Response
from agentaudit.chunking import Source
from agentaudit.items import ITEM_ORDER, load_perturbation_specs
from agentaudit.packet import write_packet
from agentaudit.packet_score import score_packet
from agentaudit.perturb import (apply_variants, build_variants, cell_variant, estimate_variants, map_bench_dirs,
                                perturb_variant_path, plan_variants, run_perturb_variants, summarise, variant_packet)
from agentaudit.resolve import run_resolve
from agentaudit.sampling import build_perturbation_design
from agentaudit.stats import wilson
from agentaudit.util import read_json

from conftest import make_sources
from test_packet_score import SPECS, PacketMock

FROZEN = [{"id": "arxiv:0001.00001", "benchmark_name": "Alpha"}, {"id": "arxiv:0002.00002", "benchmark_name": "Beta"},
          {"id": "arxiv:0003.00003", "benchmark_name": "Gamma"}]
DIRS = [r["id"].replace(":", "_") for r in FROZEN]
A1_QUOTE = "Each task was run five times per model with independent seeds"
SPECS_Y = load_perturbation_specs()
COD = {"sonnet": SPECS["sonnet"], "codex": SPECS["codex"], "gemini": SPECS["gemini"]}


class PerturbMock:
    """Answers all 25 items of the prompt: 2 with a verbatim quote when the item's inject or paraphrase text (or the
    base A1 sentence) is in the packet it was sent, otherwise 0. ``fabricate``: quotes that are not in the packet.
    ``always``: a fixed score with a real quote."""

    def __init__(self, model, fabricate=False, always=None):
        self.model, self.calls, self.fabricate, self.always = model, [], fabricate, always

    def complete(self, system, prompt, **kw):
        self.calls.append(prompt)
        ids = re.findall(r"^### Item (\w+):", prompt, re.M)
        pk = prompt.split("## Evidence packet", 1)[1].split("## Items to score", 1)[0]
        chunks = dict(re.findall(r"^### \[(S\d:[^\]]+)\] path=\S+\n(.*?)(?=\n\n### \[S\d:|\n\n## |\Z)", pk, re.S | re.M))
        out = []
        for it in ids:
            cands = [SPECS_Y[it]["inject"].strip(), SPECS_Y[it]["paraphrase"].strip()] + ([A1_QUOTE] if it == "A1" else [])
            o = {"item": it, "score": 0, "elements": [False] * 3 if it.startswith("A") else [], "quotes": [],
                 "contradicted": False, "contradiction_quotes": [], "s5_reach": None, "rationale": "searched: S1-S5"}
            if self.always is not None:
                cid0, t0 = next(iter(chunks.items()))
                o.update(score=self.always, quotes=[{"chunk_id": cid0, "text": t0[:80]}])
            for cid, t in chunks.items():
                hit = next((c for c in cands if c[:60] in t), None)
                if hit:
                    q = "completely different sentence that is nowhere in this packet at all" if self.fabricate else hit[:110]
                    o.update(score=2, quotes=[{"chunk_id": cid, "text": q}])
                    break
            out.append(o)
        return Response(json.dumps(out), self.model, {"total_tokens": 5})


@pytest.fixture(scope="module")
def base_run(tmp_path_factory):
    """Three packets named after frozen ids; base audit with three families (A1 resolves to 2, every other item 0)."""
    d = tmp_path_factory.mktemp("base")
    for b, r in zip(DIRS, FROZEN):
        write_packet(d, b, make_sources(), {"name": r["id"], "built_utc": "2026-01-01T00:00:00Z"})
        for c in COD:
            score_packet(d, b, c, COD[c], PacketMock(c), log=lambda *a: None)
    run_resolve(d, DIRS)
    return d


@pytest.fixture()
def run3(base_run, tmp_path):
    shutil.copytree(base_run, tmp_path / "run")
    return tmp_path / "run"


DESIGN = build_perturbation_design([r["id"] for r in FROZEN])  # 3 benchmarks: replacement over 40 variants
FEW = ["v01", "v02", "v03", "v04", "v05", "v06"]


# ---- plan: eligibility drops cells, never replaces them
def test_plan_drops_ineligible_cells_and_counts_them(run3):
    assert map_bench_dirs(run3, FROZEN) == {r["id"]: d for r, d in zip(FROZEN, DIRS)}
    plan = plan_variants(run3, DESIGN, FROZEN)
    assert len(plan["variants"]) == 40 and not plan["skipped_variants"]
    # A1 has base 2 everywhere: only its 8 deletion cells survive. Every other item has base 0: no deletion, rest survive
    a1 = [c for v in plan["variants"] for c in v["cells"] if c["item"] == "A1"]
    assert Counter(c["vtype"] for c in a1) == {"deletion": 8} and all(c["evidence"] for c in a1)
    assert plan["n_cells"] == 8 + 24 * 32 and plan["n_dropped"] == 1000 - plan["n_cells"] == 224
    assert Counter(d["reason"] for d in plan["dropped"]) == {"base level 2 (label would pass trivially)": 32,
                                                          "base level 0": 192}
    assert all(not any(c["vtype"] == "deletion" for c in v["cells"] if c["item"] != "A1") for v in plan["variants"])
    # dropped cells are not replaced: the cells kept are a subset of the design
    design_keys = {(r["variant"], r["item"], r["vtype"]) for r in DESIGN}
    assert {(v["variant"], c["item"], c["vtype"]) for v in plan["variants"] for c in v["cells"]} <= design_keys
    # without base results: plain draw, deletion cells dropped
    nb = plan_variants(run3, DESIGN, FROZEN, use_base=False)
    assert nb["n_cells"] == 1000 - 200 and all(d["vtype"] == "deletion" for d in nb["dropped"])
    # a benchmark without a packet skips its variants
    part = plan_variants(run3, [r for r in DESIGN], [FROZEN[0]])
    assert part["skipped_variants"] and all(v["benchmark"] == FROZEN[0]["id"] for v in part["variants"])
    assert len(part["variants"]) + len(part["skipped_variants"]) == 40
    assert [v["variant"] for v in plan_variants(run3, DESIGN, FROZEN, only_variants=["v02"])["variants"]] == ["v02"]


def test_variant_without_base_results_is_dropped_entirely(tmp_path):
    write_packet(tmp_path, DIRS[0], make_sources(), {"name": "x", "built_utc": "t"})
    plan = plan_variants(tmp_path, DESIGN, [FROZEN[0]])  # packet exists, no base audit
    assert plan["variants"] and plan["n_cells"] == 0 and plan["n_dropped"] == 25 * len(plan["variants"])


# ---- applying a variant: spread positions, one appendix, S4 comments for half
def cells_for(types_by_item, s4=()):
    out = []
    for slot, (it, vt) in enumerate(types_by_item):
        v = build_variants(it, base_level=2 if vt == "deletion" else 0, evidence_ids=["S1:arxiv/0000.00000v1.html:5-6"] if vt == "deletion" else None,
                           types=(vt,), s4_comment=it in s4)[0]
        out.append((v, slot * 6))
    return out


def test_apply_variants_spreads_inline_texts_and_builds_one_appendix_and_s4_file():
    src = make_sources()
    before = [s.text for s in src]
    cs = cells_for([("C1", "inject"), ("C2", "paraphrase"), ("C3", "decoy"), ("C4", "buried"), ("C5", "buried"), ("C6", "buried")],
                   s4=("C5",))
    out = apply_variants(src, cs)
    assert [s.text for s in src] == before  # input untouched
    s1 = next(s for s in out if s.surface == "S1").text
    lines = s1.split("\n")
    pos = [lines.index(v.text) for v, _ in cs[:3]]
    assert pos == sorted(pos) and len(set(pos)) == 3 and pos[0] < pos[1] < pos[2]  # different locations, in slot order
    appendix = s1.split("Appendix Z. Additional notes\n", 1)[1]
    assert appendix == "\n".join(v.text for v, _ in cs[3:])  # one late appendix block, items in order
    s4 = [s for s in out if s.path == "agent_eval/notes.py"]
    assert len(s4) == 1 and s4[0].surface == "S4" and s4[0].text == "# " + cs[4][0].text + "\n"  # only the flagged one
    assert len(out) == len(src) + 1
    none_s4 = apply_variants(src, cells_for([("C4", "buried")]))
    assert len(none_s4) == len(src)


def test_deletion_runs_before_inline_insertion_and_removes_cited_lines():
    from agentaudit.chunking import build_chunks, is_s5

    src = make_sources()
    chunks = build_chunks(src, is_s5)
    target = next(c for c in chunks if "five times" in c.text)
    d = build_variants("A1", base_level=2, evidence_ids=[target.id], types=("deletion",))[0]
    inj = build_variants("C1", types=("inject",))[0]
    out = apply_variants(src, [(d, 3), (inj, 12)])
    s1 = next(s for s in out if s.surface == "S1").text
    assert "five times" not in s1 and inj.text in s1
    assert len(s1.split("\n")) == len(src[0].text.split("\n")) - (target.end - target.start + 1) + 1


def test_variant_packet_hits_s4_flag_and_cap():
    src = make_sources()
    cs = cells_for([("C1", "inject"), ("C4", "buried"), ("C5", "buried"), ("C3", "decoy")], s4=("C5",))
    vp = variant_packet(src, cs, 150000)
    assert vp["hits"] == {"C1": True, "C4": True, "C5": True, "C3": True} and vp["s4_hits"] == {"C5": True}
    assert "agent_eval/notes.py" in vp["text"]
    big = src + [Source("S4", "config/big.yaml", "\n".join(f"key{i}: value number {i} and more words" for i in range(900)))]
    capped = variant_packet(big, cs, 3000)
    assert capped["sel"]["dropped"] and all(d["id"].startswith("S4:") for d in capped["sel"]["dropped"])
    assert capped["hits"]["C1"] is True  # S1 is never dropped


# ---- run: one 25-item call per variant and coder
def test_run_end_to_end_three_families(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=FEW)
    mocks = {c: PerturbMock(c) for c in COD}
    mocks["gemini"] = PerturbMock("gemini", fabricate=True)  # quotes not in the packet: unsupported -> level 0
    s = run_perturb_variants(run3, plan, {c: (COD[c], mocks[c]) for c in COD}, log=lambda *a: None)
    assert s["done"] == 6 * 3 and not s["failed"] and not s["blocked"] and s["cells"] == plan["n_cells"]
    assert all(len(m.calls) == 6 for m in mocks.values())  # one call per variant, not per cell
    first = mocks["sonnet"].calls[0]
    assert all(f"### Item {i}:" in first for i in ITEM_ORDER)  # the normal 25-item prompt
    assert "Filler paragraph 59" in first  # whole packet
    rec = read_json(perturb_variant_path(run3, "v01", "sonnet"))
    assert rec["status"] == "ok" and rec["mode"] == "packet_v3_multiplexed" and set(rec["items"]) == set(ITEM_ORDER)
    pv = plan["variants"][0]
    assert set(rec["cells"]) == {c["item"] for c in pv["cells"]}  # perturbed items; the others are scored but not labelled
    assert all(c["variant_text_in_packet"] is True for c in rec["cells"].values() if c["variant"]["text"])
    n_cells = plan["n_cells"]
    out = summarise(run3, FEW)
    son, gem = out["by_coder"]["sonnet"], out["by_coder"]["gemini"]
    sens_n = sum(1 for v in plan["variants"] for c in v["cells"] if c["vtype"] in ("inject", "buried", "paraphrase"))
    assert son["sensitivity"] == {"hits": sens_n, "n": sens_n, "rate": 1.0, "wilson95": list(wilson(sens_n, sens_n))}
    spec_n = n_cells - sens_n
    assert son["specificity"]["n"] == spec_n and son["specificity"]["hits"] == spec_n
    assert gem["sensitivity"]["hits"] == 0 and gem["sensitivity"]["wilson95"][0] < 1e-9
    res = out["by_coder"]["RESOLVED"]  # sonnet and codex (two families) reach 2; gemini's unsupported 0 is outvoted
    assert res["sensitivity"]["hits"] == sens_n
    assert set(son["by_variant"]) <= {"inject", "buried", "paraphrase", "deletion", "decoy"} and "C1" in son["by_item"]
    assert out["design"]["cells_scored_planned"] == n_cells and out["design"]["cells_dropped"] == plan["n_dropped"]
    assert sum(out["design"]["dropped_by_type"].values()) == plan["n_dropped"]
    csv_head = (run3 / "perturb" / "summary.csv").read_text(encoding="utf-8").splitlines()[0]
    assert csv_head.startswith("scope,coder,item,vtype,metric,hits,n,rate,wilson_lo,wilson_hi")
    # deletion cells: A1 level falls from base 2 to 0
    dele = [(v, c) for v in plan["variants"] for c in v["cells"] if c["vtype"] == "deletion"]
    for v, c in dele:
        r = read_json(perturb_variant_path(run3, v["variant"], "sonnet"))
        assert r["items"]["A1"]["verification"]["effective"] == 0 and r["cells"]["A1"]["base_level"] == 2
    if dele:
        assert son["deletion_level_dropped"]["hits"] == len(dele)


def test_buried_s4_half_recorded_in_run(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=["v%02d" % i for i in range(1, 41)])
    run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], PerturbMock("m"))}, log=lambda *a: None)
    flagged = {(r["variant"], r["item"]): r["s4_comment"] for r in DESIGN if r["vtype"] == "buried" and r["item"] != "A1"}  # A1: base 2, dropped
    seen = {}
    for v in plan["variants"]:
        rec = read_json(perturb_variant_path(run3, v["variant"], "sonnet"))
        for it, c in rec["cells"].items():
            if c["variant"]["vtype"] == "buried":
                seen[(v["variant"], it)] = c["s4_comment_in_packet"]
    assert len(seen) == len(flagged) and all(seen[k] is True for k, f in flagged.items() if f == "yes")
    assert all(seen[k] is None for k, f in flagged.items() if f == "no")


def test_resume_dry_run_and_estimate(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=["v01", "v02"])
    mock = PerturbMock("m")
    dry = run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], mock)}, dry_run=True)
    assert mock.calls == [] and dry["done"] == 2 and not (run3 / "perturb").exists()
    run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], mock)}, log=lambda *a: None)
    assert len(mock.calls) == 2
    again = run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], mock)})
    assert len(mock.calls) == 2 and again["skipped"] == 2
    run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], mock)}, force=True, log=lambda *a: None)
    assert len(mock.calls) == 4
    coders = {"sonnet": dict(COD["sonnet"]), "mistral": dict(COD["sonnet"], max_packet_tokens=100000), "g3": dict(COD["sonnet"], groups=3)}
    est = estimate_variants(run3, plan, coders, ["sonnet", "mistral", "g3"])
    tok = read_json(run3 / "packets" / DIRS[0] / "manifest.json")["total_chunk_tokens"]
    assert est["sonnet"]["calls"] == 2 and est["g3"]["calls"] == 6
    assert est["sonnet"]["input_tokens_est"] > 2 * tok and est["g3"]["input_tokens_est"] > est["sonnet"]["input_tokens_est"]


def test_item_groups_give_one_call_per_group(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=["v01"])
    mock = PerturbMock("m")
    run_perturb_variants(run3, plan, {"sonnet": (dict(COD["sonnet"], groups=3), mock)}, log=lambda *a: None)
    assert len(mock.calls) == 3
    rec = read_json(perturb_variant_path(run3, "v01", "sonnet"))
    assert rec["status"] == "ok" and set(rec["items"]) == set(ITEM_ORDER)


def test_auth_error_blocks_and_parse_failure_is_recorded(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=["v01", "v02"])

    class Bad:
        def complete(self, s, p, **kw):
            raise BackendAuthError("not logged in")

    s = run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], Bad())})
    assert s["blocked"] and "authentication" in s["blocked"]["reason"] and s["done"] == 0

    class Junk:
        def complete(self, s, p, **kw):
            return Response("not json", "m", {})

    s = run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], Junk())}, log=lambda *a: None)
    assert len(s["failed"]) == 2 and read_json(perturb_variant_path(run3, "v01", "sonnet"))["status"] == "parse_error"
    assert summarise(run3, ["v01", "v02"])["n_rows"] == 0  # failed variants never count


def test_partial_response_counts_only_answered_cells(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=["v01"])

    class Short(PerturbMock):
        def complete(self, system, prompt, **kw):
            r = super().complete(system, prompt)
            return Response(json.dumps(json.loads(r.text)[:20]), r.model_id, {})

    s = run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], Short("m"))}, log=lambda *a: None)
    rec = read_json(perturb_variant_path(run3, "v01", "sonnet"))
    assert rec["status"] == "partial" and len(rec["items"]) == 20 and s["failed"]
    answered = {it for it in rec["cells"] if it in rec["items"]}
    assert summarise(run3, ["v01"])["n_rows"] == len(answered)


def test_cell_variant_labels():
    v = cell_variant({"item": "C1", "vtype": "decoy", "base_level": 1})
    assert v.expected == 1 and v.expectation == "at_most" and v.base_level == 1
    d = cell_variant({"item": "A1", "vtype": "deletion", "base_level": 2, "evidence": ["S1:p:1-3"]})
    assert d.expected == 0 and d.removed_chunk_ids == ["S1:p:1-3"] and d.base_level == 2
    b = cell_variant({"item": "A1", "vtype": "buried", "s4_comment": True})
    assert b.expected == 2 and b.s4_comment is True


def test_summary_counts_decoy_rise_as_specificity_miss(run3):
    plan = plan_variants(run3, DESIGN, FROZEN, only_variants=FEW)
    run_perturb_variants(run3, plan, {"sonnet": (COD["sonnet"], PerturbMock("m", always=1))}, log=lambda *a: None)
    out = summarise(run3, FEW)
    decoy = out["by_coder"]["sonnet"]["by_variant"]["decoy"]["specificity"]
    assert decoy["n"] > 0 and decoy["hits"] == 0  # level 1 > base 0 on every decoy cell
