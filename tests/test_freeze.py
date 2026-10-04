"""Freeze tooling and release staging, and the licence checks on shipped text."""
import csv
import json
import re
from pathlib import Path

import pytest

from agentaudit import freeze as F
from agentaudit.cli import main as cli_main
from agentaudit.items import PKG

HERE = Path(__file__).resolve()
ROOT = next((p for p in (HERE.parents[2], HERE.parents[1]) if (p / "protocol" / "protocol-v1.md").exists()), None)
needs_root = pytest.mark.skipif(ROOT is None or not (ROOT / "research" / "eligibility" / "frozen_list_v1.csv").exists(),
                                reason="study tree (protocol/, rubric/, research/) not alongside the package")


@pytest.fixture()
def staged(tmp_path):
    dest = tmp_path / "release"
    r = F.stage_release(ROOT, dest, HERE.parent, log=lambda *a: None)
    return dest, r


@needs_root
def test_manifest_covers_every_required_file(staged):
    dest, r = staged
    man = json.loads((dest / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    files = set(man["files"])
    required = {"agentaudit/perturbations.yaml", "agentaudit/items.yaml", "agentaudit/queries.yaml",
                "agentaudit/prompts/packet.txt", "agentaudit/prompts/packet_system.txt", "agentaudit/prompts/gold.txt",
                "agentaudit/samples/perturbation_design_v1.csv", "agentaudit/samples/gold_abc_items_v1.csv",
                "agentaudit/samples/gold_betterbench_criteria_v1.csv", "agentaudit/samples/gold_pins_v1.json",
                "agentaudit/perturb.py", "agentaudit/gold.py", "agentaudit/sampling.py", "agentaudit/resolve.py",
                "agentaudit/verify.py", "protocol/protocol-v1.md", "protocol/eligibility.md",
                "eligibility/frozen_list_v1.csv", "rubric/rubric-v1.md", "rubric/coding-manual-v1.0.md"}
    assert required <= files, required - files
    assert {f for f in files if f.startswith("agentaudit/prompts/")} == {f"agentaudit/prompts/{p.name}" for p in (PKG / "prompts").glob("*.txt")}
    assert man["seed"] == 20261004 and re.fullmatch(r"[0-9a-f]{64}", man["freeze_sha256"])
    # every frozen file was copied, and its hash is the hash of the copy
    for rel, h in man["files"].items():
        assert (dest / rel).exists() and F.sha256_file(dest / rel) == h
    assert F.verify_release(dest) == []


@needs_root
def test_excluded_material_is_not_staged_and_inputs_are_hash_only(staged):
    dest, _ = staged
    shipped = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    banned = {"abc_scores.csv", "abc_items.csv", "abc_benchmarks.csv", "medcheck_items.csv", "betterbench_scores.csv",
              "betterbench_items.csv", "betterbench_benchmarks.csv", "SHA256SUMS.txt"}
    for s in shipped:
        parts = s.split("/")
        assert parts[-1] not in banned and not ({"raw", "pilot", "runs", "executed", "gold", "instruments"} & set(parts)), s
    assert not any(s.endswith((".pyc", ".zip")) or "__pycache__" in s or ".egg-info" in s for s in shipped)
    man = json.loads((dest / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    assert "research/gold/abc_scores.csv" in man["inputs_not_shipped"]
    assert set(man["inputs_not_shipped"]) == set(F.HASH_ONLY)
    assert not (set(man["inputs_not_shipped"]) & shipped)
    for must in ("agentaudit/cli.py", "tests/test_gold.py", "tests/test_perturb_packet.py", "protocol/protocol-v1.md",
                 "eligibility/frozen_list_v1.csv", "rubric/rubric-v1.md", "FREEZE_MANIFEST.json"):
        assert must in shipped
    assert "protocol/osf-protocol-v0.md" not in shipped  # superseded draft


@needs_root
def test_verify_detects_changes_and_hash_is_stable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    ra = F.stage_release(ROOT, a, HERE.parent, log=lambda *x: None)
    rb = F.stage_release(ROOT, b, HERE.parent, log=lambda *x: None)
    assert ra["freeze_sha256"] == rb["freeze_sha256"]  # independent of staging time
    (a / "agentaudit" / "perturbations.yaml").write_text("changed", encoding="utf-8")
    assert F.verify_release(a) == ["changed: agentaudit/perturbations.yaml"]
    (b / "rubric" / "rubric-v1.md").unlink()
    assert F.verify_release(b) == ["missing: rubric/rubric-v1.md"]
    # the source tree was copied from, not moved
    assert (ROOT / "rubric" / "rubric-v1.md").exists() and (PKG / "perturbations.yaml").exists()


@needs_root
def test_cli_freeze_stage_and_verify(tmp_path, capsys):
    dest = tmp_path / "rel"
    extra = tmp_path / "x.txt"
    extra.write_text("extra", encoding="utf-8")
    assert cli_main(["freeze", "--root", str(ROOT), "--stage", str(dest), "--tests", str(HERE.parent),
                     "--extra", f"NOTE.txt={extra}"]) == 0
    assert re.fullmatch(r"[0-9a-f]{64}", capsys.readouterr().out.strip().splitlines()[-1])
    assert (dest / "NOTE.txt").read_text(encoding="utf-8") == "extra"  # extras are copied but not hashed
    assert "NOTE.txt" not in json.loads((dest / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))["files"]
    assert cli_main(["freeze", "--verify", str(dest)]) == 0
    assert '"intact": true' in capsys.readouterr().out
    (dest / "eligibility" / "frozen_list_v1.csv").write_text("x", encoding="utf-8")
    assert cli_main(["freeze", "--verify", str(dest)]) == 1
    assert cli_main(["freeze", "--root", str(ROOT), "--out", str(tmp_path / "m")]) == 0
    assert (tmp_path / "m" / "FREEZE_MANIFEST.json").exists()


def test_frozen_package_files_exist_and_include_new_method_code():
    names = {p.relative_to(PKG).as_posix() for p in F.frozen_package_files()}
    assert {"perturb.py", "gold.py", "sampling.py", "packet.py", "samples/gold_pins_v1.json",
            "prompts/gold.txt", "perturbations.yaml"} <= names


# ---- licence compliance: MedCheck and ABC item text must be paraphrased, never reproduced
def _words(t):
    return re.findall(r"[a-z0-9]+", t.lower())


def _longest_shared_run(a, b):
    """Length in words of the longest common contiguous word run (dynamic programming)."""
    best, prev = 0, [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


@needs_root
def test_shipped_text_does_not_reproduce_medcheck_or_abc_items():
    src = []
    for name in ("abc_items.csv", "medcheck_items.csv"):
        p = ROOT / "research" / "instruments" / name
        if not p.exists():
            pytest.skip("instrument CSVs not available")
        with open(p, encoding="utf-8-sig", newline="") as f:
            src += [(name, r["item_id"], _words(re.sub(r"\[[^\]]*\]", " ", r["item_text"]))) for r in csv.DictReader(f)]
    shipped = [PKG / "items.yaml", PKG / "perturbations.yaml", PKG / "queries.yaml", *sorted((PKG / "prompts").glob("*.txt"))]
    shipped += [ROOT / s for s, _ in F.STUDY_FILES if s.endswith(".md")]
    worst = (0, None)
    for p in shipped:
        w = _words(p.read_text(encoding="utf-8"))
        for name, iid, sw in src:
            n = _longest_shared_run(w, sw)
            if n > worst[0]:
                worst = (n, f"{p.name} vs {name} {iid}")
    # the closest paraphrase (C10 vs ABC O.g.3) shares 7 words; reproducing an item would share its whole text
    assert worst[0] < 10, worst
