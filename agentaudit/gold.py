"""Published-human-gold validation (``agentaudit gold --set abc|betterbench``; protocol-v1 section 5).

No new human coding: the pipeline scores benchmarks that ABC (arXiv 2507.02825) and BetterBench
(arXiv 2411.12990) already had experts assess, using the source instrument's own item texts and scale, and agreement
with the published scores is computed.

Steps (each resumable; outputs under ``<run>/gold-<set>/``):
  pin       resolve, for every benchmark, the last repository commit and the last arXiv version on or before the
            gold's date (ABC: 2025-07-10, the date of the assessment YAML files; BetterBench: 2024-11-21, the
            Last-Modified date of the website data page). Written to ``samples/gold_pins_v1.json``.
  packets   build an evidence packet per benchmark at the pinned versions.
  score     whole-packet scoring, one call per (benchmark, coder), all items of the set in one prompt.
  agree     agreement with the published scores, per coder and resolved (two-family rule).

Scales. ABC is binary (1 satisfied, 0 not). BetterBench uses 0/5/10/15 and n/a; the prompt shows the four levels as
0, 1, 2, 3 (the instrument's own wording, with the original point value) and the comparison uses the ordinal 0-3
(0 -> 0, 5 -> 1, 10 -> 2, 15 -> 3). Gold cells that are NA are left out of kappa and counted separately.

ABC items: T.1-T.9 and R.1-R.13, plus any O.* item that the published assessment scores for at least 5 benchmarks (none
does). T.10 is left out: the instrument CSV and the published assessment define different constructs for it.
BetterBench items: a seeded sample of 20 of the 46 criteria (``sampling.betterbench_sample``).

Licence. The ABC repository has no licence, so ABC gold scores are read only to compute statistics: nothing in the
ABC outputs reproduces a per-cell gold value (``write_agreement`` strips them), and ``abc_scores.csv`` is never copied.
"""
from __future__ import annotations

import csv
import email.utils
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from .backends import BackendAuthError, BackendError
from .items import PKG
from .packet_score import CAP_TOKENS, extract_array, render_packet, select_packet
from .coding import ParseError
from .prompts import load_template, prompt_hash
from .resolve import resolve_cell
from .sampling import (SEED, abc_item_list, betterbench_sample, read_rows, write_rows)
from .stats import bootstrap_ci, cohen_kappa, raw_agreement, weighted_kappa, wilson
from .throttle import DailyLimitReached
from .util import est_tokens, read_json, safe_name, sha256_text, utcnow, write_json

SAMPLES = PKG / "samples"
PINS_PATH = SAMPLES / "gold_pins_v1.json"
ABC_ITEMS_PATH = SAMPLES / "gold_abc_items_v1.csv"
BB_CRITERIA_PATH = SAMPLES / "gold_betterbench_criteria_v1.csv"
PAPERS_PATH = SAMPLES / "gold_papers_v1.csv"
BB_POINTS = {0: 0, 5: 1, 10: 2, 15: 3}

SETS: dict[str, dict] = {
    "abc": {
        "label": "ABC (arXiv 2507.02825v5)", "instrument": "abc_items.csv", "gold": "abc_scores.csv",
        "benchmarks": "abc_benchmarks.csv", "cutoff": "2025-07-10T23:59:59Z", "levels": (0, 1), "positive": (1,),
        "top_down": (1,), "release_gold": False, "primary": "cohen_kappa",
        "scale": ("Binary, as in the instrument. 1 = the benchmark satisfies the criterion as worded; 0 = it does not, "
                  "or the packet does not show that it does. There is no partial credit and no NA."),
    },
    "betterbench": {
        "label": "BetterBench (arXiv 2411.12990v1)", "instrument": "betterbench_items.csv",
        "gold": "betterbench_scores.csv", "benchmarks": "betterbench_benchmarks.csv",
        "cutoff": "2024-11-21T23:59:59Z", "levels": (0, 1, 2, 3), "positive": (1, 2, 3), "top_down": (3, 2, 1),
        "release_gold": True, "primary": "weighted_kappa_quadratic",
        "scale": ("The instrument's four levels, shown here as 0 to 3. 0 (instrument: 0 points) = the packet neither "
                  "references nor satisfies the criterion. 1 (instrument: 5 points) = the criterion is mentioned but "
                  "not fulfilled. 2 (instrument: 10 points) = the criterion is partially met. 3 (instrument: 15 "
                  "points) = the criterion is fully met. Answer \"NA\" only for a criterion whose own text says "
                  "n/a or \"if applicable\" and where that condition holds."),
    },
}


@dataclass(frozen=True)
class InstrItem:
    id: str
    title: str
    text: str
    na_allowed: bool = False


def set_cfg(name: str) -> dict:
    if name not in SETS:
        raise ValueError(f"unknown gold set {name!r}; expected one of {sorted(SETS)}")
    return SETS[name]


def find_research_dir(arg: str | None = None) -> Path:
    cands = [arg, os.environ.get("AGENTAUDIT_RESEARCH_DIR")]
    cands += [str(p / "research") for p in [Path.cwd(), *Path.cwd().parents, *PKG.parents]]
    for c in cands:
        if c and (Path(c) / "gold").is_dir() and (Path(c) / "instruments").is_dir():
            return Path(c)
    raise FileNotFoundError("research directory with gold/ and instruments/ not found; pass --research-dir "
                            "(the gold data are not part of the released package)")


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- instruments
_BRACKET = re.compile(r"\s*\[([^\]]*)\]\s*$")


def norm_item_id(raw: str) -> str:
    return raw.strip().split(" ")[0]


def load_instrument(set_name: str, rdir: Path) -> dict[str, InstrItem]:
    cfg = set_cfg(set_name)
    out: dict[str, InstrItem] = {}
    for r in read_csv(Path(rdir) / "instruments" / cfg["instrument"]):
        iid = norm_item_id(r["item_id"])
        text = r["item_text"].strip()
        title = ""
        m = _BRACKET.search(text)
        while m:  # trailing notes added when the CSV was built; keep the App. J title for BetterBench
            note = m.group(1)
            if note.startswith("App. J title:"):
                title = note.split(":", 1)[1].strip()
            text = text[: m.start()].rstrip()
            m = _BRACKET.search(text)
        na = set_name == "betterbench" and bool(re.search(r"n/a|if applicable", f"{text} {title}", re.I))
        out[iid] = InstrItem(iid, title, text, na)
    return out


def items_for_set(set_name: str, rdir: Path | None = None) -> list[str]:
    """Item ids scored for the set, from the frozen list files."""
    if set_name == "abc":
        return [r["item_id"] for r in read_rows(ABC_ITEMS_PATH) if r["included"] == "yes"]
    return [r["criterion_id"] for r in read_rows(BB_CRITERIA_PATH) if r["selected"] == "yes"]


def write_gold_item_lists(rdir: Path, seed: int = SEED) -> dict:
    """Write the fixed item lists (ids only, no gold scores) under ``samples/``."""
    abc_inst = load_instrument("abc", rdir)
    counts: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for r in read_csv(Path(rdir) / "gold" / "abc_scores.csv"):
        k = (r["benchmark"], norm_item_id(r["item_id"]))
        if k not in seen:
            seen.add(k)
            counts[k[1]] = counts.get(k[1], 0) + 1
    abc_rows = abc_item_list(list(abc_inst), counts)
    write_rows(ABC_ITEMS_PATH, abc_rows, ["item_id", "included", "reason"])
    bb_inst = load_instrument("betterbench", rdir)
    pick = set(betterbench_sample(list(bb_inst), seed=seed))
    write_rows(BB_CRITERIA_PATH,
               [{"criterion_id": c, "selected": "yes" if c in pick else "no"} for c in bb_inst],
               ["criterion_id", "selected"])
    return {"abc_included": sum(1 for r in abc_rows if r["included"] == "yes"), "betterbench_selected": len(pick)}


# ---------------------------------------------------------------- gold data
def bench_key(name: str) -> str:
    return safe_name(name)


def load_gold(set_name: str, rdir: Path) -> dict[tuple[str, str], int | str]:
    """(bench key, item id) -> gold value on the comparison scale (ABC 0/1; BetterBench 0-3 or "NA")."""
    cfg = set_cfg(set_name)
    out: dict[tuple[str, str], int | str] = {}
    for r in read_csv(Path(rdir) / "gold" / cfg["gold"]):
        iid = norm_item_id(r.get("item_id") or r["criterion_id"])
        raw = r["score"].strip()
        if set_name == "abc":
            v: int | str = int(raw)
        else:
            v = "NA" if raw.upper() == "NA" else BB_POINTS[int(raw)]
        out[(bench_key(r["benchmark"]), iid)] = v
    return out


def gold_benchmarks(set_name: str, rdir: Path) -> list[dict]:
    """[{key, name, arxiv_id, repo_url}] for the set."""
    cfg = set_cfg(set_name)
    papers = {r["benchmark"]: r for r in read_csv(PAPERS_PATH) if r["set"] == set_name} if PAPERS_PATH.exists() else {}
    out = []
    for r in read_csv(Path(rdir) / "gold" / cfg["benchmarks"]):
        name = r["benchmark"]
        if set_name == "abc":
            m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", r["paper_url"])
            aid, repo = (m.group(1) if m else None), r["repo_url_of_benchmark"]
        else:
            aid = (r.get("arxiv_id_if_in_betterbench_reference") or "").strip() or (papers.get(name) or {}).get("arxiv_id") or None
            repo = r["repo_url"]
        out.append({"key": bench_key(name), "name": name, "arxiv_id": aid, "repo_url": repo})
    return out


# ---------------------------------------------------------------- pinning
UA = {"User-Agent": "agentaudit/0.1 (research tool; gold pinning)"}


def parse_github_url(url: str) -> tuple[str, str, str | None] | None:
    m = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)(/[^#?]*)?", url.strip())
    if not m:
        return None
    owner, repo, rest = m.group(1), m.group(2), m.group(3) or ""
    repo = repo[:-4] if repo.endswith(".git") else repo
    sub = None
    mt = re.match(r"^/tree/[^/]+/(.+?)/?$", rest)
    if mt:
        sub = mt.group(1)
    return owner, repo, sub


def _gh_headers(token: str | None) -> dict:
    h = dict(UA, Accept="application/vnd.github+json")
    tok = token or os.environ.get("GITHUB_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def github_pin(session, owner: str, repo: str, cutoff: str, token: str | None = None) -> dict:
    """Last commit on the default branch with committer date <= cutoff. Falls back to the first commit (flagged)."""
    h = _gh_headers(token)
    meta = session.get(f"https://api.github.com/repos/{owner}/{repo}", headers=h, timeout=60)
    if meta.status_code in (404, 451):  # removed, or blocked for legal reasons: the packet is paper only
        return {"status": "unavailable", "flag": f"repository not accessible (HTTP {meta.status_code}); paper only"}
    if meta.status_code != 200:
        return {"status": "error", "error": f"repo lookup {meta.status_code}"}
    mj = meta.json()
    full = mj.get("full_name", f"{owner}/{repo}")
    r = session.get(f"https://api.github.com/repos/{full}/commits", params={"until": cutoff, "per_page": 1}, headers=h,
                    timeout=60)
    if r.status_code != 200:
        return {"status": "error", "error": f"commits lookup {r.status_code}"}
    arr = r.json()
    rec = {"status": "ok", "repo": full, "default_branch": mj.get("default_branch"), "size_kb": mj.get("size"),
           "archived": mj.get("archived")}
    if arr:
        c = arr[0]
        rec.update(commit=c["sha"], commit_date=c["commit"]["committer"]["date"], flag=None)
        return rec
    r2 = session.get(f"https://api.github.com/repos/{full}/commits", params={"per_page": 1}, headers=h, timeout=60)
    last = re.search(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"', r2.headers.get("Link", "")) if r2.status_code == 200 else None
    if last:
        r2 = session.get(f"https://api.github.com/repos/{full}/commits", params={"per_page": 1, "page": last.group(1)},
                         headers=h, timeout=60)
    if r2.status_code == 200 and r2.json():
        c = r2.json()[0]
        rec.update(commit=c["sha"], commit_date=c["commit"]["committer"]["date"],
                   flag="no commit on or before the cutoff; first commit used")
        return rec
    return {"status": "error", "error": "no commits found"}


_ARXIV_VER = re.compile(r"\[v(\d+)\](?:</a>)?</strong>\s*([A-Za-z]{3}, \d{1,2} [A-Za-z]{3} \d{4} \d\d:\d\d:\d\d [A-Z]+)")


def arxiv_versions(session, arxiv_id: str) -> list[tuple[int, str]]:
    r = session.get(f"https://arxiv.org/abs/{arxiv_id}", headers=UA, timeout=60)
    r.raise_for_status()
    return [(int(v), d) for v, d in _ARXIV_VER.findall(r.text)]


def arxiv_pin(session, arxiv_id: str, cutoff: str) -> dict:
    from datetime import datetime, timezone

    vers = arxiv_versions(session, arxiv_id)
    if not vers:
        return {"status": "error", "error": "no version history parsed"}
    cut = datetime.strptime(cutoff, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ok = [(v, d) for v, d in vers if email.utils.parsedate_to_datetime(d) <= cut]
    if ok:
        v, d = ok[-1]
        return {"status": "ok", "id": arxiv_id, "version": f"v{v}", "version_date": d, "n_versions": len(vers),
                "flag": None}
    v, d = vers[0]
    return {"status": "ok", "id": arxiv_id, "version": f"v{v}", "version_date": d, "n_versions": len(vers),
            "flag": "first version is later than the cutoff; v1 used"}


def pin_set(set_name: str, rdir: Path, session=None, token: str | None = None, log=print) -> dict:
    import requests

    session = session or requests.Session()
    cfg = set_cfg(set_name)
    pins: dict = {}
    for b in gold_benchmarks(set_name, rdir):
        rec: dict = {"name": b["name"], "cutoff": cfg["cutoff"], "repo_url": b["repo_url"]}
        gh = parse_github_url(b["repo_url"]) if b["repo_url"] else None
        if gh:
            owner, repo, sub = gh
            rec["repo"] = github_pin(session, owner, repo, cfg["cutoff"], token)
            rec["repo"].update(owner=owner, name=repo, subpath=sub)
        else:
            rec["repo"] = {"status": "none", "flag": "no GitHub repository (gated or non-GitHub host); paper only"}
        if b["arxiv_id"]:
            try:
                rec["arxiv"] = arxiv_pin(session, b["arxiv_id"], cfg["cutoff"])
            except Exception as e:  # noqa: BLE001 - logged, other benchmarks continue
                rec["arxiv"] = {"status": "error", "id": b["arxiv_id"], "error": str(e)}
        else:
            rec["arxiv"] = {"status": "none", "flag": "no arXiv id known"}
        pins[b["key"]] = rec
        log(f"[pin {set_name}] {b['name']}: repo={rec['repo'].get('commit', rec['repo'].get('status'))} "
            f"arxiv={rec['arxiv'].get('version', rec['arxiv'].get('status'))}")
    return pins


def load_pins(path: Path = PINS_PATH) -> dict:
    return read_json(path) if Path(path).exists() else {"seed": SEED, "sets": {}}


def save_pins(pins: dict, path: Path = PINS_PATH) -> None:
    write_json(path, pins)


def manifest_for(key: str, pin: dict) -> dict:
    m: dict = {"name": key}
    ax = pin.get("arxiv") or {}
    if ax.get("status") == "ok":
        m["arxiv"] = {"id": ax["id"], "version": ax["version"]}
    rp = pin.get("repo") or {}
    if rp.get("status") == "ok":
        m["repo"] = {"url": f"https://github.com/{rp['repo']}", "commit": rp["commit"]}
        if rp.get("subpath"):
            m["repo"]["subpath"] = rp["subpath"]
    return m


def gold_run_dir(run: Path, set_name: str) -> Path:
    return Path(run) / f"gold-{set_name}"


def build_gold_packets(run: Path, set_name: str, pins: dict, only: list[str] | None = None,
                       max_repo_kb: int = 400_000, allow_large: bool = False, session=None, log=print) -> dict:
    from .packet import build_packet

    grun = gold_run_dir(run, set_name)
    res = {"built": [], "skipped": [], "failed": {}}
    for key, pin in sorted(pins["sets"][set_name].items()):
        if only and key not in only:
            continue
        if (grun / "packets" / key / "manifest.json").exists():
            res["skipped"].append(key)
            continue
        man = manifest_for(key, pin)
        if "arxiv" not in man and "repo" not in man:
            res["failed"][key] = "nothing to fetch (no arXiv version and no repository pinned)"
            continue
        size = (pin.get("repo") or {}).get("size_kb") or 0
        if size > max_repo_kb and not allow_large:
            res["failed"][key] = f"repository is {size} KB (> {max_repo_kb}); rerun with --allow-large"
            continue
        try:
            build_packet(man, grun, grun / "_cache", session=session)
            res["built"].append(key)
            log(f"[packets {set_name}] built {key}")
        except Exception as e:  # noqa: BLE001 - one bad download must not stop the others
            res["failed"][key] = str(e)
            log(f"[packets {set_name}] {key} failed: {e}")
    return res


# ---------------------------------------------------------------- prompt, parsing
def render_gold_prompt(set_name: str, item_ids: list[str], instr: dict[str, InstrItem], packet_text: str) -> str:
    cfg = set_cfg(set_name)
    blocks = []
    for iid in item_ids:
        it = instr[iid]
        head = f"### Criterion {iid}" + (f": {it.title}" if it.title else "")
        na = ("NA is allowed for this criterion where its own text says it does not apply."
              if it.na_allowed else "NA is not allowed for this criterion.")
        blocks.append(f"{head}\n{it.text}\n{na}")
    t = load_template("gold.txt")
    rep = {"{{INSTRUMENT}}": cfg["label"], "{{SCALE}}": cfg["scale"], "{{AS_OF}}": cfg["cutoff"][:10], "{{ITEM_BLOCKS}}": "\n\n".join(blocks),
           "{{ITEM_IDS}}": ", ".join(item_ids), "{{N_ITEMS}}": str(len(item_ids)),
           "{{LEVELS}}": " | ".join(str(x) for x in cfg["levels"]) + (' | "NA"' if set_name == "betterbench" else "")}
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.replace("{{PACKET}}", packet_text)


def _norm_gold_score(v, set_name: str):
    cfg = set_cfg(set_name)
    if isinstance(v, bool):
        raise ParseError("score is boolean")
    if isinstance(v, str):
        s = v.strip().upper()
        if s == "NA" and set_name == "betterbench":
            return "NA"
        try:
            v = float(s)
        except ValueError as e:
            raise ParseError(f"bad score: {v!r}") from e
    if isinstance(v, (int, float)) and int(v) == v:
        n = int(v)
        if n in cfg["levels"]:
            return n
        if set_name == "betterbench" and n in BB_POINTS:  # the model answered in the instrument's points
            return BB_POINTS[n]
    raise ParseError(f"bad score: {v!r}")


def parse_gold_response(text: str, item_ids: list[str], set_name: str) -> tuple[dict[str, dict], dict[str, str]]:
    arr = extract_array(text)
    ok: dict[str, dict] = {}
    err: dict[str, str] = {}
    for o in arr:
        if not isinstance(o, dict):
            continue
        iid = norm_item_id(str(o.get("item", o.get("id", ""))))
        if iid not in item_ids or iid in ok:
            continue
        try:
            score = _norm_gold_score(o.get("score"), set_name)
        except ParseError as e:
            err[iid] = str(e)
            continue
        quotes = [{"chunk_id": str(q.get("chunk_id", "")).strip().strip("[]").strip(), "text": str(q.get("text", ""))}
                  for q in (o.get("quotes") or []) if isinstance(q, dict)]
        ok[iid] = {"score": score, "elements": [], "quotes": quotes, "contradicted": False,
                   "contradiction_quotes": [], "rationale": str(o.get("rationale", ""))}
    for iid in item_ids:
        if iid not in ok and iid not in err:
            err[iid] = "missing from response"
    return ok, err


def gold_result_path(grun: Path, bench: str, coder: str) -> Path:
    return Path(grun) / "gold_scoring" / bench / f"{coder}.json"


def score_gold(run: Path, set_name: str, bench: str, coder: str, spec: dict, backend, item_ids: list[str],
               instr: dict[str, InstrItem], cap_tokens: int | None = None, force: bool = False, log=print,
               dry_run: bool = False) -> dict:
    """One whole-packet call for (benchmark, coder) covering every item of the set."""
    from .packet import load_chunks
    from .packet_score import packet_system_prompt
    from .verify import verify_result

    cfg = set_cfg(set_name)
    grun = gold_run_dir(run, set_name)
    path = gold_result_path(grun, bench, coder)
    cap = int(cap_tokens or spec.get("max_packet_tokens") or CAP_TOKENS)
    summary = {"set": set_name, "bench": bench, "coder": coder, "status": None, "items": len(item_ids)}
    if path.exists() and not force:
        try:
            prev = read_json(path)
            if prev.get("status") == "ok":
                summary["status"] = "already_done"
                return summary
        except ValueError:
            pass
    chunks = load_chunks(grun, bench)
    sel = select_packet(chunks, cap)
    packet_text = render_packet(sel["kept"])
    system = packet_system_prompt()
    prompt = render_gold_prompt(set_name, item_ids, instr, packet_text)
    summary.update(tokens_sent=sel["tokens"], dropped=len(sel["dropped"]),
                   prompt_tokens_est=est_tokens(system) + est_tokens(prompt))
    if dry_run:
        summary["status"] = "dry_run"
        return summary
    kept_texts = {c.id: c.text for c in sel["kept"]}
    rec = {"set": set_name, "bench": bench, "coder": coder, "family": spec.get("family"),
           "prompt_sha256": prompt_hash(prompt), "system_sha256": prompt_hash(system),
           "rendered_packet_sha256": sha256_text(packet_text), "cap_tokens": cap, "tokens_sent": sel["tokens"],
           "n_dropped": len(sel["dropped"]), "over_cap": sel["over_cap"], "items_requested": item_ids,
           "attempts": [], "items": {}, "status": "parse_error"}
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
                ok, err = parse_gold_response(resp.text, item_ids, set_name)
            except ParseError as e:
                att["parse_error"] = str(e)
                continue
            att["item_errors"] = err
            if len(ok) >= len(best_ok):
                best_ok, best_err = ok, err
            if not err:
                break
    except DailyLimitReached as e:
        summary.update(status="blocked", reason=str(e), next_available_unix=e.next_available)
        log(f"[{coder}] daily limit reached at {bench}; rerun to resume")
        return summary
    except BackendAuthError as e:
        summary.update(status="blocked", reason=f"authentication: {e}")
        log(f"[{coder}] backend authentication failed: {e}")
        return summary
    except BackendError as e:
        rec["error"] = str(e)
        write_json(path, rec)
        summary.update(status="failed", reason=str(e))
        return summary
    positive = cfg["positive"]
    for iid, parsed in best_ok.items():
        rec["items"][iid] = {"parsed": parsed,
                             "verification": verify_result(parsed, instr[iid], kept_texts, positive_levels=positive)}
    rec["item_errors"] = best_err
    rec["status"] = "ok" if not best_err else "partial" if best_ok else "parse_error"
    rec["timestamp"] = rec["attempts"][-1]["timestamp"] if rec["attempts"] else utcnow()
    write_json(path, rec)
    summary.update(status=rec["status"], scored=len(best_ok))
    log(f"[{coder}] {set_name} {bench}: {rec['status']} ({len(best_ok)}/{len(item_ids)} items)")
    return summary


# ---------------------------------------------------------------- agreement
def load_predictions(run: Path, set_name: str, benches: list[str] | None = None) -> tuple[dict, dict]:
    """({coder: {(bench, item): effective}}, {coder: family}) from the gold scoring files."""
    base = gold_run_dir(run, set_name) / "gold_scoring"
    preds: dict[str, dict] = {}
    fam: dict[str, str] = {}
    if not base.exists():
        return preds, fam
    for d in sorted(base.iterdir()):
        if benches and d.name not in benches:
            continue
        for f in sorted(d.glob("*.json")):
            rec = read_json(f)
            if rec.get("status") not in ("ok", "partial"):
                continue
            c = f.stem
            fam[c] = rec.get("family") or c
            for iid, x in rec["items"].items():
                preds.setdefault(c, {})[(d.name, iid)] = {"raw": x["verification"]["score_raw"],
                                                         "effective": x["verification"]["effective"]}
    return preds, fam


def resolved_predictions(preds: dict, fam: dict, levels: tuple) -> tuple[dict, dict]:
    """Apply the two-family resolution rule per cell over coders. Returns ({cell: final}, status counts)."""
    cells: dict[tuple, dict] = {}
    for c, d in preds.items():
        for cell, v in d.items():
            cells.setdefault(cell, {})[c] = {"raw": v["raw"], "effective": v["effective"], "family": fam[c]}
    out: dict = {}
    counts: dict[str, int] = {}
    for cell, votes in sorted(cells.items()):
        if len(votes) < 2:
            continue
        r = resolve_cell(votes, levels=levels)
        out[cell] = r["final"]
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return out, counts


def agreement_stats(pairs: list[tuple[str, str, object, object]], cfg: dict, n_boot: int, seed: int) -> dict:
    """pairs: (bench, item, gold, pred). Cells where either side is NA are counted and left out of the statistics."""
    levels = list(cfg["levels"])
    used = [(b, i, g, p) for b, i, g, p in pairs if g != "NA" and p != "NA"]
    g_na = sum(1 for _, _, g, _ in pairs if g == "NA")
    p_na = sum(1 for _, _, g, p in pairs if p == "NA" and g != "NA")
    both_na = sum(1 for _, _, g, p in pairs if g == "NA" and p == "NA")
    gs = [g for _, _, g, _ in used]
    ps = [p for _, _, _, p in used]
    n = len(used)
    out: dict = {"n_cells": n, "n_gold_na": g_na, "n_pred_na_where_gold_scored": p_na, "n_both_na": both_na}
    if not n:
        return out
    agree = sum(1 for g, p in zip(gs, ps) if g == p)
    out["raw_agreement"] = {"agree": agree, "n": n, "rate": agree / n, "wilson95": list(wilson(agree, n))}
    out["cohen_kappa"] = cohen_kappa(gs, ps)
    major = max(set(gs), key=gs.count)
    out["majority_class_baseline_agreement"] = gs.count(major) / n
    out["confusion"] = {str(g): {str(p): sum(1 for a, b in zip(gs, ps) if a == g and b == p) for p in levels}
                        for g in levels}
    if len(levels) > 2:
        out["weighted_kappa_quadratic"] = weighted_kappa(gs, ps, levels, "quadratic")
        out["weighted_kappa_linear"] = weighted_kappa(gs, ps, levels, "linear")
        w1 = sum(1 for g, p in zip(gs, ps) if abs(g - p) <= 1)
        out["within_one_level"] = {"hits": w1, "n": n, "rate": w1 / n, "wilson95": list(wilson(w1, n))}
    key = cfg["primary"]
    groups: dict[str, list] = {}
    for b, _, g, p in used:
        groups.setdefault(b, []).append((g, p))

    def stat(units):
        a, c = [u[0] for u in units], [u[1] for u in units]
        return cohen_kappa(a, c) if key == "cohen_kappa" else weighted_kappa(a, c, levels, "quadratic")

    ci = bootstrap_ci(groups, stat, n_boot=n_boot, seed=seed)
    out["primary_statistic"] = key
    out["primary_value"] = out.get(key)
    out["primary_ci95_bootstrap_over_benchmarks"] = list(ci) if ci else None
    per_item: dict[str, dict] = {}
    for iid in sorted({i for _, i, _, _ in used}):
        sel = [(g, p) for _, i, g, p in used if i == iid]
        per_item[iid] = {"n": len(sel), "raw_agreement": raw_agreement([x[0] for x in sel], [x[1] for x in sel])}
    out["per_item_raw_agreement"] = per_item
    return out


def gold_agreement(run: Path, set_name: str, rdir: Path, n_boot: int = 2000, seed: int = SEED,
                   benches: list[str] | None = None) -> dict:
    cfg = set_cfg(set_name)
    gold = load_gold(set_name, rdir)
    ids = set(items_for_set(set_name))
    preds, fam = load_predictions(run, set_name, benches)
    out: dict = {"set": set_name, "instrument": cfg["label"], "seed": seed, "n_boot": n_boot,
                 "gold_cutoff": cfg["cutoff"], "items": sorted(ids), "coders": fam,
                 "comparison_scale": list(cfg["levels"]),
                 "note": ("effective score (a 1+ without a verified quote counts as 0) against the published score; "
                          "cells with NA on either side are counted and left out; primary statistic: " + cfg["primary"]),
                 "by_coder": {}, "resolved": None}
    cells_out = []
    for c in sorted(preds):
        pairs = [(b, i, gold[(b, i)], v["effective"]) for (b, i), v in sorted(preds[c].items())
                 if (b, i) in gold and i in ids]
        out["by_coder"][c] = agreement_stats(pairs, cfg, n_boot, seed)
        out["by_coder"][c]["n_scored_items_without_gold"] = sum(1 for (b, i) in preds[c] if (b, i) not in gold)
        cells_out += [{"coder": c, "bench": b, "item": i, "gold": g, "pred": p} for b, i, g, p in pairs]
    res, counts = resolved_predictions(preds, fam, cfg["top_down"])
    if res:
        pairs = [(b, i, gold[(b, i)], p) for (b, i), p in sorted(res.items()) if (b, i) in gold and i in ids]
        out["resolved"] = agreement_stats(pairs, cfg, n_boot, seed)
        out["resolved"]["status_counts"] = counts
        out["resolved"]["fallback_cells"] = sum(v for k, v in counts.items() if k in ("not_established", "na_rejected_as_zero", "insufficient_coders"))
        cells_out += [{"coder": "RESOLVED", "bench": b, "item": i, "gold": g, "pred": p} for b, i, g, p in pairs]
    out["_cells"] = cells_out
    return out


def write_agreement(run: Path, set_name: str, res: dict) -> list[Path]:
    """Write agreement.json (+ agreement.csv headline table). Per-cell gold values are written only for sets whose
    gold may be redistributed (BetterBench, CC BY 4.0); for ABC only aggregate statistics are written."""
    cfg = set_cfg(set_name)
    d = gold_run_dir(run, set_name) / "agreement"
    cells = res.pop("_cells", [])
    written = []
    write_json(d / "agreement.json", res)
    written.append(d / "agreement.json")
    rows = []
    for c, s in list(res["by_coder"].items()) + ([("RESOLVED", res["resolved"])] if res.get("resolved") else []):
        ra = s.get("raw_agreement") or {}
        rows.append({"coder": c, "n_cells": s.get("n_cells"), "raw_agreement": ra.get("rate"),
                     "cohen_kappa": s.get("cohen_kappa"), "weighted_kappa_quadratic": s.get("weighted_kappa_quadratic"),
                     "weighted_kappa_linear": s.get("weighted_kappa_linear"),
                     "primary_ci_lo": (s.get("primary_ci95_bootstrap_over_benchmarks") or [None, None])[0],
                     "primary_ci_hi": (s.get("primary_ci95_bootstrap_over_benchmarks") or [None, None])[1]})
    if rows:
        write_rows(d / "agreement.csv", rows, list(rows[0]))
        written.append(d / "agreement.csv")
    if cfg["release_gold"] and cells:
        write_rows(d / "cells_with_gold.csv", cells, ["coder", "bench", "item", "gold", "pred"])
        written.append(d / "cells_with_gold.csv")
    return written


def run_gold_agree(run: Path, set_name: str, rdir: Path, n_boot: int = 2000) -> dict:
    res = gold_agreement(run, set_name, rdir, n_boot)
    write_agreement(run, set_name, res)
    return res


def estimate_gold(run: Path, set_name: str, pins: dict, caps: dict[str, int | None]) -> dict:
    """Calls and a rough input-token estimate per coder from packet manifests (when built), else the cap."""
    keys = sorted(pins["sets"].get(set_name, {}))
    grun = gold_run_dir(run, set_name)
    tok = {}
    for k in keys:
        mp = grun / "packets" / k / "manifest.json"
        tok[k] = int(read_json(mp)["total_chunk_tokens"]) if mp.exists() else None
    out = {}
    for c, cap in caps.items():
        cap = cap or CAP_TOKENS
        out[c] = {"calls": len(keys),
                  "input_tokens_est": sum(min(t, cap) if t is not None else cap for t in tok.values()) + 3000 * len(keys),
                  "packets_built": sum(1 for t in tok.values() if t is not None)}
    return out
