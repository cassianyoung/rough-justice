#!/usr/bin/env python3
"""school_work.py : school work beside the six domains. No new calls.

    python analysis/school_work.py --ai DIR        # DIR = the AI_Ethics checkout
    python analysis/school_work.py --selftest

GROUPS: run 261's (analysis/run261.GROUPS): without reasoning the 12 configurations other than Kimi K3, whose second
session was read on a new provider and is reported apart; with reasoning the 7. The six-domain comparison figures are
computed on the SAME configurations, from the first session's reads (the paper's matched readout), so the two columns
differ only in the cases. They therefore differ slightly from the paper's six-domain figures, which pool 13
configurations without reasoning.

  1. GAP: share of pairs split side by side minus share split alone (both from the same session: school work from
     run 261 block A, the six domains from run 259), in points, with the paper's two-way interval (pairs within domain
     and models resampled together, run261.diff). Macros EduGap<Group>, SixDomGap<Group> (Lo, Hi).
  2. ALONE, GIVEN A SIDE-BY-SIDE SPLIT (party_difference.given_split, unchanged): among the (model, pair) cells a model
     splits side by side, the share whose alone cell gives the two parties the same answer (party difference below
     party_difference.NO_DIFF), and the mean party difference alone, with intervals (party_difference.Boot). Macros
     <Set>NoDiffAloneGivenSplit<Group> (Num, Den, Lo, Hi) and <Set>DiffAloneGivenSplit<Group> (Lo, Hi), plus
     <Set>SplitSideBySide<Group> (cells split side by side) and <Set>SideBySideValid<Group>, for Set = Edu (school
     work), SixDom (the six domains) and SixJudg (their judgement cases).
  3. THE FIXES BY DOMAIN, SCHOOL WORK IN ITS OWN COLUMN: told in principle, told a precise rule and let through (run 261
     block A conditions C, D, E) per group and per model on the school-work pairs, as macros <Measure><Unit>Education for
     the paper's by-domain tables; and the worked example (run 261 block C, split alone with the example) per group and
     per model, for every domain and school work, as ExampleByDomain<Unit><Domain> ("" = the six domains).
v2 (2026-11-17, seven domains the paper's basis): the fixes by domain for school work are now the main pipeline's own
macros (analysis/seven_domains.py writes <Measure><Unit>Education with every other domain), so this script no longer
writes them; it still computes them, and they matched the main pipeline's on all 189 point values. The worked example's
All column (ExampleByDomain<Unit>) now covers all seven domains.
Writes results/school_work_v2.json (write-once unless unchanged).
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import run261 as R6                                             # noqa: E402

OUT = "results/school_work_v2.json"
OWN = ("results/school_work.json", OUT)
TWO = ("NoReasoning", "Reasoning")
FIXES = (("C", "ToldPrinciple"), ("D", "ToldRule"), ("E", "LetThrough"))


def tables(r61, r59, pairs):
    """{arm: {pid: {cond: record}}}: school work from run 261 block A, the six domains from run 259."""
    W = [p for p in pairs if pairs[p]["domain"] == "education"]
    out = {}
    for a in r61:
        t = {pid: rec for pid, rec in A.pair_cells(r59[a], None).items() if pid in pairs and pid not in W}
        t.update(R6.edu_records(r61[a]))
        out[a] = t
    return out


def split_cells(tab, arms, pids, cond):
    return {(a, p): (int(r["split"]), 1) for a in arms for p in pids
            for r in [tab[a].get(p, {}).get(cond)] if r and r["valid"]}


def gap(tab, pids, pairs, arms):
    bd = R6.by_dom(pids, pairs)
    d = R6.diff(split_cells(tab, arms, pids, "A"), split_cells(tab, arms, pids, "B"), bd, arms)
    return {"side": R6.boot(split_cells(tab, arms, pids, "A"), bd, arms),
            "alone": R6.boot(split_cells(tab, arms, pids, "B"), bd, arms), "gap": d}


def given_split(tab, pids, pairs, arms):
    """party_difference.given_split's definition, on these tables."""
    per, side_valid, split, alone_invalid = {}, 0, 0, 0
    for a in arms:
        for pid in pids:
            rec = tab[a].get(pid, {})
            s_, b = rec.get("A"), rec.get("B")
            if not (s_ and s_["valid"]):
                continue
            side_valid += 1
            if not s_["split"]:
                continue
            split += 1
            if b and b["valid"]:
                per.setdefault(pid, []).append((a, b["F"] - b["O"]))
            else:
                alone_invalid += 1
    strata = [[p for p in pids if pairs[p]["domain"] == d] for d in R6.DOM7 if any(pairs[p]["domain"] == d for p in pids)]
    e = PD.Boot(strata, PD.B_RESAMPLES).stat(per)
    e.update(side_valid=side_valid, split=split, split_alone_invalid=alone_invalid)
    return e


def fixes_education(tab, W, pairs, r61):
    bd = R6.by_dom(W, pairs)
    out = {}
    for cond, nm in FIXES:
        key = "let" if cond == "E" else "split"
        cells = {(a, p): (int(r[key]), 1) for a in r61 for p in W
                 for r in [tab[a].get(p, {}).get(cond)] if r and r["valid"]}
        out[nm] = {u: R6.boot({k: v for k, v in cells.items() if k[0] in arms}, bd, list(arms))
                   for u, arms in list((g, R6.GROUPS[g]) for g in TWO) + [(a, (a,)) for a in r61]}
    return out


def example_by_domain(r61, pairs):
    cells = {}
    for a, r in r61.items():
        rs = R6.reasoning(r)
        for pid in pairs:
            c = r["units"].get(f"C|{pid}")
            if not c:
                continue
            f, o = R6.yes(c["cells"]["F"], rs), R6.yes(c["cells"]["O"], rs)
            if f is not None and o is not None:
                cells[(a, pid)] = (int(A.split(f, o)), 1)
    out = {}
    units = list((g, R6.GROUPS[g]) for g in TWO) + [(a, (a,)) for a in r61]
    sets = [("", R6.DOM7)] + [(d, (d,)) for d in R6.DOM7]
    for u, arms in units:
        out[u] = {}
        for name, doms in sets:
            pids = [p for p in pairs if pairs[p]["domain"] in doms]
            out[u][name] = R6.boot({k: v for k, v in cells.items() if k[0] in arms and k[1] in pids},
                                   R6.by_dom(pids, pairs), list(arms))
    return out


def run(ai):
    r61, _, r59, _, pairs = R6.load(ai)
    tab = tables(r61, r59, pairs)
    W = [p for p in pairs if pairs[p]["domain"] == "education"]
    six = [p for p in pairs if pairs[p]["domain"] in A.DOMAINS]
    sixj = [p for p in six if pairs[p]["domain"] in O.JUDGEMENT]
    res = {"definition": __doc__.split("\n\n")[1], "groups": {g: list(R6.GROUPS[g]) for g in TWO},
           "no_difference_below": PD.NO_DIFF, "gap": {}, "given_split": {}}
    for g in TWO:
        arms = list(R6.GROUPS[g])
        res["gap"][g] = {"Edu": gap(tab, W, pairs, arms), "SixDom": gap(tab, six, pairs, arms)}
        res["given_split"][g] = {"Edu": given_split(tab, W, pairs, arms), "SixDom": given_split(tab, six, pairs, arms),
                                 "SixJudg": given_split(tab, sixj, pairs, arms)}
    res["fixes_education"] = fixes_education(tab, W, pairs, r61)
    res["example_by_domain"] = example_by_domain(r61, pairs)
    return res


def macros(res):
    v, src = {}, f"{OUT}#"

    def put(name, value, kind, path):
        v[name] = {"value": value, "kind": kind, "source": src + path}

    def share(name, e, path, ci=True):
        put(name, e["share"], "pct", path)
        put(name + "Num", e["num"], "int", path + ".num")
        put(name + "Den", e["den"], "int", path + ".den")
        if ci and e.get("ci"):
            put(name + "Lo", e["ci"][0], "pct", path + ".ci0")
            put(name + "Hi", e["ci"][1], "pct", path + ".ci1")
    for g in TWO:
        for s in ("Edu", "SixDom"):
            d = res["gap"][g][s]["gap"]
            put(f"{s}Gap{g}", d["diff"], "pts", f"gap.{g}.{s}.gap.diff")
            put(f"{s}Gap{g}Lo", d["ci"][0], "pts", f"gap.{g}.{s}.gap.ci0")
            put(f"{s}Gap{g}Hi", d["ci"][1], "pts", f"gap.{g}.{s}.gap.ci1")
        for s in ("Edu", "SixDom", "SixJudg"):
            e, p = res["given_split"][g][s], f"given_split.{g}.{s}"
            nd = e["no_diff"]
            share(f"{s}NoDiffAloneGivenSplit{g}", {**nd, "ci": nd["ci"]}, p + ".no_diff")
            put(f"{s}DiffAloneGivenSplit{g}", e["mean"], "pts", p + ".mean")
            if e["mean_ci"]:
                put(f"{s}DiffAloneGivenSplit{g}Lo", e["mean_ci"][0], "pts", p + ".mean_ci.0")
                put(f"{s}DiffAloneGivenSplit{g}Hi", e["mean_ci"][1], "pts", p + ".mean_ci.1")
            put(f"{s}SplitSideBySide{g}", e["split"], "int", p + ".split")
            put(f"{s}SideBySideValid{g}", e["side_valid"], "int", p + ".side_valid")
    unit = lambda u: u if u in TWO else O.ARM_MACRO[u]
    for u, by in res["example_by_domain"].items():
        for d, e in by.items():
            if e["share"] is not None:
                share(f"ExampleByDomain{unit(u)}{d.capitalize()}", e, f"example_by_domain.{u}.{d or 'seven_domains'}")
    return v


def selftest():
    pairs = {"W1": {"domain": "education"}, "W2": {"domain": "education"}}
    rec = lambda s, f, o: {"valid": True, "split": s, "F": f, "O": o}
    tab = {"x": {"W1": {"A": rec(True, 0.9, 0.1), "B": rec(False, 0.1, 0.1)},
                 "W2": {"A": rec(False, 0.1, 0.1), "B": rec(False, 0.1, 0.1)}}}
    e = given_split(tab, ["W1", "W2"], pairs, ["x"])
    assert e["split"] == 1 and e["side_valid"] == 2 and e["no_diff"]["num"] == 1 and abs(e["mean"]) < 1e-9
    print("selftest 1/1")


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
    n = PD.add_macros(macros(json.loads(body)), OUT, own=OWN)
    r = json.loads(body)
    for g in TWO:
        for s in ("Edu", "SixDom"):
            d = r["gap"][g][s]
            print(f"{g:12s} {s:7s} side {R6.pc(d['side'])}  alone {R6.pc(d['alone'])}  gap {100*d['gap']['diff']:+.0f} "
                  f"[{100*d['gap']['ci'][0]:+.0f}, {100*d['gap']['ci'][1]:+.0f}]")
        for s in ("Edu", "SixDom", "SixJudg"):
            e = r["given_split"][g][s]
            nd = e["no_diff"]
            print(f"{g:12s} {s:7s} split side {e['split']}/{e['side_valid']}; same answer alone {nd['num']}/{nd['den']} "
                  f"= {100*nd['share']:.0f}% [{100*nd['ci'][0]:.0f}, {100*nd['ci'][1]:.0f}]; mean diff "
                  f"{100*e['mean']:+.0f} [{100*e['mean_ci'][0]:+.0f}, {100*e['mean_ci'][1]:+.0f}]")
    print(f"macros: numbers.tex now {n}")


if __name__ == "__main__":
    main()
