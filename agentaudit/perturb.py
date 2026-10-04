"""Stage 7: perturbation validation (validity under perturbation, not ground truth).

Variants per item, with labels fixed by construction:
  inject      canonical level-2 sentence inserted mid-paper in S1          expected 2 (exact)
  buried      the same sentence in a late appendix block at the end of S1  expected 2 (exact)
  paraphrase  meaning-preserving rewrite, placed like inject               expected 2 (exact)
  deletion    every chunk cited by a verified quote in the base coding     expected 0 (at most)
              is removed; residual evidence in uncited chunks makes this a
              conservative specificity test
  decoy       near-miss text that fails the anchor, placed like inject     expected = base level (at most)

Architecture v3 (``run_perturb_packet``): each variant is a full copy of the packet, re-scored for the target
item only (single-item prompt mode with the whole packet, no retrieval). ``buried`` puts the sentence in a late
appendix block at the end of S1 and, for half of the variants (chosen by seed, see ``sampling.select_cells``), also in
a synthetic S4 code-comment chunk. The label stays 2 because the appendix copy sits on S1 (G1 scores S1-S3); the S4
copy tests whether a second, code-side copy disturbs the coder. Cells are drawn by ``sampling`` (8 per item per
type, seed 20261004, across the 45 frozen benchmarks).

The retrieval path (``run_perturb``, one chunk set per item) is kept as the ablation path of the retired
retrieval design.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, asdict
from pathlib import Path

from .backends import BackendAuthError, BackendError
from .chunking import Source, build_chunks, is_s5, parse_chunk_id
from .coding import ParseError, code_cell
from .items import ITEM_ORDER, load_items, load_perturbation_specs
from .packet import load_sources
from .resolve import resolve_cell
from .retrieve import retrieve_chunks
from .stats import wilson
from .throttle import DailyLimitReached
from .util import est_tokens, loose_normalise, normalise, read_json, sha256_text, utcnow, write_json

VARIANT_TYPES = ("inject", "buried", "paraphrase", "deletion", "decoy")
POSITIVE = ("inject", "buried", "paraphrase")
NEGATIVE = ("deletion", "decoy")


@dataclass
class Variant:
    item: str
    vtype: str
    expected: int
    expectation: str  # "exact" | "at_most"
    text: str | None = None
    removed_chunk_ids: list[str] | None = None
    s4_comment: bool = False  # buried only: also place the text in a synthetic S4 code-comment chunk
    base_level: int | None = None  # base resolved level when known (deletion's secondary label)

    @property
    def key(self) -> str:
        return f"{self.item}/{self.vtype}"


def build_variants(item_id: str, spec: dict | None = None, base_level: int = 0,
                   evidence_ids: list[str] | None = None, types=VARIANT_TYPES, s4_comment: bool = False) -> list[Variant]:
    """Construct variants and their expected labels. Pure function."""
    spec = spec or load_perturbation_specs()[item_id]
    out: list[Variant] = []
    for t in types:
        if t == "inject":
            out.append(Variant(item_id, t, 2, "exact", text=spec["inject"].strip()))
        elif t == "buried":
            out.append(Variant(item_id, t, 2, "exact", text=spec["inject"].strip(), s4_comment=bool(s4_comment)))
        elif t == "paraphrase":
            out.append(Variant(item_id, t, 2, "exact", text=spec["paraphrase"].strip()))
        elif t == "decoy":
            out.append(Variant(item_id, t, int(base_level), "at_most", text=spec["decoy"].strip(),
                               base_level=int(base_level)))
        elif t == "deletion":
            if evidence_ids:
                out.append(Variant(item_id, t, 0, "at_most", removed_chunk_ids=sorted(set(evidence_ids)),
                                   base_level=int(base_level)))
        else:
            raise ValueError(f"unknown variant type {t}")
    return out


S4_NOTE_PATH = "agent_eval/notes.py"


def _free_path(sources: list[Source], path: str) -> str:
    used = {(s.surface, s.path) for s in sources}
    p, n = path, 1
    while ("S4", p) in used:
        n += 1
        p = path.replace(".py", f"_{n}.py")
    return p


def _host_index(sources: list[Source], last: bool) -> int:
    for surf in ("S1", "S2"):
        idxs = sorted((i for i, s in enumerate(sources) if s.surface == surf), key=lambda i: sources[i].path)
        if idxs:
            return idxs[-1] if last else idxs[0]
    raise ValueError("packet has no S1 or S2 source to host a perturbation")


def apply_variant(sources: list[Source], v: Variant) -> list[Source]:
    """Return a modified copy of the sources. Pure function."""
    new = [copy.copy(s) for s in sources]
    if v.vtype in ("inject", "paraphrase", "decoy"):
        i = _host_index(new, last=False)
        lines = new[i].text.split("\n")
        lines.insert(len(lines) // 2, v.text)
        new[i].text = "\n".join(lines)
    elif v.vtype == "buried":
        i = _host_index(new, last=True)
        new[i].text = new[i].text.rstrip("\n") + "\n\nAppendix Z. Additional notes\n" + v.text
        if v.s4_comment:
            new.append(Source("S4", _free_path(new, S4_NOTE_PATH), "# " + v.text + "\n"))
    elif v.vtype == "deletion":
        drop: dict[tuple[str, str], set[int]] = {}
        for cid in v.removed_chunk_ids or []:
            p = parse_chunk_id(cid)
            if p:
                drop.setdefault((p[0], p[1]), set()).update(range(p[2], p[3] + 1))
        for s in new:
            rm = drop.get((s.surface, s.path))
            if rm:
                s.text = "\n".join(l for n, l in enumerate(s.text.split("\n"), 1) if n not in rm)
    return new


def variant_text_retrieved(v: Variant, chunk_texts: dict[str, str]) -> bool | None:
    if not v.text:
        return None
    needle = normalise(v.text)
    return any(needle in normalise(t) for t in chunk_texts.values())


def base_info(run: Path, bench: str, item_id: str) -> tuple[int, bool, list[str]]:
    """(base level, known, evidence chunk ids cited by verified quotes)."""
    level, known = 0, False
    rp = Path(run) / "resolved" / f"{bench}.json"
    if rp.exists():
        c = read_json(rp)["cells"].get(item_id)
        if c:
            level = 0 if c["final"] == "NA" else int(c["final"])
            known = True
    ev: set[str] = set()
    vd = Path(run) / "verified" / bench / item_id
    if vd.exists():
        for f in vd.glob("*.json"):
            for q in read_json(f)["quotes"]:
                if q["verified"]:
                    ev.add(q["chunk_id"])
    return level, known, sorted(ev)


def perturb_path(run: Path, bench: str, item_id: str, vtype: str, coder: str) -> Path:
    return Path(run) / "perturb" / bench / item_id / vtype / f"{coder}.json"


def plan(run: Path, bench: str, item_ids: list[str], types=VARIANT_TYPES) -> list[dict]:
    out = []
    for it in item_ids:
        lvl, known, ev = base_info(run, bench, it)
        for v in build_variants(it, base_level=lvl, evidence_ids=ev, types=types):
            d = asdict(v)
            d["base_known"] = known
            out.append(d)
    return out


def run_perturb(run: Path, bench: str, item_ids: list[str], coders: dict[str, tuple[dict, object]],
                types=VARIANT_TYPES, force: bool = False, log=print) -> dict:
    """coders: name -> (spec, backend)."""
    from .verify import verify_result

    items = load_items()
    sources = load_sources(run, bench)
    summary = {"done": 0, "skipped": 0, "failed": [], "blocked": None}
    for it in item_ids:
        lvl, known, ev = base_info(run, bench, it)
        for v in build_variants(it, base_level=lvl, evidence_ids=ev, types=types):
            chunks = build_chunks(apply_variant(sources, v), is_s5)
            by_id = {c.id: c for c in chunks}
            ret = retrieve_chunks(chunks, it)
            cs = [by_id[c["id"]] for c in ret["chunks"]]
            ctexts = {c.id: c.text for c in cs}
            hit = variant_text_retrieved(v, ctexts)
            for cname, (spec, backend) in coders.items():
                p = perturb_path(run, bench, it, v.vtype, cname)
                if p.exists() and not force and read_json(p).get("status") == "ok":
                    summary["skipped"] += 1
                    continue
                try:
                    rec = code_cell(backend, items[it], items, cs)
                except DailyLimitReached as e:
                    summary["blocked"] = {"item": it, "variant": v.vtype, "reason": str(e),
                                          "next_available_unix": e.next_available}
                    log(f"[{cname}] daily limit reached at {v.key}; rerun to resume")
                    return summary
                except Exception as e:  # noqa: BLE001 - logged, run continues
                    summary["failed"].append({"variant": v.key, "coder": cname, "error": str(e)})
                    log(f"[{cname}] {v.key} failed: {e}")
                    continue
                ver = verify_result(rec["parsed"], items[it], ctexts) if rec["parsed"] else None
                rec.update({"bench": bench, "item": it, "coder": cname, "family": spec.get("family"),
                            "variant": asdict(v), "base_known": known,
                            "retrieved_ids": [c["id"] for c in ret["chunks"]],
                            "variant_text_in_retrieval": hit, "verification": ver,
                            "expected": v.expected, "expectation": v.expectation})
                write_json(p, rec)
                summary["done"] += 1
                log(f"[{cname}] {bench} {v.key}: level={ver['effective'] if ver else 'parse_error'} "
                    f"expected={v.expectation} {v.expected} retrieved={hit}")
    return summary


# ---------------------------------------------------------------- architecture v3: whole-packet variants
def bench_dir_candidates(row: dict) -> list[str]:
    from .util import safe_name

    c = [safe_name(row["id"]), safe_name(row["id"].replace(":", "_")), safe_name(row.get("benchmark_name", "")),
         safe_name(row.get("benchmark_name", "")).lower()]
    return list(dict.fromkeys(x for x in c if x))


def map_bench_dirs(run: Path, frozen_rows: list[dict]) -> dict[str, str]:
    """frozen id -> packet directory name under ``<run>/packets`` (only benchmarks whose packet exists)."""
    base = Path(run) / "packets"
    out: dict[str, str] = {}
    for r in frozen_rows:
        for c in bench_dir_candidates(r):
            if (base / c / "manifest.json").exists():
                out[r["id"]] = c
                break
    return out


def plan_packet_cells(run: Path, sample: list[dict], frozen_rows: list[dict], items: list[str] | None = None,
                      types=VARIANT_TYPES, n: int = 8, use_base: bool = True, only_bench: list[str] | None = None) -> list[dict]:
    """Select the perturbation cells for a run. Each cell: item, vtype, benchmark (frozen id), bench (packet dir),
    s4_comment, base_level, evidence (deletion). With ``use_base`` a benchmark needs base results (resolved and
    verified quotes from the v3 audit run) to be eligible; without it the draw is the plain seeded one and deletion
    cells are not built."""
    from .sampling import select_cells

    dirs = map_bench_dirs(run, frozen_rows)
    if only_bench:
        dirs = {k: v for k, v in dirs.items() if v in only_bench or k in only_bench}
    cache: dict[tuple[str, str], dict | None] = {}

    def base_of(bid: str, item: str):
        key = (bid, item)
        if key not in cache:
            lvl, known, ev = base_info(run, dirs[bid], item)
            if use_base:
                cache[key] = {"level": lvl, "evidence": ev} if known else {"level": None, "evidence": []}
            else:
                cache[key] = None
        return cache[key]

    cells = select_cells(sample, base_of, set(dirs), n=n, items=items, types=types)
    for c in cells:
        c["bench"] = dirs[c["benchmark"]]
        b = base_of(c["benchmark"], c["item"])
        c["base_level"] = (b or {}).get("level")
        c["evidence"] = (b or {}).get("evidence", []) if c["vtype"] == "deletion" else []
    return cells


def cell_variant(cell: dict) -> Variant:
    lvl = cell.get("base_level")
    lvl = lvl if isinstance(lvl, int) else None
    vs = build_variants(cell["item"], base_level=lvl or 0, evidence_ids=cell.get("evidence"),
                        types=(cell["vtype"],), s4_comment=bool(cell.get("s4_comment")))
    if not vs:
        raise ValueError(f"cannot build variant for {cell}")
    vs[0].base_level = lvl
    return vs[0]


def variant_packet(sources: list[Source], v: Variant, cap_tokens: int) -> dict:
    """Variant sources -> chunks -> capped packet. Returns {sel, text, kept_texts, hit, s4_hit}."""
    from .packet_score import render_packet, select_packet

    chunks = build_chunks(apply_variant(sources, v), is_s5)
    sel = select_packet(chunks, cap_tokens)
    kept_texts = {c.id: c.text for c in sel["kept"]}
    hit = None
    s4_hit = None
    if v.text:
        needle = loose_normalise(v.text)
        norm = {i: loose_normalise(t) for i, t in kept_texts.items()}
        hit = any(needle in t for t in norm.values())
        if v.s4_comment:
            s4_hit = any(needle in norm[c.id] for c in sel["kept"] if c.surface == "S4")
    return {"sel": sel, "text": render_packet(sel["kept"]), "kept_texts": kept_texts, "hit": hit, "s4_hit": s4_hit}


def estimate_cells(run: Path, cells: list[dict], caps: dict[str, int | None]) -> dict:
    """Calls and estimated input tokens per coder (packet token count from each packet manifest, capped)."""
    from .packet_score import CAP_TOKENS

    tok: dict[str, int] = {}
    out = {}
    for c in cells:
        if c["bench"] not in tok:
            tok[c["bench"]] = int(read_json(Path(run) / "packets" / c["bench"] / "manifest.json")["total_chunk_tokens"])
    overhead = 2000  # system text, scale, G1-G7 and one item block
    for coder, cap in caps.items():
        cap = cap or CAP_TOKENS
        total = sum(min(tok[c["bench"]], cap) + overhead for c in cells)
        out[coder] = {"calls": len(cells), "input_tokens_est": total}
    return out


def run_perturb_packet(run: Path, cells: list[dict], coders: dict[str, tuple[dict, object]], force: bool = False,
                       log=print, dry_run: bool = False) -> dict:
    """Score every cell with every coder: one call per (cell, coder), whole packet, target item only.

    coders: name -> (spec, backend). Records go to ``perturb/<bench>/<item>/<vtype>/<coder>.json``."""
    from .packet_score import CAP_TOKENS, packet_system_prompt, parse_packet_response, render_packet_prompt
    from .prompts import prompt_hash
    from .verify import verify_result

    items = load_items()
    system = packet_system_prompt()
    summary = {"done": 0, "skipped": 0, "failed": [], "blocked": None, "cells": len(cells)}
    src_cache: dict[str, list[Source]] = {}
    for cell in cells:
        v = cell_variant(cell)
        bench, it = cell["bench"], cell["item"]
        todo = {}
        for cname, (spec, backend) in coders.items():
            p = perturb_path(run, bench, it, v.vtype, cname)
            if p.exists() and not force:
                try:
                    if read_json(p).get("status") == "ok":
                        summary["skipped"] += 1
                        continue
                except ValueError:
                    pass
            todo[cname] = (spec, backend, p)
        if not todo:
            continue
        if bench not in src_cache:
            src_cache[bench] = load_sources(run, bench)
        by_cap: dict[int, dict] = {}
        for cname, (spec, backend, p) in todo.items():
            cap = int(spec.get("max_packet_tokens") or CAP_TOKENS)
            if cap not in by_cap:
                by_cap[cap] = variant_packet(src_cache[bench], v, cap)
            vp = by_cap[cap]
            prompt = render_packet_prompt(vp["text"], [it], items)
            if dry_run:
                summary["done"] += 1
                continue
            rec = {"bench": bench, "benchmark": cell.get("benchmark"), "item": it, "coder": cname,
                   "family": spec.get("family"), "variant": asdict(v), "expected": v.expected,
                   "expectation": v.expectation, "base_level": v.base_level, "mode": "packet_v3_single_item",
                   "prompt_sha256": prompt_hash(prompt), "prompt_tokens_est": est_tokens(prompt),
                   "rendered_packet_sha256": sha256_text(vp["text"]), "cap_tokens": cap,
                   "n_dropped": len(vp["sel"]["dropped"]), "over_cap": vp["sel"]["over_cap"],
                   "variant_text_in_packet": vp["hit"], "s4_comment_in_packet": vp["s4_hit"],
                   "attempts": [], "parsed": None, "verification": None, "status": "parse_error"}
            where = f"{bench}/{it}/{v.vtype}"
            try:
                for _ in range(2):
                    resp = backend.complete(system, prompt)
                    att = {"timestamp": utcnow(), "model_id": resp.model_id, "usage": resp.usage, "meta": resp.meta,
                           "raw_response": resp.text}
                    rec["attempts"].append(att)
                    rec["model_id"] = resp.model_id
                    try:
                        ok, err = parse_packet_response(resp.text, [it], items)
                    except ParseError as e:
                        att["parse_error"] = str(e)
                        continue
                    if it in ok:
                        rec["parsed"], rec["status"] = ok[it], "ok"
                        break
                    att["item_errors"] = err
            except DailyLimitReached as e:
                summary["blocked"] = {"cell": where, "coder": cname, "reason": str(e),
                                      "next_available_unix": e.next_available}
                log(f"[{cname}] daily limit reached at {where}; rerun to resume")
                return summary
            except BackendAuthError as e:
                summary["blocked"] = {"cell": where, "coder": cname, "reason": f"authentication: {e}"}
                log(f"[{cname}] backend authentication failed: {e}")
                return summary
            except BackendError as e:
                summary["failed"].append({"cell": where, "coder": cname, "error": str(e)})
                log(f"[{cname}] {where} backend error: {e}")
                continue
            if rec["attempts"]:
                rec["timestamp"] = rec["attempts"][-1]["timestamp"]
            if rec["parsed"]:
                rec["verification"] = verify_result(rec["parsed"], items[it], vp["kept_texts"])
            write_json(p, rec)
            if rec["status"] == "ok":
                summary["done"] += 1
                log(f"[{cname}] {where}: level={rec['verification']['effective']} "
                    f"expected={v.expectation} {v.expected}")
            else:
                summary["failed"].append({"cell": where, "coder": cname, "error": "parse_error"})
    return summary


# ---------------------------------------------------------------- summary
def _level(eff) -> int:
    return 0 if eff == "NA" else int(eff)


def _ok(v: dict, level: int) -> bool:
    return level == v["expected"] if v["expectation"] == "exact" else level <= v["expected"]


def _ok_drop(v: dict, level: int) -> bool | None:
    """Secondary label (deletion only): the level fell below the base level."""
    if v["vtype"] != "deletion" or v.get("base_level") is None:
        return None
    return level < int(v["base_level"])


def _metric(sel: list[dict]) -> dict:
    pos = [r for r in sel if r["vtype"] in POSITIVE]
    neg = [r for r in sel if r["vtype"] in NEGATIVE]
    dele = [r for r in sel if r["vtype"] == "deletion" and r.get("ok_drop") is not None]
    sp = sum(r["ok"] for r in pos)
    sa = sum(r["level"] >= 1 for r in pos)
    sn = sum(r["ok"] for r in neg)
    sd = sum(1 for r in dele if r["ok_drop"])

    def m(s, n):
        return {"hits": s, "n": n, "rate": s / n if n else None, "wilson95": list(wilson(s, n)) if n else None}

    return {"sensitivity": m(sp, len(pos)), "sensitivity_any_level": m(sa, len(pos)),
            "specificity": m(sn, len(neg)), "deletion_level_dropped": m(sd, len(dele))}


def summarise(run: Path, benches: list[str]) -> dict:
    """Sensitivity (inject, buried, paraphrase: coder reaches level 2) and specificity (deletion: level 0;
    decoy: not above the base level) with Wilson 95% intervals, per coder and RESOLVED (two-family rule applied to
    the coders' votes on the same variant); overall, per variant type, per item, per item and type."""
    rows: list[dict] = []
    votes_by: dict[tuple, dict] = {}
    for b in benches:
        base = Path(run) / "perturb" / b
        if not base.exists():
            continue
        for f in sorted(base.glob("*/*/*.json")):
            rec = read_json(f)
            if rec.get("status") != "ok" or not rec.get("verification"):
                continue
            lv = _level(rec["verification"]["effective"])
            var = rec["variant"]
            rows.append({"bench": b, "item": rec["item"], "vtype": var["vtype"], "coder": rec["coder"],
                         "level": lv, "expected": var["expected"], "expectation": var["expectation"],
                         "base_level": var.get("base_level"), "ok": _ok(var, lv), "ok_drop": _ok_drop(var, lv),
                         "retrieved": rec.get("variant_text_in_packet", rec.get("variant_text_in_retrieval"))})
            slot = votes_by.setdefault((b, rec["item"], var["vtype"]), {"var": var, "votes": {}})
            slot["votes"][rec["coder"]] = {"raw": rec["verification"]["score_raw"],
                                           "effective": rec["verification"]["effective"], "family": rec.get("family")}
    for (b, it, vt), d in sorted(votes_by.items()):
        if len(d["votes"]) < 2:
            continue
        var = d["var"]
        lv = _level(resolve_cell(d["votes"])["final"])
        rows.append({"bench": b, "item": it, "vtype": vt, "coder": "RESOLVED", "level": lv,
                     "expected": var["expected"], "expectation": var["expectation"],
                     "base_level": var.get("base_level"), "ok": _ok(var, lv), "ok_drop": _ok_drop(var, lv),
                     "retrieved": None})

    out: dict = {"n_rows": len(rows), "note": "validity under perturbation, not ground truth",
                 "labels": {"inject/buried/paraphrase": "sensitivity = level 2 reached (any level >= 1 also reported)",
                            "deletion": "specificity = level 0 (secondary: level below the base level)",
                            "decoy": "specificity = level not above the base level"},
                 "by_coder": {}}
    flat: list[dict] = []

    def add_flat(scope, coder, item, vtype, met):
        for k, d in met.items():
            if d["n"]:
                lo, hi = d["wilson95"]
                flat.append({"scope": scope, "coder": coder, "item": item or "", "vtype": vtype or "", "metric": k,
                             "hits": d["hits"], "n": d["n"], "rate": round(d["rate"], 4), "wilson_lo": round(lo, 4),
                             "wilson_hi": round(hi, 4)})

    for coder in sorted({r["coder"] for r in rows}):
        sel = [r for r in rows if r["coder"] == coder]
        c = _metric(sel)
        add_flat("overall", coder, None, None, c)
        c["by_variant"] = {}
        for vt in VARIANT_TYPES:
            s2 = [r for r in sel if r["vtype"] == vt]
            if s2:
                c["by_variant"][vt] = _metric(s2)
                add_flat("variant", coder, None, vt, c["by_variant"][vt])
        c["by_item"] = {}
        c["by_item_variant"] = {}
        for it in ITEM_ORDER:
            s2 = [r for r in sel if r["item"] == it]
            if not s2:
                continue
            c["by_item"][it] = _metric(s2)
            add_flat("item", coder, it, None, c["by_item"][it])
            for vt in VARIANT_TYPES:
                s3 = [r for r in s2 if r["vtype"] == vt]
                if s3:
                    c["by_item_variant"][f"{it}/{vt}"] = _metric(s3)
                    add_flat("item_variant", coder, it, vt, c["by_item_variant"][f"{it}/{vt}"])
        out["by_coder"][coder] = c
    srows = [r for r in rows if r["coder"] != "RESOLVED" and r["vtype"] != "decoy" and r.get("retrieved") is not None]
    out["variant_text_in_packet"] = {"hits": sum(1 for r in srows if r["retrieved"]), "n": len(srows)}
    out["rows"] = rows
    write_json(Path(run) / "perturb" / "summary.json", out)
    if flat:
        import csv

        with open(Path(run) / "perturb" / "summary.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(flat[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(flat)
    return out


def json_key(var: dict) -> str:
    return var["vtype"] + "|" + str(var.get("text") or var.get("removed_chunk_ids"))
