"""Deterministic chunking. Unit = lines of the stored source text.

Chunks hold about 400 tokens (1,600 characters at 4 characters per token) and
overlap by about 50 tokens (200 characters, whole lines). Lines longer than
1,600 characters are hard-wrapped at word boundaries (about 1,200 characters)
when the source text is stored, so the line numbers in chunk ids always refer
to the stored text. Chunk id: ``S{n}:{path}:{start}-{end}`` with 1-based,
inclusive line numbers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .util import CHARS_PER_TOKEN, est_tokens, sha256_text

TARGET_TOKENS = 400
OVERLAP_TOKENS = 50
MAX_LINE_CHARS = TARGET_TOKENS * CHARS_PER_TOKEN  # 1600
WRAP_CHARS = 1200

ID_RE = re.compile(r"^S(\d):(.+):(\d+)-(\d+)$")


@dataclass
class Source:
    surface: str  # "S1".."S4"
    path: str
    text: str  # stored (wrapped) text
    url: str | None = None
    raw_sha256: str | None = None
    truncated: bool = False

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")


@dataclass
class Chunk:
    id: str
    surface: str
    path: str
    start: int
    end: int
    text: str
    s5: bool = False
    tokens: int = 0
    sha256: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "surface": self.surface, "path": self.path, "start": self.start,
                "end": self.end, "s5": self.s5, "tokens": self.tokens, "sha256": self.sha256,
                "text": self.text}

    @staticmethod
    def from_dict(d: dict) -> "Chunk":
        return Chunk(d["id"], d["surface"], d["path"], d["start"], d["end"], d["text"],
                     d.get("s5", False), d.get("tokens", 0), d.get("sha256", ""))


def wrap_long_lines(text: str) -> str:
    out: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.rstrip()
        if len(line) <= MAX_LINE_CHARS:
            out.append(line)
            continue
        cur = ""
        for w in line.split(" "):
            if cur and len(cur) + 1 + len(w) > WRAP_CHARS:
                out.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}" if cur else w
            while len(cur) > MAX_LINE_CHARS:  # a single unbroken token
                out.append(cur[:WRAP_CHARS])
                cur = cur[WRAP_CHARS:]
        out.append(cur)
    return "\n".join(out)


def chunk_id(surface: str, path: str, start: int, end: int) -> str:
    return f"{surface}:{path}:{start}-{end}"


def parse_chunk_id(cid: str) -> tuple[str, str, int, int] | None:
    m = ID_RE.match(cid)
    if not m:
        return None
    return f"S{m.group(1)}", m.group(2), int(m.group(3)), int(m.group(4))


def chunk_lines(lines: list[str], target_tokens: int = TARGET_TOKENS,
                overlap_tokens: int = OVERLAP_TOKENS) -> list[tuple[int, int]]:
    """Return 1-based inclusive (start, end) line ranges."""
    budget = target_tokens * CHARS_PER_TOKEN
    ov = overlap_tokens * CHARS_PER_TOKEN
    n = len(lines)
    ranges: list[tuple[int, int]] = []
    i = 0
    while i < n:
        j, acc = i, 0
        while j < n and (j == i or acc + len(lines[j]) + 1 <= budget):
            acc += len(lines[j]) + 1
            j += 1
        ranges.append((i + 1, j))
        if j >= n:
            break
        k, back = j, 0
        while k > i + 1 and back + len(lines[k - 1]) + 1 <= ov:
            back += len(lines[k - 1]) + 1
            k -= 1
        i = k
    return ranges


def chunk_source(src: Source, s5_detector=None) -> list[Chunk]:
    lines = src.lines
    if len(lines) == 1 and not lines[0].strip():
        return []
    out: list[Chunk] = []
    for s, e in chunk_lines(lines):
        text = "\n".join(lines[s - 1:e])
        if not text.strip():
            continue
        c = Chunk(chunk_id(src.surface, src.path, s, e), src.surface, src.path, s, e, text)
        c.tokens = est_tokens(text)
        c.sha256 = sha256_text(text)
        if s5_detector is not None and src.surface == "S4":
            c.s5 = bool(s5_detector(text))
        out.append(c)
    return out


def build_chunks(sources: Iterable[Source], s5_detector=None) -> list[Chunk]:
    chunks: list[Chunk] = []
    for src in sorted(sources, key=lambda s: (s.surface, s.path)):
        chunks.extend(chunk_source(src, s5_detector))
    return chunks


_S5_PATTERNS = [
    r"(?i)system[_ ]?(prompt|message|instruction)",
    r"""(?i)["']role["']\s*:\s*["']system["']""",
    r"""(?i)role\s*=\s*["']system["']""",
    r"\bYou are (a|an|the) ",
    r"""["']type["']\s*:\s*["']function["']""",
    r"""["']input_schema["']""",
    r"""["']parameters["']\s*:\s*\{""",
    r"(?i)tool[_ ]?(description|schema|spec)",
    r"""["']tools["']\s*:""",
    r"@tool\b",
]
_S5_RE = [re.compile(p) for p in _S5_PATTERNS]


def is_s5(text: str) -> bool:
    """Rule-based tag: system-prompt strings and tool-schema objects in code."""
    return any(r.search(text) for r in _S5_RE)
