"""Export the exact prompts ClaudeHeadlessBackend would receive for coder "sonnet" (groups=1, frozen cap).

Uses the frozen package's own functions (scorer/agentaudit is imported, never copied or edited):
load_chunks, select_packet, render_packet, render_packet_prompt, packet_system_prompt, GROUP_PLANS.

Writes, per benchmark, under audit/transport/prompts/<bench>/:
  system.txt          the system prompt (exactly what --system-prompt receives)
  user_partNN.txt     the user prompt split on line boundaries into parts of <= MAX_CHARS characters
  meta.json           sha256 of the full rendered prompt, part list, expected output schema description
Concatenating user_part01..NN byte for byte gives the user prompt (checked on export).

Usage: python export_prompts.py [--run ../audit-run-dir] [--bench NAME ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent
SCORER = AUDIT.parent / "scorer"
sys.path.insert(0, str(SCORER))

from agentaudit.coders import load_coders  # noqa: E402
from agentaudit.items import load_items  # noqa: E402
from agentaudit.packet import load_chunks  # noqa: E402
from agentaudit.packet_score import (CAP_TOKENS, GROUP_PLANS, SURFACES, packet_system_prompt, render_entry,  # noqa: E402
                                     render_packet, render_packet_prompt, select_packet, surface_of)
from agentaudit.prompts import prompt_hash  # noqa: E402
from agentaudit.util import est_tokens, sha256_text  # noqa: E402

CODER = "sonnet"
GROUPS = 1
MAX_CHARS = 60_000
MAX_LINES = 1_500  # the Read tool shows at most 2000 lines per call; stay well under


def render(run: Path, bench: str, cap: int | None = None) -> dict:
    """Return the system and user prompt exactly as score_packet builds them for CODER, one group."""
    spec = load_coders()[CODER]
    items = load_items()
    cap = int(cap or spec.get("max_packet_tokens") or CAP_TOKENS)  # same expression as score_packet
    sel = select_packet(load_chunks(run, bench), cap)
    packet_text = render_packet(sel["kept"])
    group = GROUP_PLANS[GROUPS][0]
    system = packet_system_prompt()
    prompt = render_packet_prompt(packet_text, group, items)
    return {"system": system, "prompt": prompt, "group": group, "cap": cap, "sel": sel}


def split_parts(text: str, max_chars: int = MAX_CHARS, max_lines: int = MAX_LINES) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    size = 0
    for line in text.splitlines(keepends=True):
        pieces = [line[i:i + max_chars] for i in range(0, len(line), max_chars)] if len(line) > max_chars else [line]
        for piece in pieces:
            if cur and (size + len(piece) > max_chars or len(cur) >= max_lines):
                parts.append("".join(cur))
                cur, size = [], 0
            cur.append(piece)
            size += len(piece)
    if cur:
        parts.append("".join(cur))
    return parts


def chunk_boundaries(prompt: str, kept) -> list[int]:
    """Offsets in ``prompt`` where a part may start: each surface header and each chunk entry except the first of its
    surface (a header stays with its first chunk). Located with the package's own render_entry, in render_packet order."""
    cuts: list[int] = []
    pos = 0
    for key, title in SURFACES:
        cs = sorted((c for c in kept if surface_of(c) == key), key=lambda c: (c.path, c.start))
        h = prompt.index(f"## {title}" + chr(10) * 2, pos)
        cuts.append(h)
        pos = h
        for i, c in enumerate(cs):
            e = prompt.index(render_entry(c), pos)
            if i:
                cuts.append(e)
            pos = e + len(render_entry(c))
    return cuts


def split_parts_by_chunk(prompt: str, kept, max_chars: int = MAX_CHARS, max_lines: int = MAX_LINES) -> list[str]:
    """Greedy packing of whole chunk units; a boundary never falls inside a chunk. A unit larger than the limits
    becomes a part of its own."""
    cuts = chunk_boundaries(prompt, kept)
    edges = [0] + cuts + [len(prompt)]
    units = [prompt[a:b] for a, b in zip(edges, edges[1:]) if b > a]
    parts: list[str] = []
    cur: list[str] = []
    size = lines = 0
    for u in units:
        ul = u.count(chr(10)) + 1
        if cur and (size + len(u) > max_chars or lines + ul > max_lines):
            parts.append("".join(cur))
            cur, size, lines = [], 0, 0
        cur.append(u)
        size += len(u)
        lines += ul
    if cur:
        parts.append("".join(cur))
    return parts


SCHEMA = (
    "Reply with ONLY a JSON array of 25 objects, one per item C1..C14 and A1..A11 in that order, no prose and "
    "no code fence. Each object: {\"item\": id, \"score\": 0|1|2|\"NA\" (per the item's anchors and NA clause), "
    "\"elements\": [] for core items C*, three booleans [i, ii, iii] for agent items A*, \"quotes\": "
    "[{\"chunk_id\": id, \"text\": verbatim excerpt}], \"contradicted\": bool, \"contradiction_quotes\": "
    "[{\"chunk_id\", \"text\"}], \"s5_reach\": true|false|null (A5, A6, A7 only), \"rationale\": string}. "
    "The authoritative field list is in the user prompt itself (the template and item blocks)."
)


def write_prompt_dir(d: Path, system: str, prompt: str, kept, extra: dict) -> dict:
    """Write system.txt, user_partNN.txt (chunk-boundary parts) and meta.json into ``d``. ``extra`` is merged into meta."""
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("user_part*.txt"):
        old.unlink()
    parts = split_parts_by_chunk(prompt, kept)
    assert "".join(parts) == prompt, "split is not lossless"
    (d / "system.txt").write_bytes(system.encode("utf-8"))
    names = []
    for i, p in enumerate(parts, 1):
        n = f"user_part{i:02d}.txt"
        (d / n).write_bytes(p.encode("utf-8"))
        names.append(n)
    meta = dict(extra)
    meta.update({
        "sha256_full_prompt": sha256_text(system + chr(10) * 2 + prompt),
        "full_prompt_definition": "sha256(utf-8 of system + '\n\n' + user prompt)",
        "system_sha256": prompt_hash(system), "prompt_sha256": prompt_hash(prompt),
        "prompt_chars": len(prompt), "prompt_tokens_est": est_tokens(system) + est_tokens(prompt),
        "n_parts": len(parts), "parts": names, "split": "chunk boundaries (a part never starts inside a chunk)",
        "max_part_chars": MAX_CHARS, "max_part_lines": MAX_LINES})
    (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8", newline=chr(10))
    return meta


def export_bench(run: Path, bench: str, out: Path) -> dict:
    r = render(run, bench)
    return write_prompt_dir(out / bench, r["system"], r["prompt"], r["sel"]["kept"], {
        "bench": bench, "coder": CODER, "groups": GROUPS, "items": r["group"],
        "cap_tokens": r["cap"], "tokens_before_cap": r["sel"]["tokens_before"], "tokens_sent": r["sel"]["tokens"],
        "over_cap": r["sel"]["over_cap"], "n_dropped_chunks": len(r["sel"]["dropped"]),
        "expected_output_schema": SCHEMA, "response_path": f"audit/transport/responses/{bench}.json"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default=str(AUDIT), help="run directory holding packets/ (default: audit/)")
    ap.add_argument("--bench", action="append", help="benchmark (repeatable); default: every packet")
    ap.add_argument("--out", default=str(HERE / "prompts"))
    a = ap.parse_args()
    run, out = Path(a.run), Path(a.out)
    benches = a.bench or sorted(p.name for p in (run / "packets").iterdir() if (p / "chunks.jsonl").exists())
    for b in benches:
        m = export_bench(run, b, out)
        print(f"{b}: {m['n_parts']} parts, ~{m['prompt_tokens_est']} tokens, over_cap={m['over_cap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
