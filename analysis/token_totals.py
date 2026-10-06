"""Token totals of the estimated prompt tokens recorded for the audit prompts.

Usage (from the project root): python analysis/token_totals.py
Reads audit/transport/prompts/*/meta.json (key prompt_tokens_est) for the 45 packet prompts of the main audit.
Prints the total over the 45 prompts, the median per prompt, and the total over the 44 packets that were coded
(all except HealthCraft, which failed for both coder families).
"""
import glob
import json
import statistics

rows = {}
for path in sorted(glob.glob("audit/transport/prompts/*/meta.json")):
    with open(path, encoding="utf-8") as fh:
        meta = json.load(fh)
    rows[meta["bench"]] = meta["prompt_tokens_est"]

total_all = sum(rows.values())
median_all = statistics.median(rows.values())
total_coded = sum(v for k, v in rows.items() if k != "healthcraft")
print(f"prompts: {len(rows)}")
print(f"total estimated prompt tokens, all {len(rows)} prompts: {total_all:,}")
print(f"median per prompt: {median_all:,.0f}")
print(f"total, 44 coded packets (without healthcraft): {total_coded:,}")
