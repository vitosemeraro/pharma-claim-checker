from pathlib import Path

from claimcheck import rules, smpc
from claimcheck.llm import Claim, Evidence, Verdict
from claimcheck.pipeline import quote_in_chunk, run
from claimcheck.retrieve import BM25

FIXTURE = Path(__file__).parent / "fixture_smpc.txt"


def chunks():
    return smpc.load(FIXTURE)


def test_sections_are_parsed_and_annex_ii_is_ignored():
    cs = chunks()
    assert [c.section for c in cs] == ["4.1", "4.2", "4.8", "5.1"]
    assert all("indicizzato" not in c.text for c in cs)


def test_retriever_finds_the_right_section():
    top = BM25(chunks()).search("monitoraggio del potassio dopo 4 settimane", k=1)
    assert top[0].section == "4.2"


def test_quote_check_tolerates_spacing_but_not_invention():
    c = chunks()[0]
    assert quote_in_chunk("malattia renale  cronica (con albuminuria)", c)
    assert not quote_in_chunk("indicato anche nel diabete di tipo 1", c)


class FakeLLM:
    """Returns a 'supported' verdict with an invented quote, to test the guardrail."""

    def extract(self, draft):
        return [Claim(id=1, text="Indicato anche nel diabete di tipo 1.", kind="indication")]

    def verify(self, claim, context):
        return Verdict(
            verdict="supported",
            rationale="Looks fine.",
            evidence=[Evidence(chunk_id="4.1#1", quote="indicato anche nel diabete di tipo 1")],
            suggested_fix="",
        )


def test_supported_without_a_real_citation_is_downgraded():
    result = run("Indicato anche nel diabete di tipo 1.", chunks(), FakeLLM())
    c = result.claims[0]
    assert c.verdict.verdict == "needs_review"
    assert c.downgraded and not c.verified_evidence and c.dropped_evidence


def test_rules_flag_absolute_wording_and_missing_safety_info():
    flags = rules.check("Sicuro per tutti i pazienti, senza necessità di monitoraggio.")
    kinds = {f.rule for f in flags}
    assert kinds == {"wording", "fair_balance"}
    assert any("hyperkalaemia" in f.note.lower() for f in flags)
