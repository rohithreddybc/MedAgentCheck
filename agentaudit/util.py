"""Small shared helpers: hashing, text normalisation, token estimate, json io."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

# Token estimate used everywhere (chunk sizes, retrieval cap, throttle): 4 characters per token.
CHARS_PER_TOKEN = 4


def est_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


_QUOTE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"', "«": '"', "»": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
}
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)


def normalise(text: str) -> str:
    """NFKC, normalised quote marks and dashes, collapsed whitespace. Case is kept."""
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(_ZERO_WIDTH)
    t = "".join(_QUOTE_MAP.get(c, c) for c in t)
    return re.sub(r"\s+", " ", t).strip()


def loose_normalise(text: str) -> str:
    """Loose form for quote matching: NFKC, case folded, only letters and digits kept."""
    t = unicodedata.normalize("NFKC", text).casefold()
    return "".join(c for c in t if c.isalpha() or c.isdigit())


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:  # LF on every platform, so hashes are portable
        f.write(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False))
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_") or "x"
