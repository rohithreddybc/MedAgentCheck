import pytest

from agentaudit.stats import alpha_ordinal, bootstrap_ci, wilson

# Hand computation (two coders, five units):
#   units: (0,0) (1,1) (2,2) (0,1) (1,2)
#   coincidences o: o00=2, o11=2, o22=2, o01=o10=1, o12=o21=1  -> n_0=3, n_1=4, n_2=3, n=10
#   ordinal delta^2: d01 = (3+4-(3+4)/2)^2 = 12.25, d12 = (4+3-(4+3)/2)^2 = 12.25,
#                    d02 = (3+4+3-(3+3)/2)^2 = 49
#   D_o = (2*12.25 + 2*12.25)/10 = 4.9
#   D_e = 2*(3*4*12.25 + 4*3*12.25 + 3*3*49)/(10*9) = 1470/90 = 16.3333
#   alpha = 1 - 4.9/16.3333 = 0.7
UNITS = [(0, 0), (1, 1), (2, 2), (0, 1), (1, 2)]


def test_alpha_hand_computed():
    assert alpha_ordinal(UNITS) == pytest.approx(0.7, abs=1e-12)


def test_alpha_perfect_and_undefined():
    assert alpha_ordinal([(0, 0), (1, 1), (2, 2), (1, 1)]) == pytest.approx(1.0)
    assert alpha_ordinal([(1, 1), (1, 1)]) is None  # no variation: undefined
    assert alpha_ordinal([]) is None


def test_na_is_missing_and_unpairable_units_dropped():
    with_na = UNITS + [(1, "NA"), (None, 2), (0,)]
    assert alpha_ordinal(with_na) == pytest.approx(0.7, abs=1e-12)


def test_three_coders_with_a_missing_value_matches_package():
    units = [(0, 0, 0), (1, 1, 2), (2, 2, 2), (0, 1, 1), (1, 2, None), (0, 0, 1)]
    a = alpha_ordinal(units)
    krip = pytest.importorskip("krippendorff")
    import numpy as np

    mat = np.array([[np.nan if v is None else v for v in u] for u in units], dtype=float).T
    ref = krip.alpha(reliability_data=mat, level_of_measurement="ordinal")
    assert a == pytest.approx(ref, abs=1e-9)


def test_wilson_known_value():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert wilson(0, 0) is None


def test_bootstrap_ci_deterministic_and_needs_two_groups():
    groups = {"a": [(0, 0), (1, 1)], "b": [(2, 2), (0, 1)], "c": [(1, 2), (2, 2)]}
    one = bootstrap_ci(groups, alpha_ordinal, n_boot=200, seed=1)
    two = bootstrap_ci(groups, alpha_ordinal, n_boot=200, seed=1)
    assert one == two and one[0] <= one[1]
    assert bootstrap_ci({"a": [(0, 0)]}, alpha_ordinal) is None


# ---- Cohen's and weighted kappa (gold validation)
def test_cohen_kappa_textbook_and_edge_cases():
    from agentaudit.stats import cohen_kappa, raw_agreement

    # 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no: po = 0.7, pe = 0.5 -> kappa 0.4
    a = [1] * 25 + [0] * 25
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    assert abs(cohen_kappa(a, b) - 0.4) < 1e-12 and abs(raw_agreement(a, b) - 0.7) < 1e-12
    assert cohen_kappa([1, 0, 1], [1, 0, 1]) == 1.0
    assert cohen_kappa([1, 1, 1], [1, 1, 1]) is None  # chance agreement 1: undefined
    assert cohen_kappa([], []) is None and raw_agreement([], []) is None
    assert cohen_kappa([0, 1, 0, 1], [1, 0, 1, 0]) == -1.0


def test_weighted_kappa_matches_sklearn_and_orders_errors():
    from agentaudit.stats import cohen_kappa, weighted_kappa

    g = [0, 1, 2, 3, 3, 2, 1, 0, 3, 3, 2, 0, 1, 2, 3, 3]
    p = [0, 1, 3, 3, 2, 2, 0, 0, 3, 1, 2, 1, 1, 2, 3, 0]
    lv = [0, 1, 2, 3]
    q, l = weighted_kappa(g, p, lv, "quadratic"), weighted_kappa(g, p, lv, "linear")
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError:  # pragma: no cover
        cohen_kappa_score = None
    if cohen_kappa_score is not None:
        assert abs(q - cohen_kappa_score(g, p, weights="quadratic")) < 1e-12
        assert abs(l - cohen_kappa_score(g, p, weights="linear")) < 1e-12
        assert abs(cohen_kappa(g, p) - cohen_kappa_score(g, p)) < 1e-12
    # a near miss costs less than a far miss
    base = [0, 1, 2, 3] * 5
    near = [min(3, x + 1) for x in base]
    far = [3 - x for x in base]
    assert weighted_kappa(base, near, lv) > weighted_kappa(base, far, lv)
    assert weighted_kappa(base, base, lv) == 1.0
    assert weighted_kappa([2, 2], [2, 2], lv) is None  # no variation: undefined
    with pytest.raises(ValueError):
        weighted_kappa(g, p, lv, "cubic")
