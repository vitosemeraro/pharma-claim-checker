"""python -m claimcheck --smpc data/kerendia_it.pdf --draft samples/draft_kerendia_it.md"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import report, smpc
from .llm import ClaudeLLM
from .pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description="Check a promotional draft against an SmPC before MLR review.")
    p.add_argument("--smpc", required=True, help="SmPC / RCP as PDF or text")
    p.add_argument("--draft", required=True, help="Draft promotional text (Markdown or plain text)")
    p.add_argument("--out", default="out", help="Output folder")
    args = p.parse_args()

    chunks = smpc.load(args.smpc)
    draft = Path(args.draft).read_text(encoding="utf-8")
    print(f"SmPC: {len(chunks)} chunks from {len({c.section for c in chunks})} sections")
    result = run(draft, chunks, ClaudeLLM())

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dossier.md").write_text(report.to_markdown(result, Path(args.draft).stem), encoding="utf-8")
    (out / "dossier.json").write_text(report.to_json(result), encoding="utf-8")
    for c in result.claims:
        print(f"{c.claim.id:>2}. {c.verdict.verdict:<14} {c.claim.text[:80]}")
    print(f"Flags: {len(result.flags)}. Dossier written to {out}/dossier.md")


if __name__ == "__main__":
    main()
