"""Write the dossier the human reviewer works from (Markdown + JSON)."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict

from .pipeline import Result

LABEL = {
    "supported": "Supported",
    "needs_review": "Needs review",
    "not_supported": "Not supported",
    "contradicted": "Contradicted",
}
ORDER = ["contradicted", "not_supported", "needs_review", "supported"]


def to_markdown(result: Result, title: str) -> str:
    counts = Counter(c.verdict.verdict for c in result.claims)
    out = [f"# Pre-review dossier: {title}", ""]
    out.append("Prepared automatically before medical-legal-regulatory review. "
               "Nothing here is a decision: every line is for the reviewer to confirm or overrule.")
    out += ["", "## Summary", ""]
    out += [f"- {LABEL[v]}: {counts.get(v, 0)}" for v in ORDER]
    out.append(f"- Wording and fair-balance flags: {len(result.flags)}")
    out += ["", "## Claims", ""]
    claims = sorted(result.claims, key=lambda c: (ORDER.index(c.verdict.verdict), c.claim.id))
    for c in claims:
        v = c.verdict
        out.append(f"### {c.claim.id}. {LABEL[v.verdict]} ({c.claim.kind})")
        out.append(f"> {c.claim.text}")
        out.append("")
        out.append(v.rationale)
        for ev in c.verified_evidence:
            out.append(f'- SmPC {ev.chunk_id}: "{ev.quote}"')
        for ev in c.dropped_evidence:
            out.append(f"- Citation rejected (not found in SmPC {ev.chunk_id})")
        if v.suggested_fix:
            out.append(f"\nSuggested wording: {v.suggested_fix}")
        out.append("\nReviewer: [ ] agree  [ ] overrule  Note: ________")
        out.append("")
    if result.flags:
        out += ["## Wording and fair balance", ""]
        out += [f"- **{f.rule}** {f.excerpt} {f.note}" for f in result.flags]
    return "\n".join(out) + "\n"


def to_json(result: Result) -> str:
    return json.dumps(
        {"claims": [asdict(c) | {"claim": c.claim.model_dump(), "verdict": c.verdict.model_dump(),
                                 "verified_evidence": [e.model_dump() for e in c.verified_evidence],
                                 "dropped_evidence": [e.model_dump() for e in c.dropped_evidence]}
                    for c in result.claims],
         "flags": [asdict(f) for f in result.flags]},
        ensure_ascii=False, indent=2,
    )
