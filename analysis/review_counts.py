#!/usr/bin/env python3
"""review_counts.py : counts the method and appendix state after the deep review (2026-11-18). No new calls.

    python analysis/review_counts.py [--ai DIR]   (default: banked/)

  - Claude Haiku 5.5 at maximum effort: how its cells are made up by condition (the denominator of HaikuMaxCells),
    and that every excluded cell is a void one (a draw that reached the token limit without answering).
  - The controls table: the configurations it pools, the control pairs of each session, and the side-by-side cells
    that are not valid (why that row's denominator is short).
  - The readout appendix: the graded check's cells as open models by first-session judgement pairs.
Each count is asserted against the macro it explains, so the explanation cannot drift from the figure.
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import json                                                     # noqa: E402
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import seven_domains as SD                                      # noqa: E402

SRC = "analysis/review_counts.py"
NUM = lambda: json.load(open(os.path.join(ROOT, "paper", "numbers.json")))
READOUT_MODELS = ("gpt4o", "llama70b", "qwen80b", "mistral24b", "gemma27b")


def words(n):
    return ("zero one two three four five six seven eight nine ten eleven twelve").split()[n]


def build(ai, nums, outcomes7=None):
    """The macros, given the paper's other macros (nums: {name: {"value": ...}}), which each count is asserted against."""
    val = lambda k: nums[k]["value"]
    v = {}
    put = lambda k, x, kind, path: v.__setitem__(k, {"value": x, "kind": kind, "source": f"{SRC}#{path}"})

    reads0, frames0, *_ = SD.load(ai)
    reads, frames, *_ = SD.merge(ai, reads0, frames0)

    # Claude Haiku 5.5, maximum effort (the seven-domain read the paper uses)
    r = reads["haiku55_ah"]
    by = {}
    for uk, u in r["units"].items():
        c = uk.split("|")[0]
        by.setdefault(c, {"test": 0, "control": 0})["control" if u.get("control") else "test"] += len(u["cells"])
    assert sum(x["test"] + x["control"] for x in by.values()) == val("HaikuMaxCells")
    four = {by[c]["test"] + by[c]["control"] for c in "ABCD"}
    assert len(four) == 1 and by["E"]["control"] == 0
    put("HaikuMaxCellsPerCondition", four.pop(), "int", "A-D cells each")
    put("HaikuMaxCellsTestPerCondition", by["A"]["test"], "int", "A-D test cells each")
    put("HaikuMaxCellsControlPerCondition", by["A"]["control"], "int", "A-D control cells each")
    put("HaikuMaxCellsOutside", by["E"]["test"], "int", "E cells")
    gates = {c["gate"] for u in r["units"].values() for c in u["cells"].values() if c["gate"] != "PASSED"}
    assert gates == {"EXCLUDED_VOID"}, gates
    draws = {c["n_asked"] for u in r["units"].values() for c in u["cells"].values()}
    assert draws == {5}, draws
    put("HaikuMaxDrawsPerCell", "five", "str", "n_asked")

    # The controls table (first session's controls read on the main configurations without reasoning)
    arms = O.REF_GROUPS["MainNoReasoning"]
    assert len(arms) == val("NumModelsMainNoReasoning")
    first = sorted({uk.split("|")[1] for uk, u in reads0[arms[0]]["units"].items() if u.get("control")})
    assert len(first) * len(arms) == val("DayFlipFirstRunControlsAloneDen")
    follow = val("ControlPairsTotal") - len(first)
    assert follow * len(arms) == val("DayFlipNewControlsDen")
    put("ControlPairsFirstRun", words(len(first)), "str", "first-session control pairs")
    put("ControlPairsFollowUp", follow, "int", "ControlPairsTotal - first")
    put("ControlModelsList", ", ".join(f"\\model{{{O.ARM_LABEL[x]}}}" for x in arms), "str", "REF_GROUPS.MainNoReasoning")
    bad = []
    for x in arms:
        t = A.pair_cells(reads0[x], frames0)
        bad += [(x, p) for p in first if not t[p]["A"]["valid"]]
    assert len(first) * len(arms) - len(bad) == val("DayFlipFirstRunControlsSideBySideDen")
    assert {x for x, _ in bad} == {"haiku_s"}, bad          # the caption names the model
    put("ControlSideInvalidCount", words(len(bad)), "str", "side-by-side control cells not valid")

    # The readout appendix's graded check
    jp = [p["id"] for p in frames0["pairs"] if p["domain"] in O.JUDGEMENT]
    assert len(READOUT_MODELS) * len(jp) == val("GradedJudgementCells")
    put("GradedModelsWord", words(len(READOUT_MODELS)), "str", "READOUT_MODELS")
    put("FirstSessionJudgementPairs", len(jp), "int", "first-session judgement pairs")

    # Table 16 against the low-consensus robustness check (§3.4): split by at least CONSENSUS_FROM is consensus; split by
    # fewer than four is low consensus; the pairs in between belong to neither.
    cs = (outcomes7 or json.load(open(os.path.join(ROOT, "results", "seven", "outcomes.json"))))["consensus"]
    low = [p for p, x in cs["per_pair"].items() if x["split"] < 4]
    assert len(low) == len(cs["fewer_than_four"]) and len(low) == val("LowConsensusPairsCount")
    mid = [p for p, x in cs["per_pair"].items() if 4 <= x["split"] < O.CONSENSUS_FROM]
    put("JudgementConsensusNeitherCount", words(len(mid)), "str", "consensus.per_pair split 4..CONSENSUS_FROM-1")
    put("LowConsensusBelow", words(4), "str", "outcomes.consensus fewer_than_four")
    put("JudgementConsensusInvalidCells", sum(7 - x["valid"] for x in cs["per_pair"].values()), "int",
        "consensus.per_pair models_invalid")

    # The precise rule quoted in the introduction and §3.2: pair D2's rule exactly as the models read it.
    d2 = [p for p in frames0["pairs"] if p["id"] == "D2"]
    assert len(d2) == 1 and d2[0]["domain"] == "dismissal"
    rule = d2[0]["line"].strip()
    assert not re.search(r"[\\{}%$&#_^~]", rule), rule
    put("ExampleRuleQuote", rule, "str", "frames.pairs[D2].line")

    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    a = ap.parse_args()
    v = build(a.ai, NUM())
    print(json.dumps({k: x["value"] for k, x in v.items()}, indent=1))
    print(f"macros into paper/numbers.tex (now {PD.add_macros(v, SRC, own=(SRC,))})")


if __name__ == "__main__":
    main()
