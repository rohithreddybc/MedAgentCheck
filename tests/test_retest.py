"""Coder test-retest (agentaudit retest): seeded draw, copy of the packet, second scores in <run>/retest/,
intra-coder agreement. Mocked backends only."""
import json

import pytest

from agentaudit import cli
from agentaudit.chunking import Source
from agentaudit.packet import write_packet
from agentaudit.packet_score import score_packet
from agentaudit.resolve import run_resolve
from agentaudit.retest import compare_retest, plan_retest, retest_dir, run_retest
from agentaudit.sampling import RETEST_N, SEED, draw_retest_benchmarks, rank_hash
from agentaudit.util import read_json

from conftest import make_sources
from test_packet_score import SPECS, PacketMock

FROZEN = [{"id": f"arxiv:000{i}.0000{i}", "benchmark_name": f"Bench{i}"} for i in range(1, 4)]
DIRS = [r["id"].replace(":", "_") for r in FROZEN]
CODERS = ["sonnet", "codex", "gemini"]
MODEL_OF = {"anthropic": "sonnet", "openai": "codex", "google": "gemini"}


def test_draw_is_seeded_pure_and_ten_of_forty_five():
    ids = [f"arxiv:{i:04d}.{i:05d}" for i in range(45)]
    d1 = draw_retest_benchmarks(ids)
    assert len(d1) == RETEST_N == 10 and len(set(d1)) == 10 and set(d1) <= set(ids)
    assert draw_retest_benchmarks(list(reversed(ids))) == d1  # independent of input order
    assert draw_retest_benchmarks(ids, 10, SEED) == d1
    assert draw_retest_benchmarks(ids, 10, SEED + 1) != d1
    assert d1 == sorted(ids, key=lambda b: rank_hash(20261004, "retest", b))[:10]  # the documented rule
    with pytest.raises(ValueError):
        draw_retest_benchmarks(ids[:5])


@pytest.fixture()
def audit_run(tmp_path):
    for d in DIRS:
        write_packet(tmp_path, d, make_sources(), {"name": d, "built_utc": "2026-01-01T00:00:00Z"})
        for c in CODERS:
            score_packet(tmp_path, d, c, SPECS[c], PacketMock(f"model-{c}"))
    run_resolve(tmp_path, DIRS)
    return tmp_path


def backend_factory(scores):
    """spec -> mock whose A1 score is scores[family]."""
    return lambda spec: PacketMock(f"model-{MODEL_OF[spec['family']]}", score_a1=scores[spec["family"]])


def test_plan_maps_drawn_to_packet_dirs(audit_run):
    p = plan_retest(audit_run, FROZEN, n=2)
    assert len(p["drawn"]) == 2 and all(d["packet_dir"] in DIRS for d in p["drawn"])
    assert p["seed"] == 20261004 and p["frozen_benchmarks"] == 3


def test_retest_identical_scores_give_perfect_agreement(audit_run):
    mk = backend_factory({"anthropic": 2, "openai": 2, "google": 2})
    out = run_retest(audit_run, FROZEN, CODERS, SPECS, mk, n=3)
    assert len(out["scored"]) == 9 and not out["failed"] and not out["blocked"]
    assert all(s["same_rendered_packet"] for s in out["scored"])
    # the audit run was not touched: the retest lives in its own directory
    assert (retest_dir(audit_run) / "scoring" / DIRS[0] / "sonnet" / "results.json").exists()
    assert (retest_dir(audit_run) / "packets" / DIRS[0] / "chunks.jsonl").exists()
    run_resolve(retest_dir(audit_run), DIRS)
    res = compare_retest(audit_run, FROZEN, n=3, n_boot=50)
    assert set(res["coders"]) == set(CODERS)
    for c, st in res["coders"].items():
        assert st["n_cells"] == 3 * 25 and st["n_benchmarks"] == 3
        assert st["raw_agreement"] == 1.0 and st["alpha_ordinal"] == pytest.approx(1.0)
        assert st["same_model_id"] is True
    assert res["resolved"]["raw_agreement"] == 1.0
    assert (retest_dir(audit_run) / "retest_agreement.json").exists()


def test_retest_flip_lowers_that_coders_agreement_only(audit_run):
    mk = backend_factory({"anthropic": 2, "openai": 1, "google": 2})  # codex now scores A1 at 1 instead of 2
    run_retest(audit_run, FROZEN, CODERS, SPECS, mk, n=3)
    res = compare_retest(audit_run, FROZEN, n=3, n_boot=50)
    cx, sn = res["coders"]["codex"], res["coders"]["sonnet"]
    assert sn["raw_agreement"] == 1.0
    assert cx["n_exact"] == 3 * 24 and cx["raw_agreement"] == pytest.approx(72 / 75)
    assert cx["per_item_agreement"]["A1"] == {"n": 3, "agree": 0}
    assert cx["alpha_ordinal"] < 1.0
    assert cx["reported_split_agreement"] == 1.0  # 1 and 2 are both REPORTED


def test_retest_skips_without_original_results_and_resumes(audit_run):
    import shutil

    shutil.rmtree(audit_run / "scoring" / DIRS[0] / "gemini")
    mk = backend_factory({"anthropic": 2, "openai": 2, "google": 2})
    out = run_retest(audit_run, FROZEN, CODERS, SPECS, mk, n=3)
    assert {"bench": DIRS[0], "coder": "gemini", "reason": "no original results"} in out["skipped"]
    assert len(out["scored"]) == 8
    calls = []

    def counting(spec):
        m = PacketMock("x")
        calls.append(m)
        return m

    run_retest(audit_run, FROZEN, CODERS, SPECS, counting, n=3)  # resume: group files already ok
    assert all(not m.calls for m in calls)


def test_dry_run_makes_no_calls_and_no_copy(audit_run):
    def boom(spec):
        raise AssertionError("backend must not be created on a dry run")

    out = run_retest(audit_run, FROZEN, CODERS, SPECS, boom, n=3, dry_run=True)
    assert len(out["scored"]) == 9 and all(s["dry_run"] for s in out["scored"])
    assert not retest_dir(audit_run).exists()


def test_cli_plan_only_and_registered(audit_run, tmp_path, capsys):
    import csv

    fl = tmp_path / "frozen.csv"
    with open(fl, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "benchmark_name"])
        w.writeheader()
        w.writerows(FROZEN)
    rc = cli.main(["retest", "--out", str(audit_run), "--frozen-list", str(fl), "--n", "2", "--plan-only"])
    assert rc == 0
    p = json.loads(capsys.readouterr().out)
    assert len(p["drawn"]) == 2
    rc = cli.main(["retest", "--out", str(audit_run), "--frozen-list", str(fl), "--n", "3", "--dry-run"])
    assert rc == 0 and "scored" in capsys.readouterr().out
