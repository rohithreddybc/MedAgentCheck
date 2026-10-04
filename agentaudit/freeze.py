"""Protocol freeze: hash every file that defines the method, and stage the public release repository.

``agentaudit freeze --root PROJECT --stage DIR`` copies the release files (never moves them) into DIR and writes
``FREEZE_MANIFEST.json`` there. The manifest holds the SHA-256 of

  * the package files that define the method: items.yaml, queries.yaml, perturbations.yaml (the decoy and
    injection texts), every prompt, the code of packet building, chunking, retrieval, scoring, quote verification,
    resolution, perturbation, gold validation and the statistics, and the seeded samples (the perturbation sample,
    the ABC and BetterBench item lists and the gold version pins, all under ``agentaudit/samples/``);
  * the study files: protocol-v1.md, eligibility.md, the frozen benchmark list, rubric-v1.md and the coding manual;
  * inputs that are used but not shipped (hash only): the instrument item texts, the published gold scores and their
    benchmark tables. Their licences (ABC: none; MedCheck: no rubric licence) do not allow redistribution.

``freeze_sha256`` is the hash of the canonical JSON of both sets of hashes, so it does not depend on the time of
staging. ``--verify DIR`` re-hashes a staged or checked-out release against its manifest.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import __version__
from .items import PKG
from .sampling import SEED
from .util import sha256_file, sha256_text, utcnow, write_json

# package files (relative to the package directory) whose content defines the method
FROZEN_CODE = ["packet_score.py", "chunking.py", "retrieve.py", "tag.py", "resolve.py", "verify.py", "prompts.py",
               "util.py", "packet.py", "perturb.py", "sampling.py", "gold.py", "items.py", "stats.py", "agree.py",
               "coding.py"]
FROZEN_DATA = ["items.yaml", "queries.yaml", "perturbations.yaml"]
FROZEN_GLOBS = ["prompts/*.txt", "samples/*"]

# (source path relative to the project root, path inside the release repository)
STUDY_FILES = [("protocol/protocol-v1.md", "protocol/protocol-v1.md"),
               ("protocol/eligibility.md", "protocol/eligibility.md"),
               ("research/eligibility/frozen_list_v1.csv", "eligibility/frozen_list_v1.csv"),
               ("rubric/rubric-v1.md", "rubric/rubric-v1.md"),
               ("rubric/coding-manual-v1.0.md", "rubric/coding-manual-v1.0.md")]

# used by `agentaudit gold` and `agentaudit sample`, hashed but never shipped
HASH_ONLY = ["research/instruments/abc_items.csv", "research/instruments/betterbench_items.csv",
             "research/gold/abc_scores.csv", "research/gold/abc_benchmarks.csv",
             "research/gold/betterbench_scores.csv", "research/gold/betterbench_benchmarks.csv"]

EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", "agentaudit.egg-info", ".git", "runs"}


def find_root(arg: str | None = None) -> Path:
    cands = [Path(arg)] if arg else [*Path.cwd().parents, Path.cwd(), *PKG.parents]
    for c in cands:
        if (c / "protocol" / "protocol-v1.md").exists() and (c / "rubric").is_dir():
            return c
    raise FileNotFoundError("project root (with protocol/protocol-v1.md and rubric/) not found; pass --root")


def package_files(pkg: Path = PKG) -> list[Path]:
    """Every shipped package file (sorted): code, yaml, prompts, samples. No caches."""
    out = []
    for p in sorted(pkg.rglob("*")):
        if p.is_file() and not (set(p.relative_to(pkg).parts) & EXCLUDE_NAMES) and p.suffix != ".pyc":
            out.append(p)
    return out


def frozen_package_files(pkg: Path = PKG) -> list[Path]:
    out = [pkg / f for f in FROZEN_CODE + FROZEN_DATA]
    for g in FROZEN_GLOBS:
        out += sorted(p for p in pkg.glob(g) if p.is_file())
    missing = [p for p in out if not p.exists()]
    if missing:
        raise FileNotFoundError(f"frozen files missing: {[str(m) for m in missing]}")
    return out


def frozen_hashes(root: Path, pkg: Path = PKG) -> tuple[dict, dict]:
    """({release-relative path: sha256}, {project-relative path: sha256 of inputs not shipped})."""
    files = {f"agentaudit/{p.relative_to(pkg).as_posix()}": sha256_file(p) for p in frozen_package_files(pkg)}
    for src, dst in STUDY_FILES:
        files[dst] = sha256_file(Path(root) / src)
    inputs = {}
    for rel in HASH_ONLY:
        p = Path(root) / rel
        if p.exists():
            inputs[rel] = sha256_file(p)
    return dict(sorted(files.items())), dict(sorted(inputs.items()))


def build_manifest(root: Path, pkg: Path = PKG) -> dict:
    files, inputs = frozen_hashes(root, pkg)
    canon = json.dumps([files, inputs], sort_keys=True, separators=(",", ":"))
    return {"manifest_version": 1, "package_version": __version__, "created_utc": utcnow(), "seed": SEED,
            "files": files, "inputs_not_shipped": inputs, "freeze_sha256": sha256_text(canon),
            "note": ("Hash of the protocol, rubric, items, prompts, perturbation texts, seeded samples and method code. "
                     "inputs_not_shipped are used by the gold-validation and sampling commands and are not "
                     "redistributed.")}


def verify_release(dest: Path) -> list[str]:
    """Problems found re-hashing ``dest`` against its FREEZE_MANIFEST.json (empty list = intact)."""
    man = json.loads((Path(dest) / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    bad = []
    for rel, h in man["files"].items():
        p = Path(dest) / rel
        if not p.exists():
            bad.append(f"missing: {rel}")
        elif sha256_file(p) != h:
            bad.append(f"changed: {rel}")
    canon = json.dumps([man["files"], man["inputs_not_shipped"]], sort_keys=True, separators=(",", ":"))
    if sha256_text(canon) != man["freeze_sha256"]:
        bad.append("freeze_sha256 does not match the listed hashes")
    return bad


def stage_release(root: Path, dest: Path, tests_dir: Path | None = None, extra: dict[str, Path] | None = None,
                  pkg: Path = PKG, log=print) -> dict:
    """Copy the release files into ``dest`` and write FREEZE_MANIFEST.json. Nothing is moved or deleted in the
    source tree. ``extra``: release path -> source file (pyproject, README, licences).
    Excluded by construction: gold scores, raw gold copies, pilot transcripts, benchmark data, runs/."""
    root, dest = Path(root), Path(dest)
    copied: list[str] = []

    def cp(src: Path, rel: str):
        t = dest / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, t)
        copied.append(rel)

    for p in package_files(pkg):
        cp(p, f"agentaudit/{p.relative_to(pkg).as_posix()}")
    for src, dst in STUDY_FILES:
        cp(root / src, dst)
    if tests_dir and Path(tests_dir).is_dir():
        for p in sorted(Path(tests_dir).glob("*.py")):
            cp(p, f"tests/{p.name}")
    for rel, src in (extra or {}).items():
        cp(Path(src), rel)
    man = build_manifest(root, pkg)
    write_json(dest / "FREEZE_MANIFEST.json", man)
    copied.append("FREEZE_MANIFEST.json")
    log(f"staged {len(copied)} files in {dest}")
    return {"copied": copied, "freeze_sha256": man["freeze_sha256"]}
