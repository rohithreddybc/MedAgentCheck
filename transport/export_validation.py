"""Export Claude prompts (coder "sonnet", frozen cap, groups=1) for the three validation runs, with the frozen
package rendering every prompt (no logic copied; nothing under scorer/agentaudit is edited).

  gold     python export_validation.py gold --set abc|betterbench [--bench KEY ...]
           run dir audit/gold_abc | audit/gold_bb (package layout: <run>/gold-<set>/packets built by `agentaudit gold --packets`)
           -> prompts_gold_<set>/<bench>/        prompt = gold.render_gold_prompt (all items of the set in one call)
  perturb  python export_validation.py perturb [--variant v01 ...] [--no-base]
           run dir audit/perturb (packets copied from audit/packets; aliased to the package's directory names)
           -> prompts_perturb/<variant_id>/      prompt = packet_score.render_packet_prompt over perturb.variant_packet
  retest   python export_validation.py retest
           run dir audit/retest (package layout: prepare_retest_packet copies manifest + chunks of the drawn packets)
           -> prompts_retest/<bench>/            same prompt as the audit run

Every output directory has system.txt, user_partNN.txt (chunk-boundary parts, <= 60,000 characters unless one chunk is
larger) and meta.json (sha256 of the full prompt, n_parts, schema description, run-specific fields).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from export_prompts import AUDIT, CODER, GROUPS, render, write_prompt_dir  # noqa: E402  (puts scorer/ on sys.path)
from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.gold import (find_research_dir, gold_run_dir, items_for_set, load_instrument, load_pins,  # noqa: E402
                             render_gold_prompt)
from agentaudit.items import PKG, load_items  # noqa: E402
from agentaudit.packet import load_chunks, load_sources  # noqa: E402
from agentaudit.packet_score import (CAP_TOKENS, GROUP_PLANS, packet_system_prompt, render_packet,  # noqa: E402
                                     render_packet_prompt, select_packet)
from agentaudit.perturb import cell_variant, plan_variants, variant_packet  # noqa: E402
from agentaudit.retest import plan_retest, prepare_retest_packet, retest_dir  # noqa: E402
from agentaudit.sampling import load_frozen_list, read_perturbation_design  # noqa: E402
from agentaudit.util import read_json, safe_name  # noqa: E402

ROOT = AUDIT.parent
FROZEN = ROOT / "research" / "eligibility" / "frozen_list_v1.csv"
GOLD_RUN = {"abc": AUDIT / "gold_abc", "betterbench": AUDIT / "gold_bb"}
PERTURB_RUN = AUDIT / "perturb"


def cap_for_coder() -> int:
    return int(load_coders()[CODER].get("max_packet_tokens") or CAP_TOKENS)  # same expression as the scorers


def schema_note(ids: list[str]) -> str:
    return (f"Reply with ONLY a JSON array of {len(ids)} objects, one per item in this order: {', '.join(ids)}; no prose, "
            "no code fence. Each object has item, score, quotes [{chunk_id, text verbatim}] and rationale as the user "
            "prompt specifies. The authoritative field list is in the user prompt.")


# ------------------------------------------------------------------ gold
def export_gold(set_name: str, run: Path, out: Path, only: list[str] | None = None) -> list[dict]:
    grun = gold_run_dir(run, set_name)
    pins = load_pins()["sets"][set_name]
    instr = load_instrument(set_name, find_research_dir())
    ids = items_for_set(set_name)
    cap = cap_for_coder()
    system = packet_system_prompt()
    res = []
    for key in sorted(pins):
        if only and key not in only:
            continue
        if not (grun / "packets" / key / "manifest.json").exists():
            print(f"gold {set_name} {key}: no packet (not built); skipped")
            continue
        sel = select_packet(load_chunks(grun, key), cap)
        prompt = render_gold_prompt(set_name, ids, instr, render_packet(sel["kept"]))
        m = write_prompt_dir(out / f"prompts_gold_{set_name}" / key, system, prompt, sel["kept"], {
            "mode": "gold", "set": set_name, "bench": key, "coder": CODER, "items": ids, "cap_tokens": cap,
            "tokens_before_cap": sel["tokens_before"], "tokens_sent": sel["tokens"], "over_cap": sel["over_cap"],
            "n_dropped_chunks": len(sel["dropped"]), "expected_output_schema": schema_note(ids),
            "response_path": f"audit/transport/responses_gold_{set_name}/{key}.json"})
        res.append(m)
        print(f"gold {set_name} {key}: {m['n_parts']} parts, ~{m['prompt_tokens_est']} tokens")
    return res


# ------------------------------------------------------------------ frozen id -> packet slug (from the manifests)
def slug_of_frozen(src_run: Path) -> dict[str, str]:
    import yaml

    out = {}
    for f in sorted((src_run / "manifests").glob("*.yaml")):
        m = yaml.safe_load(f.read_text(encoding="utf-8"))
        if m.get("frozen_list_id") and (src_run / "packets" / m["name"] / "manifest.json").exists():
            out[m["frozen_list_id"]] = m["name"]
    return out


# ------------------------------------------------------------------ perturb
def _drop_missing_sources(pdir: Path) -> None:
    """Make the copied packet consistent with its chunks.jsonl, which the audit packet had curated after the build
    (manifest ``privacy_exclusion``: data files with patient identifier fields are removed before any text is sent to a
    coder API). A variant packet is rebuilt from the stored sources, so those sources must go too: every source whose
    (surface, path) appears in ``privacy_exclusion.removed_chunks`` or whose stored file is missing is dropped from this
    run's manifest and its stored file is deleted from this run's copy (the audit packet itself is not touched)."""
    from agentaudit.chunking import parse_chunk_id
    from agentaudit.util import write_json

    mp = pdir / "manifest.json"
    m = read_json(mp)
    removed = set()
    for cid in (m.get("privacy_exclusion") or {}).get("removed_chunks", []):
        p = parse_chunk_id(cid)
        if p:
            removed.add((p[0], p[1]))
    keep, dropped = [], []
    for e in m["sources"]:
        if (e["surface"], e["path"]) in removed or not (pdir / e["stored"]).exists():
            dropped.append(e["stored"])
            (pdir / e["stored"]).unlink(missing_ok=True)
        else:
            keep.append(e)
    if dropped:
        m["sources_dropped_for_variants"] = dropped
        m["sources"] = keep
        write_json(mp, m)


def check_rebuild(run: Path, name: str) -> bool:
    """Chunks rebuilt from the stored sources equal the packet's chunks.jsonl (ids and text)."""
    from agentaudit.chunking import build_chunks, is_s5

    new = build_chunks(load_sources(run, name), is_s5)
    old = load_chunks(run, name)
    return [(c.id, c.text) for c in new] == [(c.id, c.text) for c in old]


def prepare_perturb_run(run: Path, src_run: Path, frozen: list[dict]) -> dict[str, str]:
    """Copy the 45 packets (manifest, chunks, sources) into ``run``/packets under the directory names that the
    package's ``map_bench_dirs`` looks for (it finds only 34 of the 45 by the slugs of the audit packets; the others
    get the first candidate name, ``safe_name(id)``). Base results (resolved, verified) are copied under the same
    names when the audit run has them."""
    slugs = slug_of_frozen(src_run)
    names: dict[str, str] = {}
    for r in frozen:
        bid = r["id"]
        slug = slugs[bid]
        cands = [safe_name(r["id"]), safe_name(r["id"].replace(":", "_")), safe_name(r.get("benchmark_name", "")),
                 safe_name(r.get("benchmark_name", "")).lower()]
        name = slug if slug.lower() in [c.lower() for c in cands] else safe_name(bid)
        names[bid] = name
        dst = run / "packets" / name
        if not (dst / "manifest.json").exists():
            shutil.copytree(src_run / "packets" / slug, dst, dirs_exist_ok=True)
        _drop_missing_sources(dst)
        if (src_run / "resolved" / f"{slug}.json").exists():
            (run / "resolved").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_run / "resolved" / f"{slug}.json", run / "resolved" / f"{name}.json")
        if (src_run / "verified" / slug).exists():
            shutil.copytree(src_run / "verified" / slug, run / "verified" / name, dirs_exist_ok=True)
    return names


def export_perturb(run: Path, out: Path, only: list[str] | None = None, use_base: bool | None = None) -> list[dict]:
    frozen = load_frozen_list(FROZEN)
    names = prepare_perturb_run(run, AUDIT, frozen)
    bad = [n for n in names.values() if not check_rebuild(run, n)]
    if bad:
        print("WARNING: chunks rebuilt from sources differ from chunks.jsonl for:", bad)
    if use_base is None:
        use_base = (run / "resolved").exists()
    design = read_perturbation_design(PKG / "samples" / "perturbation_design_v1.csv")
    plan = plan_variants(run, design, frozen, use_base=use_base, only_variants=only)
    items = load_items()
    system = packet_system_prompt()
    group = GROUP_PLANS[GROUPS][0]
    cap = cap_for_coder()
    res = []
    for pv in plan["variants"]:
        cells = [(cell_variant(c), c["slot"]) for c in pv["cells"]]
        vp = variant_packet(load_sources(run, pv["bench"]), cells, cap)
        prompt = render_packet_prompt(vp["text"], group, items)
        by_type: dict[str, int] = {}
        for c in pv["cells"]:
            by_type[c["vtype"]] = by_type.get(c["vtype"], 0) + 1
        sel = vp["sel"]
        m = write_prompt_dir(out / "prompts_perturb" / pv["variant"], system, prompt, sel["kept"], {
            "mode": "perturb", "variant": pv["variant"], "benchmark": pv["benchmark"], "bench_dir": pv["bench"],
            "coder": CODER, "groups": GROUPS, "items": group, "cap_tokens": cap, "tokens_before_cap": sel["tokens_before"],
            "tokens_sent": sel["tokens"], "over_cap": sel["over_cap"], "n_dropped_chunks": len(sel["dropped"]),
            "n_cells": len(pv["cells"]), "cells_by_type": by_type,
            "base_results": "audit run base (resolved/verified)" if use_base else
            "NONE: plan built without base results (no resolved/ in the audit run); eligibility differs from the final plan",
            "provisional": not use_base, "expected_output_schema": schema_note(group),
            "response_path": f"audit/transport/responses_perturb/{pv['variant']}.json"})
        res.append(m)
        print(f"perturb {pv['variant']} ({pv['benchmark']}): {m['n_parts']} parts, ~{m['prompt_tokens_est']} tokens, "
              f"{len(pv['cells'])} cells, over_cap={sel['over_cap']}")
    for sk in plan["skipped_variants"]:
        print("perturb skipped:", sk)
    return res


# ------------------------------------------------------------------ retest
def export_retest(out: Path, only: list[str] | None = None) -> list[dict]:
    frozen = load_frozen_list(FROZEN)
    slugs = slug_of_frozen(AUDIT)
    plan = plan_retest(AUDIT, frozen)  # the drawn ids (package function); its packet_dir mapping is not used
    rrun = retest_dir(AUDIT)
    spec_cap = cap_for_coder()
    res = []
    for d in plan["drawn"]:
        slug = slugs[d["id"]]
        if only and slug not in only:
            continue
        prepare_retest_packet(AUDIT, slug)  # package function: byte-identical copy of manifest + chunks
        omp = AUDIT / "scoring" / slug / CODER / "packet_manifest.json"
        cap, groups = spec_cap, GROUPS
        if omp.exists():  # retest uses the original run's cap and item groups
            om = read_json(omp)
            cap, groups = int(om["cap_tokens"]), len(om["groups"])
        if groups != 1:
            raise RuntimeError(f"{slug}: original run used {groups} item groups; this transport covers groups=1 only")
        r = render(rrun, slug, cap)
        m = write_prompt_dir(out / "prompts_retest" / slug, r["system"], r["prompt"], r["sel"]["kept"], {
            "mode": "retest", "bench": slug, "frozen_id": d["id"], "coder": CODER, "groups": GROUPS, "items": r["group"],
            "cap_tokens": cap,
            "cap_source": "original run packet_manifest" if omp.exists() else "frozen default (no original sonnet manifest)",
            "tokens_before_cap": r["sel"]["tokens_before"], "tokens_sent": r["sel"]["tokens"],
            "over_cap": r["sel"]["over_cap"], "n_dropped_chunks": len(r["sel"]["dropped"]),
            "expected_output_schema": schema_note(r["group"]),
            "response_path": f"audit/transport/responses_retest/{slug}.json"})
        res.append(m)
        print(f"retest {slug}: {m['n_parts']} parts, ~{m['prompt_tokens_est']} tokens")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    g = sub.add_parser("gold")
    g.add_argument("--set", required=True, choices=["abc", "betterbench"])
    g.add_argument("--run", help="default: audit/gold_abc or audit/gold_bb")
    g.add_argument("--bench", action="append")
    p = sub.add_parser("perturb")
    p.add_argument("--run", default=str(PERTURB_RUN))
    p.add_argument("--variant", action="append")
    p.add_argument("--no-base", action="store_true", help="force the plan without base results")
    t = sub.add_parser("retest")
    t.add_argument("--bench", action="append")
    for sp in (g, p, t):
        sp.add_argument("--out", default=str(HERE), help="transport directory (prompts_* are written under it)")
    a = ap.parse_args()
    out = Path(a.out)
    if a.mode == "gold":
        export_gold(a.set, Path(a.run) if a.run else GOLD_RUN[a.set], out, a.bench)
    elif a.mode == "perturb":
        export_perturb(Path(a.run), out, a.variant, False if a.no_base else None)
    else:
        export_retest(out, a.bench)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
