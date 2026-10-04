"""Architecture v3: whole-packet scoring (``agentaudit score-packet``).

One call per (benchmark, coder, item group) carries the whole evidence packet (every chunk with its id,
grouped by surface S1..S5) and the item definitions (anchors, NA clauses, G1-G7) from items.yaml, and
returns one JSON object per item. There is no retrieval step.

Packet cap: 150,000 tokens at 4 characters per token (rendered text, chunk headers included). If the packet is
over the cap, S4 chunks that are not S5 are dropped deterministically: files in order of total S4 (non-S5)
tokens, largest first, ties by path; within a file in line order; whole chunks only; until the packet is
under the cap. Everything dropped is listed in ``packet_manifest.json``. S1, S2, S3 and S5 chunks are never
dropped (a packet still over the cap after all S4 non-S5 chunks are gone is flagged ``over_cap``).

Item groups (fixed, documented; used only when a backend's context or output limit requires it, set per
coder with ``--groups``): 1 = all 25 items in one call; 2 = [C1-C14] + [A1-A11]; 3 = [C1-C9] +
[C10-C14, A1-A4] + [A5-A11]. Every call for a coder sends the same packet.

Output per (benchmark, coder), under ``<run>/scoring/<bench>/<coder>/``: ``packet_manifest.json``,
``group<N>.json`` (raw responses, model id, hashes), ``results.json`` (JSON array of 25 objects
{item, score, elements, quotes, contradicted, contradiction_quotes, s5_reach, rationale}). Each parsed
item is also written in the per-cell layout ``coding/<bench>/<item>/<coder>.json`` so verify, resolve and
agree work unchanged; those records carry ``evidence_scope: "packet_v3"`` and are verified against the
chunks that were actually sent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .backends import BackendAuthError, BackendError
from .chunking import Chunk
from .coding import ParseError, parse_obj
from .items import ITEM_ORDER, Item, global_rules, load_items, na_clause_text, scale_text
from .packet import load_chunks
from .prompts import S5_ITEMS, load_template, prompt_hash
from .throttle import DailyLimitReached
from .util import est_tokens, read_json, sha256_text, utcnow, write_json

CAP_TOKENS = 150_000

GROUP_PLANS: dict[int, list[list[str]]] = {
    1: [list(ITEM_ORDER)],
    2: [[f"C{i}" for i in range(1, 15)], [f"A{i}" for i in range(1, 12)]],
    3: [[f"C{i}" for i in range(1, 10)],
        [f"C{i}" for i in range(10, 15)] + [f"A{i}" for i in range(1, 5)],
        [f"A{i}" for i in range(5, 12)]],
}

SURFACES = [("S1", "S1: paper and appendix"), ("S2", "S2: README and docs"), ("S3", "S3: release notes and changelog"),
            ("S4", "S4: code and configuration (not agent-visible)"),
            ("S5", "S5: agent-visible prompts and tool descriptions (found in code)")]


def surface_of(c: Chunk) -> str:
    return "S5" if c.s5 else c.surface


def render_entry(c: Chunk) -> str:
    return f"### [{c.id}] path={c.path}\n{c.text}"


def select_packet(chunks: list[Chunk], cap_tokens: int = CAP_TOKENS) -> dict:
    """Apply the cap. Returns {kept, dropped, tokens, over_cap, ...}; ``kept`` keeps the input order."""
    def total(cs):
        return sum(len(render_entry(c)) + 2 for c in cs) + 200 * len(SURFACES)

    kept = list(chunks)
    cur = total(kept)
    pre_tokens = est_tokens("x" * cur)
    dropped: list[dict] = []
    if pre_tokens > cap_tokens:
        size: dict[str, int] = {}
        for c in chunks:
            if c.surface == "S4" and not c.s5:
                size[c.path] = size.get(c.path, 0) + c.tokens
        order = sorted((c for c in chunks if c.surface == "S4" and not c.s5),
                       key=lambda c: (-size[c.path], c.path, c.start))
        gone = set()
        for c in order:
            if est_tokens("x" * cur) <= cap_tokens:
                break
            gone.add(c.id)
            cur -= len(render_entry(c)) + 2
            dropped.append({"id": c.id, "path": c.path, "tokens": c.tokens, "file_s4_tokens": size[c.path]})
        kept = [c for c in chunks if c.id not in gone]
    return {"kept": kept, "dropped": dropped, "tokens_before": pre_tokens, "tokens": est_tokens("x" * cur),
            "over_cap": est_tokens("x" * cur) > cap_tokens, "cap_tokens": cap_tokens}


def render_packet(kept: list[Chunk]) -> str:
    out = []
    for key, title in SURFACES:
        cs = sorted((c for c in kept if surface_of(c) == key), key=lambda c: (c.path, c.start))
        out.append(f"## {title}\n\n" + ("\n\n".join(render_entry(c) for c in cs) if cs else "(no chunks)"))
    return "\n\n".join(out)


def render_item_block(item: Item, items: dict[str, Item]) -> str:
    na = na_clause_text(item.id, items)
    if item.module == "agent":
        el = ('"elements": three booleans for elements (i), (ii), (iii), true when the packet shows that element '
              "on S1-S3.")
    else:
        el = '"elements": [] (core items have no element list).'
    s5 = ""
    if item.id in S5_ITEMS:
        s5 = ('"s5_reach": whether the property in element (ii) reaches the agent-visible surface (S5): true, '
              "false, or null when it cannot be told.\n")
    na_text = ("None. NA is not allowed for this item: \"not mentioned\" is 0, never NA (G7)." if na is None
               else f"{na}\nAnswer \"NA\" only if this clause applies; \"not mentioned\" is 0, never NA (G7).")
    return (f"### Item {item.id}: {item.title}\n{item.item_text}\n\n#### Anchors (coding manual v1.0)\n{item.anchors}\n\n"
            f"#### NA clause\n{na_text}\n\n#### Fields for this item\n{el}\n{s5}")


def render_packet_prompt(packet_text: str, group: list[str], items: dict[str, Item]) -> str:
    t = load_template("packet.txt")
    blocks = "\n\n".join(render_item_block(items[i], items) for i in group)
    rep = {"{{SCALE}}": scale_text(), "{{GLOBAL_RULES}}": global_rules(), "{{ITEM_BLOCKS}}": blocks,
           "{{ITEM_IDS}}": ", ".join(group), "{{N_ITEMS}}": str(len(group))}
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.replace("{{PACKET}}", packet_text)  # last, so packet text is never re-expanded


def packet_system_prompt() -> str:
    return load_template("packet_system.txt").strip()


def _strip_fence(t: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", t.strip(), flags=re.I)


def extract_array(text: str) -> list:
    t = _strip_fence(text)
    obj = None
    try:
        obj = json.loads(t)
    except ValueError:
        i, j = t.find("["), t.rfind("]")
        if i >= 0 and j > i:
            try:
                obj = json.loads(t[i:j + 1])
            except ValueError:
                obj = None
        if obj is None:
            i, j = t.find("{"), t.rfind("}")
            if i >= 0 and j > i:
                try:
                    obj = json.loads(t[i:j + 1])
                except ValueError as e:
                    raise ParseError(f"invalid JSON: {e}") from e
    if obj is None:
        raise ParseError("no JSON in response")
    if isinstance(obj, dict):
        lists = [v for v in obj.values() if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)]
        if lists:
            obj = lists[0]
        elif "item" in obj:
            obj = [obj]
        else:  # {"C1": {...}, "C2": {...}}
            vals = [dict(v, item=k) for k, v in obj.items() if isinstance(v, dict) and "score" in v]
            if not vals:
                raise ParseError("JSON object holds no item list")
            obj = vals
    if not isinstance(obj, list):
        raise ParseError("JSON is not an array")
    return obj


def parse_packet_response(text: str, group: list[str], items: dict[str, Item]) -> tuple[dict[str, dict], dict[str, str]]:
    """Return ({item: parsed}, {item: error}) for the items of a group."""
    arr = extract_array(text)
    ok: dict[str, dict] = {}
    err: dict[str, str] = {}
    for o in arr:
        if not isinstance(o, dict):
            continue
        iid = str(o.get("item", o.get("id", ""))).strip().upper()
        if iid not in group or iid in ok:
            continue
        try:
            ok[iid] = parse_obj(o, items[iid])
        except ParseError as e:
            err[iid] = str(e)
    for iid in group:
        if iid not in ok and iid not in err:
            err[iid] = "missing from response"
    return ok, err


# -- paths
def scoring_dir(run: Path, bench: str, coder: str) -> Path:
    return Path(run) / "scoring" / bench / coder


def packet_chunk_texts(run: Path, bench: str, coder: str) -> dict[str, str]:
    """Chunk id -> text for the chunks that were sent to ``coder`` (from its packet manifest)."""
    man = read_json(scoring_dir(run, bench, coder) / "packet_manifest.json")
    keep = set(man["kept_ids"])
    return {c.id: c.text for c in load_chunks(run, bench) if c.id in keep}


def score_packet(run: Path, bench: str, coder: str, spec: dict, backend, groups: int = 1, cap_tokens: int | None = None,
                 force: bool = False, log=print, dry_run: bool = False) -> dict:
    items = load_items()
    cap = int(cap_tokens or spec.get("max_packet_tokens") or CAP_TOKENS)
    chunks = load_chunks(run, bench)
    sel = select_packet(chunks, cap)
    packet_text = render_packet(sel["kept"])
    plan = GROUP_PLANS[groups]
    pdir = scoring_dir(run, bench, coder)
    pman = read_json(Path(run) / "packets" / bench / "manifest.json")
    write_json(pdir / "packet_manifest.json", {
        "bench": bench, "coder": coder, "built_utc": utcnow(), "packet_sha256": pman.get("packet_sha256"),
        "rendered_packet_sha256": sha256_text(packet_text), "cap_tokens": cap,
        "tokens_before_cap": sel["tokens_before"], "tokens_sent": sel["tokens"], "over_cap": sel["over_cap"],
        "n_chunks_total": len(chunks), "n_chunks_kept": len(sel["kept"]), "n_dropped": len(sel["dropped"]),
        "dropped": sel["dropped"], "kept_ids": [c.id for c in sel["kept"]],
        "groups": plan, "drop_rule": "S4 non-S5 chunks, files by total S4 tokens desc then path, chunks in line order"})
    summary = {"coder": coder, "bench": bench, "tokens_sent": sel["tokens"], "dropped": len(sel["dropped"]),
               "groups": len(plan), "done": [], "failed": [], "blocked": None}
    system = packet_system_prompt()
    if dry_run:  # no backend call: report the size of every prompt
        summary["prompt_tokens_est"] = [est_tokens(system) + est_tokens(render_packet_prompt(packet_text, g, items))
                                        for g in plan]
        return summary
    for gi, group in enumerate(plan, 1):
        gp = pdir / f"group{gi}.json"
        if gp.exists() and not force:
            try:
                if read_json(gp).get("status") == "ok":
                    summary["done"].extend(group)
                    log(f"[{coder}] {bench} group{gi}: already done")
                    continue
            except ValueError:
                pass
        prompt = render_packet_prompt(packet_text, group, items)
        rec = {"bench": bench, "coder": coder, "group": gi, "items": group, "prompt_sha256": prompt_hash(prompt),
               "system_sha256": prompt_hash(system), "prompt_tokens_est": est_tokens(prompt), "attempts": [],
               "status": "parse_error"}
        best_ok: dict[str, dict] = {}
        best_err: dict[str, str] = {}
        try:
            for _ in range(2):
                resp = backend.complete(system, prompt)
                att = {"timestamp": utcnow(), "model_id": resp.model_id, "usage": resp.usage, "meta": resp.meta,
                       "raw_response": resp.text}
                rec["attempts"].append(att)
                rec["model_id"] = resp.model_id
                try:
                    ok, err = parse_packet_response(resp.text, group, items)
                except ParseError as e:
                    att["parse_error"] = str(e)
                    continue
                att["item_errors"] = err
                if len(ok) >= len(best_ok):
                    best_ok, best_err = ok, err
                if not err:
                    break
        except DailyLimitReached as e:
            summary["blocked"] = {"group": gi, "next_available_unix": e.next_available, "reason": str(e)}
            log(f"[{coder}] daily limit reached at group{gi}; rerun after the limit resets to resume")
            break
        except BackendAuthError as e:
            summary["blocked"] = {"group": gi, "reason": f"authentication: {e}"}
            log(f"[{coder}] backend authentication failed: {e}")
            break
        except BackendError as e:
            rec["error"] = str(e)
            write_json(gp, rec)
            summary["failed"].append({"group": gi, "error": str(e)})
            log(f"[{coder}] {bench} group{gi} backend error: {e}")
            continue
        rec["status"] = "ok" if not best_err else "partial" if best_ok else "parse_error"
        rec["item_errors"] = best_err
        rec["timestamp"] = rec["attempts"][-1]["timestamp"]
        write_json(gp, rec)
        for iid, parsed in best_ok.items():
            write_json(Path(run) / "coding" / bench / iid / f"{coder}.json", {
                "bench": bench, "item": iid, "coder": coder, "family": spec.get("family"),
                "backend": spec["backend"], "requested_model": spec.get("model"), "model_id": rec["model_id"],
                "status": "ok", "parsed": parsed, "evidence_scope": "packet_v3", "group": gi,
                "prompt_sha256": rec["prompt_sha256"], "packet_sha256": pman.get("packet_sha256"),
                "timestamp": rec["timestamp"]})
        summary["done"].extend(best_ok)
        summary["failed"].extend({"item": i, "error": e} for i, e in best_err.items())
        log(f"[{coder}] {bench} group{gi}: {rec['status']} ({len(best_ok)}/{len(group)} items, model {rec['model_id']})")
    done = [i for i in ITEM_ORDER if i in set(summary["done"])]
    if done:
        arr = []
        for iid in done:
            r = read_json(Path(run) / "coding" / bench / iid / f"{coder}.json")["parsed"]
            arr.append({"item": iid, "score": r["score"], "elements": r["elements"], "quotes": r["quotes"],
                        "contradicted": r["contradicted"], "contradiction_quotes": r["contradiction_quotes"],
                        "s5_reach": r.get("s5_reach"), "rationale": r["rationale"]})
        write_json(pdir / "results.json", arr)
        from .verify import run_verify

        run_verify(run, bench, done, [coder])
        summary["verification"] = verification_stats(run, bench, coder)
    return summary


def verification_stats(run: Path, bench: str, coder: str) -> dict:
    """Quote verification rate (loose rule) over the coder's verified cells."""
    nq = nv = nvs = cells12 = supported = 0
    for f in sorted((Path(run) / "verified" / bench).glob(f"*/{coder}.json")):
        v = read_json(f)
        nq += v["n_quotes"]
        nv += v["n_verified"]
        nvs += v["n_verified_strict"]
        if v["score_raw"] in (1, 2):
            cells12 += 1
            supported += 1 if v["supported"] else 0
    return {"quotes": nq, "verified": nv, "verified_strict": nvs,
            "quote_verification_rate": (nv / nq if nq else None),
            "strict_rate": (nvs / nq if nq else None),
            "cells_scored_1_or_2": cells12, "cells_supported": supported}
