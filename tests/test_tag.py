import json
import re

import pytest

from agentaudit.backends import BackendAuthError, BackendError, Response
from agentaudit.items import ITEM_ORDER, load_items
from agentaudit.packet import load_chunks
from agentaudit.retrieve import load_retrieval
from agentaudit.tag import (TagParseError, build_item_sets, item_glosses, make_windows, merged_path, parse_tags,
                            render_tag_prompt, run_tagging, select_item_chunks)
from agentaudit.throttle import DailyLimitReached
from agentaudit.util import est_tokens, read_json

QUIET = dict(log=lambda *_: None)


class FakeTagger:
    """Mock backend: reads the chunk ids out of the prompt and tags them by a rule."""

    def __init__(self, rule, fail_first_parse=False, too_large_over=None):
        self.rule, self.calls, self.fail_first_parse, self.too_large_over = rule, [], fail_first_parse, too_large_over

    def complete(self, system, prompt):
        ids = re.findall(r"^### \[(.+?)\] surface=", prompt, flags=re.M)
        self.calls.append(ids)
        if self.too_large_over and len(ids) > self.too_large_over:
            raise BackendError("413: Request too large for model")
        if self.fail_first_parse and len(self.calls) == 1:
            return Response("not json at all", "mock")
        return Response(json.dumps({i: self.rule(i) for i in ids}), "mock-1", usage={"total_tokens": 100})


SPEC = {"backend": "openai", "model": "mock", "family": "mock"}


def seeds_rule(cid):
    return ["A1"] if cid.startswith("S1:") else []


def sorted_chunks(run_dir):
    return sorted(load_chunks(run_dir, "toy"), key=lambda c: (c.surface, c.path, c.start, c.end))


def test_glosses_one_line_per_item_from_items_yaml():
    g = item_glosses().split("\n")
    assert len(g) == 25 and [x.split(" ", 1)[0] for x in g] == ITEM_ORDER
    assert load_items()["C1"].item_text in g[0]


def test_windows_cover_every_chunk_once_in_order_and_respect_size(run_dir):
    chunks = load_chunks(run_dir, "toy")
    wins = make_windows(chunks, 600)
    flat = [c.id for w in wins for c in w]
    assert sorted(flat) == sorted(c.id for c in chunks) and len(flat) == len(set(flat))
    assert len(wins) > 1
    for w in wins:
        assert len(w) == 1 or sum(est_tokens(f"### [{c.id}] surface={c.surface}\n{c.text}") for c in w) <= 640
    assert flat == [c.id for c in sorted_chunks(run_dir)]


def test_prompt_lists_glosses_ids_and_chunk_text(run_dir):
    chunks = load_chunks(run_dir, "toy")[:2]
    p = render_tag_prompt(chunks)
    assert "C1 Traceability" in p and all(f"[{c.id}]" in p for c in chunks) and chunks[0].text in p
    assert "Include all 2 chunk ids" in p


def test_parse_tags_cleans_ids_drops_unknowns_and_allows_empty():
    ids = ["S1:a:1-2", "S1:a:2-3"]
    txt = '```json\n{"[S1:a:1-2]": ["c1", "A4", "Z9", "A4"], "S1:a:2-3": [], "S9:x:1-1": ["C2"]}\n```'
    tags, diag = parse_tags(txt, ids)
    assert tags == {"S1:a:1-2": ["C1", "A4"], "S1:a:2-3": []}
    assert diag == {"unknown_chunks": 1, "unknown_items": 1}
    assert parse_tags('{"tags": {"S1:a:1-2": "C2, C3"}}', ids)[0] == {"S1:a:1-2": ["C2", "C3"]}
    for bad in ("no json", "[1,2]", '{"S1:a:1-2": 5}', '{"zzz": []}'):
        with pytest.raises(TagParseError):
            parse_tags(bad, ids)


def test_run_tagging_writes_merged_file_and_resumes(run_dir):
    be = FakeTagger(seeds_rule)
    s = run_tagging(run_dir, "toy", "mock", SPEC, be, window_tokens=600, **QUIET)
    assert s["complete"] and s["done"] == s["windows"] and s["calls"] == s["windows"]
    m = read_json(merged_path(run_dir, "toy", "mock"))
    chunks = load_chunks(run_dir, "toy")
    assert set(m["tags"]) == {c.id for c in chunks} and m["complete"] and m["missing"] == []
    assert all(v == (["A1"] if k.startswith("S1:") else []) for k, v in m["tags"].items())
    n = len(be.calls)
    s2 = run_tagging(run_dir, "toy", "mock", SPEC, be, window_tokens=600, **QUIET)
    assert len(be.calls) == n and s2["skipped"] == s["windows"] and s2["done"] == 0


def test_resume_after_daily_limit(run_dir):
    class Limited(FakeTagger):
        def complete(self, system, prompt):
            if len(self.calls) == 2:
                raise DailyLimitReached(9e9)
            return super().complete(system, prompt)

    s = run_tagging(run_dir, "toy", "mock", SPEC, Limited(seeds_rule), window_tokens=600, **QUIET)
    assert s["blocked"] and not s["complete"] and s["done"] == 2
    be2 = FakeTagger(seeds_rule)
    s2 = run_tagging(run_dir, "toy", "mock", SPEC, be2, window_tokens=600, **QUIET)
    assert s2["complete"] and s2["skipped"] == 2 and len(be2.calls) == s2["windows"] - 2


def test_auth_failure_blocks_without_writing(run_dir):
    class Auth(FakeTagger):
        def complete(self, system, prompt):
            raise BackendAuthError("logged out")

    s = run_tagging(run_dir, "toy", "mock", SPEC, Auth(seeds_rule), window_tokens=600, **QUIET)
    assert s["blocked"]["reason"].startswith("authentication") and not s["complete"] and s["done"] == 0


def test_parse_retry_then_ok_and_413_split(run_dir):
    be = FakeTagger(seeds_rule, fail_first_parse=True)
    s = run_tagging(run_dir, "toy", "mock", SPEC, be, window_tokens=600, **QUIET)
    assert s["complete"] and s["calls"] == s["windows"] + 1
    be = FakeTagger(seeds_rule, too_large_over=2)
    s = run_tagging(run_dir, "toy", "mock2", SPEC, be, window_tokens=100000, **QUIET)
    assert s["complete"] and s["splits"] >= 1 and be.calls[-1] and len(be.calls[-1]) <= 2
    n = len(be.calls)  # resume reuses the split record: no repeat of the failed parent call
    run_tagging(run_dir, "toy", "mock2", SPEC, be, window_tokens=100000, **QUIET)
    assert len(be.calls) == n


def test_groq_json_validate_failed_400_splits_the_window(run_dir):
    class Overflow(FakeTagger):
        def complete(self, system, prompt):
            ids = re.findall(r"^### \[(.+?)\] surface=", prompt, flags=re.M)
            if len(ids) > 3:
                self.calls.append(ids)
                raise BackendError('400: {"error":{"code":"json_validate_failed","failed_generation":"max completion tokens reached before generating a valid document"}}')
            return super().complete(system, prompt)

    s = run_tagging(run_dir, "toy", "ovf", SPEC, Overflow(seeds_rule), window_tokens=100000, **QUIET)
    assert s["complete"] and s["splits"] >= 1 and not s["failed"]


def test_missing_chunks_are_recorded_not_invented(run_dir):
    class Lazy(FakeTagger):
        def complete(self, system, prompt):
            d = json.loads(super().complete(system, prompt).text)
            d.pop(next(iter(d)))
            return Response(json.dumps(d), "m")

    s = run_tagging(run_dir, "toy", "lazy", SPEC, Lazy(seeds_rule), window_tokens=600, **QUIET)
    m = read_json(merged_path(run_dir, "toy", "lazy"))
    assert not m["complete"] and len(m["missing"]) == s["windows"] and not s["complete"]


# ------------------------------------------------------------ selection
def test_select_priority_both_then_one_then_bm25_and_cap(run_dir):
    chunks = sorted_chunks(run_dir)
    ids = [c.id for c in chunks]
    a, b, c_, d = ids[0], ids[1], ids[2], ids[3]
    ta = {a: ["A1"], c_: ["A1"], d: ["A1"]}
    tb = {b: ["A1"], c_: ["A1"]}
    scores = {i: 0.0 for i in ids}
    scores[ids[-1]] = 5.0
    scores[ids[-2]] = 3.0
    rec = select_item_chunks(chunks, "A1", {"x": ta, "y": tb}, scores, 100000)
    got = [(e["id"], e["reason"]) for e in rec["chunks"]]
    assert got[0] == (c_, "tag:both")  # both taggers first
    assert [g[0] for g in got[1:4]] == [a, b, d] and all(g[1] == "tag:one" for g in got[1:4])  # one tagger, by position
    assert got[4:] == [(ids[-1], "bm25"), (ids[-2], "bm25")]  # filler by score
    assert not rec["truncated"] and rec["n_tagged"] == 4
    assert select_item_chunks(chunks, "C1", {"x": ta}, scores, 100000)["n_tagged"] == 0  # other items' tags ignored


def test_select_cap_truncates_tagged_and_reports_it(run_dir):
    chunks = sorted_chunks(run_dir)
    tags = {c.id: ["A1"] for c in chunks}
    scores = {c.id: 1.0 for c in chunks}
    cap = 1000
    rec = select_item_chunks(chunks, "A1", {"x": tags}, scores, cap)
    assert rec["total_tokens"] <= cap and rec["truncated"] and rec["n_tagged_dropped"] > 0
    assert rec["tagged_total_tokens"] > cap and all(e["reason"].startswith("tag") for e in rec["chunks"])
    assert rec["n_tagged_kept"] + rec["n_tagged_dropped"] == len(chunks)
    full = select_item_chunks(chunks, "A1", {"x": tags}, scores, sum(c.tokens for c in chunks))
    assert not full["truncated"] and full["n_tagged_kept"] == len(chunks)


def test_single_tagger_uses_tag_one_and_filler_is_optional(run_dir):
    chunks = load_chunks(run_dir, "toy")
    scores = {c.id: 2.0 for c in chunks}
    only = select_item_chunks(chunks, "A1", {"x": {chunks[0].id: ["A1"]}}, scores, 100000, bm25_filler=False)
    assert [e["reason"] for e in only["chunks"]] == ["tag:one"]
    filled = select_item_chunks(chunks, "A1", {"x": {chunks[0].id: ["A1"]}}, scores, 100000)
    assert filled["chunks"][0]["id"] == chunks[0].id and len(filled["chunks"]) == len(chunks)


def test_build_item_sets_writes_retrieval_compatible_files(run_dir):
    run_tagging(run_dir, "toy", "mock", SPEC, FakeTagger(seeds_rule), window_tokens=600, **QUIET)
    out = build_item_sets(run_dir, "toy", ["mock"], ["A1", "C1"], sets_name="retrieval_tags")
    rec = read_json(run_dir / "retrieval_tags" / "toy" / "A1.json")
    assert rec["chunks"] == out["A1"]["chunks"] and rec["total_tokens"] <= 5000
    for k in ("item", "query", "chunks", "total_tokens", "packet_sha256", "retrieval_sha256"):
        assert k in rec
    assert all(c["reason"] in ("tag:one", "tag:both", "bm25") for c in rec["chunks"])
    build_item_sets(run_dir, "toy", ["mock"], ["A1"])  # default name is where `code` reads
    assert load_retrieval(run_dir, "toy", "A1")["chunks"] == out["A1"]["chunks"]
