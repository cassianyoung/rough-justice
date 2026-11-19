#!/usr/bin/env python3
"""held_to_less.py : the party held to less judged not met alone, fixed-rule and judgement cases on one basis. No new calls.

    python analysis/held_to_less.py [--ai DIR]   (default banked/)

BASIS. The paper's seven-domain basis (seven_domains.load / merge / extend_domains): the first session's matched reads
with school work added, the paper's groups (13 configurations without reasoning, 7 with; Kimi K3 has no school-work
reads). The cut-off and the bootstrap are those of the fixed-rule wrong-verdict figure (outcomes.wrongful): a file
(one party's case read alone on one model) is judged NOT MET when its yes-rate is below one half, valid files only;
95% intervals with pairs resampled within domain and models resampled (outcomes.FastBoot; Wilson where degenerate).

  X  HeldNotMetAlone<Group><Kind>             share of files for the party held to less judged not met alone.
  Y  HeldNotMetAloneSidePassed<Group><Kind>   the same, restricted to the model-pair cells where that model passed the
                                              party held to less side by side: a valid side-by-side cell (both orders
                                              pooled, analyse.side_pooled) with the party held to less at a yes-rate of
                                              one half or above (the same cut-off).
  Kind = FixedRule, Judgement. X FixedRule NoReasoning is the paper's 65% (HeldToLessWronglyFailedNoReasoning); the
  script refuses if it does not reproduce it exactly.

Writes results/held_to_less.json (write-once unless unchanged) and the macros (with Num, Den, Lo, Hi) into
paper/numbers.tex.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import seven_domains as SD                                      # noqa: E402

OUT = "results/held_to_less.json"
CUT = 0.5


def not_met(r):
    b = r.get("B") if r else None
    return (int(b["F_raw"] < CUT), 1) if b and b["F_valid"] else (0, 0)


def not_met_side_passed(r):
    a = r.get("A") if r else None
    if not a or not a["valid"] or a["F"] is None or a["F"] < CUT:
        return (0, 0)
    return not_met(r)


def run(ai):
    reads0, frames0, _, _, _ = SD.load(ai)
    reads, frames, _, _ = SD.merge(ai, reads0, frames0)
    SD.extend_domains()
    tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
    dom_of = {p["id"]: p["domain"] for p in frames["pairs"]}
    tests = [p["id"] for p in frames["pairs"]]
    kinds = {"FixedRule": O.FIXED, "Judgement": O.JUDGEMENT}
    out = {"definition": __doc__.split("\n\n")[2], "stats": {}}
    for kind, doms in kinds.items():
        b = O.FastBoot({d: [p for p in tests if dom_of[p] == d] for d in doms})
        for g, arms in O.GROUPS.items():
            arms = [a for a in arms if a in tables]
            out["stats"][f"{g}|{kind}"] = {
                "held_not_met": b.est(A.counts(tables, arms, b.pids, not_met)),
                "held_not_met_side_passed": b.est(A.counts(tables, arms, b.pids, not_met_side_passed)),
                "configurations": len(arms)}
    return out


def macros(res):
    v = {}
    for key, e in res["stats"].items():
        g, kind = key.split("|")
        for m, nm in (("held_not_met", "HeldNotMetAlone"), ("held_not_met_side_passed", "HeldNotMetAloneSidePassed")):
            x, name, src = e[m], f"{nm}{g}{kind}", f"{OUT}#stats.{key}.{m}"
            v[name] = {"value": x["share"], "kind": "pct", "source": src}
            v[name + "Num"] = {"value": x["num"], "kind": "int", "source": src + ".num"}
            v[name + "Den"] = {"value": x["den"], "kind": "int", "source": src + ".den"}
            v[name + "Lo"] = {"value": x["ci"][0], "kind": "pct", "source": src + ".ci0"}
            v[name + "Hi"] = {"value": x["ci"][1], "kind": "pct", "source": src + ".ci1"}
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    a = ap.parse_args()
    res = run(a.ai)
    paper = json.load(open(os.path.join(ROOT, "paper", "numbers.json")))
    for g in ("NoReasoning",):
        mine, theirs = res["stats"][f"{g}|FixedRule"]["held_not_met"], paper[f"HeldToLessWronglyFailed{g}"]
        if abs(mine["share"] - theirs["value"]) > 1e-12:
            sys.exit(f"REFUSING: fixed-rule X {mine['share']} does not reproduce the paper's {theirs['value']}")
    body = json.dumps(res, indent=1)
    p = os.path.join(ROOT, OUT)
    if os.path.exists(p) and open(p).read() != body:
        sys.exit(f"REFUSING: {OUT} exists and differs")
    if not os.path.exists(p):
        open(p, "x").write(body)
    n = PD.add_macros(macros(res), OUT, own=(OUT,))
    pc = lambda x: f"{100 * x['share']:.0f}% [{100 * x['ci'][0]:.0f}, {100 * x['ci'][1]:.0f}] ({x['num']}/{x['den']})"
    for key, e in res["stats"].items():
        print(f"  {key:24s} X {pc(e['held_not_met']):28s} Y {pc(e['held_not_met_side_passed'])}")
    print(f"macros into paper/numbers.tex (now {n})")


if __name__ == "__main__":
    main()
