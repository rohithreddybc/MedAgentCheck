"""Judge-only rerun (analysis/judge_rerun.py): transcript loading, seeded selection, re-judging, summary. The
judge call is injected, so no ollama is needed here (the live 2-transcript check is a manual run)."""
import json

import pytest

import judge_rerun as jr

MOD_SYS = "You are responsible for determining if the corrent diagnosis and the doctor diagnosis are the same disease."


def _calls(path, answer, diag="Malignant melanoma"):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"ts": 1, "model": "m", "messages": [{"role": "system", "content": "You are a doctor"},
                                                  {"role": "user", "content": "q"}], "response": "DIAGNOSIS READY: x"},
            {"ts": 2, "model": "llama3.1-8b-ctx16k",
             "messages": [{"role": "system", "content": MOD_SYS},
                          {"role": "user", "content": f"Here is the correct diagnosis: {diag}\nAre these the same?"}],
             "response": answer},
            {"ts": 3, "error": "boom", "backend": "ollama", "model": "m"}]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


@pytest.fixture()
def run_dir(tmp_path):
    eps = []
    for i, (v, ans) in enumerate([("correct", "Yes"), ("incorrect", "No"), ("correct", "Yes"), ("incorrect", "No")]):
        cp = tmp_path / "episodes" / "A" / f"MedQA_{i}_r0" / "calls.jsonl"
        _calls(cp, ans)
        eps.append({"_key": f"MedQA:{i}|A|0", "task_id": f"MedQA:{i}", "condition_name": "A", "repeat": 0,
                    "verdict": v, "driver_status": "ok", "error": None, "raw_log_path": str(cp)})
    eps.append({"_key": "MedQA:9|A|0", "task_id": "MedQA:9", "condition_name": "A", "repeat": 0, "verdict": "error",
                "driver_status": "ok", "error": "x", "raw_log_path": str(tmp_path / "none.jsonl")})
    (tmp_path / "episodes.jsonl").write_text("\n".join(json.dumps(e) for e in eps) + "\n", encoding="utf-8")
    return tmp_path


def test_verdict_rule():
    assert jr.verdict_of(" yes ") == "correct" and jr.verdict_of("Yes") == "correct"
    assert jr.verdict_of("No") == jr.verdict_of("Yes.") == jr.verdict_of("") == "incorrect"


def test_load_skips_failed_and_takes_moderator_call(run_dir):
    t = jr.load_transcripts(run_dir)
    assert len(t) == 4 and all(x["messages"][0]["content"].startswith(jr.MODERATOR_PREFIX) for x in t)
    assert {x["recorded_verdict"] for x in t} == {"correct", "incorrect"}


def test_selection_is_seeded_and_covers_both_verdicts(run_dir):
    t = jr.load_transcripts(run_dir)
    a = jr.select_transcripts(t, 2)
    assert [x["key"] for x in a] == [x["key"] for x in jr.select_transcripts(list(reversed(t)), 2)]
    assert {x["recorded_verdict"] for x in a} == {"correct", "incorrect"}
    assert len(jr.select_transcripts(t, None)) == 4


def test_rejudge_counts_flips_and_instability(run_dir):
    t = jr.load_transcripts(run_dir)
    seq = iter(["Yes", "Yes", "No", "No", "No", "No"])  # first transcript unstable; second stable
    r1 = jr.rejudge({**t[0], "recorded_verdict": "correct"}, lambda m: next(seq), 3)
    r2 = jr.rejudge({**t[1], "recorded_verdict": "incorrect"}, lambda m: next(seq), 3)
    assert r1["rejudge_verdicts"] == ["correct", "correct", "incorrect"] and not r1["all_identical"]
    assert r1["any_differs_from_recorded"] and not r1["all_match_recorded"]
    assert r2["all_identical"] and r2["all_match_recorded"]
    s = jr.summarise([r1, r2])
    assert s["transcripts"] == 2 and s["rejudgements"] == 6
    assert s["transcripts_with_unstable_rejudgements"]["k"] == 1
    assert s["rejudgements_differing_from_recorded"] == {"k": 1, "n": 6, "share": 1 / 6}


def test_run_writes_outputs_with_injected_judge(run_dir, tmp_path):
    seen = []

    def judge(messages):
        seen.append(messages)
        return "Yes" if "melanoma" in messages[1]["content"] else "No"

    out = tmp_path / "out"
    s = jr.run(run_dir, out, limit=2, repeats=3, judge_fn=judge, log=lambda *_: None)
    assert len(seen) == 6 and all(m[0]["content"].startswith(jr.MODERATOR_PREFIX) for m in seen)  # recorded prompt
    assert s["transcripts"] == 2 and s["limit"] == 2 and s["repeats"] == 3
    assert (out / "rq3_judge_rerun.csv").exists() and (out / "rq3_judge_rerun.json").exists()
    recs = [json.loads(l) for l in (out / "rq3_judge_rerun.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(recs) == 2 and all(len(r["rejudge_answers"]) == 3 for r in recs)
