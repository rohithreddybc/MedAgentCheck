"""Stage 7: perturbation validation (validity under perturbation, not ground truth).

Variants per item, with labels fixed by construction:
  inject      canonical level-2 sentence inserted mid-paper in S1          expected 2 (exact)
  buried      the same sentence in a late appendix block at the end of S1  expected 2 (exact)
  paraphrase  meaning-preserving rewrite, placed like inject               expected 2 (exact)
  deletion    every chunk cited by a verified quote in the base coding     expected 0 (at most)
              is removed; residual evidence in uncited chunks makes this a
              conservative specificity test
  decoy       near-miss text that fails the anchor, placed like inject     expected = base level (at most);
              half of the decoys: the full level-2 text only in a non-S5 S4 code comment (G1a)

Architecture v3 (``run_perturb_variants``, multiplexed): 40 variant packets, each a full copy of one benchmark's
packet in which EVERY item receives exactly one perturbation type (balanced design, ``sampling``: each item x type
pair occurs 8 times, 1,000 labelled cells). A variant is scored once with the normal 25-item whole-packet call, so a
coder needs 40 calls, not 1,000. Inject, paraphrase and decoy texts of different items go to different S1 positions
(slots); every buried text goes to one late S1 appendix block; half of the decoys (by seed) are the full level-2
inject text placed only in a non-S5 S4 code comment (G1a: code never counts as reporting, so the expected level
stays the base level) and the other half are the near-miss text in S1. Cells that fail the eligibility rule are
dropped and counted. Cross-item interference is a known limit (see IMPLEMENTATION_NOTES).

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
    s4_comment: bool = False  # decoy only: the full inject text in a non-S5 S4 code comment instead of the S1 near-miss
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
            out.append(Variant(item_id, t, 2, "exact", text=spec["inject"].strip()))
        elif t == "paraphrase":
            out.append(Variant(item_id, t, 2, "exact", text=spec["paraphrase"].strip()))
        elif t == "decoy":
            # s4_comment: the full level-2 inject text, placed only in a non-S5 S4 code comment (G1a: code never
            # counts as reporting, so the expected level stays the base level)
            out.append(Variant(item_id, t, int(base_level), "at_most",
                               text=(spec["inject"] if s4_comment else spec["decoy"]).strip(),
                               s4_comment=bool(s4_comment), base_level=int(base_level)))
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
    if v.vtype == "decoy" and v.s4_comment:
        new.append(Source("S4", _free_path(new, S4_NOTE_PATH), "# " + v.text + "\n"))
    elif v.vtype in ("inject", "paraphrase", "decoy"):
        i = _host_index(new, last=False)
        lines = new[i].text.split("\n")
        lines.insert(len(lines) // 2, v.text)
        new[i].text = "\n".join(lines)
    elif v.vtype == "buried":
        i = _host_index(new, last=True)
        new[i].text = new[i].text.rstrip("\n") + "\n\nAppendix Z. Additional notes\n" + v.text
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


# ---------------------------------------------------------------- architecture v3: multiplexed variant packets
SLOTS = len(ITEM_ORDER)


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


def _drop_reason(vtype: str, base: dict | None) -> str:
    if base is None:
        return "no base results (deletion needs them)"
    lv = base.get("level")
    if lv is None:
        return "no base result for this benchmark"
    if lv == "NA":
        return "base level NA"
    if vtype == "deletion":
        return "base level 0" if int(lv) < 1 else "no verified evidence chunk to remove"
    return "base level 2 (label would pass trivially)"


def _inject_text(item: str) -> str:
    return load_perturbation_specs()[item]["inject"].strip()


def plan_variants(run: Path, design: list[dict], frozen_rows: list[dict], use_base: bool = True,
                  only_variants: list[str] | None = None) -> dict:
    """Turn the design into a run plan. A cell that fails the eligibility rule is dropped and counted, never
    replaced; a variant whose benchmark has no packet in the run is skipped. With ``use_base`` every benchmark needs base
    results (resolved and verified quotes from the v3 audit run); without it the draw is plain and deletion
    cells are dropped."""
    from .sampling import eligible

    dirs = map_bench_dirs(run, frozen_rows)
    by_v: dict[str, list[dict]] = {}
    for r in design:
        by_v.setdefault(r["variant"], []).append(r)
    cache: dict[tuple[str, str], dict | None] = {}

    def base_of(bid: str, item: str):
        k = (bid, item)
        if k not in cache:
            if not use_base:
                cache[k] = None
            else:
                lvl, known, ev = base_info(run, dirs[bid], item)
                cache[k] = {"level": lvl, "evidence": ev} if known else {"level": None, "evidence": []}
        return cache[k]

    plan: dict = {"variants": [], "dropped": [], "skipped_variants": []}
    for vid in sorted(by_v):
        if only_variants and vid not in only_variants:
            continue
        rows = by_v[vid]
        bid = rows[0]["benchmark"]
        if bid not in dirs:
            plan["skipped_variants"].append({"variant": vid, "benchmark": bid, "reason": "no packet in the run"})
            continue
        cells = []
        for r in sorted(rows, key=lambda r: ITEM_ORDER.index(r["item"])):
            b = base_of(bid, r["item"])
            if r["vtype"] == "decoy" and r["s4_comment"] in (True, "yes") and is_s5("# " + _inject_text(r["item"])):
                # the comment would be tagged as an agent-visible (S5) chunk and then legitimately count
                plan["dropped"].append({"variant": vid, "benchmark": bid, "item": r["item"], "vtype": r["vtype"],
                                        "reason": "S4-comment text matches an S5 pattern (would be tagged agent-visible)"})
                continue
            if not eligible(r["vtype"], b):
                plan["dropped"].append({"variant": vid, "benchmark": bid, "item": r["item"], "vtype": r["vtype"],
                                        "reason": _drop_reason(r["vtype"], b)})
                continue
            cells.append({"item": r["item"], "vtype": r["vtype"], "slot": r["slot"], "s4_comment": r["s4_comment"] in (True, "yes"),
                          "base_level": (b or {}).get("level"),
                          "evidence": (b or {}).get("evidence", []) if r["vtype"] == "deletion" else []})
        plan["variants"].append({"variant": vid, "benchmark": bid, "bench": dirs[bid], "cells": cells})
    plan["n_cells"] = sum(len(v["cells"]) for v in plan["variants"])
    plan["n_dropped"] = len(plan["dropped"])
    return plan


def cell_variant(cell: dict) -> Variant:
    lvl = cell.get("base_level")
    lvl = lvl if isinstance(lvl, int) else None
    vs = build_variants(cell["item"], base_level=lvl or 0, evidence_ids=cell.get("evidence"),
                        types=(cell["vtype"],), s4_comment=bool(cell.get("s4_comment")))
    if not vs:
        raise ValueError(f"cannot build variant for {cell}")
    vs[0].base_level = lvl
    return vs[0]


def apply_variants(sources: list[Source], cells: list[tuple[Variant, int]]) -> list[Source]:
    """All perturbations of one variant packet, applied to a copy of the sources. Pure function.

    cells: (Variant, slot). Order: deletions first (line numbers of the cited chunks refer to the original text),
    then inline insertions of inject, paraphrase and decoy texts into the first S1 source at spread positions
    (slot k of 25 at line (k + 0.5) / 25 of the text), then one late appendix block at the end of the last S1
    source holding every buried text (always S1: code never counts as reporting, G1a), and one synthetic S4 file with
    a code comment for each decoy whose s4_comment flag is set (that decoy carries the full level-2 inject text, in
    S4 only, and is not inserted inline)."""
    new = [copy.copy(s) for s in sources]
    drop: dict[tuple[str, str], set[int]] = {}
    for v, _ in cells:
        if v.vtype == "deletion":
            for cid in v.removed_chunk_ids or []:
                p = parse_chunk_id(cid)
                if p:
                    drop.setdefault((p[0], p[1]), set()).update(range(p[2], p[3] + 1))
    for s in new:
        rm = drop.get((s.surface, s.path))
        if rm:
            s.text = "\n".join(l for n, l in enumerate(s.text.split("\n"), 1) if n not in rm)
    inline = [(slot, v) for v, slot in cells if v.vtype in ("inject", "paraphrase", "decoy") and not v.s4_comment]
    if inline:
        i = _host_index(new, last=False)
        lines = new[i].text.split("\n")
        n = len(lines)
        for pos, _slot, text in sorted(((int((slot + 0.5) / SLOTS * n), slot, v.text) for slot, v in inline), reverse=True):
            lines.insert(pos, text)
        new[i].text = "\n".join(lines)
    bur = sorted((v for v, _ in cells if v.vtype == "buried"), key=lambda v: ITEM_ORDER.index(v.item))
    s4 = sorted((v for v, _ in cells if v.vtype == "decoy" and v.s4_comment), key=lambda v: ITEM_ORDER.index(v.item))
    if bur:
        i = _host_index(new, last=True)
        new[i].text = new[i].text.rstrip("\n") + "\n\nAppendix Z. Additional notes\n" + "\n".join(v.text for v in bur)
    if s4:
        new.append(Source("S4", _free_path(new, S4_NOTE_PATH), "\n".join("# " + v.text for v in s4) + "\n"))
    return new


def variant_packet(sources: list[Source], cells: list[tuple[Variant, int]], cap_tokens: int) -> dict:
    """Variant sources -> chunks -> capped packet. Returns {sel, text, kept_texts, hits, s4_hits}; hits and s4_hits
    map item -> whether the inserted text (or its S4 comment copy) is in the packet that is sent."""
    from .packet_score import render_packet, select_packet

    chunks = build_chunks(apply_variants(sources, cells), is_s5)
    sel = select_packet(chunks, cap_tokens)
    kept_texts = {c.id: c.text for c in sel["kept"]}
    norm = {i: loose_normalise(t) for i, t in kept_texts.items()}
    s4_ids = [c.id for c in sel["kept"] if c.surface == "S4" and not c.s5]
    s5_ids = [c.id for c in sel["kept"] if c.s5]
    hits, s4_hits = {}, {}
    for v, _ in cells:
        if v.text:
            nd = loose_normalise(v.text)
            hits[v.item] = any(nd in t for t in norm.values())
            if v.s4_comment:  # present in a non-S5 S4 chunk, and in no S5 chunk
                s4_hits[v.item] = any(nd in norm[i] for i in s4_ids) and not any(nd in norm[i] for i in s5_ids)
    return {"sel": sel, "text": render_packet(sel["kept"]), "kept_texts": kept_texts, "hits": hits,
            "s4_hits": s4_hits, "lnorm": norm}


def _prompt_overhead(coders: dict, names: list[str]) -> dict[str, int]:
    """Estimated tokens of a prompt without packet text, per coder (system text, scale, G1-G7, 25 item blocks)."""
    from .packet_score import GROUP_PLANS, packet_system_prompt, render_packet_prompt

    items = load_items()
    system = packet_system_prompt()
    out = {}
    for n in names:
        plan = GROUP_PLANS[int(coders[n].get("groups", 1))]
        out[n] = sum(est_tokens(system) + est_tokens(render_packet_prompt("", g, items)) for g in plan)
    return out


def estimate_variants(run: Path, plan: dict, coders: dict, names: list[str]) -> dict:
    """Calls and estimated input tokens per coder (packet tokens from each packet manifest, capped, plus the
    prompt without packet). One call per variant and item group."""
    from .packet_score import CAP_TOKENS, GROUP_PLANS

    over = _prompt_overhead(coders, names)
    out = {}
    for n in names:
        cap = coders[n].get("max_packet_tokens") or CAP_TOKENS
        g = len(GROUP_PLANS[int(coders[n].get("groups", 1))])
        tot = 0
        for v in plan["variants"]:
            tok = int(read_json(Path(run) / "packets" / v["bench"] / "manifest.json")["total_chunk_tokens"])
            tot += g * min(tok, cap) + over[n]
        out[n] = {"calls": len(plan["variants"]) * g, "input_tokens_est": tot}
    return out


def perturb_variant_path(run: Path, variant: str, coder: str) -> Path:
    return Path(run) / "perturb" / variant / f"{coder}.json"


def run_perturb_variants(run: Path, plan: dict, coders: dict[str, tuple[dict, object]], force: bool = False,
                         log=print, dry_run: bool = False) -> dict:
    """Score every variant packet with every coder: one whole-packet call over all 25 items (or the coder's fixed
    item groups). Records go to ``perturb/<variant>/<coder>.json``; the plan (with dropped cells) to
    ``perturb/plan.json``.

    coders: name -> (spec, backend)."""
    from .packet_score import CAP_TOKENS, GROUP_PLANS, packet_system_prompt, parse_packet_response, render_packet_prompt
    from .prompts import prompt_hash
    from .util import normalise
    from .verify import verify_result

    items = load_items()
    system = packet_system_prompt()
    summary = {"done": 0, "skipped": 0, "failed": [], "blocked": None, "variants": len(plan["variants"]),
               "cells": plan["n_cells"], "cells_dropped": plan["n_dropped"],
               "variants_skipped": len(plan["skipped_variants"])}
    if not dry_run:
        write_json(Path(run) / "perturb" / "plan.json", {k: v for k, v in plan.items() if k != "variants"} | {
            "variants": [{"variant": v["variant"], "benchmark": v["benchmark"], "n_cells": len(v["cells"])}
                         for v in plan["variants"]]})
    for pv in plan["variants"]:
        cells = [(cell_variant(c), c["slot"]) for c in pv["cells"]]
        meta = {c["item"]: c for c in pv["cells"]}
        srcs = load_sources(run, pv["bench"])
        by_cap: dict[int, dict] = {}
        for cname, (spec, backend) in coders.items():
            p = perturb_variant_path(run, pv["variant"], cname)
            if p.exists() and not force:
                try:
                    if read_json(p).get("status") == "ok":
                        summary["skipped"] += 1
                        continue
                except ValueError:
                    pass
            cap = int(spec.get("max_packet_tokens") or CAP_TOKENS)
            if cap not in by_cap:
                by_cap[cap] = variant_packet(srcs, cells, cap)
            vp = by_cap[cap]
            plan_g = GROUP_PLANS[int(spec.get("groups", 1))]
            if dry_run:
                summary["done"] += 1
                continue
            rec = {"variant": pv["variant"], "benchmark": pv["benchmark"], "bench": pv["bench"], "coder": cname,
                   "family": spec.get("family"), "mode": "packet_v3_multiplexed", "cap_tokens": cap,
                   "rendered_packet_sha256": sha256_text(vp["text"]), "n_dropped_chunks": len(vp["sel"]["dropped"]),
                   "over_cap": vp["sel"]["over_cap"], "groups": plan_g, "attempts": [], "items": {}, "cells": {},
                   "status": "parse_error"}
            best_ok: dict[str, dict] = {}
            best_err: dict[str, str] = {}
            try:
                for gi, group in enumerate(plan_g, 1):
                    prompt = render_packet_prompt(vp["text"], group, items)
                    rec.setdefault("prompt_sha256", {})[str(gi)] = prompt_hash(prompt)
                    g_ok: dict[str, dict] = {}
                    g_err: dict[str, str] = {i: "missing from response" for i in group}
                    for _ in range(2):
                        resp = backend.complete(system, prompt)
                        att = {"group": gi, "timestamp": utcnow(), "model_id": resp.model_id, "usage": resp.usage,
                               "meta": resp.meta, "raw_response": resp.text}
                        rec["attempts"].append(att)
                        rec["model_id"] = resp.model_id
                        try:
                            ok, err = parse_packet_response(resp.text, group, items)
                        except ParseError as e:
                            att["parse_error"] = str(e)
                            continue
                        if len(ok) >= len(g_ok):
                            g_ok, g_err = ok, err
                        if not err:
                            break
                    best_ok.update(g_ok)
                    best_err.update({i: e for i, e in g_err.items() if i not in g_ok})
            except DailyLimitReached as e:
                summary["blocked"] = {"variant": pv["variant"], "coder": cname, "reason": str(e),
                                      "next_available_unix": e.next_available}
                log(f"[{cname}] daily limit reached at {pv['variant']}; rerun to resume")
                return summary
            except BackendAuthError as e:
                summary["blocked"] = {"variant": pv["variant"], "coder": cname, "reason": f"authentication: {e}"}
                log(f"[{cname}] backend authentication failed: {e}")
                return summary
            except BackendError as e:
                summary["failed"].append({"variant": pv["variant"], "coder": cname, "error": str(e)})
                log(f"[{cname}] {pv['variant']} backend error: {e}")
                continue
            for iid, parsed in best_ok.items():
                if "strict" not in vp:
                    vp["strict"] = {k: normalise(t) for k, t in vp["kept_texts"].items()}
                rec["items"][iid] = {"parsed": parsed, "verification": verify_result(
                    parsed, items[iid], vp["kept_texts"], (vp["strict"], vp["lnorm"]))}
            for v, slot in cells:
                c = meta[v.item]
                rec["cells"][v.item] = {"variant": asdict(v), "slot": slot, "expected": v.expected,
                                        "expectation": v.expectation, "base_level": v.base_level,
                                        "variant_text_in_packet": vp["hits"].get(v.item),
                                        "s4_comment_in_packet": vp["s4_hits"].get(v.item) if c["s4_comment"] else None}
            rec["item_errors"] = best_err
            rec["status"] = "ok" if not best_err else "partial" if best_ok else "parse_error"
            rec["timestamp"] = rec["attempts"][-1]["timestamp"] if rec["attempts"] else utcnow()
            write_json(p, rec)
            if rec["status"] == "ok":
                summary["done"] += 1
            else:
                summary["failed"].append({"variant": pv["variant"], "coder": cname, "error": rec["status"]})
            log(f"[{cname}] {pv['variant']} ({pv['benchmark']}): {rec['status']} "
                f"({len(best_ok)}/{sum(len(g) for g in plan_g)} items)")
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


def _records(run: Path, names: list[str] | None):
    """Normalised (unit, item, coder, family, variant dict, verification, in_packet) from both record layouts:
    perturb/<variant>/<coder>.json (multiplexed) and perturb/<bench>/<item>/<type>/<coder>.json (retrieval ablation)."""
    base = Path(run) / "perturb"
    if not base.exists():
        return
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        if names is not None and d.name not in names:
            continue
        for f in sorted(d.glob("*.json")):
            rec = read_json(f)
            if rec.get("status") not in ("ok", "partial"):
                continue
            for it, c in rec.get("cells", {}).items():
                ver = (rec["items"].get(it) or {}).get("verification")
                if ver:
                    yield (d.name, it, rec["coder"], rec.get("family"), c["variant"], ver, c.get("variant_text_in_packet"))
        for f in sorted(d.glob("*/*/*.json")):
            rec = read_json(f)
            if rec.get("status") == "ok" and rec.get("verification"):
                yield (d.name, rec["item"], rec["coder"], rec.get("family"), rec["variant"], rec["verification"],
                       rec.get("variant_text_in_retrieval"))


def summarise(run: Path, names: list[str] | None = None) -> dict:
    """Sensitivity (inject, buried, paraphrase: coder reaches level 2) and specificity (deletion: level 0;
    decoy: not above the base level) with Wilson 95% intervals, per coder and RESOLVED (two-family rule applied to
    the coders' votes on the same cell); overall, per variant type, per item, per item and type. ``names``:
    variant ids (or packet directories for the retrieval ablation); default all."""
    rows: list[dict] = []
    votes_by: dict[tuple, dict] = {}
    for unit, it, coder, fam, var, ver, ins in _records(run, names):
        lv = _level(ver["effective"])
        rows.append({"variant_id": unit, "item": it, "vtype": var["vtype"], "coder": coder, "level": lv,
                     "expected": var["expected"], "expectation": var["expectation"],
                     "base_level": var.get("base_level"), "ok": _ok(var, lv), "ok_drop": _ok_drop(var, lv),
                     "retrieved": ins, "s4": bool(var.get("s4_comment"))})
        slot = votes_by.setdefault((unit, it, var["vtype"]), {"var": var, "votes": {}})
        slot["votes"][coder] = {"raw": ver["score_raw"], "effective": ver["effective"], "family": fam}
    for (unit, it, vt), d in sorted(votes_by.items()):
        if len(d["votes"]) < 2:
            continue
        var = d["var"]
        lv = _level(resolve_cell(d["votes"])["final"])
        rows.append({"variant_id": unit, "item": it, "vtype": vt, "coder": "RESOLVED", "level": lv,
                     "expected": var["expected"], "expectation": var["expectation"],
                     "base_level": var.get("base_level"), "ok": _ok(var, lv), "ok_drop": _ok_drop(var, lv),
                     "retrieved": None, "s4": bool(var.get("s4_comment"))})

    out: dict = {"n_rows": len(rows), "note": "validity under perturbation, not ground truth",
                 "labels": {"inject/buried/paraphrase": "sensitivity = level 2 reached (any level >= 1 also reported)",
                            "deletion": "specificity = level 0 (secondary: level below the base level)",
                            "decoy": "specificity = level not above the base level"},
                 "by_coder": {}}
    pj = Path(run) / "perturb" / "plan.json"
    if pj.exists():
        pl = read_json(pj)
        by_reason: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for d in pl.get("dropped", []):
            by_reason[d["reason"]] = by_reason.get(d["reason"], 0) + 1
            by_type[d["vtype"]] = by_type.get(d["vtype"], 0) + 1
        out["design"] = {"variants_run": len(pl.get("variants", [])), "variants_skipped": pl.get("skipped_variants", []),
                         "cells_scored_planned": pl.get("n_cells"), "cells_dropped": pl.get("n_dropped"),
                         "dropped_by_reason": by_reason, "dropped_by_type": by_type}
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
        dec = {"decoy_s1": [r for r in sel if r["vtype"] == "decoy" and not r["s4"]],
               "decoy_s4_comment": [r for r in sel if r["vtype"] == "decoy" and r["s4"]]}
        c["decoy_by_surface"] = {k: _metric(v)["specificity"] for k, v in dec.items() if v}
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
