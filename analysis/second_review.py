#!/usr/bin/env python3
"""second_review.py : figures asked for after the first critic's second review. No new calls.

    python analysis/second_review.py --ai DIR        # DIR = the banked responses (default banked/)
    python analysis/second_review.py --selftest

Five pieces, each from reads already banked:

  1. SCHOOL WORK, SIDE BY SIDE (run 261 block A, condition A, both orders pooled as analyse.side_pooled). Among the
     school-work pairs a model does NOT split side by side (valid cell, not split), the kind of verdict, as in
     wrong_kinds.category: both met, both not met, reversed, unclear. Share of the unsplit cells, by group (run 261's
     groups: 12 without reasoning, Kimi K3 apart; 7 with). Macros EduSideUnsplit<Cat><Group> (Num, Den, Lo, Hi) and
     EduSideUnsplitCount<Group>, EduSideCells<Group>.
  2. SCHOOL-WORK CONSENSUS, as outcomes.consensus defines it for the six domains: for each school-work pair, how many of
     the seven reasoning configurations split it side by side; share of pairs split by at least outcomes.CONSENSUS_FROM.
     Macros EduConsensusShare (Num, Den, Lo, Hi; Wilson where the bootstrap is degenerate, as outcomes.wilson).
  3. RUN 262, THE EXAMPLE ALONE (Version A, no counter-example; exploratory): split alone with Version A, against the
     same run's bare alone, and Version A's let-through, by run 262's groups (analysis/draft_macros.GROUPS262), all
     pairs and judgement pairs. Printed "N of D", no intervals (five pairs). Into paper/numbers_exploratory.tex,
     prefix Expl, merged beside party_difference.py's macros.
  4. TABLE 6 (controls): where a control row's bootstrap interval has zero width, the Wilson score interval for its
     count (outcomes.wilson). Macros <Name>WilsonLo, <Name>WilsonHi.
  5. SECOND WORDING, VERDICTS RESTORED (run 261 block D subset, its judgement pairs): the share of files for the party
     held to less judged met (yes-rate >= analyse.HI) with the precise rule, original question and second wording, and
     with the worked example, original question. The example was not read for the plain case under the second
     wording, so that cell does not exist. Macros RestoredRuleOriginal<Group>, RestoredRuleNew<Group>,
     RestoredExampleOriginal<Group> (Num, Den, Lo, Hi), RestoredSubsetPairs.

  6. MILDER CONDUCT, THE SIDE-BY-SIDE PILOT (banked/records/RUN261_G_PILOT.json): the number of milder variants, and
     the number that split side by side on at least two of the three pilot arms (its pass criterion). Refuses unless
     every variant passed, since the text says "all". Macros MilderVariantsCount, MilderPilotPassCount. (v2, 2026-11-17)

Writes results/second_review_v2.json (write-once unless unchanged). v1 (results/second_review.json) lacked piece 6.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import macros as M                                              # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import run261 as R6                                             # noqa: E402
import wrong_kinds as WK                                        # noqa: E402

OUT = "results/second_review_v2.json"
OWN = ("results/second_review.json", OUT)
R262 = "results/run262_result.json"
GROUPS262 = {"NoReasoning": ("claude", "gpt6s_s", "qwen80b", "llama70b"), "Reasoning": ("gpt6s_r", "haiku_r")}
CATS = ("BothMet", "BothNotMet", "Reversed", "Unclear")
TWO = ("NoReasoning", "Reasoning")
CONTROL_ROWS = ("DayFlipNewControls", "DayFlipFirstRunControlsSideBySide", "DayFlipFirstRunControlsAlone",
                "DayFlipFirstRunControlsToldPrinciple", "DayFlipFirstRunControlsToldRule", "DayFlipAllControls")


def wilson_if_degenerate(e):
    if e and e.get("ci") and e["ci"][0] == e["ci"][1] and e.get("den"):
        e = dict(e, ci=O.wilson(e["num"], e["den"]), ci_method="wilson")
    return e


def school_side(r61, pairs):
    W = sorted(p for p in pairs if pairs[p]["domain"] == "education")
    cells = {}
    for a, r in r61.items():
        recs = R6.edu_records(r)
        for p in W:
            x = recs.get(p, {}).get("A")
            if x and x["valid"]:
                cells[(a, p)] = None if x["split"] else WK.category(x["F"], x["O"])
    bd = R6.by_dom(W, pairs)
    out = {}
    for g in TWO:
        arms = R6.GROUPS[g]
        mine = {k: v for k, v in cells.items() if k[0] in arms}
        uns = {k: v for k, v in mine.items() if v is not None}
        out[g] = {"cells_valid": len(mine), "unsplit": len(uns),
                  **{c: wilson_if_degenerate(R6.boot({k: (int(v == c), 1) for k, v in uns.items()}, bd, arms))
                     for c in CATS}}
        assert sum(out[g][c]["num"] for c in CATS) == len(uns)
    return out, W


def school_consensus(r61, W, pairs):
    arms = list(R6.GROUPS["Reasoning"])
    per = {}
    for p in W:
        recs = {a: R6.edu_records(r61[a]).get(p, {}).get("A") for a in arms}
        valid = [a for a, x in recs.items() if x and x["valid"]]
        per[p] = {"split": sum(recs[a]["split"] for a in valid), "valid": len(valid)}
    saved = A.DOMAINS
    A.DOMAINS = ("education",)
    try:
        b = O.FastBoot({"education": W})
    finally:
        A.DOMAINS = saved
    share = b.est({p: (int(x["split"] >= O.CONSENSUS_FROM), 1) for p, x in per.items()})
    share = wilson_if_degenerate({k: share[k] for k in ("share", "num", "den", "ci")})
    return {"models": arms, "at_least": O.CONSENSUS_FROM, "per_pair": per, "share_at_least": share}


def run262_example_alone():
    rows = json.load(open(os.path.join(ROOT, R262)))["rows"]
    out = {}
    for g, arms in GROUPS262.items():
        for kind, keep in (("All", lambda r: True), ("Judgement", lambda r: r["domain"] in O.JUDGEMENT)):
            rs = [r for r in rows if r["arm"] in arms and keep(r)]
            out[f"{g}|{kind}"] = {
                "split_example_alone": [sum(r["alone_A"]["correct"] for r in rs), len(rs)],
                "split_bare": [sum(r["alone_bare"]["correct"] for r in rs), len(rs)],
                "split_example_with_counter": [sum(r["alone_B"]["correct"] for r in rs), len(rs)],
                "let_through_example_alone": [sum(r["out_A"]["let_through"] for r in rs), len(rs)]}
    return out


def control_wilson(nums):
    out = {}
    for n in CONTROL_ROWS:
        lo, hi = nums[n + "Lo"]["value"], nums[n + "Hi"]["value"]
        if lo == hi:
            k, d = nums[n + "Num"]["value"], nums[n + "Den"]["value"]
            out[n] = {"num": k, "den": d, "bootstrap_ci": [lo, hi], "wilson": O.wilson(k, d)}
    return out


def restored(r61, r59, pairs, subset):
    jsub = [p for p in subset if pairs[p]["domain"] in O.JUDGEMENT + ("education",)]
    cells = {k: {} for k in ("rule_orig", "rule_new", "example_orig")}
    for a in r61:
        rs61 = R6.reasoning(r61[a])
        for p in jsub:
            if p.startswith("W"):
                ro = R6.yes(r61[a]["units"][f"A.D|{p}"]["cells"]["F"], rs61)
            else:
                ro = R6.yes(r59[a]["units"][f"D|{p}"]["cells"]["F"], bool(r59[a].get("reasoning")))
            rn = R6.yes(r61[a]["units"][f"D|{p}"]["cells"]["plain_rule_new"], rs61)
            eo = R6.yes(r61[a]["units"][f"C|{p}"]["cells"]["F"], rs61)
            for k, v in (("rule_orig", ro), ("rule_new", rn), ("example_orig", eo)):
                if v is not None:
                    cells[k][(a, p)] = (int(v >= A.HI), 1)
    bd = R6.by_dom(jsub, pairs)
    out = {"pairs": jsub}
    for g in TWO:
        arms = R6.GROUPS[g]
        out[g] = {k: wilson_if_degenerate(R6.boot({kk: v for kk, v in c.items() if kk[0] in arms}, bd, arms))
                  for k, c in cells.items()}
    return out


def milder_pilot(ai):
    r = json.load(open(os.path.join(ai, "records/RUN261_G_PILOT.json")))
    passed = [k.split("|")[-1] for k, v in r["variants"].items() if v["n_split"] >= 2]   # keys are "G|<pair>"
    assert len(r["arms"]) == 3 and sorted(passed) == sorted(r["pass"])
    if len(passed) != len(r["variants"]):
        sys.exit(f"REFUSING: {len(r['variants']) - len(passed)} milder variants failed the pilot; the text says all passed")
    return {"arms": r["arms"], "variants": len(r["variants"]), "passed_two_of_three": len(passed),
            "split_on_all_three": sum(1 for v in r["variants"].values() if v["n_split"] == 3)}


def run(ai):
    r61, _, r59, draft, pairs = R6.load(ai)
    side, W = school_side(r61, pairs)
    return {"definition": __doc__.split("\n\n")[2], "school_side_unsplit": side,
            "school_consensus": school_consensus(r61, W, pairs), "run262_example_alone": run262_example_alone(),
            "control_wilson": control_wilson(json.load(open(M.SIDECAR))),
            "second_wording_restored": restored(r61, r59, pairs, draft["D_subset"]), "milder_pilot": milder_pilot(ai)}


GM = {"NoReasoning": "NoReasoning", "Reasoning": "Reasoning"}


def macros(res):
    v, src = {}, f"{OUT}#"

    def share(name, e, path):
        v[name] = {"value": e["share"], "kind": "pct", "source": src + path}
        v[name + "Num"] = {"value": e["num"], "kind": "int", "source": src + path + ".num"}
        v[name + "Den"] = {"value": e["den"], "kind": "int", "source": src + path + ".den"}
        if e.get("ci"):
            v[name + "Lo"] = {"value": e["ci"][0], "kind": "pct", "source": src + path + ".ci0"}
            v[name + "Hi"] = {"value": e["ci"][1], "kind": "pct", "source": src + path + ".ci1"}
    for g in TWO:
        s = res["school_side_unsplit"][g]
        for c in CATS:
            share(f"EduSideUnsplit{c}{g}", s[c], f"school_side_unsplit.{g}.{c}")
        v[f"EduSideUnsplitCount{g}"] = {"value": s["unsplit"], "kind": "int", "source": src + f"school_side_unsplit.{g}.unsplit"}
        v[f"EduSideCells{g}"] = {"value": s["cells_valid"], "kind": "int", "source": src + f"school_side_unsplit.{g}.cells_valid"}
        r = res["second_wording_restored"][g]
        for k, nm in (("rule_orig", "RuleOriginal"), ("rule_new", "RuleNew"), ("example_orig", "ExampleOriginal")):
            share(f"Restored{nm}{g}", r[k], f"second_wording_restored.{g}.{k}")
    share("EduConsensusShare", res["school_consensus"]["share_at_least"], "school_consensus.share_at_least")
    v["RestoredSubsetPairs"] = {"value": len(res["second_wording_restored"]["pairs"]), "kind": "int",
                                "source": src + "second_wording_restored.pairs"}
    mp = res["milder_pilot"]
    v["MilderVariantsCount"] = {"value": mp["variants"], "kind": "int", "source": src + "milder_pilot.variants"}
    v["MilderPilotPassCount"] = {"value": mp["passed_two_of_three"], "kind": "int", "source": src + "milder_pilot.passed_two_of_three"}
    for n, x in res["control_wilson"].items():
        v[n + "WilsonLo"] = {"value": x["wilson"][0], "kind": "pct", "source": src + f"control_wilson.{n}.wilson.0"}
        v[n + "WilsonHi"] = {"value": x["wilson"][1], "kind": "pct", "source": src + f"control_wilson.{n}.wilson.1"}
    expl = {}
    for key, e in res["run262_example_alone"].items():
        g, kind = key.split("|")
        for k, nm in (("split_example_alone", "ExampleOnlySplit"), ("split_bare", "ExampleOnlyBareSplit"),
                      ("let_through_example_alone", "ExampleOnlyLetThrough")):
            p = f"run262_example_alone.{key}.{k}"
            expl[f"Expl{nm}{g}{kind}Num"] = {"value": e[k][0], "kind": "int", "source": src + p + ".0"}
            expl[f"Expl{nm}{g}{kind}Den"] = {"value": e[k][1], "kind": "int", "source": src + p + ".1"}
    return v, expl


def add_exploratory(new):
    """Merges into numbers_exploratory.tex beside party_difference.py's macros; asserts their lines are unchanged."""
    meta = json.load(open(PD.EXPL_SIDECAR))
    keep = {k: x for k, x in meta.items() if not k.startswith("_") and not str(x.get("source", "")).startswith(tuple(f"{o}#" for o in OWN))}
    clash = sorted(set(new) & set(keep))
    if clash:
        sys.exit(f"REFUSING: exploratory macro names already defined elsewhere: {clash[:5]}")
    before = set(open(PD.EXPL_TEX).read().splitlines())
    vals = {k: {"value": x["value"], "kind": x["kind"], "source": x["source"]} for k, x in keep.items()}
    vals.update(new)
    n = PD.write_exploratory(vals)
    after = set(open(PD.EXPL_TEX).read().splitlines())
    lost = {l for l in before - after if l.startswith("\\newcommand") and not any(f"\\{k}}}" in l for k in new)}
    assert not lost, f"exploratory lines changed: {sorted(lost)[:3]}"
    return n


def selftest():
    assert WK.category(0.9, 0.9) == "BothMet" and WK.category(0.1, 0.1) == "BothNotMet"
    assert WK.category(0.1, 0.9) == "Reversed" and WK.category(0.5, 0.1) == "Unclear" and WK.category(0.9, 0.1) is None
    e = wilson_if_degenerate({"share": 0.0, "num": 0, "den": 64, "ci": [0.0, 0.0]})
    assert e["ci"][0] == 0.0 and 0.05 < e["ci"][1] < 0.06 and e["ci_method"] == "wilson"
    assert wilson_if_degenerate({"share": 0.5, "num": 2, "den": 4, "ci": [0.2, 0.8]})["ci"] == [0.2, 0.8]
    print("selftest 3/3")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    res = run(a.ai)
    body = json.dumps(res, indent=1, default=lambda x: None)
    p = os.path.join(ROOT, OUT)
    if os.path.exists(p):
        if open(p).read() != body:
            sys.exit(f"REFUSING: {OUT} exists and differs")
    else:
        open(p, "x").write(body)
    v, expl = macros(json.loads(body))
    n = PD.add_macros(v, OUT, own=OWN)
    ne = add_exploratory(expl)
    print(json.dumps({k: res[k] for k in ("school_side_unsplit", "school_consensus", "control_wilson")}, indent=1,
                     default=lambda x: None)[:4000])
    print(json.dumps(res["run262_example_alone"]), json.dumps(res["second_wording_restored"], default=lambda x: None)[:1500])
    print(f"macros: numbers.tex now {n}, numbers_exploratory.tex now {ne}")


if __name__ == "__main__":
    main()
