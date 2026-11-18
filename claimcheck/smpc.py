"""Load an SmPC (Italian RCP or English SmPC) and split it into citable chunks.

Each chunk keeps the section number it came from (for example "4.4" or "5.1"),
so every citation in the final report points to a place a reviewer can open.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# "4.1 Indicazioni terapeutiche", "5.1 Pharmacodynamic properties", ...
SECTION_RE = re.compile(r"^\s*(\d{1,2}\.\d{1,2})\.?\s+(\S.*)$")
# The SmPC is Annex I. Labelling and package leaflet come after and are not used.
ANNEX_END_RE = re.compile(r"^\s*(ALLEGATO II|ANNEX II)\b")


@dataclass
class Chunk:
    id: str        # e.g. "5.1#3"
    section: str   # e.g. "5.1"
    title: str     # e.g. "Proprietà farmacodinamiche"
    text: str


def read_text(path: str | Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def _clean(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # words split across lines
    return re.sub(r"[ \t]+", " ", text)


def split_sections(text: str) -> list[tuple[str, str, str]]:
    """Return (section, title, body) for each numbered SmPC section."""
    sections: list[tuple[str, str, list[str]]] = []
    for line in _clean(text).splitlines():
        if ANNEX_END_RE.match(line) and sections:
            break
        m = SECTION_RE.match(line)
        if m and len(m.group(2)) < 90:
            sections.append((m.group(1), m.group(2).strip(), []))
        elif sections:
            sections[-1][2].append(line)
    return [(s, t, "\n".join(b).strip()) for s, t, b in sections if "\n".join(b).strip()]


def chunk(text: str, max_chars: int = 900) -> list[Chunk]:
    """Split each section into paragraph-sized chunks of at most ~max_chars."""
    chunks: list[Chunk] = []
    for section, title, body in split_sections(text):
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=\.)\n", body) if p.strip()]
        buf = ""
        n = 0
        for p in paragraphs:
            if buf and len(buf) + len(p) > max_chars:
                n += 1
                chunks.append(Chunk(f"{section}#{n}", section, title, buf.strip()))
                buf = ""
            buf += " " + p.replace("\n", " ")
        if buf.strip():
            n += 1
            chunks.append(Chunk(f"{section}#{n}", section, title, buf.strip()))
    return chunks


def load(path: str | Path) -> list[Chunk]:
    chunks = chunk(read_text(path))
    if not chunks:
        raise ValueError(f"No numbered SmPC sections found in {path}")
    return chunks
