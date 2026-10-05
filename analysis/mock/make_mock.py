"""Synthetic fixture for the analysis pipeline. Not real data: every number is random.

``make(root)`` writes

  <root>/scorer_run/     a scorer run directory in the real layout: coding/, verified/, resolved/ (written by the
                         scorer's own ``resolve``), perturb/ (summarised by the scorer's own ``summarise``) and
                         gold-abc/, gold-betterbench/ agreement files (from ``gold.agreement_stats``)
  <root>/rq3_runs/<bench>/episodes.jsonl
                         episode records in the layout of research/executed/runs/v3, with one incomplete task group
                         and one failed episode, so the partial-data path is exercised

Run ``python analysis/mock/make_mock.py`` to refresh the committed copy in analysis/mock/data/.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import ROOT  # noqa: E402,F401  (also puts the scorer on sys.path when it is not installed)

from agentaudit.gold import SETS, agreement_stats  # noqa: E402
from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402
from agentaudit.perturb import summarise  # noqa: E402
from agentaudit.resolve import resolve_cell, run_resolve  # noqa: E402

CODERS = {"sonnet": "anthropic", "codex": "openai", "gemini": "google"}
BENCHES = [f"mock{i:02d}" for i in range(1, 9)]
VTYPES = ("inject", "buried", "paraphrase", "deletion", "decoy")


def _wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1), encoding="utf-8", newline="\n")


def make_scorer_run(root: Path, seed: int = 1) -> Path:
    rng = random.Random(seed)
    run = Path(root) / "scorer_run"
    items = load_items()
    truth: dict[tuple[str, str], int | str] = {}
    for b in BENCHES:
        for it in ITEM_ORDER:
            p2 = 0.45 if items[it].module == "core" else 0.15
            p1 = 0.30
            r = rng.random()
            lv = 2 if r < p2 else 1 if r < p2 + p1 else 0
            if items[it].na_allowed and rng.random() < 0.06:
                lv = "NA"
            truth[(b, it)] = lv
    for b in BENCHES:
        for it in ITEM_ORDER:
            for coder, fam in CODERS.items():
                t = truth[(b, it)]
                if t == "NA":
                    raw = "NA" if rng.random() < 0.85 else 0
                else:
                    raw = t if rng.random() < 0.75 else max(0, min(2, t + rng.choice([-1, 1])))
                eff = raw
                flags = []
                if raw in (1, 2) and rng.random() < 0.08:
                    eff, flags = 0, ["unsupported"]
                contradicted = rng.random() < 0.03
                _wj(run / "coding" / b / it / f"{coder}.json",
                    {"bench": b, "item": it, "coder": coder, "family": fam, "status": "ok",
                     "evidence_scope": "packet_v3", "parsed": {"score": raw, "contradicted": contradicted}})
                _wj(run / "verified" / b / it / f"{coder}.json",
                    {"bench": b, "item": it, "coder": coder, "family": fam, "score_raw": raw, "effective": eff,
                     "n_verified": 0 if flags else 1, "flags": flags, "contradicted": contradicted,
                     "contradiction_verified": contradicted and rng.random() < 0.6, "quotes": []})
    run_resolve(run, BENCHES)
    _perturb(run, rng)
    _gold(run, rng)
    return run


def _perturb(run: Path, rng: random.Random) -> None:
    resolved = {b: json.loads((run / "resolved" / f"{b}.json").read_text(encoding="utf-8"))["cells"] for b in BENCHES}
    for v in range(8):
        bench = BENCHES[v % len(BENCHES)]
        variant = f"v{v + 1:02d}"
        # balanced assignment: each item receives one type, rotated by item index and variant number
        assign = {it: VTYPES[(i + v) % 5] for i, it in enumerate(ITEM_ORDER)}
        for coder, fam in CODERS.items():
            cells, its = {}, {}
            for it, vt in assign.items():
                base = resolved[bench][it]["final"]
                base = 0 if base == "NA" else int(base)
                if vt in ("inject", "buried", "paraphrase"):
                    exp, kind = 2, "exact"
                    lvl = 2 if rng.random() < (0.93 if vt == "inject" else 0.8) else rng.choice([0, 1])
                elif vt == "deletion":
                    exp, kind = 0, "at_most"
                    lvl = 0 if rng.random() < 0.85 else rng.choice([1, 2])
                else:
                    exp, kind = base, "at_most"
                    lvl = base if rng.random() < 0.9 else min(2, base + 1)
                cells[it] = {"variant": {"item": it, "vtype": vt, "expected": exp, "expectation": kind,
                                         "base_level": base, "s4_comment": vt == "decoy" and rng.random() < 0.5},
                             "slot": 0, "expected": exp, "expectation": kind, "base_level": base,
                             "variant_text_in_packet": True}
                its[it] = {"verification": {"score_raw": lvl, "effective": lvl}}
            _wj(run / "perturb" / variant / f"{coder}.json",
                {"variant": variant, "bench": bench, "coder": coder, "family": fam, "status": "ok",
                 "cells": cells, "items": its})
    summarise(run)


def _gold(run: Path, rng: random.Random) -> None:
    for name in ("abc", "betterbench"):
        cfg = SETS[name]
        lv = list(cfg["levels"])
        pairs_by = {c: [] for c in CODERS}
        pairs_res = []
        for b in BENCHES[:10]:
            for k in range(8):
                it = f"{name}.{k}"
                g = rng.choice(lv)
                preds = {c: (g if rng.random() < 0.7 else rng.choice(lv)) for c in CODERS}
                for c in CODERS:
                    pairs_by[c].append((b, it, g, preds[c]))
                votes = {c: {"raw": p, "effective": p, "family": CODERS[c]} for c, p in preds.items()}
                pairs_res.append((b, it, g, resolve_cell(votes, levels=cfg["top_down"])["final"]))
        res = {"set": name, "instrument": cfg["label"], "comparison_scale": lv,
               "by_coder": {c: agreement_stats(p, cfg, 200, 1) for c, p in pairs_by.items()},
               "resolved": agreement_stats(pairs_res, cfg, 200, 1)}
        _wj(run / f"gold-{name}" / "agreement" / "agreement.json", res)


def mock_scorer(task: str, predictions: list, ground_truths: list) -> dict:
    """Stand-in for the benchmark's eval.scoring.compute_all_metrics: 1.0 when every reference ICD-10 code is
    submitted, else 0.0. Only used by the tests and the mock run."""
    gt = {d["icd10"] for d in ground_truths[0]["active_diagnoses"]}
    pr = {d["icd10"] for d in predictions[0].get("active_diagnoses", [])}
    return {"weighted_problem_list_f1_neutral": 1.0 if gt <= pr else 0.0}


def make_rq3(root: Path, seed: int = 2, tasks: int = 4) -> Path:
    rng = random.Random(seed)
    base = Path(root) / "rq3_runs"
    for bench, temps in [("AgentClinic", {"A": 0.05, "B": 0.7}), ("RadABench", {"A": 0.0, "B": 0.7}),
                         ("synthetic_hospital", {"A": 0.0, "B": 0.7})]:
        rows = []
        for ti in range(tasks):
            task = f"T{ti}"
            for cond, temp in temps.items():
                p_div = 0.4 if cond == "A" else 0.8
                p_pass = 0.7 if ti % 2 == 0 else 0.2
                variants = [["ASK", "ASK", f"DIAG:x{v}"] for v in range(4)]
                for rep in range(5):
                    # leave the last task of the last benchmark incomplete, and fail one episode in AgentClinic
                    if bench == "synthetic_hospital" and ti == tasks - 1 and rep >= 3:
                        continue
                    actions = rng.choice(variants) if rng.random() < p_div else variants[0]
                    ok = rng.random() < p_pass
                    ep = {"_key": f"{task}|{cond}|{rep}", "bench": bench, "condition_name": cond, "task_id": task,
                          "condition": {"model": "mock", "temperature": temp}, "repeat": rep, "actions": actions,
                          "driver_status": "ok", "error": None}
                    if bench == "AgentClinic":
                        ep["actions_strict"] = actions + [f"salt{rng.randint(0, 2)}"]
                        ep["verdict"] = "correct" if ok else "incorrect"
                        if ti == 0 and cond == "A" and rep == 4:
                            ep.update(driver_status="failed", error="timeout", verdict=None)
                    elif bench == "RadABench":
                        ep["verdict"] = {"pass": ok, "milestone": ok, "has_error": False}
                    else:
                        # reward = 1 when the submitted ICD-10 code equals the reference code (toy criterion, see
                        # mock_scorer); a few reported rewards are deliberately wrong, and one episode has no reference
                        sub = {"active_diagnoses": [{"icd10": "A00" if ok else "B99", "acuity": "acute"}],
                               "chronic_conditions": []}
                        ref = {"task": "patient_diagnosis",
                               "ground_truth": {"active_diagnoses": [{"icd10": "A00", "acuity": "acute"}],
                                                "chronic_conditions": []}}
                        reported = 1.0 if ok else 0.0
                        if ti == 1 and cond == "A" and rep == 2:
                            reported = 1.0 - reported  # grader/state disagreement
                        if ti == 0 and cond == "B" and rep == 0:
                            ref = None  # state missing
                        ep["verdict"] = {"done": True, "reward": reported, "pass": reported >= 0.5,
                                         "metrics": {"n_neutral_predictions": 0}}
                        ep["final_state"] = {"env_state": {"reward": reported}, "reference": ref, "submission": sub}
                    rows.append(ep)
        p = base / bench / "episodes.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8", newline="\n")
    return base


def make(root: Path) -> dict[str, Path]:
    return {"scorer_run": make_scorer_run(root), "rq3_runs": make_rq3(root)}


if __name__ == "__main__":
    out = HERE / "data"
    print(make(out))
