"""Checks the request we send to the Claude API, without calling it."""
import json
from pathlib import Path

import anthropic
import httpx2 as httpx

from claimcheck import smpc
from claimcheck.llm import Claim, ClaudeLLM


def test_verify_request_and_parsing():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["beta"] = request.headers.get("anthropic-beta")
        out = {"verdict": "contradicted", "rationale": "SmPC 4.2 says otherwise.",
               "evidence": [{"chunk_id": "4.2#1", "quote": "Non è raccomandato iniziare il trattamento"}],
               "suggested_fix": "Specify the eGFR threshold."}
        return httpx.Response(200, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": json.dumps(out)}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1}})

    client = anthropic.Anthropic(api_key="test", base_url="https://example.test",
                                 http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    chunks = smpc.load(Path(__file__).parent / "fixture_smpc.txt")
    verdict = ClaudeLLM(client).verify(Claim(id=1, text="Per tutti i pazienti", kind="posology"), chunks[:2])

    assert verdict.verdict == "contradicted"
    assert seen["body"]["model"] == "claude-opus-5-5"
    assert seen["body"]["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in seen["beta"]
    assert '<excerpt id="4.2#1"' in seen["body"]["messages"][0]["content"]
