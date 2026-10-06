"""Run the exported retest prompts (audit/transport/prompts_retest/<bench>/, the same prompts the Claude coder answered)
through the frozen CodexHeadlessBackend, for the retest benchmarks that the CLI retest skipped ("no packet in the run":
packet-directory slug mapping of the frozen code). Reuses run_codex_prompts.py with the retest directories; nothing under
scorer/agentaudit is edited. Output: responses_retest_codex/<bench>.json + .meta.json; import with
`python import_validation.py --mode retest --coder codex`.

Usage: python run_codex_retest.py [--bench slug ...] [--force]   (default: the two skipped benchmarks)
"""
from __future__ import annotations

import sys

import run_codex_prompts as m

DEFAULT = ["synthetic-hospital", "diaggym-diagbench"]  # frozen ids arxiv:2609.30027, arxiv:2510.24654

m.PROMPTS = m.HERE / "prompts_retest"
m.OUT = m.HERE / "responses_retest_codex"
m.LOG = m.AUDIT / "codex_retest_transport.log"

if __name__ == "__main__":
    args = sys.argv[1:]
    benches = []
    rest = []
    it = iter(args)
    for a in it:
        if a == "--bench":
            benches.append(next(it))
        else:
            rest.append(a)
    argv = ["run_codex_retest.py", "--no-reuse", "--workers", "1"] + rest
    for b in (benches or DEFAULT):
        argv += ["--variant", b]
    sys.argv = argv
    raise SystemExit(m.main())
