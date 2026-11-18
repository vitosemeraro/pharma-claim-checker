# claim-checker

A first pass on promotional material before medical-legal-regulatory (MLR) review.

In pharma, every piece that goes to doctors (a leaflet, an email, a rep's slide) has to say
only what the Summary of Product Characteristics (SmPC, in Italy the RCP) supports, and it has
to carry the safety information. Medical, Legal and Regulatory check it line by line, and drafts
often go back and forth several times. This tool does the first read. It does not approve anything.

I built it as a working example for an application. The drug in the sample is real and its SmPC is
public. **The draft in `samples/` is fictional, written with deliberate mistakes to test the checker.
It is not Bayer material.**

## What it does

1. **Splits the SmPC into citable pieces.** Each piece keeps its section number (4.1, 4.4, 5.1...),
   so a reviewer can open the exact place.
2. **Finds the claims in the draft.** Claude lists every sentence that states an indication, a
   result, a safety point or a dosing rule, copied word for word.
3. **Looks up each claim.** A small BM25 search picks the SmPC pieces most likely to matter.
   A document this size does not need a vector database.
4. **Checks each claim against those pieces only.** Claude returns one of four verdicts
   (supported, needs review, not supported, contradicted), a short reason, a suggested rewording,
   and the exact words it relied on.
5. **Checks the citations in code.** If a quote is not really in the SmPC piece it points to, the
   citation is thrown out, and a "supported" claim without a real citation is downgraded to
   "needs review". The model cannot approve a claim with a quote it made up.
6. **Runs fixed rules that need no model**: absolute wording ("sicuro", "tutti i pazienti",
   "senza necessità di monitoraggio") and missing safety information (hyperkalaemia, potassium
   monitoring, reference to the SmPC).
7. **Writes a dossier for the reviewer** in Markdown and JSON, worst problems first, with a box
   to agree or overrule on every line.

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...            # your own key
# download the SmPC as described in data/README.md
python -m claimcheck --smpc data/kerendia_it.pdf --draft samples/draft_kerendia_it.md --out out
pytest -q                               # tests run offline, no API key needed
```

It uses `claude-opus-5-5` with structured outputs, so every answer comes back in a fixed shape.
If the model declines a request, the API retries it on a fallback model. If that also fails, the
claim goes to manual review.

## What I would measure

- Review rounds per piece, before and after.
- Days from first draft to approval.
- Share of the tool's flags the reviewers agreed with, and what they caught that it missed.
  This last one decides whether it is worth keeping.

## Limits

- It reads one document. A real setup would also use the approved claims library, the
  references dossier and the local rules on promotional material (in Italy, Legislative
  Decree 219/2006 and AIFA's procedures).
- PDF extraction is plain text. Tables in section 4.2 and 4.8 lose their layout, so dose and
  frequency tables deserve a human look.
- Fixed rules are written for Italian. The model steps work in Italian or English.
- It prepares the review. People in Medical, Legal and Regulatory make the decision.
