"""Run every reproduction script in order (from the repository root: python repro/run_all.py [--skip-swap]).

Each script reads released files only, asserts that its values equal the released analysis outputs, and exits non-zero on
the first mismatch. Reproduced tables are written to repro/out/ (git-ignored).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ["reproduce_audit.py", "reproduce_perturbation.py", "reproduce_retest.py", "reproduce_gold.py", "reproduce_rules.py",
           "reproduce_cap.py", "reproduce_reruns.py", "reproduce_coauthor.py"]


def main() -> int:
    extra = sys.argv[1:]
    for s in SCRIPTS:
        t0 = time.time()
        args = [sys.executable, str(HERE / s)] + (extra if s == "reproduce_gold.py" else [])
        print(f"\n=== {s} ===", flush=True)
        r = subprocess.run(args, cwd=HERE.parent)
        if r.returncode:
            print(f"FAILED: {s} (exit {r.returncode})")
            return r.returncode
        print(f"({time.time() - t0:.0f} s)")
    print("\nAll reproduction scripts passed: every reproduced value equals the released value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
