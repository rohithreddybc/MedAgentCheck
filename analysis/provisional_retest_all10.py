"""PROVISIONAL: Claude (sonnet) coder test-retest on all 10 drawn benchmarks.

`agentaudit retest --compare-only` maps frozen ids to packet directories with bench_dir_candidates(), which tries
safe_name(id), safe_name(benchmark_name) and its lower case. For 'DiagGym/DiagBench' and 'Synthetic Hospital' that gives
diaggym_diagbench and synthetic_hospital (underscores), but the packet directories are diaggym-diagbench and
synthetic-hospital (hyphens, the manifest `name`). So the two have packet_dir = null and drop out (8 of 10 matched).
Frozen code is not edited. This script maps ids through audit/manifests/*.yaml (`frozen_list_id` -> `name`) instead and
reuses the frozen statistics read-only. No file under audit/ is written.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from common import OUT, ROOT, SEED, write_csv  # noqa: F401  (common puts scorer on sys.path)
from agentaudit.agree import load_scores
from agentaudit.retest import _pair_stats
from agentaudit.sampling import draw_retest_benchmarks, load_frozen_list

AUDIT = ROOT / "audit"
PROV = OUT / "provisional"
CODER = "sonnet"

frozen = load_frozen_list(ROOT / "research" / "eligibility" / "frozen_list_v1.csv")
drawn = draw_retest_benchmarks([r["id"] for r in frozen], 10, SEED)
slug = {}
for p in (AUDIT / "manifests").glob("*.yaml"):
    m = yaml.safe_load(p.read_text(encoding="utf-8"))
    slug[m["frozen_list_id"]] = m["name"]
benches = [slug[i] for i in drawn]
missing = [i for i in drawn if i not in slug or not (AUDIT / "coding" / slug[i]).exists()
           or not (AUDIT / "retest" / "coding" / slug[i]).exists()]

o_cells, _ = load_scores(AUDIT, benches)
r_cells, _ = load_scores(AUDIT / "retest", benches)
pairs, groups, per_bench = [], {}, {}
for (b, it), votes in sorted(o_cells.items()):
    rv = r_cells.get((b, it), {})
    if CODER in votes and CODER in rv:
        p = (votes[CODER], rv[CODER])
        pairs.append(p)
        groups.setdefault(b, []).append(list(p))
        d = per_bench.setdefault(b, [0, 0])
        d[0] += 1
        d[1] += p[0] == p[1]
st = _pair_stats(pairs, groups, 2000, SEED)
st["n_benchmarks"] = len(groups)

rows = [{"id": i, "packet_dir": slug[i], "n_cells": per_bench.get(slug[i], [0, 0])[0],
         "n_exact": per_bench.get(slug[i], [0, 0])[1],
         "raw_agreement": (per_bench[slug[i]][1] / per_bench[slug[i]][0]) if slug[i] in per_bench else None,
         "frozen_compare_only_matched": slug[i] not in ("diaggym-diagbench", "synthetic-hospital"),
         "status": "PROVISIONAL: Claude coder only, not resolved"} for i in drawn]
write_csv(PROV / "retest_all10_per_benchmark.csv", rows)
out = {"status": "PROVISIONAL: Claude coder only (sonnet), intra-coder original vs retest, not resolved",
       "seed": SEED, "n_boot": 2000, "drawn": drawn, "packet_dirs": benches, "missing": missing,
       "ci_method": "bootstrap over benchmarks (frozen agentaudit.stats.bootstrap_ci), percentile 95%", **st}
(PROV / "retest_all10.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("missing", "n_cells", "n_applicable_both", "n_na_mismatch", "raw_agreement",
      "raw_agreement_wilson95", "alpha_ordinal", "alpha_ci95", "weighted_kappa_quadratic", "n_benchmarks")}, indent=1))
for r in rows:
    print(r["packet_dir"], r["n_cells"], r["raw_agreement"])
