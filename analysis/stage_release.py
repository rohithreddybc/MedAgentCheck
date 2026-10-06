"""Provenance: derives results/, transport/, reruns/ and analysis/ from the authors' working tree (not runnable without it)."""
from __future__ import annotations
import csv, hashlib, json, os, re, shutil, sys
from pathlib import Path

W = Path(os.environ["AUDIT_WORKDIR"])  # the authors' working tree (audit/, analysis/, research/ ...)
R = W / "release" / "agentaudit"
AUD = W / "audit"
ANA = W / "analysis"
V3 = W / "research" / "executed" / "runs" / "v3"
MAXW = 25
STATS = {"quotes_truncated": 0, "raw_unparsed": 0, "paths_scrubbed": 0, "files": 0}

PATH_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+rohit[^\s\"',\]\)]*", re.I)


def scrub_str(s: str) -> str:
    n = PATH_RE.subn("<local-path>", s)
    if n[1]:
        STATS["paths_scrubbed"] += n[1]
    return n[0]


def trunc_text(t: str):
    w = t.split()
    if len(w) <= MAXW:
        return t, None
    return " ".join(w[:MAXW]) + " ...", {"full_words": len(w), "full_sha256": hashlib.sha256(t.encode("utf8")).hexdigest()}


def sanitize(o, key=None):
    """Recursively truncate quotes to 25 words and scrub local paths."""
    if isinstance(o, dict):
        if "text" in o and isinstance(o["text"], str) and ("chunk_id" in o):
            new = {k: sanitize(v, k) for k, v in o.items()}
            t, meta = trunc_text(o["text"])
            if meta:
                STATS["quotes_truncated"] += 1
                new["text"] = t
                new["truncated"] = True
                new.update(meta)
            return new
        return {k: sanitize(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [sanitize(v, key) for v in o]
    if isinstance(o, str):
        if key == "raw_response":
            return sanitize_raw(o)
        return scrub_str(o)
    return o


def sanitize_raw(s: str) -> str:
    """raw_response is a JSON array in a string. Truncate over-long quotes; keep everything else."""
    txt = s.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", txt)
    try:
        j = json.loads(txt)
    except Exception:
        # try to locate the array
        a, b = txt.find("["), txt.rfind("]")
        try:
            j = json.loads(txt[a:b + 1])
        except Exception:
            STATS["raw_unparsed"] += 1
            return "[unparsed raw response withheld; sha256 " + hashlib.sha256(s.encode("utf8")).hexdigest() + "]"
    before = STATS["quotes_truncated"]
    j2 = sanitize(j)
    if STATS["quotes_truncated"] == before and txt == s.strip():
        return scrub_str(s)  # untouched
    return json.dumps(j2, ensure_ascii=False, indent=0)


def rj(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def wj(p: Path, o, indent=1):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    STATS["files"] += 1


def copy_json(src: Path, dst: Path):
    wj(dst, sanitize(rj(src)))


def copy_text(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    txt = src.read_text(encoding="utf-8")
    dst.write_text(scrub_str(txt), encoding="utf-8", newline="\n")
    STATS["files"] += 1


def copy_tree(src: Path, dst: Path, skip=lambda p: False):
    for p in sorted(src.rglob("*")):
        if p.is_dir() or skip(p):
            continue
        rel = p.relative_to(src)
        if p.suffix == ".json":
            copy_json(p, dst / rel)
        else:
            copy_text(p, dst / rel)


# ---------------------------------------------------------------- results/resolved (cells + quotes + flags)
res = R / "results"
benches = sorted(p.stem for p in (AUD / "resolved").glob("*.json") if p.stem != "summary")
for b in benches:
    r = rj(AUD / "resolved" / f"{b}.json")
    out = {"bench": b, "cells": {}}
    for item, c in r["cells"].items():
        cell = dict(c)
        cell["coders"] = {}
        for vf in sorted((AUD / "verified" / b / item).glob("*.json")):
            v = rj(vf)
            coder = vf.stem
            cod = {k: v[k] for k in ("score_raw", "effective", "supported", "supported_strict", "n_quotes", "n_verified",
                                      "n_verified_strict", "contradicted", "contradiction_verified", "flags", "elements",
                                      "quotes", "contradiction_quotes", "family")}
            cf = AUD / "coding" / b / item / f"{coder}.json"
            if cf.exists():
                cd = rj(cf)
                cod["model_id"] = cd.get("model_id")
                cod["timestamp"] = cd.get("timestamp")
                cod["rationale"] = (cd.get("parsed") or {}).get("rationale")
                cod["prompt_sha256"] = cd.get("prompt_sha256")
                cod["packet_sha256"] = cd.get("packet_sha256")
            cell["coders"][coder] = cod
        out["cells"][item] = cell
    wj(res / "resolved" / f"{b}.json", sanitize(out))
copy_text(AUD / "resolved" / "resolved.csv", res / "resolved" / "resolved.csv")
copy_json(AUD / "resolved" / "summary.json", res / "resolved" / "summary.json")

# ---------------------------------------------------------------- manifests (input manifests, sanitized packet manifests)
for p in sorted((AUD / "manifests").glob("*.yaml")):
    copy_text(p, res / "manifests" / p.name)
for p in sorted((AUD / "packets").glob("*/manifest.json")):
    m = rj(p)
    pe = m.get("privacy_exclusion") or {}
    removed = pe.get("removed_chunks", [])
    removed_files = {re.sub(r":\d+-\d+$", "", c).split(":", 1)[-1] for c in removed}
    m["sources"] = [{k: v for k, v in s.items() if k not in ("chunks", "stored")}
                    for s in m["sources"] if s.get("path") not in removed_files]
    if pe:
        m["privacy_exclusion"] = {"date": pe.get("date"), "n_removed_chunks": len(removed),
                                  "note": "files and chunks that hold patient-identifier fields were removed before coding; names withheld"}
    wj(res / "packet_manifests" / f"{p.parent.name}.json", sanitize(m))

# ---------------------------------------------------------------- coder responses
cr = res / "coder_responses"
for p in sorted((AUD / "scoring").glob("*/*/*.json")):
    copy_json(p, cr / "base" / p.relative_to(AUD / "scoring"))
for sub, name in [("responses", "sonnet_subagent_raw_base"), ("responses_perturb", "sonnet_subagent_raw_perturb"),
                  ("responses_perturb_codex", "codex_raw_perturb"), ("responses_retest", "sonnet_subagent_raw_retest"),
                  ("responses_retest_codex", "codex_raw_retest")]:
    for p in sorted((AUD / "transport" / sub).iterdir()):
        if p.suffix == ".json":
            if p.name.endswith(".meta.json"):
                copy_json(p, cr / name / p.name)
            else:
                # raw arrays: sanitize via the same routine
                s = p.read_text(encoding="utf-8")
                dst = cr / name / p.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(sanitize_raw(s) + "\n", encoding="utf-8")
                STATS["files"] += 1
        else:
            copy_text(p, cr / name / p.name)

# ---------------------------------------------------------------- gold agreement (statistics only)
copy_tree(AUD / "gold_abc" / "gold-abc" / "agreement", res / "gold" / "abc", skip=lambda p: p.name == "cells_with_gold.csv")
copy_tree(AUD / "gold_bb" / "gold-betterbench" / "agreement", res / "gold" / "betterbench", skip=lambda p: p.name == "cells_with_gold.csv")

# ---------------------------------------------------------------- perturbation (final run; no variant packets)
copy_tree(AUD / "perturb" / "perturb", res / "perturbation")

# ---------------------------------------------------------------- retest (no packets)
copy_tree(AUD / "retest", res / "retest", skip=lambda p: "packets" in p.relative_to(AUD / "retest").parts)

# ---------------------------------------------------------------- analysis outputs
EXC = {"RESULTS_SUMMARY.md", "coder_isolation_audit.md"}
copy_tree(ANA / "out", res / "analysis_out", skip=lambda p: p.name in EXC and p.parent == ANA / "out")

# ---------------------------------------------------------------- transport
tr = R / "transport"
for p in sorted((AUD / "transport").iterdir()):
    if p.is_file() and p.suffix in (".py", ".md"):
        copy_text(p, tr / p.name)
copy_text(ANA / "coder_isolation_audit.py", tr / "coder_isolation_audit.py")
copy_text(ANA / "out" / "coder_isolation_audit.md", tr / "coder_isolation_audit.md")

# ---------------------------------------------------------------- analysis (new files only)
an = R / "analysis"
frozen_names = {"common.py", "figures.py", "judge_rerun.py", "rq1_rq2.py", "rq3_reruns.py"}
for p in sorted(ANA.glob("*.py")):
    if p.name in {"rq1_rq2.py", "rq3_reruns.py"}:
        copy_text(p, an / "postfreeze" / p.name)
    elif p.name in frozen_names or p.name == "coder_isolation_audit.py":
        continue
    else:
        copy_text(p, an / p.name)
copy_text(ANA / "out" / "RESULTS_SUMMARY.md", an / "out" / "RESULTS_SUMMARY.md")
if not (R / "analysis" / "README.md").exists():
    copy_text(ANA / "README.md", an / "README.md")

# ---------------------------------------------------------------- reruns
rr = R / "reruns"
KEEP = ["_key", "bench", "task_id", "condition_name", "condition", "repeat", "model_ids", "system_fingerprints",
        "timestamps", "driver_start", "driver_status", "wall_s", "n_calls", "n_error_calls", "calls", "usage", "env_seed",
        "actions", "verdict", "error", "episode_error"]
for bdir in sorted(V3.iterdir()):
    if not bdir.is_dir():
        continue
    rows = []
    for line in (bdir / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        o = {k: e[k] for k in KEEP if k in e}
        rc = e.get("role_config")
        if isinstance(rc, dict):
            o["role_config"] = rc
        v = e.get("verdict")
        if isinstance(v, dict):
            o["verdict"] = {k: x for k, x in v.items() if k not in ("reference_answer", "conclusion")}
        for k in ("error", "episode_error"):
            if isinstance(o.get(k), str):
                o[k] = scrub_str(o[k])[:160]
        if isinstance(e.get("actions"), list):
            if bdir.name == "synthetic_hospital":
                # arguments (synthetic patient ids, diagnoses) withheld: keep tool names, hash covers the full sequence
                o["actions"] = [a.split("{", 1)[0] for a in e["actions"]]
                o["actions_note"] = "tool names only; actions_sha256 is over the full canonical sequence with arguments"
            o["n_actions"] = len(e["actions"])
            o["actions_sha256"] = hashlib.sha256(json.dumps(e["actions"], ensure_ascii=False, separators=(",", ":")).encode("utf8")).hexdigest()
        if isinstance(e.get("actions_strict"), list):
            o["actions_strict_sha256"] = hashlib.sha256(json.dumps(e["actions_strict"], ensure_ascii=False, separators=(",", ":")).encode("utf8")).hexdigest()
        rows.append(o)
    (rr).mkdir(parents=True, exist_ok=True)
    with open(rr / f"{bdir.name}_episodes.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for o in rows:
            f.write(json.dumps(sanitize(o), ensure_ascii=False) + "\n")
    STATS["files"] += 1
    cap = bdir / "capability.json"
    if cap.exists():
        copy_json(cap, rr / f"{bdir.name}_capability.json")

print(STATS)
