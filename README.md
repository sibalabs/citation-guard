<div align="center">

# citation-guard

**Don't show an AI answer unless it can prove where it came from.**

A tiny, dependency-free Python check that sits between an LLM and your user.

![python](https://img.shields.io/badge/python-3.10%2B-blue) ![deps](https://img.shields.io/badge/dependencies-0-brightgreen) ![tests](https://img.shields.io/badge/tests-21%20passing-brightgreen) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

</div>

---

## The problem

You give a model some documents and tell it "only answer from these". It usually does. Sometimes it quietly makes up a number, a date or a policy, and it sounds exactly as confident as when it's right. A prompt is a request, not a guarantee.

**citation-guard turns that request into a rule enforced by plain code.** The model must attach a verbatim quote to every claim. The guard checks each quote against the passages you supplied. If anything doesn't match, the answer is thrown away, and your app says "I couldn't find that" instead of showing something unsupported.

```
 question + passages ──► LLM ──► reply (answer + quotes) ──► citation-guard ──┬─► verified answer ──► user
                                                                              └─► None ──► "not found in your documents"
```

## Quick start

```bash
pip install -e .          # no dependencies
python examples/demo.py
```

```python
from citation_guard import verify

passages = [{"text": "Client meals are reimbursed up to $75 per person with an itemized receipt."}]

reply = {                                   # what your model returns (parsed JSON)
    "answerable": True,
    "answer": "Up to $75 per person [1].",
    "citations": [{"n": 1, "quote": "reimbursed up to $75 per person"}],
}

out = verify(reply, passages)
if out:
    print(out.answer)         # "Up to $75 per person [1]."
    print(out.citations)      # [{"n": 1, "quote": "reimbursed up to $75 per person"}]
else:
    print("I couldn't find that in your documents.")
```

A made-up answer is rejected:

```python
reply["answer"] = "Up to $200 per person [1]."
reply["citations"][0]["quote"] = "reimbursed up to $200 per person"
verify(reply, passages)   # -> None
```

## The reply format

Ask your model (via your prompt or structured-output schema) for JSON in this shape. Passages are numbered from 1 in the prompt, so `[1]` means `passages[0]`.

| Field | Type | Meaning |
|---|---|---|
| `answerable` | `bool` | `true` if the passages contain the answer. `false` means "don't know" and is never shown. |
| `answer` | `str` | The reply text, with `[n]` markers after each claim. Max 900 characters. |
| `citations` | `list` | One entry per passage used: `{"n": int, "quote": str}`. |

Each passage only needs a `"text"` key. Extra keys (`doc_name`, `section`, ...) are ignored, so you can reuse the same list to render source cards.

## API

### `verify(reply, passages) -> Verified | None`

Returns `Verified(answer, citations)` when the reply is fully grounded, otherwise `None`. It never raises on bad model output, so malformed JSON shapes simply return `None`.

`Verified.answer` is the text to display (markers may have been corrected or added). `Verified.citations` is sorted by passage number and contains only quotes that were confirmed.

## The rules

| # | Rule | Why |
|---|---|---|
| 1 | Reply must be a dict with `answerable: true`, a non-empty `answer` of at most 900 characters, and at least one citation | Refusals and empty answers are never shown as answers |
| 2 | Every citation's `n` must be a real passage number | Catches invented sources |
| 3 | Every quote must be at least 8 characters after trimming | A tiny quote like `"$75"` proves nothing |
| 4 | The quote must appear **verbatim** in passage `n` | The core guarantee |
| 5 | Every `[n]` in the answer must have a verified quote | No claim without evidence |
| 6 | If the quote is in a different passage, repoint `[n]` only when **exactly one** other passage holds it | Fixes harmless numbering slips, refuses ambiguous ones |
| 7 | If the answer has no markers, add them for the verified quotes only | Models forget markers; we never invent support |

Matching ignores case, repeated whitespace, curly vs straight quotes, and punctuation at the ends of a quote. It does **not** fuzzy-match words, so a changed number or name fails.

## Design decisions

- **Reject by default.** A false "I don't know" costs a retry. A false answer costs trust.
- **Code, not a second model.** A verbatim substring check is deterministic, free, instant and can't be talked into agreeing.
- **Zero dependencies.** Standard library only, so it drops into any stack.
- **Never raises.** Untrusted model output goes in; `Verified` or `None` comes out.

## Limits (read these)

- It proves the **quote exists** in your passages, not that the model's wording of the claim is a correct reading of it. Keep answers short and close to the quote, and keep a human-review path for high-stakes use.
- It can't tell you the passages themselves are right or current.
- Verbatim matching means a model that paraphrases its quote gets rejected. Tell it to copy quotes exactly.

## Project layout

```
src/citation_guard/guard.py   the whole implementation (~90 lines)
tests/test_guard.py           21 tests: accept, reject, repoint, ambiguity, normalisation
examples/demo.py              grounded vs made-up answer
.github/workflows/tests.yml   CI on Python 3.10 - 3.13
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

Built by [Siba Labs](https://www.upwork.com/). Extracted from a document Q&A assistant; all example data is invented. MIT licensed.
