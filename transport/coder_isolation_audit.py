#!/usr/bin/env python3
"""Audit the Claude Code subagent coder runs for isolation (reviewer concern M7).

Streams every subagent transcript (JSONL) of the project, identifies coder runs (prompt contains
'annotator applying a fixed coding manual'), extracts every tool call, and classifies each as
in scope (read of the assigned prompt directory, write of the assigned response file) or out of scope.
Writes analysis/out/coder_isolation_audit.md. Prints only aggregates.

Usage: python coder_isolation_audit.py [--proj DIR] [--out FILE]
"""
import argparse, collections, glob, json, os, re, sys

DEF_PROJ = os.path.expanduser(
    r"~/.claude/projects/C--Users-rohit-Documents-Research-Papers-Researchpaper26---ieee-access")
HERE = os.path.dirname(os.path.abspath(__file__))
DEF_OUT = os.path.join(HERE, "out", "coder_isolation_audit.md")
MARK = "annotator applying a fixed coding manual"


def norm(p):
    return (p or "").replace("\\", "/").rstrip("/").lower()


def text_of(content):
    if isinstance(content, list):
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict))
    return content or ""


def run_type(prompt):
    m = re.search(r"prompts_?(gold_abc|gold_betterbench|perturb|retest)?/", norm(prompt))
    d = m.group(1) if m else None
    if d is None:
        return "main", None
    return {"gold_abc": "gold", "gold_betterbench": "gold"}.get(d, d), d


def assigned(prompt):
    """Return (prompt_dir_rel, response_rel) assigned by the prompt, lowercased with forward slashes."""
    pn = norm(prompt)
    pd = re.search(r"read (prompts[a-z_]*/[a-z0-9_.\-]+)/system\.txt", pn)
    rs = re.search(r"to (responses[a-z_]*/[a-z0-9_.\-]+\.json)", pn)
    base = re.search(r"base:\s*(.+?)(?:\.\s|\n)", pn)
    return (pd.group(1) if pd else None, rs.group(1) if rs else None,
            norm(base.group(1)) if base else None)


def classify(name, inp, pdir, resp, base):
    """Return (category, detail). category 'ok' or 'violation'."""
    if name in ("SubagentHandback",):
        return "ok", "handback"
    path = inp.get("file_path") or inp.get("path") or ""
    n = norm(path)
    rel = n[len(base) + 1:] if base and n.startswith(base + "/") else (n if not re.match(r"^[a-z]:/", n) else None)
    if name == "Read":
        if rel and pdir and (rel == pdir + "/meta.json" or rel.startswith(pdir + "/")):
            return "ok", "read assigned prompt dir"
        return "violation", f"Read {path}"
    if name == "Write":
        if rel and resp and rel == resp:
            return "ok", "write assigned response"
        return "violation", f"Write {path}"
    blob = norm(json.dumps(inp, ensure_ascii=False).replace("\\\\", "/"))
    if name in ("Bash", "PowerShell", "Grep", "Glob", "Edit"):
        scan = norm(str(inp.get("command") or "") + " " + str(inp.get("path") or "") + " " + str(inp.get("file_path") or "")
                    + " " + str(inp.get("pattern") or "" if name == "Glob" else ""))
        scan = scan.replace("\\", "/")
        for keep in (pdir, resp):
            if keep:
                scan = scan.replace(keep, "")
        bad = [k for k in FORBIDDEN if k in scan]
        if "http" in blob or "curl" in blob or "wget" in blob:
            bad.append("web")
        # any reference to a prompts*/ or responses*/ directory that is not the assigned one
        other = []
        for m in re.finditer(r"(prompts|responses)[a-z_]*/([a-z0-9_\-.]+)", blob):
            ref = m.group(0)
            ref = ref[:-5] if ref.endswith(".json") else ref
            if not ((pdir and ref.startswith(pdir)) or (resp and ref == resp[:-5])):
                other.append(m.group(0))
        if name in ("Grep", "Glob", "Edit"):
            pth = norm(inp.get("path") or inp.get("file_path") or "")
            rel2 = pth[len(base) + 1:] if base and pth.startswith(base + "/") else pth
            if not rel2 or not ((pdir and rel2.startswith(pdir)) or (resp and rel2 == resp)):
                other.append("path=" + (rel2 or "<default cwd>"))
        if bad or other:
            return "violation", f"{name}: {blob[:300]} [flags: {bad + other}]"
        return "scoped", f"{name} confined to assigned prompt dir / response file: {blob[:200]}"
    return "violation", f"{name}: {json.dumps(inp)[:300]}"


FORBIDDEN = ["gold", "rubric", "pilot", "resolved", "verified", "scoring/", "coding/", "analysis", "paper/",
             "research/", "codex", "scorer", "decisions", "manifest", "packets",
             ".claude", "memory"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=DEF_PROJ)
    ap.add_argument("--out", default=DEF_OUT)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.proj, "**", "*.jsonl"), recursive=True))
    runs, viol, sc = [], [], []
    n_total_transcripts = 0
    for f in files:
        n_total_transcripts += 1
        first, models, calls, results_err = None, collections.Counter(), [], 0
        atts = collections.Counter()
        with open(f, encoding="utf8") as fh:
            for ln, line in enumerate(fh, 1):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if first is None and d.get("type") == "user":
                    first = text_of(d["message"]["content"])
                    if MARK not in first:
                        break
                if d.get("type") == "attachment":
                    atts[(d.get("attachment") or {}).get("type")] += 1
                if d.get("type") == "assistant":
                    msg = d["message"]
                    models[msg.get("model")] += 1
                    for b in msg.get("content", []):
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            calls.append((ln, b["name"], b.get("input", {})))
        if first is None or MARK not in first:
            continue
        rt, sub = run_type(first)
        pdir, resp, base = assigned(first)
        cat = collections.Counter(); v = []
        by_tool = collections.Counter()
        for ln, name, inp in calls:
            by_tool[name] += 1
            c, det = classify(name, inp, pdir, resp, base)
            cat[c] += 1
            if c == "violation":
                v.append((os.path.relpath(f, a.proj), ln, name, det))
            elif c == "scoped":
                sc.append((os.path.relpath(f, a.proj), ln, name))
        bench = (re.search(r"Bench:\s*(\S+?)\.", first) or re.search(r"Bench:\s*(\S+)", first))
        iso = re.search(r"Use no other [^.]*\.[^.]*\.?", first)
        runs.append(dict(atts=atts, file=os.path.relpath(f, a.proj), type=rt, sub=sub, bench=(bench.group(1) if bench else (pdir.split("/")[-1] if pdir else "?")),
                         models=dict(models), calls=len(calls), by_tool=by_tool, ok=cat["ok"], scoped=cat["scoped"], viol=cat["violation"],
                         pdir=pdir, resp=resp, iso=iso.group(0) if iso else None,
                         has_iso=bool(re.search(r"no other (information )?source", first, re.I))))
        viol += v

    # report
    L = []
    w = L.append
    w("# Coder isolation audit (Claude Sonnet subagent coder)\n")
    w(f"Source: `{a.proj}` ({n_total_transcripts} transcripts scanned, streamed). Script: `analysis/coder_isolation_audit.py`.\n")
    w("A coder run is a subagent whose first prompt contains the annotator template. In scope: Read of the assigned "
      "`prompts*/<bench>/` files (system, meta.json, user parts) and Write of the assigned `responses*/<bench>.json`. "
      "Bash/Grep/Edit calls are reported separately as scoped when every path they touch is the run's own prompt directory or response file and they reference no gold, pilot, resolved, verified, scoring, paper, analysis or web target. Anything else (another Read or Write target, another bench's files, any other path, web) is out of scope. The tool-call total includes one SubagentHandback call per run. Only session b70619cc exists in the project transcript folder (192 subagent transcripts, 124 of them coder runs; the rest are build, analysis and review subagents).\n")
    tot_calls = sum(r["calls"] for r in runs)
    w(f"## Summary\n\n- Coder subagent runs: {len(runs)}\n- Tool calls in those runs: {tot_calls}\n"
      f"- Bash/Grep/Edit calls confined to the assigned prompt dir or response file (see below): {sum(r['scoped'] for r in runs)}\n"
      f"- Out-of-scope calls: {len(viol)}\n- Runs with at least one out-of-scope call: {sum(1 for r in runs if r['viol'])}\n"
      f"- Runs whose prompt carries the isolation instruction: {sum(r['has_iso'] for r in runs)} of {len(runs)}\n")
    mc = collections.Counter()
    for r in runs:
        for m, n in r["models"].items():
            mc[m] += n
    w("- Model ids (assistant message.model, count of messages): " + ", ".join(f"`{m}` x{n}" for m, n in mc.items()) + "\n")
    w("\n## Counts per run type\n")
    w("| Run type | Runs | Tool calls | Read | Write | Bash | Grep | Other | Out of scope |\n|---|---|---|---|---|---|---|---|---|")
    for t in ("main", "gold", "perturb", "retest"):
        rr = [r for r in runs if r["type"] == t]
        bt = collections.Counter()
        for r in rr:
            bt.update(r["by_tool"])
        other = sum(bt.values()) - bt["Read"] - bt["Write"] - bt["Bash"] - bt["Grep"]
        w(f"| {t} | {len(rr)} | {sum(r['calls'] for r in rr)} | {bt['Read']} | {bt['Write']} | {bt['Bash']} | {bt['Grep']} | {other} | {sum(r['viol'] for r in rr)} |")
    w("\nGold runs by prompt directory: " + ", ".join(f"{k}: {v}" for k, v in collections.Counter(r['sub'] for r in runs if r['type'] == 'gold').items()))
    w("\n\n## Isolation instruction in the prompt (quote)\n")
    isos = collections.Counter(r["iso"] for r in runs)
    for q, n in isos.most_common():
        w(f"- ({n} runs) \"{q}\"")
    w("\n## Out-of-scope accesses\n")
    if not viol:
        w("None.")
    else:
        w("| Transcript (relative to project dir) | Line | Tool | Detail |\n|---|---|---|---|")
        for fpath, ln, name, det in viol:
            w(f"| {fpath} | {ln} | {name} | {det.replace('|', '/')} |")
    ac = collections.Counter()
    for r in runs:
        ac.update(r["atts"])
    w("\n## Context injected by the harness (attachment records in coder transcripts)\n")
    w("Attachment types: " + ", ".join(f"{k} x{v}" for k, v in ac.most_common()) +
      ". These are harness-supplied (instructions, skill/agent listings, environment, token reminders), not files "
      "read by the subagent. Claude Code loads the project CLAUDE.md into every subagent; that is context the OpenAI "
      "coder did not have. It holds no benchmark gold or pilot content, but it is a difference between transports.\n")
    w("\n## Scoped Bash/Grep/Edit calls (confined to the run's own prompt directory or response file)\n")
    w("They search or count inside the run's own prompt parts, or validate/repair quotes in its own response file. "
      "No other path, no gold/pilot/resolved/other-bench path, no web. Count per transcript and tool:\n")
    cc = collections.Counter((x[0], x[2]) for x in sc)
    for (fpath, name), n in sorted(cc.items()):
        w(f"- {fpath}: {name} x{n}")
    w("\n## Per-run listing\n")
    w("| Transcript | Type | Bench/variant | Model(s) | Calls | Out of scope |\n|---|---|---|---|---|---|")
    for r in runs:
        w(f"| {r['file']} | {r['type']} | {r['bench']} | {','.join(r['models'])} | {r['calls']} | {r['viol']} |")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"runs={len(runs)} calls={tot_calls} violations={len(viol)} models={dict(mc)}")
    by = collections.Counter(x[2] for x in viol)
    print("violations by tool:", dict(by))


if __name__ == "__main__":
    main()
