from agentaudit.items import load_items
from agentaudit.util import normalise
from agentaudit.verify import verify_quote, verify_result

CH = {"S1:p:1-3": "Each task was run “five” times\nper model — with independent seeds. The ﬁnal score is the mean.",
      "S1:p:4-6": "Other text entirely about the weather and unrelated matters."}
NORM = {k: normalise(v) for k, v in CH.items()}


def test_normalise_quotes_dashes_whitespace_nfkc():
    assert normalise("  a’s “b” – c\n\t d ") == "a's \"b\" - c d"
    assert normalise("ﬁnal") == "final"  # NFKC ligature
    assert normalise("zero​width") == "zerowidth"


def test_verbatim_after_normalisation():
    q = {"chunk_id": "S1:p:1-3", "text": 'run "five" times per model - with independent seeds'}
    assert verify_quote(q, NORM)["verified"]
    q2 = {"chunk_id": "[S1:p:1-3]", "text": "independent seeds. The final score is the mean"}
    r = verify_quote(q2, NORM)
    assert r["verified"] and r["verified_strict"]


def test_wrong_chunk_unknown_chunk_and_paraphrase_fail():
    assert verify_quote({"chunk_id": "S1:p:4-6", "text": "run five times per model"}, NORM)["reason"] == "not_a_substring"
    assert verify_quote({"chunk_id": "S9:x:1-2", "text": "run five times per model"}, NORM)["reason"] == "chunk_not_in_retrieval_set"
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "each task ran five times"}, NORM)["verified"] is False


def test_loose_ignores_case_spacing_and_punctuation_strict_does_not():
    CH2 = {"c": "Pass ∧ k scores [ 24 ] were 10\\% higher ( gpt-3.5-turbo-0613 ) than the baseline."}
    n2 = {k: normalise(v) for k, v in CH2.items()}
    q = {"chunk_id": "c", "text": "PASS k scores [24] were 10% higher (gpt-3.5-turbo-0613) than the baseline"}
    r = verify_quote(q, n2)
    assert r["verified"] is True and r["verified_strict"] is False and r["reason"] == "ok"
    # exact copy: both rules agree
    q = {"chunk_id": "c", "text": "scores [ 24 ] were 10\\% higher ( gpt-3.5-turbo-0613 ) than"}
    r = verify_quote(q, n2)
    assert r["verified"] and r["verified_strict"]
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "EACH TASK WAS RUN"}, NORM)["verified"] is False  # 14 characters: too short
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "EACH TASK WAS RUN FIVE TIMES"}, NORM)["verified"] is True


def test_minimum_is_20_normalised_characters():
    short = {"chunk_id": "S1:p:1-3", "text": "run five times per"}  # 15 letters after normalisation
    r = verify_quote(short, NORM)
    assert r["verified"] is False and r["reason"] == "quote_too_short"
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "run five times per model"}, NORM)["verified"]  # 20
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "run"}, NORM)["reason"] == "quote_too_short"
    # punctuation and spaces do not count towards the minimum
    assert verify_quote({"chunk_id": "S1:p:1-3", "text": "run -- five -- times -- per"}, NORM)["verified"] is False


def test_strict_field_is_secondary_and_counted_in_result():
    items = load_items()
    p = {"score": 2, "quotes": [{"chunk_id": "S1:p:1-3", "text": "EACH TASK WAS RUN “FIVE” TIMES PER MODEL"}],
         "contradicted": False, "contradiction_quotes": [], "elements": [True, True, True]}
    v = verify_result(p, items["A1"], CH)
    assert v["supported"] and v["n_verified"] == 1 and v["n_verified_strict"] == 0 and not v["supported_strict"]
    assert v["quotes"][0]["verified"] and not v["quotes"][0]["verified_strict"]


def test_ellipsis_fragments_all_must_match():
    ok = {"chunk_id": "S1:p:1-3", "text": "Each task was run ... independent seeds"}
    bad = {"chunk_id": "S1:p:1-3", "text": "Each task was run ... something invented here"}
    assert verify_quote(ok, NORM)["verified"]
    assert not verify_quote(bad, NORM)["verified"]


def test_unsupported_downgrade_and_na_rules():
    items = load_items()
    parsed = {"score": 2, "quotes": [{"chunk_id": "S1:p:4-6", "text": "invented evidence that is not there"}],
              "contradicted": False, "contradiction_quotes": [], "elements": [True, True, True]}
    v = verify_result(parsed, items["A1"], CH)
    assert v["effective"] == 0 and "unsupported" in v["flags"] and not v["supported"]
    good = dict(parsed, quotes=[{"chunk_id": "S1:p:1-3", "text": "with independent seeds"}])
    v = verify_result(good, items["A1"], CH)
    assert v["effective"] == 2 and v["supported"]
    # NA is not allowed on A1 (no NA clause) and is coerced to 0; A5 has an NA clause
    na = {"score": "NA", "quotes": [], "contradicted": False, "contradiction_quotes": [], "elements": None}
    assert verify_result(na, items["A1"], CH)["effective"] == 0
    assert verify_result(na, items["A5"], CH)["effective"] == "NA"


def test_contradiction_needs_verified_quote():
    items = load_items()
    p = {"score": 1, "quotes": [{"chunk_id": "S1:p:1-3", "text": "with independent seeds"}], "contradicted": True,
         "contradiction_quotes": [{"chunk_id": "S1:p:4-6", "text": "made up contradicting text here"}],
         "elements": [True, False, False]}
    assert verify_result(p, items["A1"], CH)["contradiction_verified"] is False


def test_mojibake_repair_before_matching():
    from agentaudit.verify import repair_mojibake
    broken = "groundâ€‘truth"
    assert repair_mojibake(broken) == "ground‑truth" and repair_mojibake("plain text") == "plain text"
    chunks = {"c": normalise("the ground‑truth label is hidden")}
    assert verify_quote({"chunk_id": "c", "text": "the groundâ€‘truth label is hidden"}, chunks)["verified"]
