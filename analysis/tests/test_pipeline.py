"""End-to-end tests on the synthetic fixture (analysis/mock/make_mock.py). Nothing here uses real data."""
import json
import math

import pytest

import figures
import make_mock
import rq1_rq2
import rq3_reruns


@pytest.fixture(scope="module")
def mock(tmp_path_factory):
    root = tmp_path_factory.mktemp("mock")
    return make_mock.make(root)


@pytest.fixture(scope="module")
def rq12(mock, tmp_path_factory):
    d = tmp_path_factory.mktemp("rq12")
    res = rq1_rq2.run(mock["scorer_run"], d / "out", d / "tables", n_boot=200)
    return res, d


@pytest.fixture(scope="module")
def rq3(mock, tmp_path_factory):
    d = tmp_path_factory.mktemp("rq3")
    res = rq3_reruns.run(mock["rq3_runs"], d / "out", d / "tables", expected_tasks=4, scorer=make_mock.mock_scorer)
    return res, d


# ------------------------------------------------------------------ RQ1 / RQ2
def test_rq12_outputs_exist(rq12):
    _, d = rq12
    for f in ["rq1_prevalence", "rq1_modules", "rq1_resolution", "rq1_contradictions", "rq2_alpha",
              "rq2_perturbation", "rq2_gold"]:
        assert (d / "out" / f"{f}.csv").exists(), f
    for f in ["rq1_prevalence", "rq1_modules", "rq2_alpha", "rq2_perturbation", "rq2_gold"]:
        t = (d / "tables" / f"{f}.tex").read_text(encoding="utf-8")
        assert r"\toprule" in t and r"\bottomrule" in t and r"\begin{tabular}" in t


def test_prevalence_wilson_and_monotone(rq12):
    res, _ = rq12
    prev = [r for r in res["prevalence"] if r["rule"] == "resolved"]
    assert [r["item"] for r in prev][:3] == ["C1", "C2", "C3"] and len(prev) == 25
    for r in prev:
        assert r["n_applicable"] + r["n_na"] == r["n_cells"] == 8
        assert r["n_full"] <= r["n_reported"] <= r["n_applicable"]
        if r["n_applicable"]:
            assert 0 <= r["reported_lo"] <= r["share_reported"] <= r["reported_hi"] <= 1
            assert r["full_lo"] <= r["share_full"] <= r["full_hi"]


def test_modules(rq12):
    res, _ = rq12
    mods = {(r["module"], r["rule"]): r for r in res["modules"]}
    assert set(mods) == {("core", "resolved"), ("agent", "resolved"), ("core", "majority"), ("agent", "majority")}
    assert mods[("core", "resolved")]["n_items"] == 14 and mods[("agent", "resolved")]["n_items"] == 11
    for m in mods.values():
        assert 0 <= m["mean_bench_fraction_of_max"] <= 1
        assert m["share_full"] <= m["share_reported"]


def test_resolution_counts(rq12):
    res, _ = rq12
    d = {r["status"]: r["n_cells"] for r in res["resolution"]}
    assert d["TOTAL_CELLS"] == 8 * 25
    parts = sum(v for k, v in d.items() if k not in ("ALL_FALLBACK", "PRIMARY_EQUALS_MAJORITY", "TOTAL_CELLS"))
    assert parts == d["TOTAL_CELLS"]


def test_alpha_sets(rq12):
    res, _ = rq12
    assert {r["kind"] for r in res["alpha"]} == {"all_coders", "cross_family_pair"}
    pairs = {r["set"] for r in res["alpha"] if r["kind"] == "cross_family_pair"}
    assert len(pairs) == 3  # three coders from three families
    for r in res["alpha"]:
        if r["scope"] == "overall":
            assert -1 <= r["alpha"] <= 1 and r["ci_lo"] <= r["ci_hi"]


def test_perturbation(rq12):
    res, _ = rq12
    pt = res["perturbation"]
    coders = {r["coder"] for r in pt}
    assert "RESOLVED" in coders and {"sonnet", "codex", "gemini"} <= coders
    overall = [r for r in pt if r["scope"] == "overall"]
    assert {r["metric"] for r in overall} == {"sensitivity", "sensitivity_any_level", "specificity"}
    for r in pt:
        eps = 1e-9
        assert -eps <= r["wilson_lo"] <= r["rate"] + eps and r["rate"] - eps <= r["wilson_hi"] <= 1 + eps
        assert r["hits"] <= r["n"]


def test_gold(rq12):
    res, _ = rq12
    g = res["gold"]
    assert {r["set"] for r in g} == {"abc", "betterbench"}
    assert any(r["coder"] == "RESOLVED" for r in g)
    bb = [r for r in g if r["set"] == "betterbench"][0]
    assert bb["weighted_kappa_quadratic"] is not None


def test_contradiction_flags(rq12):
    res, _ = rq12
    assert len(res["contradictions"]) >= 25
    for r in res["contradictions"]:
        assert r["cells_flag_verified_quote"] <= r["cells_with_flag"] <= 8


# ------------------------------------------------------------------ RQ3
def test_pass_hat_k_and_verdict():
    assert rq3_reruns.pass_hat_k(5, 5, 5) == 1.0
    assert rq3_reruns.pass_hat_k(0, 5, 1) == 0.0
    assert math.isclose(rq3_reruns.pass_hat_k(3, 5, 2), 3 / 10)
    assert rq3_reruns.verdict_pass({"verdict": "correct"}) is True
    assert rq3_reruns.verdict_pass({"verdict": "incorrect"}) is False
    assert rq3_reruns.verdict_pass({"verdict": {"pass": True}}) is True
    assert rq3_reruns.verdict_pass({"verdict": None}) is None


def _ep(task, rep, actions, ok, cond="A"):
    return {"_key": f"{task}|{cond}|{rep}", "bench": "X", "condition_name": cond, "task_id": task, "repeat": rep,
            "condition": {"temperature": 0.0}, "actions": actions, "verdict": {"pass": ok}, "driver_status": "ok",
            "error": None}


def test_divergence_logic(tmp_path):
    eps = []
    for r in range(5):  # identical actions, mixed verdicts: not divergent, unstable
        eps.append(_ep("t1", r, ["a", "b"], r < 2))
    for r in range(5):  # different actions, constant verdict: divergent, stable, same-verdict-different-actions
        eps.append(_ep("t2", r, ["a", str(r % 2)], True))
    for r in range(5):  # identical, constant
        eps.append(_ep("t3", r, ["z"], False))
    for r in range(3):  # incomplete group: counted but excluded
        eps.append(_ep("t4", r, ["q"], True))
    (tmp_path / "X").mkdir()
    (tmp_path / "X" / "episodes.jsonl").write_text("\n".join(json.dumps(e) for e in eps), encoding="utf-8")
    res = rq3_reruns.compute(tmp_path, ["X"], expected_tasks=4)
    d = res["divergence"][0]
    assert (d["tasks_complete"], d["divergent_n"], d["unstable_n"], d["same_verdict_diff_actions_n"]) == (3, 1, 1, 1)
    assert d["partial"] is True and d["episodes_seen"] == 18
    pk = {r["k"]: r["pass_hat_k"] for r in res["passk"]}
    assert math.isclose(pk[1], (0.4 + 1 + 0) / 3)  # t1: c=2 of 5 -> 0.4
    assert all(pk[k] >= pk[k + 1] for k in range(1, 5))


def test_rq3_partial_and_outputs(rq3):
    res, d = rq3
    assert res["partial"] is True
    st = {(s["bench"], s["condition"]): s for s in res["status"]}
    assert st[("AgentClinic", "A")]["episodes_failed"] == 1 and st[("AgentClinic", "A")]["tasks_complete"] == 3
    assert st[("RadABench", "A")]["tasks_complete"] == 4 and not st[("RadABench", "A")]["partial"]
    assert json.loads((d / "out" / "rq3_status.json").read_text())["partial"] is True
    for f in ["rq3_divergence.csv", "rq3_passk.csv", "rq3_ci_width.csv", "rq3_groups.csv", "rq3_grader_state.csv"]:
        assert (d / "out" / f).exists(), f
    t = (d / "tables" / "rq3_divergence.tex").read_text(encoding="utf-8")
    assert r"\toprule" in t and "PARTIAL DATA" in t and r"\dagger" in t


def test_rq3_ci_width_consistency(rq3):
    res, _ = rq3
    pk = {(r["bench"], r["condition"]): r for r in res["passk"] if r["k"] == 1}
    for r in res["ci_width"]:
        if r.get("ci_width_5run") is None:
            continue
        p = pk[(r["bench"], r["condition"])]
        # the 5-run headline CI is the pass^1 CI (same estimator, same resamples)
        assert math.isclose(r["ci_width_5run"], p["ci_hi"] - p["ci_lo"], abs_tol=1e-9)
        assert math.isclose(r["score_5run"], p["pass_hat_k"], abs_tol=1e-9)


def test_grader_vs_state(rq3):
    res, d = rq3
    gs = {r["condition"]: r for r in res["grader_state"] if r["bench"] == "synthetic_hospital"}
    assert gs
    for r in gs.values():
        assert r["agree"] + r["disagree"] + r["neutral_set_required"] + r["state_missing"] == r["n_episodes"]
    # no threshold is used: outcomes come from comparing the reported and the recomputed reward
    eps = [e for e in res["grader_state_episodes"]]
    assert all(e["outcome"] != "agree" or abs(e["recomputed_reward"] - e["reported_reward"]) <= 1e-6 for e in eps)
    assert sum(e["outcome"] == "state_missing" for e in eps) == 1  # the episode without a reference
    assert any(e["outcome"] == "disagree" for e in eps)


def test_recompute_reward_cases():
    ep = {"final_state": {"reference": {"task": "patient_diagnosis", "ground_truth": {
        "active_diagnoses": [{"icd10": "A00"}], "chronic_conditions": []}},
        "submission": {"active_diagnoses": [{"icd10": "A00"}], "chronic_conditions": []}}}
    assert rq3_reruns.recompute_reward(ep, make_mock.mock_scorer) == ("ok", 1.0)
    ep["final_state"]["submission"] = None  # README.md:225-226: missing submission scores 0
    assert rq3_reruns.recompute_reward(ep, make_mock.mock_scorer) == ("ok", 0.0)
    ep["final_state"]["reference"] = None
    assert rq3_reruns.recompute_reward(ep, make_mock.mock_scorer)[0] == "state_missing"
    assert rq3_reruns.recompute_reward({}, make_mock.mock_scorer)[0] == "state_missing"


def test_real_benchmark_scorer_if_available():
    fn = rq3_reruns._benchmark_scorer()
    if fn is None:
        pytest.skip("synthetic_hospital repository or its dependencies not available")
    gt = {"active_diagnoses": [{"icd10": "A69.20", "acuity": "acute"}], "chronic_conditions": []}
    perfect = {"active_diagnoses": [{"icd10": "A69.20", "acuity": "acute"}], "chronic_conditions": []}
    assert fn("patient_diagnosis", [perfect], [gt])["weighted_problem_list_f1_neutral"] == pytest.approx(1.0)


# ------------------------------------------------------------------ figures
def test_figures_render(rq12, rq3, tmp_path):
    out = tmp_path / "figs"
    figures.fig_prevalence(rq12[1] / "out" / "rq1_prevalence.csv", out / "fig4.pdf")
    figures.fig_ci_width(rq3[1] / "out" / "rq3_ci_width.csv", out / "fig5.pdf", rq3[1] / "out" / "rq3_status.json")
    for f in ("fig4.pdf", "fig5.pdf"):
        assert (out / f).read_bytes()[:4] == b"%PDF"


def test_flow_parse_and_render(tmp_path):
    md = figures.FLOW_MD
    if not md.exists():
        pytest.skip("flow_counts.md not present")
    f = figures.parse_flow(md.read_text(encoding="utf-8"))
    assert f["ft_excluded"] + f["included"] == f["fulltext"]
    assert f["raw_total"] - f["dups"] == f["unique"]
    figures.fig_flow(md, tmp_path / "fig2.pdf")
    assert (tmp_path / "fig2.pdf").read_bytes()[:4] == b"%PDF"


# ------------------------------------------------------------------ R-rule sensitivity switch
def _write_eligibility(d):
    import csv

    fl = d / "frozen.csv"
    ov = d / "overrides.csv"
    rows = [("mock01", "none (E1-E5 met; R1-R7 re-checked, no change)"), ("mock02", "R1"), ("mock03", "R4"),
            ("mock04", "E1-E5"), ("mock05", "R6a"), ("mock06", "none"), ("ghost07", "R6"), ("mock08", "R1 (more)")]
    with open(fl, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "benchmark_name", "rule_applied"])
        w.writerows((i, i, r) for i, r in rows)
    with open(ov, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "benchmark_name", "first_pass", "final", "rule"])
        w.writerow(["mock04", "mock04", "X1", "INCLUDE", "R1"])  # changed decision, no rule_applied: still affected
        w.writerow(["mock06", "mock06", "INCLUDE", "INCLUDE", "R1"])  # confirmed, not changed: kept
    return fl, ov


def test_rule_affected_selection(tmp_path):
    fl, ov = _write_eligibility(tmp_path)
    ids = {r["id"] for r in rq1_rq2.rule_affected(fl, ov)}
    assert ids == {"mock02", "mock03", "mock04", "mock05", "ghost07", "mock08"}
    hit, unmatched = rq1_rq2.rule_affected_benches([f"mock0{i}" for i in range(1, 9)], fl, ov)
    assert set(hit) == {"mock02", "mock03", "mock04", "mock05", "mock08"}
    assert [u["id"] for u in unmatched] == ["ghost07"]


def test_exclude_rule_affected_writes_suffixed_outputs_and_leaves_primary(mock, tmp_path):
    fl, ov = _write_eligibility(tmp_path)
    out, tables = tmp_path / "out", tmp_path / "tables"
    full = rq1_rq2.run(mock["scorer_run"], out, tables, n_boot=50)
    primary_csv = (out / "rq1_prevalence.csv").read_text(encoding="utf-8")
    res = rq1_rq2.run(mock["scorer_run"], out, tables, n_boot=50, exclude_rule_affected=True, frozen_list=fl,
                      overrides=ov)
    assert res["benchmarks"] == ["mock01", "mock06", "mock07"]  # 8 mock benchmarks minus the 5 affected
    assert [r["bench"] for r in res["excluded"]] == ["mock02", "mock03", "mock04", "mock05", "mock08"]
    prev = [r for r in res["prevalence"] if r["rule"] == "resolved"]
    assert len(prev) == 25 and all(r["n_cells"] == 3 for r in prev)
    assert (out / "rq1_prevalence_ruleexcl.csv").exists() and (tables / "rq1_prevalence_ruleexcl.tex").exists()
    assert (out / "rq1_rule_excluded.csv").exists() and (out / "rq1_rule_sensitivity_delta.csv").exists()
    assert (out / "rq2_alpha_ruleexcl.csv").exists()
    assert not (out / "rq2_perturbation_ruleexcl.csv").exists()
    assert (out / "rq1_prevalence.csv").read_text(encoding="utf-8") == primary_csv  # primary output untouched
    assert len(full["benchmarks"]) == 8
    assert len(res["delta"]) == 25 and all(d["n_all"] >= d["n_excl"] for d in res["delta"])
