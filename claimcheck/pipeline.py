"""Draft in, reviewer dossier out."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from . import rules
from .llm import LLM, Claim, Evidence, Verdict
from .retrieve import BM25
from .smpc import Chunk


@dataclass
class CheckedClaim:
    claim: Claim
    verdict: Verdict
    verified_evidence: list[Evidence] = field(default_factory=list)
    dropped_evidence: list[Evidence] = field(default_factory=list)
    downgraded: bool = False


@dataclass
class Result:
    claims: list[CheckedClaim]
    flags: list[rules.Flag]


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("–", "-").replace("≥", ">=").replace("≤", "<=")
    return re.sub(r"\s+", " ", text).strip()


def quote_in_chunk(quote: str, chunk: Chunk | None) -> bool:
    return bool(chunk) and _norm(quote) in _norm(chunk.text)


def run(draft: str, chunks: list[Chunk], llm: LLM, k: int = 6) -> Result:
    index = BM25(chunks)
    by_id = {c.id: c for c in chunks}
    checked: list[CheckedClaim] = []
    for claim in llm.extract(draft):
        context = index.search(claim.text, k=k)
        verdict = llm.verify(claim, context)
        cc = CheckedClaim(claim, verdict)
        for ev in verdict.evidence:
            (cc.verified_evidence if quote_in_chunk(ev.quote, by_id.get(ev.chunk_id)) else cc.dropped_evidence).append(ev)
        # A "supported" verdict with no citation we can find in the SmPC is not supported.
        if verdict.verdict == "supported" and not cc.verified_evidence:
            verdict.verdict = "needs_review"
            verdict.rationale += " (Downgraded: the cited passage could not be found in the SmPC.)"
            cc.downgraded = True
        checked.append(cc)
    return Result(checked, rules.check(draft))
