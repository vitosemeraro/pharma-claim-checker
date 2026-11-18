"""Deterministic checks that do not need a model.

These catch the wording that medical-legal reviewers flag every time, and the
safety information a promotional piece has to carry. They are cheap and
predictable, so they run on every draft before any model call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Flag:
    rule: str
    excerpt: str
    note: str


# Absolute or comparative wording that almost never survives review.
RISKY_WORDING = {
    r"\b(sicur[oaie]|safe)\b": "Absolute safety wording. Safety must be described with the SmPC data, not as a quality.",
    r"\bsenza (effetti collaterali|rischi|necessit[aà] di monitoraggio)\b": "Denies a risk or a monitoring step.",
    r"\b(il migliore|la migliore|best[- ]in[- ]class|superiore a)\b": "Superlative or comparative claim. Needs a head-to-head study.",
    r"\btutti i pazienti\b|\bindipendentemente\b": "Generalisation. Check it against contraindications and posology limits.",
    r"\b(nessun|zero)\b": "Absolute negative. Rarely supported by trial data.",
}

# Safety information the piece should carry (fair balance). Keyed by SmPC topic.
REQUIRED_MENTIONS = {
    "iperkaliemia|hyperkal": "Hyperkalaemia is the most common adverse reaction (SmPC 4.4, 4.8).",
    "potassio|potassium": "Serum potassium monitoring is part of posology (SmPC 4.2).",
    "riassunto delle caratteristiche|rcp|smpc": "The piece should point to the full SmPC.",
}


def check(draft: str) -> list[Flag]:
    flags: list[Flag] = []
    low = draft.lower()
    for pattern, note in RISKY_WORDING.items():
        for m in re.finditer(pattern, low):
            start = max(0, m.start() - 50)
            excerpt = draft[start : m.end() + 50].replace("\n", " ").strip()
            flags.append(Flag("wording", f"…{excerpt}…", note))
    for pattern, note in REQUIRED_MENTIONS.items():
        if not re.search(pattern, low):
            flags.append(Flag("fair_balance", "(missing)", note))
    return flags
