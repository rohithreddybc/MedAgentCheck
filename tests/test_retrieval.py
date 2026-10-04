import json

from agentaudit.chunking import Source, build_chunks, is_s5
from agentaudit.items import ITEM_ORDER, load_queries
from agentaudit.retrieve import retrieve_chunks, run_retrieval, tokenize

from conftest import make_sources


def _chunks():
    return build_chunks(make_sources(), is_s5)


def test_retrieval_deterministic_across_calls_and_input_order():
    a = retrieve_chunks(_chunks(), "A1")
    b = retrieve_chunks(list(reversed(_chunks())), "A1")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert [c["rank"] for c in a["chunks"]] == list(range(1, len(a["chunks"]) + 1))


def test_runs_write_identical_files(run_dir):
    run_retrieval(run_dir, "toy", ["A1", "A5"])
    f = run_dir / "retrieval" / "toy" / "A1.json"
    first = f.read_text(encoding="utf-8")
    run_retrieval(run_dir, "toy", ["A1", "A5"])
    assert f.read_text(encoding="utf-8") == first


def test_relevant_chunk_ranked_first_and_cap_respected():
    r = retrieve_chunks(_chunks(), "A1")
    assert "five times" in next(c for c in _chunks() if c.id == r["chunks"][0]["id"]).text
    q = load_queries()
    assert r["total_tokens"] <= q["params"]["token_cap"]
    assert len(r["chunks"]) <= q["params"]["k"]


def test_always_include_s5_for_tool_items():
    r = retrieve_chunks(_chunks(), "A5")
    s5_ids = {c.id for c in _chunks() if c.s5}
    assert s5_ids and s5_ids <= {c["id"] for c in r["chunks"]}
    assert any(c["reason"] == "always:s5" for c in r["chunks"])
    r1 = retrieve_chunks(_chunks(), "A1")
    assert all(c["reason"] == "bm25" for c in r1["chunks"])


def test_every_item_has_a_query_and_tokenizer_is_lowercase_alnum():
    q = load_queries()["items"]
    assert set(q) == set(ITEM_ORDER) and all(v["query"].strip() for v in q.values())
    assert tokenize("Pass^k, GPT-4o!") == ["pass", "k", "gpt", "4o"]


def test_empty_packet_gives_empty_set():
    assert retrieve_chunks([], "C1")["chunks"] == []
