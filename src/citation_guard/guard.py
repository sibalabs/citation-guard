"""Check a model's reply before anyone sees it.

An answer is shown only if every claim points at a passage that was really supplied and every quoted
snippet appears, word for word, in that passage. Anything else is rejected (None) so the caller can
fall back to "I couldn't find that in your documents" instead of showing an unsupported claim.

Expected model reply (JSON-style dict):
    {"answerable": true, "answer": "Up to $75 per person [1].",
     "citations": [{"n": 1, "quote": "reimbursed up to $75 per person"}]}
Passages are 1-indexed in the prompt, so [1] means passages[0]. Each passage needs a "text" key.
"""
from __future__ import annotations

import re
from typing import Any, NamedTuple

MAX_ANSWER_CHARS = 900
MIN_QUOTE_CHARS = 8  # a quote shorter than this proves nothing

_MARK = re.compile(r"\[(\d+)\]")
_EDGE = " .,;:!?\"'"
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


class Verified(NamedTuple):
    answer: str
    citations: list[dict]  # [{"n": passage_number, "quote": verified_text}], sorted by n


def _norm(text: str) -> str:
    """Case, whitespace and curly-quote differences are not worth rejecting an answer over."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().lower()


def _core(quote: str) -> str:
    return _norm(quote).strip(_EDGE)


def verify(reply: Any, passages: list[dict]) -> Verified | None:
    """Return Verified(answer, citations) if the reply is fully grounded, otherwise None."""
    if not isinstance(reply, dict) or reply.get("answerable") is not True:
        return None
    answer, cites = reply.get("answer"), reply.get("citations")
    if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER_CHARS:
        return None
    if not isinstance(cites, list) or not cites:
        return None

    texts = [_norm(p["text"]) for p in passages]
    marks = {int(m) for m in _MARK.findall(answer)}
    verified: dict[int, str] = {}  # real passage number -> quote
    remap: dict[int, int] = {}     # number the model used -> number that really holds the quote

    for c in cites:
        if not isinstance(c, dict):
            return None
        n, quote = c.get("n"), c.get("quote")
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(passages):
            return None
        if not isinstance(quote, str) or len(_core(quote)) < MIN_QUOTE_CHARS:
            return None
        q = _core(quote)
        if q in texts[n - 1]:
            real = n
        else:
            # Mislabelled? Repoint only when exactly one other passage holds the quote.
            others = [i for i, t in enumerate(texts, 1) if i != n and q in t]
            if len(others) != 1:
                return None
            real = others[0]
        if remap.setdefault(n, real) != real:
            return None  # same number used for two different passages: ambiguous
        verified[real] = quote.strip()

    if not marks <= set(remap):
        return None  # a [n] marker in the text has no verified quote behind it

    if any(k != v for k, v in remap.items()):
        answer = _MARK.sub(lambda m: f"[{remap[int(m.group(1))]}]", answer)
        marks = {remap[k] for k in marks}

    answer = answer.strip()
    if not marks:  # model forgot markers; add them, but only for quotes we verified
        answer += " " + "".join(f"[{n}]" for n in sorted(verified))
    return Verified(answer, [{"n": n, "quote": verified[n]} for n in sorted(verified)])
