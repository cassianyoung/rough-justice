#!/usr/bin/env python3
"""file_verdicts.py : judgement cases, file by file. No new calls.

    python analysis/file_verdicts.py --ai DIR        # DIR = the AI_Ethics checkout

A FILE is one party's case read alone on one model (a cell). For the judgement-case pairs of the six first-session
domains, under each condition: the share of files for the party held to less judged NOT MET (yes-rate below one half),
and the share of files for the other party judged MET (yes-rate one half or above), the cut-off of the paper's
wrong-verdict table (outcomes.wrongful). Valid files only (analyse.valid: Claude Haiku 5.5's void cells excluded).
Intervals: 95%, pairs within domain and models resampled together (outcomes.FastBoot); Wilson where degenerate.

CONDITIONS AND SOURCES
  alone, told in principle, told a precise rule: the first session (the paper's matched readout), the paper's groups
      (13 configurations without reasoning, 7 with).
  worked example: the second session (C), its groups (12 without reasoning, Kimi K3 apart; 7 with); and its
      same-session alone baseline (Cbase) beside it.
  precise rule, original and second wording, on the second wording's random subset (its judgement pairs from the six
      first-session domains): original = the first session's told-a-precise-rule files on those pairs; second wording =
      the second session's plain case with the rule asked whether the party "met all of its obligations". The second
      wording was read for the party held to less only, so the other party's column is empty there.
Writes results/file_verdicts.json (write-once unless unchanged) and macros FileHeldNotMet<Cond><Group> and
FileOtherMet<Cond><Group> (with Num, Den, Lo, Hi) into paper/numbers.tex, own source results/file_verdicts.json.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import run261 as R6                                             # noqa: E402

OUT = "results/file_verdicts.json"
JUDG6 = O.JUDGEMENT
CONDS = (("Alone", "alone"), ("ToldPrinciple", "told in principle"), ("ExampleBaseline", "alone, second session"),
         ("Example", "worked example"), ("ToldRule", "told a precise rule"),
         ("ToldRuleSubset", "precise rule, original question (subset)"),
         ("ToldRuleSecondWording", "precise rule, second wording (subset)"))


def run(ai):
    rec = lambda p: json.load(open(os.path.join(ai, p)))
    arms = list(O.NO_R + O.WITH_R)
    r59 = {a: rec(f"records/RUN259_MATCHED_READS/RUN259_READ__{a}.json") for a in arms}
    r61 = {a: rec(f"records/RUN261_READ__{a}.json") for a in arms}
    d259 = rec("data/sfv_259/draft_v3.json")
    subset = rec("data/sfv_261/draft_v2.json")["D_subset"]
    pairs = {p["id"]: p for p in d259["pairs"]}
    jp = [p for p in pairs if pairs[p]["domain"] in JUDG6]
    jsub = [p for p in subset if p in pairs and pairs[p]["domain"] in JUDG6]
    held, other = {c: {} for c, _ in CONDS}, {c: {} for c, _ in CONDS}

    def put(c, a, pid, F, Ob, rs):
        f, o = R6.yes(F, rs), (R6.yes(Ob, rs) if Ob is not None else None)
        if f is not None:
            held[c][(a, pid)] = (int(f < 0.5), 1)
        if o is not None:
            other[c][(a, pid)] = (int(o >= 0.5), 1)
    for a in arms:
        rs59, rs61 = bool(r59[a].get("reasoning")), bool(r61[a].get("reasoning"))
        for pid in jp:
            for c, cond in (("Alone", "B"), ("ToldPrinciple", "C"), ("ToldRule", "D")):
                u = r59[a]["units"][f"{cond}|{pid}"]["cells"]
                put(c, a, pid, u["F"], u["O"], rs59)
            u = r61[a]["units"][f"C|{pid}"]["cells"]
            put("Example", a, pid, u["F"], u["O"], rs61)
            u = r61[a]["units"][f"Cbase|{pid}"]["cells"]
            put("ExampleBaseline", a, pid, u["F"], u["O"], rs61)
        for pid in jsub:
            u = r59[a]["units"][f"D|{pid}"]["cells"]
            put("ToldRuleSubset", a, pid, u["F"], u["O"], rs59)
            put("ToldRuleSecondWording", a, pid, r61[a]["units"][f"D|{pid}"]["cells"]["plain_rule_new"], None, rs61)
    first = {"NoReasoning": O.NO_R, "Reasoning": O.WITH_R}
    second = {"NoReasoning": R6.GROUPS["NoReasoning"], "Reasoning": R6.GROUPS["Reasoning"]}
    out = {"definition": __doc__.split("\n\n")[1], "subset_judgement_pairs": jsub, "stats": {}}
    for c, _ in CONDS:
        groups = second if c in ("Example", "ExampleBaseline", "ToldRuleSecondWording") else first
        pids = jsub if c in ("ToldRuleSubset", "ToldRuleSecondWording") else jp
        bd = R6.by_dom(pids, pairs)
        for g, gs in groups.items():
            sel = lambda d: {k: v for k, v in d.items() if k[0] in gs and k[1] in pids}
            out["stats"][f"{c}|{g}"] = {"held_not_met": R6.boot(sel(held[c]), bd, list(gs)),
                                        "other_met": R6.boot(sel(other[c]), bd, list(gs)) if sel(other[c]) else None,
                                        "configurations": len(gs)}
    return out


def macros(res):
    v = {}
    for key, e in res["stats"].items():
        c, g = key.split("|")
        for m, nm in (("held_not_met", "FileHeldNotMet"), ("other_met", "FileOtherMet")):
            x = e[m]
            if not x or x.get("share") is None:
                continue
            name, src = f"{nm}{c}{g}", f"{OUT}#stats.{key}.{m}"
            v[name] = {"value": x["share"], "kind": "pct", "source": src}
            v[name + "Num"] = {"value": x["num"], "kind": "int", "source": src + ".num"}
            v[name + "Den"] = {"value": x["den"], "kind": "int", "source": src + ".den"}
            if x.get("ci"):
                v[name + "Lo"] = {"value": x["ci"][0], "kind": "pct", "source": src + ".ci0"}
                v[name + "Hi"] = {"value": x["ci"][1], "kind": "pct", "source": src + ".ci1"}
    v["FileVerdictsSubsetPairs"] = {"value": len(res["subset_judgement_pairs"]), "kind": "int",
                                    "source": f"{OUT}#subset_judgement_pairs"}
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    a = ap.parse_args()
    res = run(a.ai)
    body = json.dumps(res, indent=1)
    p = os.path.join(ROOT, OUT)
    if os.path.exists(p):
        if open(p).read() != body:
            sys.exit(f"REFUSING: {OUT} exists and differs")
    else:
        open(p, "x").write(body)
    n = PD.add_macros(macros(res), OUT, own=(OUT,))
    for key, e in res["stats"].items():
        print(f"  {key:34s} held to less not met {R6.pc(e['held_not_met']):28s} other met {R6.pc(e['other_met'])}")
    print(f"macros into paper/numbers.tex (now {n})")


if __name__ == "__main__":
    main()
