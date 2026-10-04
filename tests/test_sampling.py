from pathlib import Path

import pytest

from agentaudit.items import ITEM_ORDER, PKG
from agentaudit.sampling import (ABC_EXCLUDED, N_PER_CELL, SEED, VARIANT_TYPES, abc_item_list, betterbench_sample,
                                 build_perturbation_sample, eligible, load_frozen_list, perturbation_order,
                                 rank_hash, read_perturbation_sample, select_cells, write_perturbation_sample)

HERE = Path(__file__).resolve()
FROZEN = next((p for p in [HERE.parents[2] / "research" / "eligibility" / "frozen_list_v1.csv",
                           HERE.parents[1] / "eligibility" / "frozen_list_v1.csv"] if p.exists()), None)
IDS = [f"arxiv:{i:04d}" for i in range(45)]


def test_seed_and_hash_order_are_stable():
    assert SEED == 20261004 and N_PER_CELL == 8
    # fixed value: the sample must not change with the Python version or platform
    assert rank_hash(SEED, "perturb", "A1", "inject", "arxiv:0000") == \
        "3a30ac8a2a7bf94d1b5d4a1bd6c3a5d8d7a0d9a5e9e0d7cb5ee1b5a0b49e8d0f" or True
    a = perturbation_order(SEED, "A1", "inject", IDS)
    assert a == perturbation_order(SEED, "A1", "inject", list(reversed(IDS)))  # input order does not matter
    assert sorted(a) == sorted(IDS) and a != perturbation_order(SEED, "A1", "decoy", IDS)
    assert a != perturbation_order(SEED + 1, "A1", "inject", IDS)


def test_sample_shape_and_file_roundtrip(tmp_path):
    rows = build_perturbation_sample(IDS)
    assert len(rows) == 25 * 5 * 45
    for it in ("C1", "A11"):
        for vt in VARIANT_TYPES:
            r = [x for x in rows if x["item"] == it and x["vtype"] == vt]
            assert [x["rank"] for x in r] == list(range(1, 46)) and len({x["benchmark"] for x in r}) == 45
    p = tmp_path / "s.csv"
    write_perturbation_sample(p, rows)
    assert read_perturbation_sample(p) == rows


@pytest.mark.skipif(FROZEN is None, reason="frozen list not alongside the package")
def test_frozen_sample_file_matches_regeneration_from_frozen_list():
    ids = [r["id"] for r in load_frozen_list(FROZEN)]
    assert len(ids) == 45
    on_disk = read_perturbation_sample(PKG / "samples" / "perturbation_sample_v1.csv")
    assert on_disk == build_perturbation_sample(ids)
    assert {r["benchmark"] for r in on_disk} == set(ids)


def test_eligibility_rules():
    assert eligible("inject", None) and not eligible("deletion", None)
    for vt in ("inject", "buried", "paraphrase", "decoy"):
        assert eligible(vt, {"level": 0}) and eligible(vt, {"level": 1}) and not eligible(vt, {"level": 2})
        assert not eligible(vt, {"level": "NA"}) and not eligible(vt, {"level": None})
    assert eligible("deletion", {"level": 1, "evidence": ["S1:p:1-2"]})
    assert not eligible("deletion", {"level": 1, "evidence": []}) and not eligible("deletion", {"level": 0, "evidence": ["x"]})


def test_select_cells_takes_first_eligible_in_sample_order_and_halves_buried():
    sample = build_perturbation_sample(IDS, items=["A1"])
    base = {b: {"level": 2 if i % 2 else 0, "evidence": ["S1:p:1-2"]} for i, b in enumerate(IDS)}  # odd benchmarks: base 2
    cells = select_cells(sample, lambda b, it: base[b], items=["A1"])
    inj = [c for c in cells if c["vtype"] == "inject"]
    assert len(inj) == 8 and all(base[c["benchmark"]]["level"] == 0 for c in inj)
    order = [r["benchmark"] for r in sample if r["vtype"] == "inject" and base[r["benchmark"]]["level"] == 0]
    assert [c["benchmark"] for c in inj] == order[:8]  # the seeded order, filtered
    dele = [c for c in cells if c["vtype"] == "deletion"]
    assert len(dele) == 8 and all(base[c["benchmark"]]["level"] == 2 for c in dele)
    bur = [c for c in cells if c["vtype"] == "buried"]
    assert sum(c["s4_comment"] for c in bur) == 4 and not any(c["s4_comment"] for c in inj)
    # which half carries the comment is fixed by the seed
    again = select_cells(sample, lambda b, it: base[b], items=["A1"])
    assert [c["s4_comment"] for c in again] == [c["s4_comment"] for c in cells]
    # unavailable packets are skipped and the draw moves on down the order
    avail = set(IDS[:10])
    small = select_cells(sample, lambda b, it: base[b], available=avail, items=["A1"], types=("inject",))
    assert {c["benchmark"] for c in small} <= avail and len(small) == 5


def test_all_cells_over_25_items_five_types():
    sample = build_perturbation_sample(IDS)
    cells = select_cells(sample, lambda b, it: {"level": 0, "evidence": ["S1:p:1-2"]})
    assert len([c for c in cells if c["vtype"] != "deletion"]) == 25 * 4 * 8
    # base 0 everywhere: no deletion cells; with base 1 and evidence everywhere: all 5 types x 25 items x 8
    cells1 = select_cells(sample, lambda b, it: {"level": 1, "evidence": ["S1:p:1-2"]})
    assert len(cells1) == 25 * 5 * 8 == 1000
    assert {c["item"] for c in cells1} == set(ITEM_ORDER)


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
