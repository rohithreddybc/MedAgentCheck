from pathlib import Path

import pytest

from agentaudit.items import ITEM_ORDER, global_rules, load_items, na_clause_text
from agentaudit.packet import classify_repo_files, html_to_text, parse_repo_url, source_rel_path

# rubric/ sits next to scorer/ in the study tree and next to tests/ in the released repository
ROOT = next((p for p in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1])
             if (p / "rubric" / "rubric-v1.md").exists()), Path(__file__).resolve().parents[2])
RUBRIC = ROOT / "rubric" / "rubric-v1.md"
MANUAL = ROOT / "rubric" / "coding-manual-v1.0.md"


def test_25_items_and_na_clauses():
    it = load_items()
    assert list(it) == ITEM_ORDER and len(it) == 25
    assert {i for i in it if it[i].na_allowed} == {"C9", "A5", "A6", "A7"}
    assert "NA as for A5" in na_clause_text("A6", it) and "no tool interface" in na_clause_text("A6", it)
    assert it["C1"].n_elements == 0 and it["A1"].n_elements == 3
    assert global_rules().count("**G") == 8 and "**G1a" in global_rules()


@pytest.mark.skipif(not (RUBRIC.exists() and MANUAL.exists()), reason="rubric docs not alongside the package")
def test_item_text_is_verbatim_from_source_docs():
    rub, man = RUBRIC.read_text(encoding="utf-8"), MANUAL.read_text(encoding="utf-8")
    for it in load_items().values():
        assert it.item_text in rub, it.id
        assert it.anchors in man, it.id
        if it.na_clause:
            assert it.na_clause in man, it.id
    for line in global_rules().split("\n"):
        assert line.lstrip("- ") in man


def test_classify_repo_files_surfaces_and_limits():
    files = {
        "README.md": b"# readme", "docs/guide.md": b"guide", "CHANGELOG.md": b"v1", "LICENSE": b"MIT",
        "agent/tools.py": b"def f(): pass", "src/misc.py": b"x=1", "data/tasks.jsonl": b"\n".join(b'{"a": %d}' % i for i in range(80)),
        "big/eval.py": b"x" * (200 * 1024 + 1), "node_modules/agent/x.py": b"y", "img/agent.png": b"\x89PNG\x00",
        "config.yaml": b"a: 1", "sub/README.md": b"# sub",
    }
    srcs = {(s.surface, s.path): s for s in classify_repo_files(files)}
    assert ("S2", "README.md") in srcs and ("S2", "docs/guide.md") in srcs and ("S2", "sub/README.md") in srcs
    assert ("S3", "CHANGELOG.md") in srcs
    assert ("S4", "agent/tools.py") in srcs and ("S4", "config.yaml") in srcs
    assert ("S4", "src/misc.py") not in srcs  # no keyword in path or name
    assert ("S4", "big/eval.py") not in srcs  # over 200 KB
    assert ("S4", "node_modules/agent/x.py") not in srcs and ("S4", "img/agent.png") not in srcs
    d = srcs[("S4", "data/tasks.jsonl")]  # 'tasks' contains 'task'; data truncated to 50 lines
    assert d.truncated and len(d.text.split("\n")) == 50


def test_classification_deterministic():
    files = {f"agent/t{i}.py": b"x" for i in range(400)}
    a = [s.path for s in classify_repo_files(files)]
    b = [s.path for s in classify_repo_files(dict(reversed(list(files.items()))))]
    assert a == b and len(a) == 300


def test_html_to_text_math_tables_headings():
    html = ("<html><nav>menu</nav><body><h2>Methods</h2><p>We use <math alttext='k=5'>k</math> runs.</p>"
            "<table><tr><td>A</td><td>0.5</td></tr></table><script>x</script></body></html>")
    t = html_to_text(html)
    assert "## Methods" in t and "k=5" in t and "A | 0.5" in t and "menu" not in t and "x" not in t.replace("0.5", "")


def test_misc_helpers():
    assert parse_repo_url("https://github.com/SamuelSchmidgall/AgentClinic") == ("SamuelSchmidgall", "AgentClinic")
    from agentaudit.chunking import Source
    assert source_rel_path(Source("S4", "a/../b.py", "")) == "sources/S4/a/b.py.txt"
