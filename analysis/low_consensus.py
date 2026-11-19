#!/usr/bin/env python3
"""low_consensus.py : the largest change, without reasoning, when the low-consensus judgement pairs are left out. No new calls.

    python analysis/low_consensus.py

Over every figure without reasoning that the review checks recompute without the low-consensus pairs
(<Measure>NoReasoning<Kind>ExclLowConsensus, analysis/review_checks.py on seven domains, results/seven/review_checks.json),
the largest absolute change from the same figure on all pairs, in points, ROUNDED UP to a whole point, so that "no figure
moves by more than N points" is true as written. Macro LowConsensusMaxChangeNoReasoning (a word), with its unrounded value
and the figure it comes from in the sidecar note.
"""
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import macros as M                                              # noqa: E402
import party_difference as PD                                   # noqa: E402

SRC = "results/seven/review_checks.json"


def build(n):
    """n: the paper's macros ({name: {"value", "source"}})."""
    rows = []
    for k, x in n.items():
        if k.endswith("ExclLowConsensus") and "NoReasoning" in k and not k.startswith("FirstSession"):
            base = k[:-len("ExclLowConsensus")]
            assert x["source"].startswith(SRC + "#"), k
            rows.append((abs(x["value"] - n[base]["value"]) * 100, k))
    top, name = max(rows)
    v = {"LowConsensusMaxChangeNoReasoning": {
        "value": math.ceil(top), "kind": "word", "source": f"analysis/low_consensus.py#max over {SRC} ExclLowConsensus",
        "note": f"largest change without reasoning over {len(rows)} figures, rounded up: {top:.2f} points ({name})"}}
    return v, top, name


def main():
    v, top, name = build(json.load(open(M.SIDECAR)))
    total = PD.add_macros(v, "analysis/low_consensus.py", own=("analysis/low_consensus.py",))
    print(f"{name}: {top:.2f} points -> {math.ceil(top)}; numbers.tex now {total}")


if __name__ == "__main__":
    main()
