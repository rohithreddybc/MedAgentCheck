"""Stage 1: build an evidence packet for one benchmark at one pinned version.

Surfaces: S1 paper and appendix (arXiv HTML, PDF fallback), S2 README and docs,
S3 changelog and release notes, S4 code chosen by a fixed path and name rule,
S5 agent-visible prompts and tool schemas (a rule-based tag on S4 chunks).
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

import yaml

from .chunking import Chunk, Source, build_chunks, is_s5, wrap_long_lines
from .util import est_tokens, read_json, safe_name, sha256_bytes, sha256_text, utcnow, write_json

UA = {"User-Agent": "agentaudit/0.1 (research tool; evidence packet builder)"}

S4_KEYWORDS = ("tool", "tools", "env", "environment", "grader", "eval", "judge", "metric", "prompt",
               "config", "task", "agent", "sandbox", "server", "fhir", "api")
S4_EXTS = (".py", ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".jsonl")
S4_DATA_EXTS = (".json", ".jsonl", ".txt")
S4_MAX_BYTES = 200 * 1024
S4_MAX_FILES = 300
S4_DATA_LINES = 50
S4_DATA_LINE_CHARS = 400
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build", ".github", ".idea"}
RULE_VERSION = "s4-rule-v1"

CHANGELOG_RE = re.compile(r"^(changelog|changes|history|releases?|news)(\..*)?$", re.I)


# ---------------------------------------------------------------- manifest
def load_manifest(path: Path) -> dict:
    m = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if "name" not in m:
        raise ValueError("manifest missing 'name'")
    m.setdefault("extra_docs", [])
    return m


# ---------------------------------------------------------------- S1
def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer", "noscript", "svg", "button", "img"]):
        t.decompose()
    for mt in soup.find_all("math"):
        alt = mt.get("alttext") or mt.get_text(" ", strip=True)
        mt.replace_with(f" {alt} ")
    block_names = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "figcaption", "caption", "tr", "pre", "dt", "dd"]
    consumed: set[int] = set()
    lines: list[str] = []
    for el in soup.find_all(block_names):
        if id(el) in consumed:
            continue
        if el.name == "tr":
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in el.find_all(["td", "th"])]
            text = " | ".join(c for c in cells if c)
            for d in el.find_all(True):
                consumed.add(id(d))
        else:
            if el.find(block_names):
                continue  # only leaf blocks; their children carry the text
            text = " ".join(el.get_text(" ", strip=True).split())
            if el.name.startswith("h") and len(el.name) == 2 and text:
                text = "#" * int(el.name[1]) + " " + text
        if text:
            lines.append(text)
    return "\n".join(lines)


def pdf_to_text(data: bytes) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    parts = []
    for i, page in enumerate(doc, 1):
        parts.append(f"[page {i}]")
        parts.append(page.get_text("text"))
    return "\n".join(parts)


def fetch_arxiv(session, arxiv_id: str, version: str) -> tuple[str, str, str, bytes, str]:
    """Return (path, text, url, raw_bytes, fmt)."""
    ver = version if version.startswith("v") else f"v{version}"
    html_url = f"https://arxiv.org/html/{arxiv_id}{ver}"
    r = session.get(html_url, headers=UA, timeout=60)
    if r.status_code == 200 and "html" in r.headers.get("content-type", "html"):
        text = html_to_text(r.content.decode("utf-8", errors="replace"))  # not r.text: no charset header
        if len(text) > 5000:
            return f"arxiv/{arxiv_id}{ver}.html", text, html_url, r.content, "html"
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}{ver}"
    r = session.get(pdf_url, headers=UA, timeout=120)
    r.raise_for_status()
    return f"arxiv/{arxiv_id}{ver}.pdf", pdf_to_text(r.content), pdf_url, r.content, "pdf"


def fetch_extra(session, url: str) -> tuple[str, bytes]:
    r = session.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "pdf" in ct or url.lower().endswith(".pdf"):
        return pdf_to_text(r.content), r.content
    if "html" in ct:
        return html_to_text(r.content.decode("utf-8", errors="replace")), r.content
    return r.content.decode("utf-8", errors="replace"), r.content


# ---------------------------------------------------------------- repo
def parse_repo_url(url: str) -> tuple[str, str]:
    m = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$", url.strip())
    if not m:
        raise ValueError(f"unsupported repo url: {url}")
    return m.group(1), m.group(2)


def fetch_repo_files(session, owner: str, repo: str, commit: str, cache_dir: Path) -> tuple[dict[str, bytes], str]:
    """Download the zip snapshot at a commit; return ({relpath: bytes}, zip_sha256)."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    zp = cache_dir / f"{owner}__{repo}__{commit}.zip"
    if not zp.exists():
        url = f"https://codeload.github.com/{owner}/{repo}/zip/{commit}"
        with session.get(url, headers=UA, timeout=300, stream=True) as r:
            r.raise_for_status()
            tmp = zp.with_suffix(".part")
            with open(tmp, "wb") as f:
                for part in r.iter_content(1 << 20):
                    f.write(part)
            tmp.replace(zp)
    data = zp.read_bytes()
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if len(parts) < 2:
                continue
            files["/".join(parts[1:])] = z.read(info)
    return files, sha256_bytes(data)


def fetch_releases(session, owner: str, repo: str) -> tuple[str, bytes] | None:
    import os

    headers = dict(UA, Accept="application/vnd.github+json")
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    try:
        r = session.get(f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=100",
                        headers=headers, timeout=60)
        if r.status_code != 200:
            return None
        rels = r.json()
    except Exception:
        return None
    if not rels:
        return None
    parts = []
    for rel in rels:
        parts.append(f"# {rel.get('name') or rel.get('tag_name')} (tag {rel.get('tag_name')}, "
                     f"published {rel.get('published_at')})")
        parts.append(rel.get("body") or "")
    return "\n".join(parts), r.content


def fetch_commit_date(session, owner: str, repo: str, commit: str) -> str | None:
    try:
        r = session.get(f"https://api.github.com/repos/{owner}/{repo}/commits/{commit}",
                        headers=dict(UA, Accept="application/vnd.github+json"), timeout=30)
        if r.status_code == 200:
            return r.json()["commit"]["committer"]["date"]
    except Exception:
        pass
    return None


def _decode(b: bytes) -> str | None:
    if b"\x00" in b[:4096]:
        return None
    return b.decode("utf-8", errors="replace")


def _s4_candidate(rel: str) -> bool:
    p = PurePosixPath(rel)
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    if p.suffix.lower() not in S4_EXTS:
        return False
    hay = [part.lower() for part in p.parts[:-1]] + [p.stem.lower()]
    return any(k in h for k in S4_KEYWORDS for h in hay)


def classify_repo_files(files: dict[str, bytes]) -> list[Source]:
    """Pure function: repo files -> S2, S3, S4 sources (deterministic)."""
    out: list[Source] = []
    used: set[str] = set()
    for rel in sorted(files):
        p = PurePosixPath(rel)
        base = p.name.lower()
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if base.startswith("readme") and p.suffix.lower() in ("", ".md", ".rst", ".txt"):
            surface = "S2"
        elif p.parts[0].lower() in ("docs", "doc") and len(p.parts) > 1 and p.suffix.lower() in (".md", ".rst", ".txt"):
            surface = "S2"
        elif len(p.parts) == 1 and CHANGELOG_RE.match(base):
            surface = "S3"
        else:
            continue
        txt = _decode(files[rel])
        if txt is None:
            continue
        used.add(rel)
        out.append(Source(surface, rel, wrap_long_lines(txt), raw_sha256=sha256_bytes(files[rel])))

    cands = []
    for rel in files:
        if rel in used or not _s4_candidate(rel):
            continue
        ext = PurePosixPath(rel).suffix.lower()
        is_data = ext in S4_DATA_EXTS
        if len(files[rel]) > S4_MAX_BYTES and not is_data:
            continue
        group = 2 if is_data else (1 if ext == ".md" else 0)
        cands.append((group, rel.count("/"), rel))
    cands.sort()
    for _, _, rel in cands[:S4_MAX_FILES]:
        ext = PurePosixPath(rel).suffix.lower()
        txt = _decode(files[rel])
        if txt is None:
            continue
        truncated = False
        if ext in S4_DATA_EXTS:
            ls = txt.replace("\r\n", "\n").split("\n")
            if len(ls) > S4_DATA_LINES or any(len(l) > S4_DATA_LINE_CHARS for l in ls[:S4_DATA_LINES]):
                truncated = True
            txt = "\n".join(l[:S4_DATA_LINE_CHARS] for l in ls[:S4_DATA_LINES])
        out.append(Source("S4", rel, wrap_long_lines(txt), raw_sha256=sha256_bytes(files[rel]), truncated=truncated))
    return out


# ---------------------------------------------------------------- packet io
def packet_dir(run: Path, name: str) -> Path:
    return Path(run) / "packets" / name


def source_rel_path(src: Source) -> str:
    parts = [p for p in PurePosixPath(src.path).parts if p not in ("..", "/")]
    return "sources/" + src.surface + "/" + "/".join(parts) + ".txt"


def compute_packet_hash(chunks: list[Chunk]) -> str:
    return sha256_text("\n".join(f"{c.id}\t{c.sha256}" for c in sorted(chunks, key=lambda c: c.id)))


def write_packet(run: Path, name: str, sources: list[Source], meta: dict) -> dict:
    pd = packet_dir(run, name)
    pd.mkdir(parents=True, exist_ok=True)
    chunks = build_chunks(sources, is_s5)
    by_src: dict[tuple[str, str], int] = {}
    for c in chunks:
        by_src[(c.surface, c.path)] = by_src.get((c.surface, c.path), 0) + 1
    src_entries = []
    tok_by_surface: dict[str, int] = {}
    for s in sorted(sources, key=lambda s: (s.surface, s.path)):
        rel = source_rel_path(s)
        fp = pd / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(s.text, encoding="utf-8")
        t = est_tokens(s.text)
        tok_by_surface[s.surface] = tok_by_surface.get(s.surface, 0) + t
        src_entries.append({"surface": s.surface, "path": s.path, "stored": rel, "url": s.url,
                            "raw_sha256": s.raw_sha256, "text_sha256": sha256_text(s.text),
                            "tokens": t, "chunks": by_src.get((s.surface, s.path), 0),
                            "truncated": s.truncated})
    with open(pd / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    manifest = dict(meta)
    manifest.update({
        "sources": src_entries,
        "n_files": len(src_entries),
        "n_chunks": len(chunks),
        "n_s5_chunks": sum(1 for c in chunks if c.s5),
        "total_chunk_tokens": sum(c.tokens for c in chunks),
        "source_tokens_by_surface": tok_by_surface,
        "packet_sha256": compute_packet_hash(chunks),
        "params": {"chunk_tokens": 400, "overlap_tokens": 50, "chars_per_token": 4, "s4_rule": RULE_VERSION,
                   "s4_keywords": list(S4_KEYWORDS), "s4_exts": list(S4_EXTS),
                   "s4_max_bytes": S4_MAX_BYTES, "s4_max_files": S4_MAX_FILES,
                   "s4_data_lines": S4_DATA_LINES},
    })
    write_json(pd / "manifest.json", manifest)
    return manifest


def load_chunks(run: Path, name: str) -> list[Chunk]:
    p = packet_dir(run, name) / "chunks.jsonl"
    return [Chunk.from_dict(json.loads(l)) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_sources(run: Path, name: str) -> list[Source]:
    pd = packet_dir(run, name)
    man = read_json(pd / "manifest.json")
    out = []
    for e in man["sources"]:
        txt = (pd / e["stored"]).read_text(encoding="utf-8")
        out.append(Source(e["surface"], e["path"], txt, e.get("url"), e.get("raw_sha256"), e.get("truncated", False)))
    return out


def build_packet(manifest: dict, run: Path, cache_dir: Path | None = None, session=None) -> dict:
    import requests

    session = session or requests.Session()
    name = safe_name(manifest["name"])
    cache_dir = Path(cache_dir or Path(run) / "_cache")
    sources: list[Source] = []
    meta: dict = {"name": name, "built_utc": utcnow(), "manifest_input": manifest}

    ax = manifest.get("arxiv")
    if ax:
        path, text, url, raw, fmt = fetch_arxiv(session, str(ax["id"]), str(ax["version"]))
        sources.append(Source("S1", path, wrap_long_lines(text), url, sha256_bytes(raw)))
        meta["arxiv"] = {"id": str(ax["id"]), "version": str(ax["version"]), "url": url, "format": fmt}
    repo = manifest.get("repo")
    if repo:
        owner, rname = parse_repo_url(repo["url"])
        commit = repo["commit"]
        files, zsha = fetch_repo_files(session, owner, rname, commit, cache_dir)
        sub = (repo.get("subpath") or "").strip("/")
        if sub:  # a benchmark that lives in a sub-directory of a larger repository: keep only that directory
            files = {k: v for k, v in files.items() if k.startswith(sub + "/")}
        sources.extend(classify_repo_files(files))
        rel = fetch_releases(session, owner, rname)
        if rel:
            sources.append(Source("S3", "github/releases", wrap_long_lines(rel[0]),
                                  f"https://api.github.com/repos/{owner}/{rname}/releases", sha256_bytes(rel[1])))
        meta["repo"] = {"url": repo["url"], "commit": commit, "subpath": sub or None, "zip_sha256": zsha,
                        "commit_date": fetch_commit_date(session, owner, rname, commit),
                        "access_date_utc": utcnow()}
    for ed in manifest.get("extra_docs", []):
        text, raw = fetch_extra(session, ed["url"])
        surface = ed.get("surface", "S2")
        slug = safe_name(ed.get("name") or ed["url"].split("//")[-1])
        sources.append(Source(surface, f"extra/{slug}", wrap_long_lines(text), ed["url"], sha256_bytes(raw)))
    return write_packet(run, name, sources, meta)
