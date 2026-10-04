from pathlib import Path

import pytest

from agentaudit.items import ITEM_ORDER, PKG
from agentaudit.sampling import (ABC_EXCLUDED, N_PER_PAIR, N_VARIANTS, SEED, VARIANT_TYPES, abc_item_list,
                                 betterbench_sample, build_perturbation_design, draw_variant_benchmarks, eligible,
                                 load_frozen_list, rank_hash, read_perturbation_design, write_perturbation_design)

HERE = Path(__file__).resolve()
FROZEN = next((p for p in [HERE.parents[2] / "research" / "eligibility" / "frozen_list_v1.csv",
                           HERE.parents[1] / "eligibility" / "frozen_list_v1.csv"] if p.exists()), None)
IDS = [f"arxiv:{i:04d}" for i in range(45)]


def test_seed_and_hash_are_stable():
    assert SEED == 20261004 and N_VARIANTS == 40 and N_PER_PAIR == 8
    # fixed value: the design must not change with the Python version or platform
    assert rank_hash(SEED, "perturb", "A1", "inject", "arxiv:0000") ==         "4a939b49305156bdd0f26dfef9083bc71de1b3ae5859d3d637273dbcf45e4c4b"
    a = draw_variant_benchmarks(IDS)
    assert a == draw_variant_benchmarks(list(reversed(IDS))) and len(set(a)) == 40  # no replacement with 45 available
    assert a != draw_variant_benchmarks(IDS, seed=SEED + 1)
    few = draw_variant_benchmarks(IDS[:3])  # replacement only when fewer benchmarks than variants
    assert len(few) == 40 and set(few) == set(IDS[:3])


def test_design_is_balanced_one_type_per_item_per_variant(tmp_path):
    rows = build_perturbation_design(IDS)
    assert len(rows) == 25 * 40 == 1000
    from collections import Counter

    pair = Counter((r["item"], r["vtype"]) for r in rows)
    assert len(pair) == 25 * 5 and set(pair.values()) == {8}  # every item x type pair exactly 8 times
    per_variant = Counter((r["variant"], r["item"]) for r in rows)
    assert set(per_variant.values()) == {1} and len({r["variant"] for r in rows}) == 40  # one type per item per variant
    assert len({r["benchmark"] for r in rows}) == 40 and {r["benchmark"] for r in rows} <= set(IDS)
    for v in ("v01", "v40"):
        assert sorted(r["slot"] for r in rows if r["variant"] == v) == list(range(25))  # distinct S1 positions
        assert len({r["benchmark"] for r in rows if r["variant"] == v}) == 1
    for it in ("A1", "C13"):  # half of each item's 8 decoys are S4-comment decoys (full level-2 text, S4 only)
        bur = [r for r in rows if r["item"] == it and r["vtype"] == "decoy"]
        assert len(bur) == 8 and sum(r["s4_comment"] == "yes" for r in bur) == 4
    assert all(r["s4_comment"] == "no" for r in rows if r["vtype"] != "decoy")
    assert rows == build_perturbation_design(IDS) != build_perturbation_design(IDS, seed=1)
    p = tmp_path / "d.csv"
    write_perturbation_design(p, rows)
    back = read_perturbation_design(p)
    assert [(r["variant"], r["item"], r["vtype"], r["slot"]) for r in back] == [(r["variant"], r["item"], r["vtype"], r["slot"]) for r in rows]
    assert back[0]["s4_comment"] in (True, False)
    with pytest.raises(ValueError):
        build_perturbation_design(IDS, n_variants=42)


@pytest.mark.skipif(FROZEN is None, reason="frozen list not alongside the package")
def test_frozen_design_file_matches_regeneration_from_frozen_list():
    ids = [r["id"] for r in load_frozen_list(FROZEN)]
    assert len(ids) == 45
    on_disk = read_perturbation_design(PKG / "samples" / "perturbation_design_v1.csv")
    regen = read_perturbation_design  # noqa: F841
    fresh = build_perturbation_design(ids)
    assert [(r["variant"], r["benchmark"], r["item"], r["vtype"], r["slot"], r["s4_comment"] == "yes") for r in fresh] ==         [(r["variant"], r["benchmark"], r["item"], r["vtype"], r["slot"], r["s4_comment"]) for r in on_disk]
    assert {r["benchmark"] for r in on_disk} <= set(ids) and len({r["benchmark"] for r in on_disk}) == 40


def test_eligibility_rules():
    assert eligible("inject", None) and not eligible("deletion", None)
    for vt in ("inject", "buried", "paraphrase", "decoy"):
        assert eligible(vt, {"level": 0}) and eligible(vt, {"level": 1}) and not eligible(vt, {"level": 2})
        assert not eligible(vt, {"level": "NA"}) and not eligible(vt, {"level": None})
    assert eligible("deletion", {"level": 1, "evidence": ["S1:p:1-2"]})
    assert not eligible("deletion", {"level": 1, "evidence": []}) and not eligible("deletion", {"level": 0, "evidence": ["x"]})


def test_betterbench_sample_and_abc_list():
    crit = [f"J.{s}-{n}" for s, k in ((1, 14), (2, 10), (3, 19), (4, 3)) for n in range(1, k + 1)]
    assert len(crit) == 46
    pick = betterbench_sample(crit)
    assert len(pick) == 20 and len(set(pick)) == 20 and pick == [c for c in crit if c in pick]
    assert betterbench_sample(crit) == pick and betterbench_sample(crit, seed=1) != pick
    abc = abc_item_list(["T.1", "T.10", "O.a.1", "O.g.2", "R.3", "O.c.2 [App. D only]"], {"O.a.1": 5, "O.g.2": 4})
    got = {r["item_id"]: r["included"] for r in abc}
    assert got == {"T.1": "yes", "T.10": "no", "O.a.1": "yes", "O.g.2": "no", "R.3": "yes", "O.c.2": "no"}
    assert "T.10" in ABC_EXCLUDED


def test_shipped_gold_lists_follow_the_rules():
    from agentaudit.gold import ABC_ITEMS_PATH, BB_CRITERIA_PATH
    from agentaudit.sampling import read_rows

    abc = read_rows(ABC_ITEMS_PATH)
    inc = [r["item_id"] for r in abc if r["included"] == "yes"]
    assert inc == [f"T.{i}" for i in range(1, 10)] + [f"R.{i}" for i in range(1, 14)]  # T.10 out; no O.* has 5 benchmarks
    bb = read_rows(BB_CRITERIA_PATH)
    assert len(bb) == 46 and sum(r["selected"] == "yes" for r in bb) == 20
    assert [r["criterion_id"] for r in bb if r["selected"] == "yes"] == \
        betterbench_sample([r["criterion_id"] for r in bb])
    text = Path(ABC_ITEMS_PATH).read_text(encoding="utf-8") + Path(BB_CRITERIA_PATH).read_text(encoding="utf-8")
    assert "score" not in text.lower().split("\n")[0]  # ids and reasons only, no gold values
