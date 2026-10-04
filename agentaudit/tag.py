"""Stage 2a: exhaustive evidence tagging, and item chunk sets built from the tags.

A tagger reads every chunk of a packet, in windows, and returns {chunk_id: [item ids]} (an empty
list is allowed). Item glosses come from items.yaml. Tag files are resumable: one file per window
under ``<run>/tags/<bench>/<tagger>/windows/``, merged into ``<run>/tags/<bench>/<tagger>.json``.

Item chunk sets (``build_item_sets``): chunks tagged by two or more taggers first, then chunks
tagged by one tagger (both groups in chunk position order), then BM25 filler, all inside the token
cap. The sets are written in the same format as ``retrieve`` so ``code`` reads them unchanged.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from .backends import BackendError
from .chunking import Chunk
from .items import ITEM_ORDER, PKG, Item, load_items, load_queries
from .packet import load_chunks, packet_dir
from .retrieve import retrieval_path, tokenize
from .util import est_tokens, read_json, sha256_text, utcnow, write_json

GPT_OSS_WINDOW_TOKENS = 5000  # chunk text plus headers per window (the rendered prompt adds about 1,200)
CLAUDE_WINDOW_TOKENS = 150_000  # whole packet in one call unless it exceeds this
TAG_MAX_TOKENS = 1500  # reply budget for the gpt-oss backend; counts against the TPM throttle


class TagParseError(Exception):
    pass


# ------------------------------------------------------------------ prompt
def item_glosses(items: dict[str, Item] | None = None) -> str:
    """One line per item: id, title, item text."""
    items = items or load_items()
    lines = []
    for iid in ITEM_ORDER:
        it = items[iid]
        lines.append(f"{iid} {it.title.rstrip('.')}: {' '.join(it.item_text.split())}")
    return "\n".join(lines)


def tag_system_prompt() -> str:
    return (PKG / "prompts" / "tag_system.txt").read_text(encoding="utf-8").strip()


def render_tag_chunk(c: Chunk) -> str:
    tag = " agent_visible" if c.s5 else ""
    return f"### [{c.id}] surface={c.surface}{tag}\n{c.text}"


def render_tag_prompt(chunks: list[Chunk], glosses: str | None = None) -> str:
    t = (PKG / "prompts" / "tag.txt").read_text(encoding="utf-8")
    t = t.replace("{{GLOSSES}}", glosses or item_glosses()).replace("{{N_CHUNKS}}", str(len(chunks)))
    return t.replace("{{CHUNKS}}", "\n\n".join(render_tag_chunk(c) for c in chunks))  # last: chunk text is data


# ------------------------------------------------------------------ windows
def chunk_order(chunks: list[Chunk]) -> list[Chunk]:
    """Document order: surface, path, start line."""
    return sorted(chunks, key=lambda c: (c.surface, c.path, c.start, c.end))


def make_windows(chunks: list[Chunk], window_tokens: int) -> list[list[Chunk]]:
    """Greedy windows in document order; a window holds at most window_tokens of rendered chunk text
    (a single chunk larger than that gets its own window)."""
    wins: list[list[Chunk]] = []
    cur: list[Chunk] = []
    used = 0
    for c in chunk_order(chunks):
        t = est_tokens(render_tag_chunk(c))
        if cur and used + t > window_tokens:
            wins.append(cur)
            cur, used = [], 0
        cur.append(c)
        used += t
    if cur:
        wins.append(cur)
    return wins


# ------------------------------------------------------------------ parsing
def _clean_id(s: str) -> str:
    return str(s).strip().strip("[]").strip()


def parse_tags(text: str, chunk_ids: list[str]) -> tuple[dict[str, list[str]], dict]:
    """Parse a tagger reply. Returns ({chunk_id: [item ids]} for the ids in chunk_ids that the reply
    covers, diagnostics). Unknown chunk ids and unknown item ids are dropped and counted."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise TagParseError("no JSON object in response")
    try:
        obj = json.loads(t[i:j + 1])
    except ValueError as e:
        raise TagParseError(f"invalid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise TagParseError("JSON is not an object")
    if len(obj) == 1:  # tolerate {"tags": {...}}
        (k, v), = obj.items()
        if k not in chunk_ids and isinstance(v, dict):
            obj = v
    valid = set(chunk_ids)
    out: dict[str, list[str]] = {}
    unknown_chunks = unknown_items = 0
    for k, v in obj.items():
        cid = _clean_id(k)
        if cid not in valid:
            unknown_chunks += 1
            continue
        if isinstance(v, str):
            v = [x for x in re.split(r"[,\s]+", v) if x]
        if not isinstance(v, list):
            raise TagParseError(f"value for {cid} is not a list")
        ids = []
        for x in v:
            xi = str(x).strip().upper()
            if xi in ITEM_ORDER:
                if xi not in ids:
                    ids.append(xi)
            else:
                unknown_items += 1
        out[cid] = [x for x in ITEM_ORDER if x in ids]
    if chunk_ids and not out:
        raise TagParseError("no known chunk ids in response")
    return out, {"unknown_chunks": unknown_chunks, "unknown_items": unknown_items}


# ------------------------------------------------------------------ running
def window_key(chunks: list[Chunk]) -> str:
    return sha256_text("|".join(c.id for c in chunks))[:12]


def window_path(run: Path, bench: str, tagger: str, key: str) -> Path:
    return Path(run) / "tags" / bench / tagger / "windows" / f"{key}.json"


def merged_path(run: Path, bench: str, tagger: str) -> Path:
    return Path(run) / "tags" / bench / f"{tagger}.json"


def _is_too_large(e: Exception) -> bool:
    """413, or Groq's 400 when the reply hit max_tokens before the JSON closed: both are cured by a smaller window."""
    s = str(e).lower()
    return (s.startswith("413") or "request too large" in s or "request_too_large" in s
            or "max completion tokens reached" in s)


def tag_window(backend, chunks: list[Chunk], glosses: str, parse_attempts: int = 2) -> dict:
    """Call the backend for one window. Returns a record with status ok | parse_error."""
    prompt = render_tag_prompt(chunks, glosses)
    system = tag_system_prompt()
    ids = [c.id for c in chunks]
    rec = {"chunk_ids": ids, "prompt_sha256": sha256_text(prompt), "prompt_chars": len(prompt),
           "attempts": [], "tags": {}, "missing": ids, "status": "parse_error"}
    for _ in range(parse_attempts):
        resp = backend.complete(system, prompt)
        att = {"timestamp": utcnow(), "model_id": resp.model_id, "usage": resp.usage, "meta": resp.meta,
               "raw_response": resp.text}
        rec["attempts"].append(att)
        rec["model_id"] = resp.model_id
        try:
            tags, diag = parse_tags(resp.text, ids)
        except TagParseError as e:
            att["parse_error"] = str(e)
            continue
        rec.update(status="ok", tags=tags, missing=[i for i in ids if i not in tags], diagnostics=diag)
        break
    rec["timestamp"] = rec["attempts"][-1]["timestamp"]
    return rec


def _run_window(run, bench, tagger, spec, backend, chunks, glosses, force, summary, log, depth=0):
    """Tag one window (resumable). A 413 or too-large reply splits the window in two."""
    from .backends import BackendAuthError
    from .throttle import DailyLimitReached, RequestTooLarge

    key = window_key(chunks)
    p = window_path(run, bench, tagger, key)
    if p.exists() and not force:
        try:
            old = read_json(p)
        except ValueError:
            old = {}
        if old.get("status") == "ok":
            summary["skipped"] += 1
            return True
        if old.get("status") == "split":
            ok = True
            for half in (old["children"]):
                sub = [c for c in chunks if c.id in set(half)]
                ok = _run_window(run, bench, tagger, spec, backend, sub, glosses, force, summary, log, depth + 1) and ok
            return ok
    try:
        rec = tag_window(backend, chunks, glosses)
    except DailyLimitReached as e:
        summary["blocked"] = {"reason": str(e), "next_available_unix": e.next_available}
        log(f"[tag {tagger}] daily limit reached; rerun after the limit resets to resume")
        return False
    except BackendAuthError as e:
        summary["blocked"] = {"reason": f"authentication: {e}"}
        log(f"[tag {tagger}] backend authentication failed: {e}")
        return False
    except (RequestTooLarge, BackendError) as e:
        if (isinstance(e, RequestTooLarge) or _is_too_large(e)) and len(chunks) > 1:
            mid = len(chunks) // 2
            halves = [chunks[:mid], chunks[mid:]]
            write_json(p, {"status": "split", "chunk_ids": [c.id for c in chunks], "reason": str(e)[:300],
                           "children": [[c.id for c in h] for h in halves]})
            summary["splits"] += 1
            log(f"[tag {tagger}] window {key} too large; split into {len(halves[0])}+{len(halves[1])} chunks")
            ok = True
            for h in halves:
                ok = _run_window(run, bench, tagger, spec, backend, h, glosses, force, summary, log, depth + 1) and ok
            return ok
        summary["failed"].append({"window": key, "error": str(e)[:300]})
        log(f"[tag {tagger}] window {key} backend error: {str(e)[:200]}")
        return True
    rec.update({"bench": bench, "tagger": tagger, "family": spec.get("family"), "backend": spec["backend"],
                "requested_model": spec["model"], "window": key})
    write_json(p, rec)
    summary["calls"] += len(rec["attempts"])
    if rec["status"] == "ok":
        summary["done"] += 1
    else:
        summary["failed"].append({"window": key, "error": "parse_error"})
    log(f"[tag {tagger}] {bench} window {key} ({len(chunks)} chunks): {rec['status']}"
        + (f", {len(rec['missing'])} missing" if rec["status"] == "ok" and rec["missing"] else ""))
    return True


def collect_window_files(run: Path, bench: str, tagger: str, chunks: list[Chunk]) -> dict:
    """Merge every ok window file into {chunk_id: [item ids]} for this tagger."""
    d = Path(run) / "tags" / bench / tagger / "windows"
    tags: dict[str, list[str]] = {}
    models = set()
    n_calls = 0
    if d.exists():
        for f in sorted(d.glob("*.json")):
            try:
                rec = read_json(f)
            except ValueError:
                continue
            if rec.get("status") == "ok":
                tags.update(rec["tags"])
                n_calls += len(rec.get("attempts", []))
                if rec.get("model_id"):
                    models.add(rec["model_id"])
    all_ids = [c.id for c in chunk_order(chunks)]
    return {"bench": bench, "tagger": tagger, "model_ids": sorted(models), "n_chunks": len(all_ids),
            "n_tagged_chunks": sum(1 for i in all_ids if i in tags), "n_calls": n_calls,
            "missing": [i for i in all_ids if i not in tags], "complete": all(i in tags for i in all_ids),
            "tags": {i: tags[i] for i in all_ids if i in tags}}


def run_tagging(run: Path, bench: str, tagger: str, spec: dict, backend, window_tokens: int | None = None,
                force: bool = False, max_calls: int | None = None, log=print) -> dict:
    chunks = load_chunks(run, bench)
    if window_tokens is None:
        window_tokens = CLAUDE_WINDOW_TOKENS if spec["backend"] == "claude" else GPT_OSS_WINDOW_TOKENS
    glosses = item_glosses()
    wins = make_windows(chunks, window_tokens)
    summary = {"bench": bench, "tagger": tagger, "windows": len(wins), "done": 0, "skipped": 0, "calls": 0,
               "splits": 0, "failed": [], "blocked": None}
    for w in wins:
        if max_calls is not None and summary["calls"] >= max_calls:
            summary["blocked"] = summary["blocked"] or {"reason": "max_calls reached"}
            break
        if not _run_window(run, bench, tagger, spec, backend, w, glosses, force, summary, log):
            break
    merged = collect_window_files(run, bench, tagger, chunks)
    merged.update(window_tokens=window_tokens, updated_utc=utcnow())
    write_json(merged_path(run, bench, tagger), merged)
    summary["complete"] = merged["complete"]
    summary["n_chunks"] = merged["n_chunks"]
    summary["n_tagged_chunks"] = merged["n_tagged_chunks"]
    return summary


# ------------------------------------------------------------------ item chunk sets
def load_tags(run: Path, bench: str, tagger: str) -> dict[str, list[str]]:
    return read_json(merged_path(run, bench, tagger))["tags"]


def select_item_chunks(chunks: list[Chunk], item_id: str, tagsets: dict[str, dict[str, list[str]]],
                       scores: dict[str, float], cap: int, bm25_filler: bool = True) -> dict:
    """Pure selection for one item. tagsets: tagger -> {chunk_id: [item ids]}. scores: chunk id -> BM25
    score for the item query. Order: tagged by two or more taggers, tagged by one (both in chunk position
    order), then BM25 filler (positive scores only, best first). A chunk that does not fit the cap is
    skipped and the next one is tried."""
    order = chunk_order(chunks)
    pos = {c.id: i for i, c in enumerate(order)}
    cmap = {c.id: c for c in chunks}
    votes: dict[str, int] = {}
    for tags in tagsets.values():
        for cid, its in tags.items():
            if item_id in its and cid in cmap:
                votes[cid] = votes.get(cid, 0) + 1
    tagged = sorted(votes, key=lambda cid: (-votes[cid], pos[cid]))
    selected: list[dict] = []
    seen: set[str] = set()
    used = 0
    dropped: list[str] = []
    for cid in tagged:
        c = cmap[cid]
        if used + c.tokens > cap:
            dropped.append(cid)
            continue
        selected.append({"id": cid, "score": round(scores.get(cid, 0.0), 9),
                         "reason": "tag:both" if votes[cid] >= 2 and len(tagsets) >= 2 else "tag:one",
                         "tags": votes[cid], "tokens": c.tokens})
        seen.add(cid)
        used += c.tokens
    tagged_tokens = used
    if bm25_filler:
        ranked = sorted(order, key=lambda c: (-scores.get(c.id, 0.0), c.id))
        for c in ranked:
            if c.id in seen or scores.get(c.id, 0.0) <= 0:
                continue
            if used + c.tokens > cap:
                continue
            selected.append({"id": c.id, "score": round(scores[c.id], 9), "reason": "bm25", "tags": 0,
                             "tokens": c.tokens})
            seen.add(c.id)
            used += c.tokens
    for rank, e in enumerate(selected, 1):
        e["rank"] = rank
    tagged_all_tokens = sum(cmap[c].tokens for c in tagged)
    return {"item": item_id, "chunks": selected, "total_tokens": used, "tagged_tokens": tagged_tokens,
            "n_tagged": len(tagged), "n_tagged_kept": len(tagged) - len(dropped), "n_tagged_dropped": len(dropped),
            "tagged_total_tokens": tagged_all_tokens, "truncated": bool(dropped), "dropped": dropped}


def build_item_sets(run: Path, bench: str, taggers: list[str], items: list[str] | None = None,
                    sets_name: str = "retrieval", bm25_filler: bool = True, queries: dict | None = None) -> dict:
    """Build and write the item chunk sets for one benchmark from the merged tag files."""
    queries = queries or load_queries()
    cap = int(queries["params"]["token_cap"])
    chunks = load_chunks(run, bench)
    man = read_json(packet_dir(run, bench) / "manifest.json")
    tagsets = {t: load_tags(run, bench, t) for t in taggers}
    ordered = sorted(chunks, key=lambda c: c.id)
    bm = BM25Okapi([tokenize(c.text) for c in ordered])
    out = {}
    for it in items or list(ITEM_ORDER):
        q = queries["items"][it]["query"]
        sc = {c.id: round(float(s), 9) for c, s in zip(ordered, bm.get_scores(tokenize(q)))}
        rec = select_item_chunks(chunks, it, tagsets, sc, cap, bm25_filler)
        rec.update({"bench": bench, "query": q, "taggers": taggers, "bm25_filler": bm25_filler,
                    "params": {"token_cap": cap, "order": "tag:both, tag:one (chunk position), bm25 filler"},
                    "n_packet_chunks": len(chunks), "packet_sha256": man["packet_sha256"]})
        rec["retrieval_sha256"] = sha256_text("|".join(c["id"] for c in rec["chunks"]))
        base = Path(run) / sets_name / bench / f"{it}.json" if sets_name != "retrieval" else retrieval_path(run, bench, it)
        write_json(base, rec)
        out[it] = rec
    return out
