from agentaudit.resolve import majority_level, resolve_cell

G, S, O = "gpt-oss", "sonnet", "opus"


def V(raw, eff=None, fam="claude"):
    return {"raw": raw, "effective": raw if eff is None else eff, "family": fam}


def vote(x, fam):
    return V(*x, fam=fam) if isinstance(x, tuple) else V(x, fam=fam)


def votes(g, s, o):
    return {G: vote(g, "oss"), S: vote(s, "claude"), O: vote(o, "claude")}


def test_all_agree():
    r = resolve_cell(votes(2, 2, 2))
    assert r["final"] == 2 and r["status"] == "resolved" and not r["fallback"]


def test_highest_level_with_two_coders_incl_cross_family():
    assert resolve_cell(votes(2, 1, 1))["final"] == 1  # only gpt-oss at 2
    assert resolve_cell(votes(2, 2, 0))["final"] == 2
    assert resolve_cell(votes(1, 2, 2))["final"] == 1  # Claude pair at 2, gpt-oss only 1


def test_cross_family_required_two_claude_coders_alone_do_not_resolve():
    r = resolve_cell(votes(0, 2, 2))
    assert r["final"] == 0 and r["fallback"] and r["status"] == "not_established"
    assert r["majority_final"] == 2  # the majority-rule sensitivity variant differs


def test_unsupported_scores_do_not_count():
    r = resolve_cell(votes((2, 0), 2, 2))  # gpt-oss 2 without a verified quote
    assert r["final"] == 0 and r["fallback"]
    r = resolve_cell(votes((2, 0), 1, 1))
    assert r["final"] == 0 and r["fallback"]


def test_established_zero_is_not_a_fallback():
    r = resolve_cell(votes(0, 0, 2))
    assert r["final"] == 0 and r["status"] == "established_zero" and not r["fallback"]


def test_na_accepted_needs_two_incl_cross_family():
    r = resolve_cell(votes("NA", "NA", 0))
    assert r["final"] == "NA" and r["status"] == "na_accepted"
    assert resolve_cell(votes("NA", 0, "NA"))["final"] == "NA"


def test_na_rejected_is_treated_as_zero():
    r = resolve_cell(votes("NA", 0, 1))
    assert r["final"] == 0 and r["fallback"] and r["status"] == "na_rejected_as_zero"
    r = resolve_cell(votes(2, "NA", "NA"))  # two Claude NA without gpt-oss: not accepted
    assert r["final"] == 0 and r["fallback"]


def test_level_beats_na():
    assert resolve_cell({G: V(2, fam="oss"), S: V(2), O: V("NA")})["final"] == 2


def test_two_coders_only_and_single_coder():
    assert resolve_cell({G: V(1, fam="oss"), S: V(2)})["final"] == 1
    assert resolve_cell({S: V(2)})["status"] == "insufficient_coders"


def test_no_cross_family_flag_for_single_family_users():
    v = {"a": V(2), "b": V(2)}
    assert resolve_cell(v)["final"] == 0
    assert resolve_cell(v, require_cross_family=False)["final"] == 2


def test_majority_rule_variant():
    assert majority_level(votes(2, 2, 0)) == 2
    assert majority_level(votes(2, 1, 0)) == 1
    assert majority_level(votes(0, 1, 0)) == 0
    assert majority_level(votes("NA", "NA", 2)) == "NA"
