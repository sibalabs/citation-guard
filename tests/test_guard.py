import pytest

from citation_guard import verify

P = [{"doc_name": "Employee Handbook", "section": "§6.1",
      "text": "Client meals are reimbursed up to $75 per person with an itemized receipt. Alcohol is not reimbursed."}]
P2 = [
    {"text": "Paid sick leave for exempt employees is calculated like other paid leave."},
    {"text": "On the 90th day of employment, eligible employees may begin to use paid sick time."},
]
Q = "reimbursed up to $75 per person"


def reply(answer="Up to $75 per person [1].", cites=None, answerable=True):
    return {"answerable": answerable, "answer": answer,
            "citations": [{"n": 1, "quote": Q}] if cites is None else cites}


def test_faithful_answer_is_accepted():
    out = verify(reply(), P)
    assert out and out.answer == "Up to $75 per person [1]."
    assert out.citations == [{"n": 1, "quote": Q}]


def test_missing_markers_are_added_when_the_quote_is_verified():
    assert verify(reply("Up to $75 per person."), P).answer.endswith("[1]")


@pytest.mark.parametrize("bad", [
    reply("Up to $200 [1].", [{"n": 1, "quote": "reimbursed up to $200 per person"}]),  # not in text
    reply(cites=[]),                                                                    # no citations
    reply("Up to $75 [2].", [{"n": 2, "quote": Q}]),                                    # passage 2 doesn't exist
    reply("Up to $75 [1][2]."),                                                         # [2] has no quote
    reply(answerable=False),
    reply("", ),                                                                        # empty answer
    reply("x" * 901),                                                                   # too long
    reply(cites="nope"),
    reply(cites=[{"n": 1, "quote": "$75"}]),                                            # quote too short
    reply(cites=[{"n": True, "quote": Q}]),                                             # bool is not an int
    reply(cites=["not a dict"]),
    "not a dict",
    None,
])
def test_unverifiable_replies_are_rejected(bad):
    assert verify(bad, P) is None


def test_wrongly_numbered_citation_is_repointed_to_the_real_passage():
    quote = "On the 90th day of employment, eligible employees may begin to use paid sick time"
    out = verify(reply("From the 90th day [1].", [{"n": 1, "quote": quote}]), P2)
    assert out.answer == "From the 90th day [2]." and out.citations[0]["n"] == 2


def test_quote_in_no_passage_is_rejected_even_with_repointing():
    assert verify(reply("x [1]", [{"n": 1, "quote": "On the 30th day of employment, eligible"}]), P2) is None


def test_quote_in_two_other_passages_is_ambiguous_and_rejected():
    twin = [{"text": "nothing"}, {"text": "Refunds take 14 days to arrive."}, {"text": "Refunds take 14 days to arrive."}]
    assert verify(reply("14 days [1]", [{"n": 1, "quote": "Refunds take 14 days"}]), twin) is None


def test_one_number_pointing_at_two_passages_is_rejected():
    cites = [{"n": 1, "quote": "paid sick time on the 90th day"}, {"n": 1, "quote": "calculated like other paid leave"}]
    assert verify(reply("a [1]", cites), P2) is None


def test_case_whitespace_and_curly_quotes_do_not_cause_false_rejections():
    p = [{"text": "The “standard” plan\n  includes   2 seats."}]
    out = verify(reply("2 seats [1]", [{"n": 1, "quote": 'THE "standard" plan includes 2 seats.'}]), p)
    assert out is not None


def test_a_hallucinated_extra_citation_does_not_get_through():
    cites = [{"n": 1, "quote": Q}, {"n": 1, "quote": "reimbursed up to $500 per person"}]
    assert verify(reply(cites=cites), P) is None
