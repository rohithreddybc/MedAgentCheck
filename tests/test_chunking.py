from agentaudit.chunking import (Source, build_chunks, chunk_id, chunk_lines, chunk_source, is_s5,
                                 parse_chunk_id, wrap_long_lines)
from agentaudit.util import est_tokens


def _src(n_lines=200, width=80, surface="S1", path="p/a.txt"):
    text = "\n".join(("line %03d " % i).ljust(width, "x") for i in range(n_lines))
    return Source(surface, path, text)


def test_chunk_ids_format_and_roundtrip():
    chunks = chunk_source(_src())
    assert chunks[0].id == "S1:p/a.txt:1-%d" % chunks[0].end
    for c in chunks:
        assert c.id == chunk_id("S1", "p/a.txt", c.start, c.end)
        assert parse_chunk_id(c.id) == ("S1", "p/a.txt", c.start, c.end)
    assert parse_chunk_id("garbage") is None


def test_chunk_size_overlap_and_coverage():
    chunks = chunk_source(_src())
    assert len(chunks) > 3
    assert all(c.tokens <= 400 + 25 for c in chunks)
    assert chunks[-1].end == 200
    for a, b in zip(chunks, chunks[1:]):
        assert b.start <= a.end  # overlap or adjacency, never a gap
        assert b.start > a.start
    overlap_lines = [(a.end - b.start + 1) for a, b in zip(chunks, chunks[1:])]
    assert all(0 <= o <= 3 for o in overlap_lines) and max(overlap_lines) >= 1  # ~50 tokens = 200 chars = 2 lines
    assert est_tokens(chunks[0].text) == chunks[0].tokens


def test_chunking_deterministic():
    a = [c.to_dict() for c in build_chunks([_src(), _src(path="z.txt")])]
    b = [c.to_dict() for c in build_chunks([_src(path="z.txt"), _src()])]
    assert a == b


def test_long_line_wrapped_and_ids_refer_to_stored_text():
    long_line = " ".join(["word"] * 2000)
    text = wrap_long_lines("short\n" + long_line)
    assert all(len(l) <= 1600 for l in text.split("\n"))
    chunks = chunk_source(Source("S2", "README.md", text))
    assert chunks[-1].end == len(text.split("\n"))


def test_single_oversize_line_still_progresses():
    lines = ["x" * 1500] * 5
    assert chunk_lines(lines)[-1][1] == 5


def test_s5_tagging_only_on_s4():
    code = 'SYSTEM_PROMPT = "You are a doctor"\n'
    assert is_s5(code)
    assert is_s5('{"type": "function", "parameters": {"a": 1}}')
    assert not is_s5("def add(a, b):\n    return a + b")
    cs = build_chunks([Source("S4", "tools.py", code), Source("S1", "paper", code)], is_s5)
    assert {c.surface: c.s5 for c in cs} == {"S4": True, "S1": False}
