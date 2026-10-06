"""PROVISIONAL RQ1 prevalence from the Claude coder (sonnet) alone, 44 coded benchmarks.

Score = effective level from audit/verified/<bench>/<item>/sonnet.json (a 1+ without a verified quote counts as 0).
NA cells leave the denominator. No second coder, no resolution, no adjudication. Per-item Wilson 95% CIs treat
benchmarks as independent. Module aggregates use a bootstrap over benchmarks (seed 20261004, 2000 draws), because the
25 items inside a benchmark are not independent. Contradiction flags are the coder's G2 flag; "verified" means at least
one contradiction quote was found in the packet. Flags are candidate findings only (G2), not findings.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from common import OUT, ROOT, SEED, write_csv
from agentaudit.items import ITEM_ORDER, load_items
from agentaudit.stats import wilson

AUDIT = ROOT / "audit"
PROV = OUT / "provisional"
TAG = "PROVISIONAL: Claude coder only, not resolved"
items = load_items()

cells = {}   # (bench,item) -> dict
for f in sorted((AUDIT / "verified").glob("*/*/sonnet.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    cells[(d["bench"], d["item"])] = d
benches = sorted({b for b, _ in cells})
assert all((b, i) in cells for b in benches for i in ITEM_ORDER), "incomplete coding"


def lvl(c):
    v = c["effective"]
    return None if v == "NA" else int(v)


rows = []
for it in ITEM_ORDER:
    vs = [lvl(cells[(b, it)]) for b in benches]
    app = [v for v in vs if v is not None]
    n = len(app)
    k1 = sum(v >= 1 for v in app)
    k2 = sum(v == 2 for v in app)
    w1, w2 = wilson(k1, n), wilson(k2, n)
    cf = [cells[(b, it)] for b in benches]
    rows.append({"item": it, "module": items[it].module, "title": items[it].title, "n_benchmarks": len(benches),
                 "n_applicable": n, "n_na": len(vs) - n, "n_ge1": k1, "share_ge1": k1 / n if n else None,
                 "ge1_wilson_lo": w1[0] if w1 else None, "ge1_wilson_hi": w1[1] if w1 else None,
                 "n_eq2": k2, "share_eq2": k2 / n if n else None,
                 "eq2_wilson_lo": w2[0] if w2 else None, "eq2_wilson_hi": w2[1] if w2 else None,
                 "mean_level": sum(app) / n if n else None,
                 "n_contradiction_flags": sum(c["contradicted"] for c in cf),
                 "n_contradiction_flags_verified": sum(c["contradiction_verified"] for c in cf),
                 "status": TAG})
write_csv(PROV / "rq1_prevalence_provisional.csv", rows)

# module aggregates, bootstrap over benchmarks
mods = {"core": [i for i in ITEM_ORDER if items[i].module == "core"],
        "agent": [i for i in ITEM_ORDER if items[i].module == "agent"]}


def agg(bs, mod):
    vs = [lvl(cells[(b, i)]) for b in bs for i in mods[mod]]
    vs = [v for v in vs if v is not None]
    return (sum(vs) / len(vs), sum(v >= 1 for v in vs) / len(vs), sum(v == 2 for v in vs) / len(vs)) if vs else (None,) * 3


def stats(bs):
    a, c = agg(bs, "agent"), agg(bs, "core")
    return {"agent_mean": a[0], "core_mean": c[0], "diff_mean": a[0] - c[0],
            "agent_ge1": a[1], "core_ge1": c[1], "diff_ge1": a[1] - c[1],
            "agent_eq2": a[2], "core_eq2": c[2], "diff_eq2": a[2] - c[2]}


pt = stats(benches)
rng = random.Random(SEED)
boots = []
for _ in range(2000):
    boots.append(stats([benches[rng.randrange(len(benches))] for _ in benches]))
mrows = []
for k, v in pt.items():
    xs = sorted(b[k] for b in boots)
    mrows.append({"metric": k, "estimate": v, "boot_lo": xs[int(0.025 * 1999)], "boot_hi": xs[int(0.975 * 1999)]})
for r in mrows:
    r["status"] = TAG
for m in mods:
    nm = sum(1 for b in benches for i in mods[m] if lvl(cells[(b, i)]) is None)
    mrows.append({"metric": f"{m}_n_items", "estimate": len(mods[m]), "status": TAG})
    mrows.append({"metric": f"{m}_na_cells", "estimate": nm, "status": TAG})
    mrows.append({"metric": f"{m}_contradiction_flags", "estimate": sum(
        cells[(b, i)]["contradicted"] for b in benches for i in mods[m]), "status": TAG})
write_csv(PROV / "rq1_modules_provisional.csv", mrows)

r = {m["metric"]: m for m in mrows}
fmt = lambda k, p=True: (f"{r[k]['estimate']:.1%}" if p else f"{r[k]['estimate']:.2f}") + \
    f" (95% bootstrap {r[k]['boot_lo']:.1%}-{r[k]['boot_hi']:.1%})" if p else \
    f"{r[k]['estimate']:.2f} ({r[k]['boot_lo']:.2f}-{r[k]['boot_hi']:.2f})"
tl = ["| Item | Module | n | >=1 (Wilson 95%) | =2 (Wilson 95%) | mean | contradiction flags (verified) |", "|---|---|---|---|---|---|---|"]
for x in rows:
    tl.append(f"| {x['item']} {x['title']} | {x['module']} | {x['n_applicable']} | {x['share_ge1']:.0%} "
              f"({x['ge1_wilson_lo']:.0%}-{x['ge1_wilson_hi']:.0%}) | {x['share_eq2']:.0%} "
              f"({x['eq2_wilson_lo']:.0%}-{x['eq2_wilson_hi']:.0%}) | {x['mean_level']:.2f} | "
              f"{x['n_contradiction_flags']} ({x['n_contradiction_flags_verified']}) |")
tot_flags = sum(x["n_contradiction_flags"] for x in rows)
md = f"""# Provisional RQ1 prevalence (Claude coder)

**{TAG}.** Coder: sonnet (claude-sonnet-5-5 via Claude Code subagent), effective level after quote verification, 44 coded benchmarks (the 45th frozen-list packet has no coding), 25 items each (14 core C1-C14, 11 agent A1-A11). NA cells leave the denominator. No second coder, no resolution, no adjudication: the codex coder exists but is not used here, so these shares are one model's reading and cannot be called resolved. Per-item Wilson intervals treat benchmarks as independent.

## Module aggregates (pooled applicable cells; bootstrap over benchmarks, seed {SEED}, 2000 draws)

| Metric | Agent module | Core module | Agent minus core |
|---|---|---|---|
| Share reported (level >= 1) | {fmt('agent_ge1')} | {fmt('core_ge1')} | {fmt('diff_ge1')} |
| Share fully reported (level 2) | {fmt('agent_eq2')} | {fmt('core_eq2')} | {fmt('diff_eq2')} |
| Mean level (0-2) | {fmt('agent_mean', False)} | {fmt('core_mean', False)} | {fmt('diff_mean', False)} |

Contradiction flags: {tot_flags} in total ({r['agent_contradiction_flags']['estimate']:.0f} on agent items, {r['core_contradiction_flags']['estimate']:.0f} on core items); candidate findings only, not verified against benchmark documentation or sent for right of reply.

## Per item

""" + "\n".join(tl) + "\n"
(PROV / "rq1_prevalence_provisional.md").write_text(md, encoding="utf-8")
print(md)
