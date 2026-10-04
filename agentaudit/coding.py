"""Stage 3: one call per (benchmark, item, coder). Resumable; logs model id, time, prompt hash, raw response."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .backends import BackendAuthError, BackendError
from .chunking import Chunk
from .items import Item, load_items
from .packet import load_chunks
from .prompts import prompt_hash, render_prompt, system_prompt
from .retrieve import load_retrieval
from .throttle import DailyLimitReached
from .util import read_json, utcnow, write_json


class ParseError(Exception):
    pass


def coding_path(run: Path, bench: str, item_id: str, coder: str) -> Path:
    return Path(run) / "coding" / bench / item_id / f"{coder}.json"


def extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ParseError("no JSON object in response")
    try:
        obj = json.loads(t[i:j + 1])
    except ValueError as e:
        raise ParseError(f"invalid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise ParseError("JSON is not an object")
    return obj


def _norm_score(v):
    if isinstance(v, bool):
        raise ParseError("score is boolean")
    if isinstance(v, (int, float)) and int(v) == v and int(v) in (0, 1, 2):
        return int(v)
    if isinstance(v, str):
        s = v.strip().upper().replace("/", "")
        if s in ("0", "1", "2"):
            return int(s)
        if s == "NA":
            return "NA"
    raise ParseError(f"bad score: {v!r}")


def _norm_quotes(v) -> list[dict]:
    out = []
    for q in v or []:
        if isinstance(q, dict):
            out.append({"chunk_id": str(q.get("chunk_id", "")).strip().strip("[]").strip(), "text": str(q.get("text", ""))})
    return out


def parse_result(text: str, item: Item) -> dict:
    return parse_obj(extract_json(text), item)


def parse_obj(obj: dict, item: Item) -> dict:
    if "score" not in obj:
        raise ParseError("missing score")
    score = _norm_score(obj["score"])
    el = obj.get("elements")
    if item.n_elements and isinstance(el, list) and len(el) == item.n_elements and all(isinstance(x, bool) for x in el):
        elements = el
    else:
        elements = [] if not item.n_elements else None
    out = {
        "score": score,
        "elements": elements,
        "quotes": _norm_quotes(obj.get("quotes")),
        "contradicted": bool(obj.get("contradicted", False)),
        "contradiction_quotes": _norm_quotes(obj.get("contradiction_quotes")),
        "rationale": str(obj.get("rationale", "")),
    }
    if "s5_reach" in obj:
        out["s5_reach"] = obj["s5_reach"] if isinstance(obj["s5_reach"], bool) else None
    return out


def code_cell(backend, item: Item, items: dict[str, Item], chunks: list[Chunk], parse_attempts: int = 2) -> dict:
    """Call the backend for one cell with a chunk set; return the record (without bench/coder fields)."""
    prompt = render_prompt(item, items, chunks)
    system = system_prompt()
    rec = {"prompt_sha256": prompt_hash(prompt), "system_sha256": prompt_hash(system),
           "prompt_chars": len(prompt), "attempts": [], "parsed": None, "status": "parse_error"}
    for _ in range(parse_attempts):
        resp = backend.complete(system, prompt)
        att = {"timestamp": utcnow(), "model_id": resp.model_id, "usage": resp.usage, "meta": resp.meta,
               "raw_response": resp.text}
        rec["attempts"].append(att)
        rec["model_id"] = resp.model_id
        try:
            rec["parsed"] = parse_result(resp.text, item)
            rec["status"] = "ok"
            break
        except ParseError as e:
            att["parse_error"] = str(e)
    rec["timestamp"] = rec["attempts"][-1]["timestamp"]
    return rec


def run_coding(run: Path, bench: str, coder: str, spec: dict, backend, item_ids: list[str],
               force: bool = False, log=print) -> dict:
    items = load_items()
    chunks = {c.id: c for c in load_chunks(run, bench)}
    summary = {"done": [], "skipped": [], "failed": [], "blocked": None}
    for iid in item_ids:
        p = coding_path(run, bench, iid, coder)
        if p.exists() and not force:
            try:
                if read_json(p).get("status") == "ok":
                    summary["skipped"].append(iid)
                    continue
            except ValueError:
                pass
        ret = load_retrieval(run, bench, iid)
        cs = [chunks[c["id"]] for c in ret["chunks"]]
        try:
            rec = code_cell(backend, items[iid], items, cs)
        except DailyLimitReached as e:
            summary["blocked"] = {"item": iid, "next_available_unix": e.next_available, "reason": str(e)}
            log(f"[{coder}] daily limit reached at {iid}; rerun after the limit resets to resume")
            break
        except BackendAuthError as e:
            summary["blocked"] = {"item": iid, "reason": f"authentication: {e}"}
            log(f"[{coder}] backend authentication failed: {e}")
            break
        except BackendError as e:
            summary["failed"].append({"item": iid, "error": str(e)})
            log(f"[{coder}] {iid} backend error: {e}")
            continue
        rec.update({"bench": bench, "item": iid, "coder": coder, "family": spec.get("family"),
                    "backend": spec["backend"], "requested_model": spec["model"],
                    "retrieval_sha256": ret.get("retrieval_sha256"), "packet_sha256": ret.get("packet_sha256")})
        write_json(p, rec)
        (summary["done"] if rec["status"] == "ok" else summary["failed"]).append(
            iid if rec["status"] == "ok" else {"item": iid, "error": "parse_error"})
        log(f"[{coder}] {bench} {iid}: {rec['status']}"
            + (f" score={rec['parsed']['score']}" if rec["parsed"] else ""))
    return summary
