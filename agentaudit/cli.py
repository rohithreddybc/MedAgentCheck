"""agentaudit command line. Every stage writes under the run directory given by --out."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .items import PKG, parse_item_list
from .util import utcnow, write_json


def _benches(run: Path, arg: list[str] | None) -> list[str]:
    if arg:
        return arg
    base = run / "packets"
    return sorted(p.name for p in base.iterdir()) if base.exists() else []


def cmd_packet(a) -> int:
    from .packet import build_packet, load_manifest

    man = load_manifest(a.manifest)
    m = build_packet(man, Path(a.out), Path(a.cache_dir) if a.cache_dir else None)
    print(json.dumps({"name": m["name"], "files": m["n_files"], "chunks": m["n_chunks"],
                      "chunk_tokens": m["total_chunk_tokens"], "s5_chunks": m["n_s5_chunks"],
                      "packet_sha256": m["packet_sha256"]}, indent=2))
    return 0


def cmd_retrieve(a) -> int:
    from .retrieve import run_retrieval

    run = Path(a.out)
    for b in _benches(run, a.bench):
        r = run_retrieval(run, b, parse_item_list(a.items))
        for it, rec in r.items():
            print(f"{b} {it}: {len(rec['chunks'])} chunks, {rec['total_tokens']} tokens")
    return 0


def cmd_tag(a) -> int:
    from .coders import load_coders, make_backend
    from .tag import TAG_MAX_TOKENS, build_item_sets, run_tagging

    run = Path(a.out)
    coders = load_coders(a.coders_file)
    rc = 0
    if not a.select_only:
        for tname in a.tagger:
            spec = dict(coders[tname])
            if a.model:
                spec["model"] = a.model
            if spec["backend"] == "openai":
                spec["max_tokens"] = TAG_MAX_TOKENS
            backend = make_backend(spec, state_dir=run / "state", throttle_state=a.throttle_state, base_url=a.base_url)
            for b in _benches(run, a.bench):
                s = run_tagging(run, b, tname, spec, backend, window_tokens=a.window_tokens, force=a.force,
                                max_calls=a.max_calls)
                print(json.dumps({k: v for k, v in s.items()}))
                if s["blocked"] or s["failed"] or not s["complete"]:
                    rc = 2
    if a.select or a.select_only:
        sel = a.select_taggers.split(",") if a.select_taggers else a.tagger
        for b in _benches(run, a.bench):
            r = build_item_sets(run, b, sel, parse_item_list(a.items), sets_name=a.sets_name,
                                bm25_filler=not a.no_filler)
            n_tr = sum(1 for x in r.values() if x["truncated"])
            print(f"{b}: wrote {len(r)} item chunk sets to {a.sets_name}/ ({n_tr} truncated by the cap)")
    return rc


def cmd_code(a) -> int:
    from .coders import load_coders, make_backend
    from .coding import run_coding

    run = Path(a.out)
    coders = load_coders(a.coders_file)
    rc = 0
    for cname in a.coder:
        spec = coders[cname]
        if a.model:
            spec = dict(spec, model=a.model)
        backend = make_backend(spec, state_dir=run / "state", throttle_state=a.throttle_state, base_url=a.base_url)
        for b in _benches(run, a.bench):
            s = run_coding(run, b, cname, spec, backend, parse_item_list(a.items), force=a.force)
            print(json.dumps({"coder": cname, "bench": b, "done": len(s["done"]), "skipped": len(s["skipped"]),
                              "failed": s["failed"], "blocked": s["blocked"]}))
            if s["blocked"] or s["failed"]:
                rc = 2
    return rc


def cmd_score_packet(a) -> int:
    from .coders import load_coders, make_backend
    from .packet_score import score_packet

    run = Path(a.out)
    coders = load_coders(a.coders_file)
    rc = 0
    for cname in a.coder:
        spec = coders[cname]
        if a.model:
            spec = dict(spec, model=a.model)
        backend = make_backend(spec, state_dir=run / "state", throttle_state=a.throttle_state, base_url=a.base_url)
        groups = a.groups or int(spec.get("groups", 1))
        for b in _benches(run, a.bench):
            s = score_packet(run, b, cname, spec, backend, groups=groups, cap_tokens=a.cap_tokens, force=a.force, dry_run=a.dry_run)
            print(json.dumps(s))
            if s["blocked"] or s["failed"]:
                rc = 2
    return rc


def cmd_doctor(a) -> int:
    from .doctor import run_doctor

    rows = run_doctor(do_ping=a.ping)
    for r in rows:
        print(f"{r['backend']:8s} family={r['family']:10s} {'LIVE' if r['live'] else 'not live':8s} {r['detail']}"
              + (f" | ping: {r['ping']}" if "ping" in r else ""))
    print(json.dumps(rows) if a.json else f"live backends: {[r['backend'] for r in rows if r['live']] or 'none'}")
    return 0 if any(r["live"] for r in rows) else 1


def cmd_verify(a) -> int:
    from .verify import run_verify

    run = Path(a.out)
    for b in _benches(run, a.bench):
        res = run_verify(run, b, parse_item_list(a.items) if a.items else None)
        n_un = sum(1 for r in res if "unsupported" in r["flags"])
        print(f"{b}: verified {len(res)} cells; {n_un} unsupported 1/2 scores")
    return 0


def cmd_resolve(a) -> int:
    from .resolve import run_resolve

    run = Path(a.out)
    s = run_resolve(run, _benches(run, a.bench), require_cross_family=not a.no_cross_family)
    print(json.dumps(s, indent=2))
    return 0


def cmd_agree(a) -> int:
    from .agree import run_agree

    run = Path(a.out)
    r = run_agree(run, _benches(run, a.bench), n_boot=a.n_boot)
    for name, res in r["sets"].items():
        print(name, json.dumps(res["overall"]))
    return 0


def _coder_caps(coders: dict, names: list[str]) -> dict:
    return {n: coders[n].get("max_packet_tokens") for n in names}


def cmd_perturb(a) -> int:
    from .coders import load_coders, make_backend
    from .perturb import (VARIANT_TYPES, estimate_cells, plan, plan_packet_cells, run_perturb, run_perturb_packet,
                          summarise)
    from .sampling import N_PER_CELL, load_frozen_list, read_perturbation_sample

    run = Path(a.out)
    types = tuple(a.variants.split(",")) if a.variants else VARIANT_TYPES
    items = parse_item_list(a.items)
    if a.mode == "retrieval":  # ablation path of the retired retrieval design
        benches = _benches(run, a.bench)
        if a.summarise:
            s = summarise(run, benches)
            print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=2))
            return 0
        if a.plan_only:
            for b in benches:
                for v in plan(run, b, items, types):
                    print(b, json.dumps(v))
            return 0
        coders = load_coders(a.coders_file)
        cb = {c: (coders[c], make_backend(coders[c], state_dir=run / "state", throttle_state=a.throttle_state,
                                          base_url=a.base_url)) for c in a.coder}
        for b in benches:
            s = run_perturb(run, b, items, cb, types, force=a.force)
            print(json.dumps({"bench": b, **{k: v for k, v in s.items()}}))
        summarise(run, benches)
        return 0
    if a.summarise:
        pdir = run / "perturb"
        names = sorted(p.name for p in pdir.iterdir() if p.is_dir()) if pdir.exists() else []
        s = summarise(run, names)
        print(json.dumps({k: v for k, v in s.items() if k != "rows"}, indent=2))
        return 0
    sample = read_perturbation_sample(a.sample or PKG / "samples" / "perturbation_sample_v1.csv")
    frozen = load_frozen_list(a.frozen_list)
    cells = plan_packet_cells(run, sample, frozen, items, types, a.n_per_cell or N_PER_CELL,
                              use_base=not a.no_base, only_bench=a.bench)
    coders = load_coders(a.coders_file)
    names = a.coder or ["sonnet", "codex", "gemini"]
    if a.plan_only or a.dry_run:
        by: dict[str, int] = {}
        for c in cells:
            by[c["vtype"]] = by.get(c["vtype"], 0) + 1
        est = estimate_cells(run, cells, _coder_caps(coders, names)) if cells else {}
        print(json.dumps({"cells": len(cells), "by_type": by, "estimate_per_coder": est}, indent=2))
        if a.plan_only:
            for c in cells:
                print(json.dumps(c))
            return 0
    cb = {c: (coders[c], None if a.dry_run else make_backend(coders[c], state_dir=run / "state",
                                                            throttle_state=a.throttle_state, base_url=a.base_url))
          for c in names}
    s = run_perturb_packet(run, cells, cb, force=a.force, dry_run=a.dry_run)
    print(json.dumps(s))
    if not a.dry_run:
        summarise(run, sorted({c["bench"] for c in cells}))
    return 2 if (s["blocked"] or s["failed"]) else 0


def cmd_sample(a) -> int:
    from .gold import find_research_dir, write_gold_item_lists
    from .sampling import SEED, build_perturbation_sample, load_frozen_list, write_perturbation_sample

    ids = [r["id"] for r in load_frozen_list(a.frozen_list)]
    rows = build_perturbation_sample(ids, seed=a.seed or SEED)
    out = Path(a.out_dir) if a.out_dir else PKG / "samples"
    write_perturbation_sample(out / "perturbation_sample_v1.csv", rows)
    info = {"benchmarks": len(ids), "perturbation_rows": len(rows)}
    if not a.no_gold_lists:
        info.update(write_gold_item_lists(find_research_dir(a.research_dir)))
    print(json.dumps(info))
    return 0


def cmd_gold(a) -> int:
    from .coders import load_coders, make_backend
    from .gold import (PINS_PATH, build_gold_packets, estimate_gold, find_research_dir, gold_run_dir, items_for_set,
                       load_instrument, load_pins, pin_set, run_gold_agree, save_pins, score_gold)

    run = Path(a.out)
    rdir = find_research_dir(a.research_dir)
    steps = {s for s in ("pin", "packets", "score", "agree") if getattr(a, s)} or {"pin", "packets", "score", "agree"}
    pins_path = Path(a.pins) if a.pins else PINS_PATH
    pins = load_pins(pins_path)
    rc = 0
    if "pin" in steps and (a.refresh_pins or a.set not in pins["sets"]):
        pins["sets"][a.set] = pin_set(a.set, rdir)
        pins.setdefault("pinned_utc", {})[a.set] = utcnow()
        save_pins(pins, pins_path)
        bad = {k: [v["repo"].get("error"), v["arxiv"].get("error")] for k, v in pins["sets"][a.set].items()
               if v["repo"].get("status") == "error" or v["arxiv"].get("status") == "error"}
        print(json.dumps({"pinned": len(pins["sets"][a.set]), "errors": bad}))
        rc = 2 if bad else rc
    if a.set not in pins["sets"]:
        print("no pins for this set; run with --pin first")
        return 2
    only = a.bench
    if "packets" in steps and not a.dry_run:
        r = build_gold_packets(run, a.set, pins, only, allow_large=a.allow_large)
        print(json.dumps({"packets": {k: (v if k == "failed" else len(v)) for k, v in r.items()}}))
        rc = 2 if r["failed"] else rc
    coders = load_coders(a.coders_file)
    if "score" in steps and (a.coder or a.dry_run):
        instr = load_instrument(a.set, rdir)
        ids = items_for_set(a.set)
        names = a.coder or ["sonnet", "codex", "gemini"]
        if a.dry_run:
            print(json.dumps({"estimate_per_coder": estimate_gold(run, a.set, pins, _coder_caps(coders, names)),
                              "items": len(ids)}))
        grun = gold_run_dir(run, a.set)
        keys = [k for k in sorted(pins["sets"][a.set]) if (not only or k in only)
                and (grun / "packets" / k / "manifest.json").exists()]
        for cname in names:
            spec = coders[cname]
            backend = None if a.dry_run else make_backend(spec, state_dir=run / "state", throttle_state=a.throttle_state)
            for k in keys:
                s = score_gold(run, a.set, k, cname, spec, backend, ids, instr, cap_tokens=a.cap_tokens,
                               force=a.force, dry_run=a.dry_run)
                print(json.dumps(s))
                if s["status"] in ("blocked", "failed"):
                    rc = 2
                if s["status"] == "blocked":
                    break
    if "agree" in steps and not a.dry_run:
        res = run_gold_agree(run, a.set, rdir, n_boot=a.n_boot)
        keep = ("n_cells", "raw_agreement", "cohen_kappa", "weighted_kappa_quadratic")
        allc = {**res["by_coder"], **({"RESOLVED": res["resolved"]} if res["resolved"] else {})}
        print(json.dumps({"agreement": {c: {k: v for k, v in s.items() if k in keep} for c, s in allc.items()}}))
    return rc


def cmd_report(a) -> int:
    from .report import run_report

    run = Path(a.out)
    for p in run_report(run, _benches(run, a.bench)):
        print(p)
    return 0


def cmd_freeze(a) -> int:
    from .freeze import build_manifest, find_root, stage_release, verify_release

    if a.verify:
        bad = verify_release(Path(a.verify))
        print(json.dumps({"intact": not bad, "problems": bad}))
        return 1 if bad else 0
    root = find_root(a.root)
    if a.stage:
        extra = {rel: Path(src) for rel, src in (e.split("=", 1) for e in a.extra or [])}
        r = stage_release(root, Path(a.stage), Path(a.tests) if a.tests else None, extra)
        print(r["freeze_sha256"])
        return 0
    man = build_manifest(root)
    write_json(Path(a.out) / "FREEZE_MANIFEST.json", man)
    print(man["freeze_sha256"])
    return 0


def cmd_items(a) -> int:
    from .items import ITEM_ORDER, load_items

    it = load_items()
    for i in ITEM_ORDER:
        print(f"{i}\t{it[i].title}\tNA={'yes' if it[i].na_allowed else 'no'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentaudit", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, bench=True, items=True):
        sp.add_argument("--out", required=True, help="run directory (all outputs go here)")
        if bench:
            sp.add_argument("--bench", action="append", help="benchmark name (repeatable); default: all packets")
        if items:
            sp.add_argument("--items", help="comma list, e.g. A1,C6 (default: all 25)")

    sp = sub.add_parser("packet", help="build an evidence packet from a manifest.yaml")
    sp.add_argument("manifest")
    sp.add_argument("--out", required=True)
    sp.add_argument("--cache-dir")
    sp.set_defaults(fn=cmd_packet)

    sp = sub.add_parser("retrieve", help="BM25 item-targeted retrieval")
    common(sp)
    sp.set_defaults(fn=cmd_retrieve)

    sp = sub.add_parser("tag", help="exhaustive evidence tagging (stage 2a) and tag-based item chunk sets")
    common(sp)
    sp.add_argument("--tagger", action="append", required=True, help="gpt-oss-120b | sonnet | opus (repeatable)")
    sp.add_argument("--coders-file")
    sp.add_argument("--model", help="override the model id for the tagger")
    sp.add_argument("--base-url")
    sp.add_argument("--throttle-state", help="path of a shared throttle state file")
    sp.add_argument("--window-tokens", type=int, help="override the window size (default 5,000 gpt-oss; 150,000 Claude)")
    sp.add_argument("--max-calls", type=int, help="stop after this many backend calls per benchmark")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--select", action="store_true", help="after tagging, write the item chunk sets")
    sp.add_argument("--select-only", action="store_true", help="skip tagging; build item chunk sets from existing tags")
    sp.add_argument("--select-taggers", help="comma list of taggers whose tags are unioned (default: --tagger)")
    sp.add_argument("--sets-name", default="retrieval", help="directory under --out for the sets (default retrieval)")
    sp.add_argument("--no-filler", action="store_true", help="tags only, no BM25 filler")
    sp.set_defaults(fn=cmd_tag)

    sp = sub.add_parser("code", help="code items with one or more coders")
    common(sp)
    sp.add_argument("--coder", action="append", required=True, help="gpt-oss-120b | sonnet | opus | name from --coders-file")
    sp.add_argument("--coders-file")
    sp.add_argument("--model", help="override the model id for the coder")
    sp.add_argument("--base-url", help="override the OpenAI-compatible base url")
    sp.add_argument("--throttle-state", help="path of a shared throttle state file (default: <out>/state/)")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_code)

    sp = sub.add_parser("score-packet", help="v3: whole-packet scoring, one call per (benchmark, coder)")
    common(sp, items=False)
    sp.add_argument("--coder", action="append", required=True,
                    help="sonnet | opus | codex | gemini | mistral | name from --coders-file")
    sp.add_argument("--coders-file")
    sp.add_argument("--model", help="override the model id for the coder")
    sp.add_argument("--base-url")
    sp.add_argument("--throttle-state", help="path of a shared throttle state file (openai-compatible backends)")
    sp.add_argument("--groups", type=int, choices=[1, 2, 3], help="fixed item groups (default 1: all 25 in one call)")
    sp.add_argument("--cap-tokens", type=int, help="packet cap (default 150,000; mistral 100,000)")
    sp.add_argument("--dry-run", action="store_true", help="write the packet manifest and print prompt sizes; no backend call")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_score_packet)

    sp = sub.add_parser("doctor", help="report which backends are live (no quota spent unless --ping)")
    sp.add_argument("--ping", action="store_true", help="also send a 1-token request to each backend that passes")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_doctor)

    sp = sub.add_parser("verify", help="verify quotes against chunks")
    common(sp)
    sp.set_defaults(fn=cmd_verify)

    sp = sub.add_parser("resolve", help="apply the frozen resolution rule")
    common(sp, items=False)
    sp.add_argument("--no-cross-family", action="store_true", help="package users with one model family only")
    sp.set_defaults(fn=cmd_resolve)

    sp = sub.add_parser("agree", help="Krippendorff alpha (ordinal)")
    common(sp, items=False)
    sp.add_argument("--n-boot", type=int, default=2000)
    sp.set_defaults(fn=cmd_agree)

    sp = sub.add_parser("perturb", help="perturbation validation (v3: whole-packet variants, single-item prompts)")
    sp.add_argument("--out", required=True, help="run directory (needs the packets and the base audit results)")
    sp.add_argument("--bench", action="append", help="packet directory name or frozen id (repeatable)")
    sp.add_argument("--items", help="comma list, e.g. A1,C6 (default: all 25)")
    sp.add_argument("--coder", action="append", help="default sonnet, codex, gemini")
    sp.add_argument("--coders-file")
    sp.add_argument("--base-url")
    sp.add_argument("--throttle-state")
    sp.add_argument("--variants", help="comma list of inject,buried,paraphrase,deletion,decoy")
    sp.add_argument("--mode", choices=["packet", "retrieval"], default="packet",
                    help="packet = v3 (default); retrieval = the retired retrieval design (ablation)")
    sp.add_argument("--sample", help="perturbation sample file (default: the frozen agentaudit/samples file)")
    sp.add_argument("--frozen-list", help="frozen benchmark list CSV (required in packet mode)")
    sp.add_argument("--n-per-cell", type=int, help="variants per item per type (default 8)")
    sp.add_argument("--no-base", action="store_true",
                    help="plain seeded draw without base-result eligibility (no deletion cells)")
    sp.add_argument("--plan-only", action="store_true", help="print the selected cells and the call and token estimate")
    sp.add_argument("--dry-run", action="store_true", help="build every variant packet and prompt; no backend call")
    sp.add_argument("--summarise", action="store_true")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_perturb)

    sp = sub.add_parser("sample", help="write the seeded samples (perturbation sample, gold item lists)")
    sp.add_argument("--frozen-list", required=True)
    sp.add_argument("--out-dir", help="default: agentaudit/samples")
    sp.add_argument("--seed", type=int)
    sp.add_argument("--research-dir", help="directory with gold/ and instruments/ (for the gold item lists)")
    sp.add_argument("--no-gold-lists", action="store_true")
    sp.set_defaults(fn=cmd_sample)

    sp = sub.add_parser("gold", help="validate against published human gold (ABC, BetterBench)")
    sp.add_argument("--set", required=True, choices=["abc", "betterbench"])
    sp.add_argument("--out", required=True, help="run directory; outputs go to <out>/gold-<set>/")
    sp.add_argument("--research-dir", help="directory with gold/ and instruments/ (not part of the release)")
    sp.add_argument("--pins", help="pins file (default: agentaudit/samples/gold_pins_v1.json)")
    sp.add_argument("--pin", action="store_true", help="step: resolve the commits and arXiv versions on or before the gold date")
    sp.add_argument("--refresh-pins", action="store_true", help="with --pin: overwrite existing pins")
    sp.add_argument("--packets", action="store_true", help="step: build the evidence packets")
    sp.add_argument("--score", action="store_true", help="step: whole-packet scoring (needs --coder)")
    sp.add_argument("--agree", action="store_true", help="step: agreement with the published scores")
    sp.add_argument("--coder", action="append")
    sp.add_argument("--coders-file")
    sp.add_argument("--throttle-state")
    sp.add_argument("--bench", action="append", help="benchmark key (repeatable)")
    sp.add_argument("--cap-tokens", type=int)
    sp.add_argument("--allow-large", action="store_true", help="also download repositories over 400 MB")
    sp.add_argument("--n-boot", type=int, default=2000)
    sp.add_argument("--dry-run", action="store_true", help="no downloads, no backend calls; print the call and token estimate")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_gold)

    sp = sub.add_parser("report", help="score cards")
    common(sp, items=False)
    sp.set_defaults(fn=cmd_report)

    sp = sub.add_parser("freeze", help="hash the frozen files and stage the release repository")
    sp.add_argument("--root", help="project root with protocol/, rubric/, research/ (default: found from the cwd)")
    sp.add_argument("--out", help="directory for FREEZE_MANIFEST.json (manifest only)")
    sp.add_argument("--stage", help="copy the release files into this directory and write the manifest there")
    sp.add_argument("--tests", help="tests directory to include in the staged release")
    sp.add_argument("--extra", action="append", help="release_path=source_file added to the staged release (repeatable)")
    sp.add_argument("--verify", help="re-hash a staged release directory against its FREEZE_MANIFEST.json")
    sp.set_defaults(fn=cmd_freeze)

    sp = sub.add_parser("items", help="list items")
    sp.set_defaults(fn=cmd_items)

    a = p.parse_args(argv)
    if a.cmd == "perturb" and a.mode == "retrieval" and not (a.plan_only or a.summarise) and not a.coder:
        p.error("perturb --mode retrieval needs --coder (or --plan-only / --summarise)")
    if a.cmd == "perturb" and a.mode == "packet" and not (a.summarise or a.frozen_list):
        p.error("perturb needs --frozen-list in packet mode")
    if a.cmd == "freeze" and not (a.out or a.stage or a.verify):
        p.error("freeze needs --out, --stage or --verify")
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
