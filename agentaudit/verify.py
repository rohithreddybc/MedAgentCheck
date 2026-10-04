"""Stage 4: machine verification of quotes.

Primary rule (loose, field ``verified``): a quote counts if it is a substring of its
chunk after NFKC, case folding and dropping every character that is not a letter or a
digit, and its normalised length is at least 20 characters (summed over fragments).
This removes the spacing, punctuation and symbol differences that text rendering
introduces (``[ 24 ]``, a backslash before a percent sign, LaTeX alt text). Secondary rule (strict, field
``verified_strict``): verbatim substring after NFKC, quote-mark and dash normalisation
and whitespace collapse, case kept, at least 12 characters. Ellipses split a quote into
fragments and every fragment must match. A 1 or 2 with no loosely verified quote is
"unsupported" and carries effective level 0 into resolution.
"""
from __future__ import annotations

import re
from pathlib import Path

from .items import Item, load_items
from .packet import load_chunks
from .retrieve import load_retrieval
from .util import loose_normalise, normalise, read_json, write_json

MIN_FRAGMENT_CHARS = 12  # strict rule (secondary)
MIN_LOOSE_CHARS = 20  # loose rule (primary): normalised characters, summed over fragments
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")


_MOJIBAKE = re.compile("[ÂÃâ][-ÿŒœŠšŸŽžƒˆ˜–-›€™]")


def repair_mojibake(text: str) -> str:
    """Undo UTF-8 read as cp1252 (some models emit it for non-ASCII characters). No-op if not applicable."""
    if not _MOJIBAKE.search(text):
        return text
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def clean_chunk_id(cid: str) -> str:
    return cid.strip().strip("[]").strip()


def verify_quote(quote: dict, norm_chunks: dict[str, str], loose_chunks: dict[str, str] | None = None) -> dict:
    """norm_chunks: id -> strictly normalised chunk text. loose_chunks: id -> loosely normalised chunk
    text (derived from norm_chunks when omitted). ``verified`` is the loose result; ``verified_strict``
    is the strict result."""
    cid = clean_chunk_id(quote.get("chunk_id", ""))
    text = quote.get("text", "")
    res = {"chunk_id": cid, "text": text, "words": len(text.split()), "verified": False,
           "verified_strict": False, "reason": ""}
    if cid not in norm_chunks:
        res["reason"] = "chunk_not_in_retrieval_set"
        return res
    body = norm_chunks[cid]
    lbody = loose_chunks[cid] if loose_chunks is not None and cid in loose_chunks else loose_normalise(body)
    res["reason"] = "not_a_substring"
    too_short = False
    for cand in dict.fromkeys([text, repair_mojibake(text)]):
        raw_frags = _ELLIPSIS.split(cand)
        sfrags = [f for f in (normalise(f) for f in raw_frags) if f]
        lfrags = [f for f in (loose_normalise(f) for f in raw_frags) if f]
        if sfrags and sum(len(f) for f in sfrags) >= MIN_FRAGMENT_CHARS and all(f in body for f in sfrags):
            res["verified_strict"] = True
        if lfrags and sum(len(f) for f in lfrags) >= MIN_LOOSE_CHARS:
            if all(f in lbody for f in lfrags):
                res["verified"] = True
                res["reason"] = "ok"
        else:
            too_short = True
        if res["verified"]:
            break
    if not res["verified"] and too_short:
        res["reason"] = "quote_too_short"
    return res


def verify_result(parsed: dict, item: Item, chunk_texts: dict[str, str], _cache: tuple | None = None,
                  positive_levels: tuple = (1, 2)) -> dict:
    """chunk_texts: id -> raw chunk text for the chunk set the coder saw. ``_cache``: precomputed
    (strict, loose) normalised dicts, so a whole-packet run normalises the packet once.
    ``positive_levels``: scores that need a verified quote (checklist (1, 2); ABC (1,); BetterBench (1, 2, 3)).
    ``item`` needs only ``na_allowed``."""
    if _cache is not None:
        norm, lnorm = _cache
    else:
        norm = {cid: normalise(t) for cid, t in chunk_texts.items()}
        lnorm = {cid: loose_normalise(t) for cid, t in chunk_texts.items()}
    quotes = [verify_quote(q, norm, lnorm) for q in parsed.get("quotes", [])]
    cquotes = [verify_quote(q, norm, lnorm) for q in parsed.get("contradiction_quotes", [])]
    raw = parsed["score"]
    flags: list[str] = []
    eff = raw
    n_ver = sum(1 for q in quotes if q["verified"])
    n_ver_strict = sum(1 for q in quotes if q["verified_strict"])
    if raw == "NA" and not item.na_allowed:
        eff = 0
        flags.append("na_not_allowed")
    if raw in positive_levels and n_ver == 0:
        eff = 0
        flags.append("unsupported")
    if any(q["words"] > 25 for q in quotes):
        flags.append("quote_over_25_words")
    contradicted = bool(parsed.get("contradicted"))
    return {
        "score_raw": raw,
        "effective": eff,
        "supported": (raw in positive_levels and n_ver > 0),
        "n_quotes": len(quotes),
        "n_verified": n_ver,
        "n_verified_strict": n_ver_strict,
        "supported_strict": (raw in positive_levels and n_ver_strict > 0),
        "quotes": quotes,
        "contradicted": contradicted,
        "contradiction_verified": contradicted and any(q["verified"] for q in cquotes),
        "contradiction_quotes": cquotes,
        "elements": parsed.get("elements"),
        "flags": flags,
    }


def verified_path(run: Path, bench: str, item_id: str, coder: str) -> Path:
    return Path(run) / "verified" / bench / item_id / f"{coder}.json"


def run_verify(run: Path, bench: str, item_ids: list[str] | None = None, coders: list[str] | None = None) -> list[dict]:
    items = load_items()
    chunks = {c.id: c.text for c in load_chunks(run, bench)}
    base = Path(run) / "coding" / bench
    out = []
    if not base.exists():
        return out
    pk_cache: dict[str, tuple] = {}
    for idir in sorted(base.iterdir()):
        if item_ids and idir.name not in item_ids:
            continue
        ret = None
        for f in sorted(idir.glob("*.json")):
            coder = f.stem
            if coders and coder not in coders:
                continue
            rec = read_json(f)
            if rec.get("status") != "ok":
                continue
            cache = None
            if rec.get("evidence_scope") == "packet_v3":
                from .packet_score import packet_chunk_texts

                if coder not in pk_cache:
                    t = packet_chunk_texts(run, bench, coder)
                    pk_cache[coder] = (t, ({k: normalise(x) for k, x in t.items()},
                                           {k: loose_normalise(x) for k, x in t.items()}))
                ctexts, cache = pk_cache[coder]
            else:
                if ret is None:
                    ret = load_retrieval(run, bench, idir.name)
                ctexts = {c["id"]: chunks[c["id"]] for c in ret["chunks"]}
            v = verify_result(rec["parsed"], items[idir.name], ctexts, cache)
            v.update({"bench": bench, "item": idir.name, "coder": coder, "family": rec.get("family")})
            write_json(verified_path(run, bench, idir.name, coder), v)
            out.append(v)
    return out
