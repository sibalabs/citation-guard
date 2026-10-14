"""Run: python examples/demo.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from citation_guard import verify

passages = [{"text": "Client meals are reimbursed up to $75 per person with an itemized receipt."}]

good = {"answerable": True, "answer": "Up to $75 per person [1].",
        "citations": [{"n": 1, "quote": "reimbursed up to $75 per person"}]}
made_up = {"answerable": True, "answer": "Up to $200 per person [1].",
           "citations": [{"n": 1, "quote": "reimbursed up to $200 per person"}]}

for name, r in [("grounded", good), ("made up", made_up)]:
    out = verify(r, passages)
    print(f"{name:9}->", out.answer if out else "REJECTED (fall back to 'not found in your documents')")
