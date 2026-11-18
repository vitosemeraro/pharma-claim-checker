"""The two model steps: pull the claims out of a draft, then check each one.

The model never sees the whole SmPC for a claim, only the chunks the retriever
found. It has to quote the passage it relies on, and pipeline.py checks that the
quote really is in that chunk. A citation the code cannot find is not accepted.
"""
from __future__ import annotations

from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, Field

from .smpc import Chunk

MODEL = "claude-opus-5-5"


class Claim(BaseModel):
    id: int
    text: str = Field(description="The claim, copied word for word from the draft")
    kind: Literal["indication", "efficacy", "safety", "posology", "other"]


class Claims(BaseModel):
    claims: list[Claim]


class Evidence(BaseModel):
    chunk_id: str = Field(description="Id of the SmPC chunk, e.g. '5.1#3'")
    quote: str = Field(description="Exact words copied from that chunk, 5 to 40 words")


class Verdict(BaseModel):
    verdict: Literal["supported", "needs_review", "not_supported", "contradicted"]
    rationale: str = Field(description="One or two plain sentences for the reviewer")
    evidence: list[Evidence]
    suggested_fix: str = Field(description="A compliant rewording, or empty if supported")


EXTRACT_SYSTEM = """You help a pharmaceutical medical-legal-regulatory (MLR) team.
List every factual or promotional claim in the draft that a reviewer would need to check
against the Summary of Product Characteristics: indication, efficacy, safety, dosing,
monitoring, comparisons. Copy each claim word for word. Skip headings, contact details
and purely descriptive sentences that make no claim."""

VERIFY_SYSTEM = """You check one promotional claim against excerpts of the medicine's
Summary of Product Characteristics (SmPC / RCP). Use only the excerpts given.

Verdicts:
- supported: the excerpts state it, with the same population, endpoint and size of effect.
- needs_review: partly supported, missing context (population, endpoint, absolute numbers),
  or worded more strongly than the data.
- not_supported: the excerpts do not contain it, or the result cited was not
  statistically significant, or it concerns a population outside the indication.
- contradicted: the excerpts say otherwise.

Every piece of evidence must be copied exactly from the excerpt whose id you give.
If you cannot quote it, do not cite it. A human reviewer makes the final decision;
write the rationale for them, plainly."""


class LLM(Protocol):
    def extract(self, draft: str) -> list[Claim]: ...
    def verify(self, claim: Claim, chunks: list[Chunk]) -> Verdict: ...


class ClaudeLLM:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str = MODEL):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def _parse(self, system: str, user: str, schema: type[BaseModel]):
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": "high"},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("The model declined this request; send the draft to manual review.")
        return response.parsed_output

    def extract(self, draft: str) -> list[Claim]:
        return self._parse(EXTRACT_SYSTEM, f"<draft>\n{draft}\n</draft>", Claims).claims

    def verify(self, claim: Claim, chunks: list[Chunk]) -> Verdict:
        excerpts = "\n\n".join(
            f'<excerpt id="{c.id}" section="{c.section} {c.title}">\n{c.text}\n</excerpt>'
            for c in chunks
        )
        user = f"{excerpts}\n\n<claim kind=\"{claim.kind}\">{claim.text}</claim>"
        return self._parse(VERIFY_SYSTEM, user, Verdict)
