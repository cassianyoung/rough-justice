#!/usr/bin/env python3
"""haiku_void_check.py : Claude Haiku 5.5 at maximum effort, the cells it left unanswered. No
new calls.

On haiku55_ah some draws reasoned until the 64,000-token limit and returned no answer (stop_reason max_tokens). With five
draws, any such draw excludes the cell (the registered rule for reasoning models). This script

  1. counts the excluded cells by condition and kind of case, and the pair records they remove;
  2. recomputes, with every pair record so removed counted as WRONG (not decided correctly in A to D; let through in
     E, the outcome the measure counts against the model), that model's figures and the with-reasoning group's,
     beside the figures with the cells excluded; and
  3. writes macros for the method sentence and the appendix (paper/numbers.tex, own source results/haiku55_void_check.json).

Reads the matched reads (the paper's readout). Writes results/haiku55_void_check.json and results/HAIKU55_VOID_CHECK.md
(write-once unless unchanged), and stops (exit 3) if any with-reasoning group figure moves by more than 2 points.

    python analysis/haiku_void_check.py --reads DIR --frames FILE
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402

ARM = "haiku55_ah"
OUT_JSON = "results/haiku55_void_check_v2.json"   # v2: models resampled as well as pairs
OUT_MD = "results/HAIKU55_VOID_CHECK_v2.md"
KEYS = ("A", "B", "C", "D", "E")
CONDS = {"A": "side by side", "B": "alone", "C": "alone, told in principle", "D": "alone, told a precise rule",
         "E": "outside the rule"}
STOP_POINTS = 2.0


def excluded(read):
    """The excluded cells, as (condition, pair, cell key, kind of case, void draws)."""
    out = []
    for uk, u in read["units"].items():
        cond, pid = uk.split("|")
        for k, c in u["cells"].items():
            if c["gate"] != "PASSED":
                kind = "control" if u.get("control") else ("FixedRule" if u["domain"] in O.FIXED else "Judgement")
                out.append({"cond": cond, "pair": pid, "cell": k, "kind": kind, "gate": c["gate"],
                            "void": c["n_void"], "draws": c["n_asked"]})
    return out


def worst_case(rec):
    """A pair record with its invalid conditions counted as wrong."""
    r = {k: dict(v) for k, v in rec.items()}
    for k, v in r.items():
        if v.get("valid"):
            continue
        if k == "E":
            v.update(valid=True, bare=0.0, line=1.0, let=True, line_valid=True, line_yes=1.0)
        else:
            v.update(valid=True, F=0.0, O=1.0, split=False)
            if k in ("B", "C", "D"):
                v.update(F_valid=True, O_valid=True, F_raw=0.0, O_raw=1.0)
    return r


def compute(reads, frames, worst):
    orig = A.pair_cells

    def pc(read, fr):
        t = orig(read, fr)
        return {pid: worst_case(rec) for pid, rec in t.items()} if (worst and read.get("arm") == ARM) else t
    A.pair_cells = pc
    try:
        main, _ = O.compute(reads, frames)
    finally:
        A.pair_cells = orig
    pick = lambda e: {"share": e["share"], "ci": e["ci"], "num": e["num"], "den": e["den"]}
    return {g: {ds: {k: pick(main[g][ds][k]) for k in KEYS} for ds in ("", "FixedRule", "Judgement")}
            for g in ("Reasoning", ARM)}


def pair_losses(read, frames):
    t = A.pair_cells(read, frames)
    tests = {p["id"]: p["domain"] for p in frames["pairs"]}
    out = {}
    for pid, rec in t.items():
        if pid not in tests:
            continue
        kind = "FixedRule" if tests[pid] in O.FIXED else "Judgement"
        for k in KEYS:
            if k in rec and not rec[k]["valid"]:
                out.setdefault(k, {"FixedRule": 0, "Judgement": 0})[kind] += 1
    return out


def macros(ex, read, losses, both):
    src = f"{OUT_JSON}#"
    cells = sum(len(u["cells"]) for u in read["units"].values())
    v = {"HaikuMaxVoidCells": {"value": len(ex), "kind": "int", "source": src + "excluded"},
         "HaikuMaxCells": {"value": cells, "kind": "int", "source": src + "cells"},
         "HaikuMaxVoidShare": {"value": len(ex) / cells, "kind": "pct", "source": src + "excluded/cells"},
         "HaikuMaxVoidDraws": {"value": sum(e["void"] for e in ex), "kind": "int", "source": src + "excluded[].void"}}
    for c in KEYS:
        for kind in ("FixedRule", "Judgement", "control"):
            n = sum(1 for e in ex if e["cond"] == c and e["kind"] == kind)
            v[f"HaikuMaxVoidCells{O_NAME[c]}{kind.capitalize() if kind == 'control' else kind}"] = \
                {"value": n, "kind": "int", "source": src + f"excluded[cond={c},kind={kind}]"}
    for way, res in both.items():
        for g, gm in (("Reasoning", "Reasoning"), (ARM, "HaikuFiveFiveMaxEffort")):
            for ds in ("", "FixedRule", "Judgement"):
                for k in KEYS:
                    e = res[g][ds][k]
                    if e["share"] is None:
                        continue
                    name = f"VoidCheck{way}{O_NAME[k]}{gm}{ds}"
                    v[name] = {"value": e["share"], "kind": "pct", "source": src + f"{way}.{g}.{ds or 'all'}.{k}"}
                    if e["ci"]:
                        v[name + "Lo"] = {"value": e["ci"][0], "kind": "pct", "source": src + f"{way}.{g}.{ds or 'all'}.{k}.ci0"}
                        v[name + "Hi"] = {"value": e["ci"][1], "kind": "pct", "source": src + f"{way}.{g}.{ds or 'all'}.{k}.ci1"}
    return v


O_NAME = {"A": "SideBySide", "B": "Alone", "C": "ToldPrinciple", "D": "ToldRule", "E": "LetThrough"}


def pct(e):
    if e["share"] is None:
        return "n/a"
    lo, hi = e["ci"] or (e["share"], e["share"])
    return f"{100 * e['share']:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}] ({e['num']}/{e['den']})"


def markdown(ex, losses, both, moved):
    L = ["# Claude Haiku 5.5 at maximum effort: cells without an answer", "",
         f"{len(ex)} cells excluded, every one because a draw reached the 64,000-token limit with no answer "
         f"({sum(e['void'] for e in ex)} draws). Generated by `analysis/haiku_void_check.py`; no new calls.", "",
         "## Excluded cells by condition and kind of case", "", "| Condition | Fixed-rule | Judgement | Control | Total |",
         "|---|---|---|---|---|"]
    for c in KEYS:
        n = lambda kind: sum(1 for e in ex if e["cond"] == c and e["kind"] == kind)
        L.append(f"| {CONDS[c]} | {n('FixedRule')} | {n('Judgement')} | {n('control')} | "
                 f"{sum(1 for e in ex if e['cond'] == c)} |")
    L += ["", "## Test-pair records removed (a pair needs both its cells)", "", "| Condition | Fixed-rule | Judgement |",
          "|---|---|---|"]
    for c in KEYS:
        x = losses.get(c, {"FixedRule": 0, "Judgement": 0})
        L.append(f"| {CONDS[c]} | {x['FixedRule']} | {x['Judgement']} |")
    for g, lab in (("Reasoning", "With reasoning (7 models)"), (ARM, "Claude Haiku 5.5 (max effort)")):
        L += ["", f"## {lab}: excluded against counted as wrong", "",
              "| Cases | Condition | Excluded | Counted as wrong | Change (points) |", "|---|---|---|---|---|"]
        for ds, dl in (("", "all"), ("FixedRule", "fixed-rule"), ("Judgement", "judgement")):
            for k in KEYS:
                a, b = both["Excluded"][g][ds][k], both["Wrong"][g][ds][k]
                ch = "" if a["share"] is None or b["share"] is None else f"{100 * (b['share'] - a['share']):+.1f}"
                L.append(f"| {dl} | {CONDS[k]} | {pct(a)} | {pct(b)} | {ch} |")
    L += ["", f"Largest change in a with-reasoning group figure: {moved:.1f} points "
          f"({'within' if moved <= STOP_POINTS else 'ABOVE'} the {STOP_POINTS:.0f}-point stop)."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads", required=True); ap.add_argument("--frames", required=True)
    a = ap.parse_args()
    frames = json.load(open(a.frames))
    reads, _ = A.load_reads(a.reads)
    ex = excluded(reads[ARM])
    assert all(e["gate"] == "EXCLUDED_VOID" for e in ex), "an exclusion other than a token-limit void"
    losses = pair_losses(reads[ARM], frames)
    both = {"Excluded": compute(reads, frames, False), "Wrong": compute(reads, frames, True)}
    moved = max(abs(both["Wrong"]["Reasoning"][ds][k]["share"] - both["Excluded"]["Reasoning"][ds][k]["share"]) * 100
                for ds in ("", "FixedRule", "Judgement") for k in KEYS
                if both["Excluded"]["Reasoning"][ds][k]["share"] is not None)
    res = {"definition": __doc__.split("\n\n")[1], "excluded": ex, "pair_records_removed": losses, "figures": both,
           "max_group_change_points": moved, "cells": sum(len(u["cells"]) for u in reads[ARM]["units"].values())}
    md = markdown(ex, losses, both, moved)
    for p, body in ((OUT_JSON, json.dumps(res, indent=1)), (OUT_MD, md)):
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            if open(fp).read() != body:
                sys.exit(f"REFUSING: {p} exists and differs")
        else:
            open(fp, "x").write(body)
    n = PD.add_macros(macros(ex, reads[ARM], losses, both), OUT_JSON, own=(OUT_JSON, "results/haiku55_void_check.json"))
    print(md)
    print(f"macros into paper/numbers.tex (now {n})")
    if moved > STOP_POINTS:
        print(f"STOP: a with-reasoning group figure moves {moved:.1f} points (> {STOP_POINTS:.0f})")
        sys.exit(3)


if __name__ == "__main__":
    main()
