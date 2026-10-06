"""Diagnosis of the perturbation-specificity result (Claude Sonnet only; 2026-10-06). Analysis side only.

Reads, never writes, the frozen run under audit/perturb/ and imports the frozen scorer package read-only. No LLM calls.
Writes analysis/out/perturb_diagnosis.md and analysis/out/perturb_diagnosis_cells.csv.

Why this can be done offline: every variant record stores each cell's variant definition and the coder's quotes with
their verification result. The variant packet is rebuilt here with the frozen ``variant_packet``; the hash of the
rebuilt packet is checked against the hash stored in the record. A quote's chunk, surface, S5 flag and provenance
(original text, the cell's own inserted text, or text inserted for another item) are therefore exact.

Q1  Deletion failures (perturbed effective level > 0). Classes, from the provenance and surface of verified quotes:
      (a) alternative on-surface evidence remains: at least one verified quote lies in ORIGINAL (not inserted) text on a
          surface that counts for the item (S1-S3; S5 only for A5, A6, A7; coding manual G1a). The label "expected
          level 0" is then wrong by construction.
      (b) no verified quote. Cannot occur with a positive effective level (``verify_result`` sets a 1 or 2 without a
          verified quote to 0); counted as a check.
      (c) other: verified quotes lie only in text inserted for another item (c1, cross-item interference) or only on a
          surface that never counts (c2, S4 code, or S5 outside A5-A7: a G1a violation).
Q2  Decoy failures (perturbed level > resolved base level), by subtype (S1 near-miss, S4 comment).
Q3  Secondary specificities: the coder's own base score as reference; class (a) deletion cells removed.

Provenance rule: loose normalisation (letters and digits only, as in the frozen verifier); a quote belongs to an
inserted text if every fragment is inside it, or the inserted text is inside the quote.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from common import OUT, ROOT, SEED, write_csv

from agentaudit.items import ITEM_ORDER  # noqa: E402
from agentaudit.packet import load_sources  # noqa: E402
from agentaudit.perturb import Variant, variant_packet  # noqa: E402
from agentaudit.stats import wilson  # noqa: E402
from agentaudit.util import loose_normalise, read_json, sha256_text  # noqa: E402
from agentaudit.verify import _ELLIPSIS  # noqa: E402

RUN = ROOT / "audit" / "perturb"
CODER = "sonnet"
S5_ITEMS = {"A5", "A6", "A7"}  # S5 counts only for these (coding manual G1a)

# Manual reading of a seeded sample of class (a) cells (see MANUAL_NOTE); filled in after reading, kept here so the
# report regenerates identically.
SAMPLE_VERDICT = {
    ("v16", "C2"): "supports", ("v03", "C4"): "supports", ("v23", "C4"): "supports",
    ("v28", "A7"): "supports; element (i) only, a second quote is cross-item",
    ("v20", "A3"): "supports", ("v19", "A8"): "partial; original quote covers the grader input, level 2 needs cross-item validation text",
    ("v06", "A6"): "supports", ("v30", "A10"): "supports",
    ("v26", "A8"): "partial; level 2 needs cross-item validation text",
    ("v24", "A10"): "thin; a table header only, level 1 plausible", ("v23", "A7"): "supports",
    ("v05", "C1"): "supports", ("v17", "A9"): "partial; one original quote, leakage controls come from cross-item text",
    ("v05", "A4"): "supports; second quote cross-item", ("v16", "A8"): "supports", ("v39", "C2"): "supports",
}
DECOY_READING = {
    ("v02", "A6"): "original disclosure that the patient agent generates answers; level 1 equals own base; the decoy sentence was not cited",
    ("v04", "C7"): "original text: unpinned GPT-4o judge; level 1 equals own base",
    ("v11", "A11"): "original S1/S2 text (synthetic data, separate terms); the coder explicitly treats the S1 note and S4 comment as contradicting, not as reporting",
    ("v20", "C3"): "decoy text 'cases were chosen to cover a diverse range of conditions' is a stated selection rule, which meets the C3 level-1 anchor; base 0 to 1 is a decoy-design fault, not coder error",
    ("v26", "C1"): "original S1/S2 text (named cohorts, manifest check); level 2 equals own base",
    ("v33", "A7"): "mixed: cites the decoy ('simulated environment'), an original action-type sentence and cross-item text; level 2 above own base 1",
}


def lv(x) -> int:
    return 0 if x == "NA" else int(x)


def frags(text: str) -> list[str]:
    return [f for f in (loose_normalise(x) for x in _ELLIPSIS.split(text or "")) if f]


def matches(fr: list[str], t: str) -> bool:
    return bool(fr and t) and (all(f in t for f in fr) or t in "".join(fr))


def pct(h: int, n: int) -> str:
    if not n:
        return "n/a"
    lo, hi = wilson(h, n)
    return f"{h}/{n} = {100 * h / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def own_base(bench: str, item: str) -> dict:
    p = RUN / "verified" / bench / item / f"{CODER}.json"
    v = read_json(p)
    return {"raw": v["score_raw"], "level": lv(v["effective"])}


def base_chunks(bench: str) -> dict[str, str]:
    out = {}
    with open(RUN / "packets" / bench / "chunks.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out[d["id"]] = d["text"]
    return out


def load_cells() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    checks = {"variants": 0, "hash_ok": 0}
    for d in sorted((RUN / "perturb").glob("v*"), key=lambda p: p.name):
        rec = read_json(d / f"{CODER}.json")
        checks["variants"] += 1
        cells = [(Variant(**c["variant"]), c["slot"]) for c in rec["cells"].values()]
        vp = variant_packet(load_sources(RUN, rec["bench"]), cells, rec["cap_tokens"])
        if sha256_text(vp["text"]) == rec["rendered_packet_sha256"]:
            checks["hash_ok"] += 1
        kept = {c.id: c for c in vp["sel"]["kept"]}
        ins = {v.item: (v.vtype, v.s4_comment, loose_normalise(v.text)) for v, _ in cells if v.text}
        bch = None
        for v, slot in cells:
            it = v.item
            ver = (rec["items"].get(it) or {}).get("verification")
            if not ver:
                continue
            level = lv(ver["effective"])
            parsed = rec["items"][it]["parsed"]
            qs = []
            for q in ver["quotes"]:
                if not q["verified"]:
                    continue
                ch = kept.get(q["chunk_id"])
                fr = frags(q["text"])
                prov = "orig"
                hit = None
                if matches(fr, ins.get(it, (0, 0, ""))[2]):
                    prov, hit = "own", it
                else:
                    for o, (ovt, os4, ot) in ins.items():
                        if o != it and matches(fr, ot):
                            prov, hit = "other", f"{o}/{ovt}"
                            break
                surf = "S5" if (ch is not None and ch.s5) else (ch.surface if ch is not None else "?")
                counting = surf in ("S1", "S2", "S3") or (surf == "S5" and it in S5_ITEMS)
                qs.append({"chunk_id": q["chunk_id"], "text": q["text"], "prov": prov, "hit": hit, "surface": surf,
                           "counting": counting, "strict": q["verified_strict"], "frags": fr})
            row = {"variant": rec["variant"], "bench": rec["bench"], "item": it, "vtype": v.vtype,
                   "s4": bool(v.s4_comment), "base_resolved": v.base_level, "level": level,
                   "raw": ver["score_raw"], "own_base": own_base(rec["bench"], it)["level"],
                   "own_base_raw": own_base(rec["bench"], it)["raw"], "quotes": qs,
                   "rationale": parsed.get("rationale", ""), "removed": v.removed_chunk_ids or [],
                   "decoy_text": v.text if v.vtype == "decoy" else None}
            if v.vtype == "deletion":
                if bch is None:
                    bch = base_chunks(rec["bench"])
                deleted = loose_normalise(" ".join(bch.get(c, "") for c in v.removed_chunk_ids or []))
                for q in qs:
                    q["in_deleted_text"] = bool(q["frags"]) and all(f in deleted for f in q["frags"])
            rows.append(row)
    return rows, checks


def classify(r: dict) -> tuple[str, str]:
    qs = r["quotes"]
    if r["vtype"] == "deletion":
        if r["level"] == 0:
            return "pass", ""
        if not qs:
            return "b", "no verified quote"
        if any(q["prov"] == "orig" and q["counting"] for q in qs):
            return "a", "/".join(sorted({q["surface"] for q in qs if q["prov"] == "orig" and q["counting"]}))
        if any(q["prov"] == "other" for q in qs):
            return "c", "c1 cross-item inserted text"
        return "c", "c2 non-counting surface"
    if r["vtype"] == "decoy":
        if r["level"] <= r["base_resolved"]:
            return "pass", ""
        if not qs:
            return "none", "no verified quote"
        if any(q["prov"] == "own" for q in qs):
            return ("S4 comment credited" if r["s4"] else "near-miss credited"), ""
        if any(q["prov"] == "other" for q in qs):
            return "cross-item inserted text", ""
        if r["level"] <= r["own_base"]:
            return "own-base artefact", ""
        return "other original evidence above own base", ""
    return "n/a", ""


def main() -> None:
    rows, chk = load_cells()
    neg = [r for r in rows if r["vtype"] in ("deletion", "decoy")]
    for r in neg:
        r["cls"], r["sub"] = classify(r)
    dele = [r for r in neg if r["vtype"] == "deletion"]
    dec = [r for r in neg if r["vtype"] == "decoy"]
    dec_s1 = [r for r in dec if not r["s4"]]
    dec_s4 = [r for r in dec if r["s4"]]

    # reproduction of the frozen summary
    sj = read_json(RUN / "perturb" / "summary.json")["by_coder"][CODER]
    repro = {"deletion": (sum(r["level"] == 0 for r in dele), len(dele)),
             "decoy": (sum(r["level"] <= r["base_resolved"] for r in dec), len(dec))}
    assert repro["deletion"] == (sj["by_variant"]["deletion"]["specificity"]["hits"], sj["by_variant"]["deletion"]["specificity"]["n"])
    assert repro["decoy"] == (sj["by_variant"]["decoy"]["specificity"]["hits"], sj["by_variant"]["decoy"]["specificity"]["n"])
    assert chk["variants"] == chk["hash_ok"] == 39

    # own base never below resolved base?
    below = sum(1 for r in neg if r["own_base"] < (r["base_resolved"] or 0))
    own_gt = sum(1 for r in neg if r["own_base"] > (r["base_resolved"] or 0))

    # --- Q1
    dfail = [r for r in dele if r["level"] > 0]
    c1 = Counter(r["cls"] for r in dfail)
    n_a, n_b, n_c = c1["a"], c1["b"], c1["c"]
    a_cells = [r for r in dfail if r["cls"] == "a"]
    a_surf = Counter(r["sub"] for r in a_cells)
    a_dup = sum(1 for r in a_cells if any(q["prov"] == "orig" and q["counting"] and q.get("in_deleted_text") for q in r["quotes"]))
    a_strict = sum(1 for r in a_cells if any(q["prov"] == "orig" and q["counting"] and q["strict"] for q in r["quotes"]))
    a_ge_own = sum(1 for r in a_cells if r["level"] >= r["own_base"])
    a_same_chunkfile = 0
    c_sub = Counter(r["sub"] for r in dfail if r["cls"] == "c")
    dele_ids = Counter(r["item"] for r in dfail)
    a_by_item = Counter(r["item"] for r in a_cells)
    n_del_by_item = Counter(r["item"] for r in dele)

    # --- Q2
    def decoy_table(cs: list[dict]) -> Counter:
        return Counter(r["cls"] for r in cs if r["cls"] != "pass")

    d1, d4 = decoy_table(dec_s1), decoy_table(dec_s4)
    f1 = [r for r in dec_s1 if r["cls"] != "pass"]
    f4 = [r for r in dec_s4 if r["cls"] != "pass"]
    ge_own1 = sum(1 for r in f1 if r["level"] <= r["own_base"])
    ge_own4 = sum(1 for r in f4 if r["level"] <= r["own_base"])
    cred1_le_own = sum(1 for r in f1 if r["cls"] == "near-miss credited" and r["level"] <= r["own_base"])
    cred4_le_own = sum(1 for r in f4 if r["cls"] == "S4 comment credited" and r["level"] <= r["own_base"])

    trans = Counter((r["base_resolved"], r["level"], "S4" if r["s4"] else "S1") for r in dec if r["cls"] != "pass")
    hit_types = Counter()
    pairs = Counter()
    for r in neg:
        if r["cls"] == "cross-item inserted text" or r["sub"].startswith("c1"):
            q = next(q for q in r["quotes"] if q["prov"] == "other")
            hit_types[(r["vtype"], q["hit"].split("/")[1])] += 1
            pairs[(r["item"], q["hit"].split("/")[0])] += 1
    n_cross = sum(hit_types.values())
    cross_dec = sum(v for (vt, _), v in hit_types.items() if vt == "decoy")
    s4_cells = [r for r in dec_s4]
    s4_quote_cells = sum(1 for r in s4_cells if any(q["surface"] == "S4" and not q["counting"] for q in r["quotes"]))
    s4_own_cells = sum(1 for r in s4_cells if any(q["prov"] == "own" for q in r["quotes"]))
    a_mixed = sum(1 for r in a_cells if any(q["prov"] == "other" for q in r["quotes"]))
    a_above_own = sum(1 for r in a_cells if r["level"] > r["own_base"])
    a_clean = sum(1 for r in a_cells if not any(q["prov"] == "other" for q in r["quotes"]) and r["level"] <= r["own_base"])

    # --- Q3
    own_dec_ok = sum(r["level"] <= r["own_base"] for r in dec)
    own_dec1_ok = sum(r["level"] <= r["own_base"] for r in dec_s1)
    own_dec4_ok = sum(r["level"] <= r["own_base"] for r in dec_s4)
    prim_dec_ok = repro["decoy"][0]
    prim_dec1_ok = sum(r["level"] <= r["base_resolved"] for r in dec_s1)
    prim_dec4_ok = sum(r["level"] <= r["base_resolved"] for r in dec_s4)
    del0 = repro["deletion"][0]
    drop_res = sum(r["level"] < r["base_resolved"] for r in dele)
    drop_own = sum(r["level"] < r["own_base"] for r in dele)
    n_dele, n_dec = len(dele), len(dec)
    ex_a = n_dele - n_a
    ex_ac1 = n_dele - n_a - c_sub["c1 cross-item inserted text"]
    # the decoy "S4 comment credited" and "near-miss credited" cells stay: those are genuine failures of the coder.

    lines: list[str] = []
    A = lines.append
    A("# Perturbation specificity diagnosis (Claude Sonnet only)\n")
    A("Generated by `analysis/perturb_diagnosis.py` from `audit/perturb/` (frozen run, read-only; no LLM calls). "
      "The run now holds all 39 variants for both coders; this diagnosis was written for sonnet and was not extended to the OpenAI coder or the resolved level (their frozen rates are in `rq2_perturbation.csv`), so every figure here is for sonnet. "
      f"All {chk['variants']} variant packets were rebuilt with the frozen `variant_packet` and matched the stored packet hash "
      f"({chk['hash_ok']}/{chk['variants']}). The primary figures were reproduced from the records: deletion "
      f"{pct(*repro['deletion'])}, decoy {pct(*repro['decoy'])}, overall {pct(repro['deletion'][0] + repro['decoy'][0], n_dele + n_dec)}.\n")
    A("Reference levels. *Resolved base* is the two-family resolved level used by the frozen metric (the level both Sonnet and "
      "Codex supported). *Own base* is the effective level Sonnet gave the same cell in the unperturbed packet "
      f"(`audit/perturb/verified/<bench>/<item>/sonnet.json`). Own base is below resolved base in {below} negative cells and above it in "
      f"{own_gt} of {len(neg)}, as expected when the resolved level is the lower of two coders.\n")

    A("## 1. Deletion failures\n")
    A(f"Deletion cells: {n_dele}; perturbed level 0 in {del0}; failures (level > 0): {len(dfail)}. "
      "Every verified quote of a failing cell lies in a chunk that was NOT deleted, by construction: the quote is verified against "
      "the perturbed packet, in which the chunks cited by any verified base quote (either coder) had been removed. "
      "The question is therefore what the remaining evidence was.\n")
    A("| Class | Cells | Meaning |\n|---|---|---|")
    A(f"| (a) alternative on-surface evidence remains | {n_a} | a verified quote in original text on S1-S3 (S5 for A5-A7) |")
    A(f"| (b) no verified quote | {n_b} | impossible with a positive effective level (downgraded to 0), so 0 by construction |")
    A(f"| (c1) only cross-item inserted text | {c_sub['c1 cross-item inserted text']} | quotes lie in text inserted for another item |")
    A(f"| (c2) only non-counting surface | {c_sub['c2 non-counting surface']} | S4 code or S5 outside A5-A7 (G1a violation) |")
    A(f"| total | {len(dfail)} | |\n")
    A(f"Class (a) detail. Surfaces of the counting quote: {dict(sorted(a_surf.items()))}. In {a_dup} of {n_a} cells the same wording also "
      f"occurs in the deleted text (content repeated elsewhere in the packet). {a_strict} of {n_a} have a strictly verified counting quote. "
      f"The perturbed level was at or above Sonnet's own base level in {a_ge_own} of {n_a}. Purity: {a_clean} of {n_a} cells cite only original "
      f"text and stay at or below own base; {a_mixed} also cite text inserted for another item; {a_above_own} exceed own base.\n")
    A("Class (a) by item (cells / deletion cells of that item):\n")
    A("| " + " | ".join(ITEM_ORDER) + " |\n|" + "---|" * len(ITEM_ORDER))
    A("| " + " | ".join(f"{a_by_item[i]}/{n_del_by_item[i]}" for i in ITEM_ORDER) + " |\n")
    A(f"Cross-item interference (deletion class c1 plus decoy cross-item class): {n_cross} cells ({n_cross - cross_dec} deletion, {cross_dec} decoy). "
      "In every one the quote lies in S1 text inserted for ANOTHER item in the same multiplexed variant packet (scored cell type, type of the credited planted text: count): "
      + ", ".join(f"{vt} {t}: {n}" for (vt, t), n in sorted(hit_types.items())) + ". "
      "Most frequent item pairs (scored item, item whose text was credited): "
      + ", ".join(f"{a}<-{b} {n}" for (a, b), n in pairs.most_common(8)) + ". "
      "These pairs are conceptually adjacent (for example C10/C11, C13/A1, C12/A8, C9/A7, C5/C6/A9): the canonical level-2 sentence planted for one item "
      "also meets part of the anchor of its neighbour.\n")
    A("Why it happens. The deletion removes only the chunks cited by a verified base quote. The frozen design note already says residual "
      "evidence in uncited chunks makes deletion a conservative test; the counts above show how conservative: the failures are not "
      "over-credit of absent text but credit of text that remains in S1-S3 or was planted for a neighbouring item.\n")

    A("## 2. Decoy failures\n")
    A(f"Decoy cells: {n_dec} (S1 near-miss {len(dec_s1)}, S4 comment {len(dec_s4)}); failures (level above resolved base): "
      f"{len(f1) + len(f4)} (S1 {len(f1)}, S4 {len(f4)}).\n")
    A("Classes are assigned in this order: a verified quote from the cell's own decoy text; else from text inserted for another item; "
      "else level at or below Sonnet's own base level (artefact of comparing one coder with the conservative resolved base); else other.\n")
    names = ["near-miss credited", "S4 comment credited", "cross-item inserted text", "own-base artefact",
             "other original evidence above own base", "none"]
    A("| Class | S1 near-miss | S4 comment |\n|---|---|---|")
    for nme in names:
        A(f"| {nme} | {d1.get(nme, 0)} | {d4.get(nme, 0)} |")
    A(f"| total failures | {len(f1)} | {len(f4)} |\n")
    A(f"Failures whose perturbed level is at or below own base (all classes): S1 {ge_own1}/{len(f1)}, S4 {ge_own4}/{len(f4)}. "
      f"Of the cells that credited the decoy text itself, {cred1_le_own} (S1) and {cred4_le_own} (S4) are at or below own base.\n")
    A("Transitions of the failing decoy cells (resolved base -> perturbed level; S1 / S4): "
      + "; ".join(f"{b}->{l}: {sum(n for (bb, ll, sf), n in trans.items() if bb == b and ll == l and sf == 'S1')} / "
                  f"{sum(n for (bb, ll, sf), n in trans.items() if bb == b and ll == l and sf == 'S4')}"
                  for (b, l) in sorted({(b, l) for (b, l, _) in trans})) + ".\n")
    A(f"G1a check. Of {len(s4_cells)} S4-comment decoy cells, {s4_own_cells} have a verified quote from the planted comment and {s4_quote_cells} have any "
      "verified quote in a non-S5 S4 chunk at all. The frozen verifier ties a score of 1 or 2 to verified quotes, so a G1a violation would appear as such a quote.\n")
    A("The S4 comment class is a violation of coding manual G1a (code comments never count as reporting). The S1 near-miss class is credit "
      "of text written to fail the anchor; it is a failure of the coder or of the decoy text and cannot be separated here without reading the "
      "decoys (see section 4).\n")

    A("## 3. Secondary specificities (sonnet)\n")
    A("| Metric | Cells | Rate [Wilson 95%] |\n|---|---|---|")
    A(f"| primary, as frozen: deletion level 0 | {n_dele} | {pct(del0, n_dele)} |")
    A(f"| primary, as frozen: decoy not above resolved base | {n_dec} | {pct(prim_dec_ok, n_dec)} |")
    A(f"| primary, as frozen: overall | {n_dele + n_dec} | {pct(del0 + prim_dec_ok, n_dele + n_dec)} |")
    A(f"| decoy not above OWN base | {n_dec} | {pct(own_dec_ok, n_dec)} |")
    A(f"| decoy S1 near-miss, resolved base / own base | {len(dec_s1)} | {pct(prim_dec1_ok, len(dec_s1))} / {pct(own_dec1_ok, len(dec_s1))} |")
    A(f"| decoy S4 comment, resolved base / own base | {len(dec_s4)} | {pct(prim_dec4_ok, len(dec_s4))} / {pct(own_dec4_ok, len(dec_s4))} |")
    A(f"| deletion level fell below resolved base (frozen secondary) | {n_dele} | {pct(drop_res, n_dele)} |")
    A(f"| deletion level fell below OWN base | {n_dele} | {pct(drop_own, n_dele)} |")
    A(f"| deletion level 0, class (a) cells removed | {ex_a} | {pct(del0, ex_a)} |")
    A(f"| deletion level 0, classes (a) and (c1) removed | {ex_ac1} | {pct(del0, ex_ac1)} |")
    A(f"| decoy vs resolved base, cross-item failures removed | {n_dec - cross_dec} | {pct(prim_dec_ok, n_dec - cross_dec)} |")
    A(f"| overall, decoy vs resolved base, class (a) removed | {ex_a + n_dec} | {pct(del0 + prim_dec_ok, ex_a + n_dec)} |")
    A(f"| overall, decoy vs OWN base, class (a) removed | {ex_a + n_dec} | {pct(del0 + own_dec_ok, ex_a + n_dec)} |")
    A(f"| overall, decoy vs OWN base, classes (a) and (c1) removed | {ex_ac1 + n_dec} | {pct(del0 + own_dec_ok, ex_ac1 + n_dec)} |\n")
    A("Caveats on the corrected figures. Removing class (a) removes only failing deletion cells; a deletion cell the coder passed "
      "while on-surface evidence remained (the coder missed it) cannot be identified, so the corrected deletion rate is an upper bound "
      "on specificity under the claim that every class (a) cell is invalid, not an estimate. Own-base referencing makes the decoy test "
      "more lenient than the frozen label: a coder that already credits level 2 in the base packet cannot fail it. Both are secondary "
      "analyses; the frozen metric is unchanged.\n")

    A("## 4. Manual reading of a sample of class (a) cells and of the non-cross-item decoy failures\n")
    A("A reading by the analyst (the model running this script), not an independent coder and not checked by a second person. It asks only "
      "whether the verified counting-surface quote plausibly supports the credited level for that item, using the coding manual anchors. "
      "The sample is 16 class (a) deletion cells drawn with `random.Random(20261004).sample`.\n")
    A("| Cell | Level / own base | Counting quote surface | Verdict |\n|---|---|---|---|")
    for r in random.Random(SEED).sample(a_cells, min(16, len(a_cells))):
        v = SAMPLE_VERDICT.get((r["variant"], r["item"]), "not read")
        surf = ",".join(sorted({q["surface"] for q in r["quotes"] if q["prov"] == "orig" and q["counting"]}))
        A(f"| {r['variant']} {r['item']} | {r['level']} / {r['own_base']} | {surf} | {v} |")
    nv = Counter(SAMPLE_VERDICT.get((r["variant"], r["item"]), "not read").split(";")[0]
                 for r in random.Random(SEED).sample(a_cells, min(16, len(a_cells))))
    A("")
    A("Tally: " + ", ".join(f"{k} {v}" for k, v in sorted(nv.items())) + ". So class (a) is mostly sound evidence left in the packet, "
      "not coder over-credit; a minority of cells rest on thin quotes or on cross-item text for the level reached.\n")
    A("Decoy failures that are not cross-item (all six; the other 66 are cross-item):\n")
    A("| Cell | Class | Level / own base / resolved base | Reading |\n|---|---|---|---|")
    for r in neg:
        if r["vtype"] == "decoy" and r["cls"] in ("near-miss credited", "own-base artefact", "S4 comment credited",
                                                  "other original evidence above own base"):
            A(f"| {r['variant']} {r['item']} | {r['cls']} ({'S4' if r['s4'] else 'S1'}) | {r['level']} / {r['own_base']} / {r['base_resolved']} | "
              f"{DECOY_READING.get((r['variant'], r['item']), 'not read')} |")
    A("")
    A("Cross-item cells read: 8 seeded decoy cells and 6 seeded deletion class (c1) cells were printed and read; in every one the credited "
      "sentence planted for another item is genuine evidence for the scored item under its anchor (for example C11's trivial-agent rates for "
      "C10, A1's run and temperature statement for C13 and A4, A11's data-origin sentences for C2, A9's leakage controls for C5 and C6). "
      "The cell list is in `perturb_diagnosis_cells.csv`.\n")
    A("## 5. Interpretation\n")
    A("The frozen metric asks whether Sonnet, given a variant packet in which all 25 items are perturbed at once, returns the labelled "
      "level for each cell. Its specificity of 40.3% does not show that Sonnet credits absent or non-reporting evidence. All "
      f"{len(dfail)} deletion failures carry a verified quote that is in the packet, either as original S1-S3 text left after only the cited chunks "
      f"were removed ({n_a}) or as a canonical level-2 sentence planted for a neighbouring item ({c_sub['c1 cross-item inserted text']}); none is an unverified "
      f"quote ({n_b}) or a G1a violation ({c_sub['c2 non-counting surface']}). Of the {len(f1) + len(f4)} decoy failures, {d1.get('cross-item inserted text', 0) + d4.get('cross-item inserted text', 0)} credit another item's planted text, "
      f"{d1.get('own-base artefact', 0) + d4.get('own-base artefact', 0)} are the own-base artefact, {d1.get('near-miss credited', 0)} credit the near-miss text itself, and {s4_own_cells} of {len(s4_cells)} S4-comment cells credit the comment, "
      "so G1a held. Own-base referencing therefore moves decoy specificity only from "
      f"{100 * prim_dec_ok / n_dec:.1f}% to {100 * own_dec_ok / n_dec:.1f}%; the larger cause is cross-item interference in the multiplexed design, "
      "which the protocol lists as a limitation but did not estimate. The metric does show that this design, with uncited-chunk deletion and "
      "conceptually adjacent items sharing one packet, does not produce clean negative labels, and that Sonnet reliably recovers planted "
      "text (sensitivity 97.2%). It does not show that Sonnet is specific, because a majority of the negative cells were contaminated by remaining or planted evidence. It also cannot "
      "show that Sonnet is not over-crediting: the corrected rates are conditional on failures that were classified as evidence-backed, "
      "the 16 passing deletion cells are not known to have been valid negatives, and the reading in section 4 is one reader's. The defensible "
      "wording is that the perturbation specificity of the coder-plus-multiplexed-packet pipeline is low for design reasons, and that a "
      "clean specificity test needs per-item (non-multiplexed) packets with all on-surface evidence removed.\n")

    (OUT / "perturb_diagnosis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    out_rows = []
    for r in neg:
        out_rows.append({"variant": r["variant"], "bench": r["bench"], "item": r["item"], "vtype": r["vtype"],
                         "decoy_surface": ("S4 comment" if r["s4"] else "S1 near-miss") if r["vtype"] == "decoy" else "",
                         "base_resolved": r["base_resolved"], "own_base": r["own_base"], "level": r["level"],
                         "class": r["cls"], "subclass": r["sub"],
                         "n_verified_quotes": len(r["quotes"]),
                         "quote_prov": ";".join(f"{q['prov']}:{q['surface']}" + ("*" if q["counting"] else "") for q in r["quotes"])})
    write_csv(OUT / "perturb_diagnosis_cells.csv", out_rows)

    summary = {"deletion_fail": dict(c1), "a_surface": dict(a_surf), "c_sub": dict(c_sub), "d1": dict(d1), "d4": dict(d4)}
    print(json.dumps(summary, indent=1))
    print("own_base below/above resolved:", below, own_gt)
    print("a dup in deleted", a_dup, "strict", a_strict, "ge own", a_ge_own)
    print("dec own ok", own_dec_ok, own_dec1_ok, own_dec4_ok, "prim", prim_dec_ok, prim_dec1_ok, prim_dec4_ok)
    print("del drop res/own", drop_res, drop_own, "ex_a", ex_a, "ex_ac1", ex_ac1)
    print("ge_own1/4", ge_own1, len(f1), ge_own4, len(f4), cred1_le_own, cred4_le_own)


if __name__ == "__main__":
    main()
