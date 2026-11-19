#!/usr/bin/env python3
"""draft_macros.py : the macros draft v1 needs beyond those the analysis already writes. No new
calls.

Two outputs:

  1. CONFIRMED (run 259), into paper/numbers.tex through party_difference.add_macros (own source
     results/domain_drop.json, so every other line of numbers.tex is asserted unchanged):
       AloneDropMinDomain, AloneDropMaxDomain   the smallest and largest per-domain drop, side by side minus alone,
                                                models without reasoning, in whole points; with the domain named
                                                (AloneDropMinDomainName, AloneDropMaxDomainName).
     Computed from results/outcomes_run259_v5.json main.NoReasoning.<Domain>.{A,B}.share, unrounded.

  2. PROVISIONAL (discovery run 262, five reused pairs, six models), into paper/numbers_provisional.tex with sidecar
     paper/numbers_provisional.json. Each macro is \\Prov<Name>; the paper prints it through \\Prov{<Name>}, which
     highlights it. tools/check_typed_numbers.py refuses any \\Prov in a final build. Source: results/run262_result.json
     (a byte copy of banked/records/RUN262_RESULT.json, sha256 recorded in the sidecar). Definitions as run 262's
     outcomes: decided correctly alone = party held to less >= 0.6 and the other party <= 0.4; let through = the
     failing case rejected bare (<= 0.4) and accepted with the fix (>= 0.6), share over all cells. Version B (example
     plus counter-example) is "the worked example" in the draft.

    python analysis/draft_macros.py
    python analysis/draft_macros.py --selftest
"""
import argparse, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import macros as M                                              # noqa: E402

OUTCOMES = "results/outcomes_run259_v6.json"          # v5: the matched readout (run 263 swapped in, 2026-11-16)
DROP_JSON = "results/domain_drop_v4.json"          # v4: with intervals (outcomes v6, models and pairs resampled)
DROP_OWN = ("results/domain_drop.json", "results/domain_drop_v2.json", "results/domain_drop_v3.json", DROP_JSON)
R262 = "results/run262_result.json"
PROV_TEX = os.path.join(ROOT, "paper", "numbers_provisional.tex")
PROV_SIDECAR = os.path.join(ROOT, "paper", "numbers_provisional.json")
DOMAINS = ("Insurance", "Thresholds", "Seniority", "Dismissal", "Suitability", "Vulnerable")
GROUPS262 = {"NoReasoning": ("claude", "gpt6s_s", "qwen80b", "llama70b"), "Reasoning": ("gpt6s_r", "haiku_r")}
PROV_NOTE = ("% PROVISIONAL: discovery run 262 (five reused pairs, six models), not part of the registered results.\n"
             "% Printed highlighted through \\Prov{Name}; the final build refuses any. Written by analysis/draft_macros.py.\n")

# name: (group, field, test) ; the draft's [Prov:Name=value] placeholders, plus the reasoning half of the same-run
# rule figure, which the draft's sentence compares against both groups
PROV = {
    "ExampleAloneNoReasoning":        ("NoReasoning", "alone_B", "correct"),
    "BareAloneSameRun":               ("NoReasoning", "alone_bare", "correct"),
    "ExampleAloneReasoning":          ("Reasoning", "alone_B", "correct"),
    "BareAloneReasoningSameRun":      ("Reasoning", "alone_bare", "correct"),
    "ExampleLetThroughNoReasoning":   ("NoReasoning", "out_B", "let_through"),
    "ExampleLetThroughReasoning":     ("Reasoning", "out_B", "let_through"),
    "RuleLetThroughSameRun":          ("NoReasoning", "out_rule", "let_through"),
    "RuleLetThroughReasoningSameRun": ("Reasoning", "out_rule", "let_through"),
}
# counts printed "N of D" (the author's rulings 1 and 2): the conditional let-through (of the cells the example
# decides correctly alone, the cells whose added failing is still rejected) and Version A's let-through
COUNTS = {
    "ExampleStillRejectedNoReasoning": ("NoReasoning", "cond"),
    "ExampleStillRejectedReasoning":   ("Reasoning", "cond"),
    "ExampleALetThroughNoReasoning":   ("NoReasoning", "out_A"),
    "ExampleALetThroughReasoning":     ("Reasoning", "out_A"),
}
# the worked-example column of the main results table, split by kind of case like the other
# columns; counts, since run 262 has one fixed-rule pair (I4). Bare = the same cells with no example.
FIXED262 = ("insurance", "thresholds")
for _g in GROUPS262:
    for _ds in ("All", "FixedRule", "Judgement"):
        COUNTS[f"ExampleAlone{_g}{_ds}"] = (_g, "alone_B", _ds)
        COUNTS[f"BareAlone{_g}{_ds}SameRun"] = (_g, "alone_bare", _ds)
# the values the draft typed, asserted so a drift between the draft and the data stops the build
DRAFT_TYPED = {"ExampleAloneNoReasoning": 0.60, "BareAloneSameRun": 0.05, "ExampleAloneReasoning": 0.40,
               "BareAloneReasoningSameRun": 0.30, "ExampleLetThroughNoReasoning": 0.0,
               "ExampleLetThroughReasoning": 0.0, "RuleLetThroughSameRun": 0.55}


def drops(outcomes):
    nr = outcomes["main"]["NoReasoning"]
    return {d: nr[d]["A"]["share"] - nr[d]["B"]["share"] for d in DOMAINS}


def drop_ci(outcomes):
    nr = outcomes["main"]["NoReasoning"]
    return {d: nr[d]["A-B"]["ci"] for d in DOMAINS if "A-B" in nr[d]}


def drop_macros(outcomes):
    dd = drops(outcomes)
    ci = drop_ci(outcomes) if "A-B" in outcomes["main"]["NoReasoning"][DOMAINS[0]] else {}
    lo, hi = min(dd, key=dd.get), max(dd, key=dd.get)
    src = f"{DROP_JSON}#"
    extra = {}
    for nm, d in (("AloneDropMinDomain", lo), ("AloneDropMaxDomain", hi)):
        if d in ci:
            extra[nm + "Lo"] = {"value": ci[d][0], "kind": "ptsu", "source": src + f"ci.{d}.0"}
            extra[nm + "Hi"] = {"value": ci[d][1], "kind": "ptsu", "source": src + f"ci.{d}.1"}
    return dd, {**extra,
        "AloneDropMinDomain": {"value": dd[lo], "kind": "ptsu", "source": src + f"drop.{lo}"},
        "AloneDropMaxDomain": {"value": dd[hi], "kind": "ptsu", "source": src + f"drop.{hi}"},
        "AloneDropMinDomainName": {"value": lo.lower(), "kind": "str", "source": src + "min"},
        "AloneDropMaxDomainName": {"value": hi.lower(), "kind": "str", "source": src + "max"},
    }


def prov_values(result):
    rows = result["rows"]
    out = {}
    for name, (g, field, test) in PROV.items():
        cells = [r for r in rows if r["arm"] in GROUPS262[g]]
        num = sum(1 for r in cells if r[field][test])
        out[name] = {"value": num / len(cells), "num": num, "den": len(cells), "kind": "pct",
                     "source": f"{R262}#rows[arm in {list(GROUPS262[g])}].{field}.{test}"}
    for name, (g, what, *kind) in COUNTS.items():
        cells = [r for r in rows if r["arm"] in GROUPS262[g]]
        if kind and kind[0] == "All":
            base = cells
            num = sum(1 for r in base if r[what]["correct"])
            src = f"rows[arm in {list(GROUPS262[g])}].{what}.correct"
        elif kind:
            fixed = kind[0] == "FixedRule"
            base = [r for r in cells if (r["domain"] in FIXED262) == fixed]
            num = sum(1 for r in base if r[what]["correct"])
            src = f"rows[arm in {list(GROUPS262[g])} and domain {'in' if fixed else 'not in'} {list(FIXED262)}].{what}.correct"
        elif what == "cond":
            base = [r for r in cells if r["alone_B"]["correct"]]
            num = sum(1 for r in base if not r["out_B"]["let_through"])
            src = f"rows[arm in {list(GROUPS262[g])} and alone_B.correct].not out_B.let_through"
        else:
            base = cells
            num = sum(1 for r in base if r[what]["let_through"])
            src = f"rows[arm in {list(GROUPS262[g])}].{what}.let_through"
        out[name] = {"value": f"{num} of {len(base)}", "num": num, "den": len(base), "kind": "str",
                     "source": f"{R262}#{src}"}
    return out


def write_provisional(vals, sha, tex=PROV_TEX, sidecar=PROV_SIDECAR):
    lines, meta = [PROV_NOTE], {"_source": R262, "_sha256": sha}
    for name in sorted(vals):
        v = vals[name]
        text = M.fmt(v["value"], v["kind"])
        lines.append(f"\\newcommand{{\\Prov{name}}}{{{text}}}\n")
        meta["Prov" + name] = {"printed": text, "value": v["value"], "num": v["num"], "den": v["den"],
                               "kind": v["kind"], "source": v["source"]}
    open(tex, "w").write("".join(lines))
    open(sidecar, "w").write(json.dumps(meta, indent=1, sort_keys=True) + "\n")
    return len(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    import party_difference as PD
    outcomes = json.load(open(os.path.join(ROOT, OUTCOMES)))
    dd, dm = drop_macros(outcomes)
    rec = {"definition": "side by side (A) minus alone (B) share decided correctly, models without reasoning, by domain",
           "source": f"{OUTCOMES}#main.NoReasoning.<Domain>.A/B.share", "drop": dd, "ci": drop_ci(outcomes),
           "min": min(dd, key=dd.get), "max": max(dd, key=dd.get)}
    p = os.path.join(ROOT, DROP_JSON)
    if os.path.exists(p) and json.load(open(p)) != json.loads(json.dumps(rec)):
        sys.exit(f"REFUSING: {DROP_JSON} exists and differs from the recomputation")
    if not os.path.exists(p):
        with open(p, "x") as f:
            json.dump(rec, f, indent=1)
    # The domain-drop macros moved to the seven-domain results (analysis/seven_domains.py) when seven domains became the
    # paper's basis; this file's six-domain figures survive only as FirstSession copies. Add them only if unowned.
    import macros as M
    owned = {k for k, x in json.load(open(M.SIDECAR)).items() if not k.startswith("_") and k in dm
             and not str(x.get("source", "")).startswith(tuple(f"{s}#" for s in DROP_OWN))}
    n = PD.add_macros(dm, DROP_JSON, own=DROP_OWN) if not owned else len(json.load(open(M.SIDECAR)))
    if owned:
        print(f"domain-drop macros owned by the seven-domain results ({len(owned)}); {DROP_JSON} reproduced, not re-added")
    raw = open(os.path.join(ROOT, R262), "rb").read()
    vals = prov_values(json.loads(raw))
    for k, want in DRAFT_TYPED.items():
        assert round(100 * vals[k]["value"]) == round(100 * want), f"{k}: data {vals[k]['value']:.3f}, draft {want}"
    k = write_provisional(vals, hashlib.sha256(raw).hexdigest())
    print(f"{len(dm)} macros into paper/numbers.tex (now {n}); domain drops "
          f"{ {d: round(100 * x) for d, x in dd.items()} }")
    print(f"{k} provisional macros into paper/numbers_provisional.tex: "
          f"{ {n: f'{v['num']}/{v['den']}' for n, v in vals.items()} }")


def selftest():
    fake = {"main": {"NoReasoning": {d: {"A": {"share": 0.7}, "B": {"share": 0.7 - 0.1 * (i + 1)}}
                                     for i, d in enumerate(DOMAINS)}}}
    dd, dm = drop_macros(fake)
    assert dm["AloneDropMinDomainName"]["value"] == "insurance" and dm["AloneDropMaxDomainName"]["value"] == "vulnerable"
    assert M.fmt(dm["AloneDropMaxDomain"]["value"], "ptsu") == "60"
    rows = [{"arm": a, "domain": "dismissal", "alone_B": {"correct": a == "claude"}, "alone_bare": {"correct": False},
             "out_B": {"let_through": False}, "out_rule": {"let_through": True}, "out_A": {"let_through": False}}
            for a in GROUPS262["NoReasoning"] + GROUPS262["Reasoning"]]
    v = prov_values({"rows": rows})
    assert v["ExampleAloneNoReasoning"]["num"] == 1 and v["ExampleAloneNoReasoning"]["den"] == 4
    assert v["RuleLetThroughReasoningSameRun"]["value"] == 1.0 and v["ExampleLetThroughReasoning"]["value"] == 0.0
    assert v["ExampleStillRejectedNoReasoning"]["value"] == "1 of 1"      # only claude is decided correctly
    for r in rows:
        r["domain"] = "insurance" if r["arm"] in ("claude", "gpt6s_r") else "dismissal"
    v = prov_values({"rows": rows})
    assert v["ExampleAloneNoReasoningFixedRule"]["value"] == "1 of 1"
    assert v["ExampleAloneNoReasoningJudgement"]["value"] == "0 of 3"
    assert v["BareAloneReasoningJudgementSameRun"]["value"] == "0 of 1"
    assert v["ExampleAloneNoReasoningAll"]["value"] == "1 of 4"
    print("selftest 3/3")


if __name__ == "__main__":
    main()
