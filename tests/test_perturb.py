import pytest

from agentaudit.chunking import Source, build_chunks, is_s5
from agentaudit.items import ITEM_ORDER, load_perturbation_specs
from agentaudit.perturb import VARIANT_TYPES, apply_variant, build_variants, variant_text_retrieved
from agentaudit.retrieve import retrieve_chunks

from conftest import make_sources


def test_specs_cover_all_items():
    specs = load_perturbation_specs()
    assert set(specs) == set(ITEM_ORDER)
    for s in specs.values():
        assert s["inject"].strip() and s["paraphrase"].strip() and s["decoy"].strip()
        assert s["inject"].strip() != s["paraphrase"].strip()


def test_label_construction():
    vs = {v.vtype: v for v in build_variants("A1", base_level=1, evidence_ids=["S1:p:3-9", "S1:p:3-9", "S2:r:1-4"])}
    assert set(vs) == set(VARIANT_TYPES)
    for t in ("inject", "buried", "paraphrase"):
        assert vs[t].expected == 2 and vs[t].expectation == "exact"
    assert vs["inject"].text == vs["buried"].text != vs["paraphrase"].text
    assert vs["decoy"].expected == 1 and vs["decoy"].expectation == "at_most"
    assert vs["deletion"].expected == 0 and vs["deletion"].removed_chunk_ids == ["S1:p:3-9", "S2:r:1-4"]


def test_deletion_variant_needs_evidence_and_decoy_defaults_to_zero():
    vs = {v.vtype: v for v in build_variants("C6")}
    assert "deletion" not in vs and vs["decoy"].expected == 0
    with pytest.raises(ValueError):
        build_variants("C6", types=("nonsense",))


def test_apply_inject_buried_and_not_mutating_input():
    src = make_sources()
    before = [s.text for s in src]
    v = {x.vtype: x for x in build_variants("A1")}
    inj = apply_variant(src, v["inject"])
    bur = apply_variant(src, v["buried"])
    assert [s.text for s in src] == before
    s1_inj = next(s for s in inj if s.surface == "S1").text
    s1_bur = next(s for s in bur if s.surface == "S1").text
    assert v["inject"].text in s1_inj and v["inject"].text in s1_bur
    assert s1_bur.rstrip().endswith(v["inject"].text)  # late appendix block
    assert s1_inj.split("\n").index(v["inject"].text) == len(before[0].split("\n")) // 2
    assert next(s for s in inj if s.surface == "S4").text == before[2]  # S4 untouched


def test_apply_deletion_removes_cited_lines():
    src = make_sources()
    chunks = build_chunks(src, is_s5)
    target = next(c for c in chunks if "five times" in c.text)
    v = build_variants("A1", evidence_ids=[target.id], types=("deletion",))[0]
    out = apply_variant(src, v)
    new_text = next(s for s in out if s.surface == "S1").text
    assert "five times" not in new_text
    assert len(new_text.split("\n")) == len(src[0].text.split("\n")) - (target.end - target.start + 1)


def test_injected_text_is_retrieved_for_its_item():
    src = make_sources()
    v = build_variants("A1", types=("inject",))[0]
    chunks = build_chunks(apply_variant(src, v), is_s5)
    rec = retrieve_chunks(chunks, "A1")
    texts = {c.id: c.text for c in chunks if c.id in {e["id"] for e in rec["chunks"]}}
    assert variant_text_retrieved(v, texts) is True
