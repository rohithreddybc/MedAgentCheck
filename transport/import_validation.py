"""Import subagent answers for the three validation runs as stored responses of coder "sonnet".

Same principle as import_responses.py: the frozen package's own scoring function runs with a replay backend that returns
the stored answer where ClaudeHeadlessBackend would have returned the CLI's text, so storage, JSON parsing and quote
verification are the package's own code. Model id "claude-sonnet-5-5 via Claude Code subagent", transport "subagent".
A prompt that the package renders now but that was not exported (changed packet, changed plan) has no replay entry and
is reported as pending, never scored.

  gold     python import_validation.py --mode gold --set abc|betterbench [--bench KEY ...] [--force]
           responses_gold_<set>/<bench>.json  -> audit/gold_abc|gold_bb/gold-<set>/gold_scoring/<bench>/sonnet.json
           (gold.score_gold; verification inside)
  perturb  python import_validation.py --mode perturb [--variant v01 ...] [--force]
           responses_perturb/<variant>.json   -> audit/perturb/perturb/<variant>/sonnet.json
           (perturb.run_perturb_variants over the variants that have a response; perturb/plan.json describes the variants of the
           last call, so finish with one call that has all 40 responses)
           --coder codex (perturb only): responses_perturb_codex/<variant>.json + .meta.json (written by run_codex_prompts.py;
           model id and timestamp from the meta file) -> audit/perturb/perturb/<variant>/codex.json, coder spec from
           audit/coders_codex55.yaml, then summary.json / summary.csv for all variants with records (both coders + RESOLVED)
  retest   python import_validation.py --mode retest [--bench NAME ...] [--force] [--coder codex]
           --coder codex: responses_retest_codex/<bench>.json + .meta.json (run_codex_retest.py) -> audit/retest/scoring/<bench>/codex/...
           (existing codex retest records are not rescored); afterwards (both coders) the retest run is resolved and retest_agreement.json rewritten for all 10 drawn benchmarks
           responses_retest/<bench>.json      -> audit/retest/scoring/<bench>/sonnet/... + coding/ + verified/
           (packet_score.score_packet with the original run's cap and item groups, then the package's verification)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_validation import (AUDIT, CODER, FROZEN, GOLD_RUN, PERTURB_RUN, cap_for_coder,  # noqa: E402
                               prepare_perturb_run, slug_of_frozen)
from agentaudit.backends import BackendError, Response  # noqa: E402
from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.gold import find_research_dir, gold_result_path, gold_run_dir, items_for_set, load_instrument, score_gold  # noqa: E402
from agentaudit.packet_score import score_packet  # noqa: E402
from agentaudit.perturb import perturb_variant_path, plan_variants, run_perturb_variants  # noqa: E402
from agentaudit.prompts import prompt_hash  # noqa: E402
from agentaudit.retest import prepare_retest_packet, retest_dir  # noqa: E402
from agentaudit.sampling import load_frozen_list, read_perturbation_design  # noqa: E402
from agentaudit.items import PKG  # noqa: E402
from agentaudit.util import read_json, write_json  # noqa: E402

MODEL_ID = "claude-sonnet-5-5 via Claude Code subagent"
TRANSPORT = "subagent"


class HashReplayBackend:
    """prompt sha256 -> stored answer. A prompt without an entry is a BackendError (nothing is stored for it)."""

    def __init__(self, answers: dict[str, str]):
        self.answers = answers

    def complete(self, system: str, prompt: str) -> Response:
        h = prompt_hash(prompt)
        if h not in self.answers:
            raise BackendError("no exported prompt / response for this rendered prompt (stale export or no response file)")
        return Response(text=self.answers[h], model_id=MODEL_ID, usage={}, raw=None,
                        meta={"transport": TRANSPORT, "attempts": 1})


def collect(prompts_dir: Path, responses_dir: Path, keys: list[str] | None) -> tuple[dict[str, str], list[str], list[str]]:
    """({prompt_sha256: answer text}, imported keys, pending keys)."""
    answers, have, pending = {}, [], []
    for d in sorted(p for p in prompts_dir.iterdir() if (p / "meta.json").exists()) if prompts_dir.exists() else []:
        if keys and d.name not in keys:
            continue
        rp = responses_dir / f"{d.name}.json"
        if rp.exists():
            answers[read_json(d / "meta.json")["prompt_sha256"]] = rp.read_text(encoding="utf-8")
            have.append(d.name)
        else:
            pending.append(d.name)
    return answers, have, pending


def patch(path: Path, key: str, response_file: str) -> None:
    if path.exists():
        r = read_json(path)
        if any(a.get("model_id") == MODEL_ID for a in r.get("attempts", [])) or r.get("model_id") == MODEL_ID:
            r["transport"] = TRANSPORT
            r["response_file"] = response_file
            write_json(path, r)


def do_gold(set_name: str, run: Path, keys, force: bool) -> int:
    answers, have, pending = collect(HERE / f"prompts_gold_{set_name}", HERE / f"responses_gold_{set_name}", keys)
    print(f"gold {set_name}: {len(have)} responses, {len(pending)} pending")
    spec = load_coders()[CODER]
    instr = load_instrument(set_name, find_research_dir())
    ids = items_for_set(set_name)
    backend = HashReplayBackend(answers)
    rc = 0
    for b in have:
        s = score_gold(run, set_name, b, CODER, spec, backend, ids, instr, cap_tokens=cap_for_coder(), force=force)
        print(s)
        patch(gold_result_path(gold_run_dir(run, set_name), b, CODER), b, f"transport/responses_gold_{set_name}/{b}.json")
        rc = 2 if s["status"] not in ("ok", "already_done") else rc
    return rc


class MetaReplayBackend:
    """Replay for a coder whose answers carry their own model id / timestamp (``<variant>.meta.json``)."""

    def __init__(self, answers: dict[str, tuple[str, dict]]):
        self.answers = answers

    def complete(self, system: str, prompt: str) -> Response:
        h = prompt_hash(prompt)
        if h not in self.answers:
            raise BackendError("no exported prompt / response for this rendered prompt (stale export or no response file)")
        text, m = self.answers[h]
        return Response(text=text, model_id=m["model_id"], usage={}, raw=None,
                        meta={**(m.get("backend_meta") or {}), "transport": "codex exec", "source": m.get("source"),
                              "attempts": 1})


def do_perturb_codex(run: Path, keys, force: bool) -> int:
    from agentaudit.perturb import summarise

    prompts, resp = HERE / "prompts_perturb", HERE / "responses_perturb_codex"
    answers, metas, have = {}, {}, []
    for d in sorted(p for p in prompts.iterdir() if (p / "meta.json").exists()):
        if keys and d.name not in keys:
            continue
        rp, mp = resp / f"{d.name}.json", resp / f"{d.name}.meta.json"
        if not (rp.exists() and mp.exists()):
            continue
        m = read_json(mp)
        h = read_json(d / "meta.json")["prompt_sha256"]
        if m["prompt_sha256"] != h:
            print(f"{d.name}: response was produced for a different prompt; skipped")
            continue
        answers[h] = (rp.read_bytes().decode("utf-8"), m)
        metas[d.name] = m
        have.append(d.name)
    print(f"perturb codex: {len(have)} responses")
    frozen = load_frozen_list(FROZEN)
    prepare_perturb_run(run, AUDIT, frozen)
    design = read_perturbation_design(PKG / "samples" / "perturbation_design_v1.csv")
    plan = plan_variants(run, design, frozen, use_base=(run / "resolved").exists(), only_variants=have)
    spec = load_coders(str(AUDIT / "coders_codex55.yaml"))["codex"]
    s = run_perturb_variants(run, plan, {"codex": (spec, MetaReplayBackend(answers))}, force=force)
    print(s)
    for v in have:  # keep the CLI's model id / timestamp on the records
        p = perturb_variant_path(run, v, "codex")
        if not p.exists():
            continue
        r = read_json(p)
        m = metas[v]
        r["transport"] = "codex exec (frozen CodexHeadlessBackend, identical prompt)"
        r["response_file"] = f"transport/responses_perturb_codex/{v}.json"
        r["prompt_source"] = f"transport/prompts_perturb/{v}"
        r["answer_source"] = m.get("source")
        r["timestamp"] = m["timestamp"]
        for a in r.get("attempts", []):
            a["timestamp"] = m["timestamp"]
        for c in r.get("cells", {}).values():
            c["timestamp"] = m["timestamp"]
        write_json(p, r)
    allv = sorted(p.name for p in prompts.iterdir() if (p / "meta.json").exists())
    summ = summarise(run, allv)
    print({"n_rows": summ["n_rows"], "coders": list(summ["by_coder"])})
    return 2 if (s["blocked"] or s["failed"]) else 0


def do_perturb(run: Path, keys, force: bool) -> int:
    answers, have, pending = collect(HERE / "prompts_perturb", HERE / "responses_perturb", keys)
    print(f"perturb: {len(have)} responses, {len(pending)} pending")
    frozen = load_frozen_list(FROZEN)
    prepare_perturb_run(run, AUDIT, frozen)
    use_base = (run / "resolved").exists()
    design = read_perturbation_design(PKG / "samples" / "perturbation_design_v1.csv")
    plan = plan_variants(run, design, frozen, use_base=use_base, only_variants=have)
    s = run_perturb_variants(run, plan, {CODER: (load_coders()[CODER], HashReplayBackend(answers))}, force=force)
    print(s)
    for v in have:
        patch(perturb_variant_path(run, v, CODER), v, f"transport/responses_perturb/{v}.json")
    return 2 if (s["blocked"] or s["failed"]) else 0


def finalize_retest(audit: Path, n_boot: int = 2000) -> dict:
    """What `agentaudit retest --compare-only` does (resolve the retest run, then compare_retest), but with the frozen id to
    packet directory mapping taken from the manifests, so that all 10 drawn benchmarks are included (the package's mapping
    leaves out diaggym-diagbench and synthetic-hospital: underscore slugs). The package functions are unchanged; only
    `agentaudit.perturb.map_bench_dirs` is replaced for the duration of the call."""
    import agentaudit.perturb as ap
    from agentaudit.resolve import run_resolve
    from agentaudit.retest import compare_retest, plan_retest

    frozen = load_frozen_list(FROZEN)
    slugs = slug_of_frozen(audit)
    orig = ap.map_bench_dirs
    ap.map_bench_dirs = lambda run, rows: {r["id"]: slugs[r["id"]] for r in rows if r["id"] in slugs}
    try:
        rrun = retest_dir(audit)
        plan = plan_retest(audit, frozen)
        benches = [d["packet_dir"] for d in plan["drawn"] if d["packet_dir"] and (rrun / "coding" / d["packet_dir"]).exists()]
        run_resolve(rrun, benches)
        r = compare_retest(audit, frozen, n_boot=n_boot)
    finally:
        ap.map_bench_dirs = orig
    for c, st in r["coders"].items():
        print({"coder": c, **{k: st[k] for k in ("n_cells", "n_benchmarks", "raw_agreement", "alpha_ordinal", "alpha_ci95",
                                                  "weighted_kappa_quadratic", "same_model_id")}})
    print({"resolved": r["resolved"], "benchmarks": benches})
    return r


def do_retest_codex(audit: Path, keys, force: bool) -> int:
    """Codex retest answers (run_codex_retest.py) for the benchmarks the CLI retest skipped. Scored with the package's
    score_packet and the coder's own original cap / groups; benchmarks that already have a codex retest record are untouched."""
    prompts, resp = HERE / "prompts_retest", HERE / "responses_retest_codex"
    spec = load_coders(str(AUDIT / "coders_codex55.yaml"))["codex"]
    rrun = retest_dir(audit)
    rc = 0
    for d in sorted(p for p in prompts.iterdir() if (p / "meta.json").exists()):
        b = d.name
        if keys and b not in keys:
            continue
        rp, mp = resp / f"{b}.json", resp / f"{b}.meta.json"
        if not (rp.exists() and mp.exists()):
            continue
        m = read_json(mp)
        h = read_json(d / "meta.json")["prompt_sha256"]
        if m["prompt_sha256"] != h:
            print(f"retest codex {b}: response was produced for a different prompt; skipped")
            continue
        omp = audit / "scoring" / b / "codex" / "packet_manifest.json"
        if not omp.exists():
            print(f"retest codex {b}: no original codex results in the audit run; skipped")
            continue
        om = read_json(omp)
        prepare_retest_packet(audit, b)
        backend = MetaReplayBackend({h: (rp.read_bytes().decode("utf-8"), m)})
        s = score_packet(rrun, b, "codex", spec, backend, groups=len(om["groups"]), cap_tokens=om["cap_tokens"], force=force)
        nman = read_json(rrun / "scoring" / b / "codex" / "packet_manifest.json")
        s["same_rendered_packet"] = nman["rendered_packet_sha256"] == om["rendered_packet_sha256"]
        print(s)
        files = [rrun / "scoring" / b / "codex" / "group1.json"] + [rrun / "coding" / b / i / "codex.json" for i in s.get("done", [])]
        for f in files:
            if f.exists():
                r = read_json(f)
                r["transport"] = "codex exec (frozen CodexHeadlessBackend, identical prompt)"
                r["response_file"] = f"transport/responses_retest_codex/{b}.json"
                write_json(f, r)
        if s["failed"] or s["blocked"] or not s["same_rendered_packet"]:
            rc = 2
    return rc


def do_retest(audit: Path, keys, force: bool) -> int:
    answers, have, pending = collect(HERE / "prompts_retest", HERE / "responses_retest", keys)
    print(f"retest: {len(have)} responses, {len(pending)} pending")
    spec = load_coders()[CODER]
    rrun = retest_dir(audit)
    backend = HashReplayBackend(answers)
    rc = 0
    for b in have:
        omp = audit / "scoring" / b / CODER / "packet_manifest.json"
        if not omp.exists():
            print(f"retest {b}: no original sonnet results in the audit run; skipped (as run_retest would)")
            continue
        om = read_json(omp)
        prepare_retest_packet(audit, b)
        s = score_packet(rrun, b, CODER, spec, backend, groups=len(om["groups"]), cap_tokens=om["cap_tokens"], force=force)
        nman = read_json(rrun / "scoring" / b / CODER / "packet_manifest.json")
        s["same_rendered_packet"] = nman["rendered_packet_sha256"] == om["rendered_packet_sha256"]
        print(s)
        patch(rrun / "scoring" / b / CODER / "group1.json", b, f"transport/responses_retest/{b}.json")
        for iid in s.get("done", []):
            patch(rrun / "coding" / b / iid / f"{CODER}.json", b, f"transport/responses_retest/{b}.json")
        if s["failed"] or s["blocked"] or not s["same_rendered_packet"]:
            rc = 2
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", required=True, choices=["gold", "perturb", "retest"])
    ap.add_argument("--set", choices=["abc", "betterbench"])
    ap.add_argument("--run", help="run directory (default: audit/gold_abc | audit/gold_bb | audit/perturb | audit for retest, whose results go to <run>/retest)")
    ap.add_argument("--bench", action="append", help="benchmark key / variant id (repeatable); default: all with a response")
    ap.add_argument("--variant", action="append")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--coder", choices=["sonnet", "codex"], default="sonnet", help="perturb and retest modes (default sonnet)")
    a = ap.parse_args()
    if a.mode == "gold":
        if not a.set:
            ap.error("--mode gold needs --set")
        return do_gold(a.set, Path(a.run) if a.run else GOLD_RUN[a.set], a.bench, a.force)
    if a.mode == "perturb" and a.coder == "codex":
        return do_perturb_codex(Path(a.run) if a.run else PERTURB_RUN, a.variant or a.bench, a.force)
    if a.mode == "perturb":
        return do_perturb(Path(a.run) if a.run else PERTURB_RUN, a.variant or a.bench, a.force)
    if a.mode == "retest" and a.coder == "codex":
        rc = do_retest_codex(Path(a.run) if a.run else AUDIT, a.bench, a.force)
    else:
        rc = do_retest(Path(a.run) if a.run else AUDIT, a.bench, a.force)
    finalize_retest(Path(a.run) if a.run else AUDIT)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
