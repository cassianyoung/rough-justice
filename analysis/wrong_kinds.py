#!/usr/bin/env python3
"""wrong_kinds.py : how run 259's alone cells are decided wrongly. No new calls.

    python analysis/wrong_kinds.py --reads DIR --frames FILE
    python analysis/wrong_kinds.py --selftest --frames FILE

A cell is one test pair on one model, alone, bare (condition B), entered only if both parties' readings are valid
(analyse.valid). Decided correctly: the party held to less at yes-rate >= 0.6 and the other party at <= 0.4 (the 60 / 40
rule of analyse.split). Every other valid cell is decided wrongly, and falls in exactly one of:
  both not met : the party held to less <= 0.4 and the other party <= 0.4;
  both met     : the party held to less >= 0.6 and the other party >= 0.6;
  reversed     : the party held to less <= 0.4 and the other party >= 0.6;
  unclear      : the rest (at least one party strictly between 0.4 and 0.6).

Each is given as a share of all valid cells and as a share of the wrongly decided cells, for fixed-rule cases (insurance
disclosure, statutory thresholds) and judgement cases (the other four domains), for the paper's two model groups (13
without reasoning, 7 with) and per model. Intervals: 95% percentile bootstrap over pairs within domain, 10,000
resamples, seed 259, and models resampled too where a figure pools more than one (outcomes.FastBoot, as the paper's
other shares); a share of wrongly decided cells is the ratio of the two resampled counts.

Macros (paper/numbers.tex), Unit = NoReasoning, Reasoning or the model's name (outcomes.ARM_MACRO), Kind = FixedRule or
Judgement, each with Num, Den, Lo, Hi:
  WronglyDecidedAlone{Unit}{Kind}                 share of valid cells decided wrongly;
  Wrong{Cat}{Unit}{Kind}                          share of valid cells in category Cat;
  Wrong{Cat}AmongWrong{Unit}{Kind}                share of wrongly decided cells in category Cat;
Cat = BothNotMet, BothMet, Reversed, Unclear. Where a unit has no wrongly decided cell, the AmongWrong share, Lo and Hi
are not written (Num and Den, both 0, are). Writes results/wrong_kinds.json and results/WRONG_KINDS.md once; a later
call recomputes and asserts they reproduce, so outcomes.py can call apply() at its end.
"""
import argparse, json, os, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                            # noqa: E402
import macros as M                                             # noqa: E402
import outcomes as O                                           # noqa: E402
import party_difference as PD                                  # noqa: E402

CATS = [("BothNotMet", "both not met"), ("BothMet", "both met"), ("Reversed", "reversed"), ("Unclear", "unclear")]
KINDS = {"FixedRule": O.FIXED, "Judgement": O.JUDGEMENT}
# v2: the matched readout (run 263 swapped in, 2026-11-16)
OUT_JSON = "results/wrong_kinds_v3.json"          # v3: models resampled as well as pairs (2026-11-16)
OUT_MD = "results/WRONG_KINDS_v3.md"
OWN_SOURCES = ("results/wrong_kinds.json", "results/wrong_kinds_v2.json", OUT_JSON)


def category(F, Ob, hi=A.HI, lo=A.LO):
    """None when decided correctly; otherwise the category of the wrong decision."""
    if F >= hi and Ob <= lo:
        return None
    if F <= lo and Ob <= lo:
        return "BothNotMet"
    if F >= hi and Ob >= hi:
        return "BothMet"
    if F <= lo and Ob >= hi:
        return "Reversed"
    return "Unclear"


def ratio(b, num, den):
    """Share num / den, resampled together over pairs and (where more than one) models; num, den: {arm: {pid: count}}.
    A degenerate interval is replaced by a Wilson interval on the cell count (outcomes.FastBoot's rule)."""
    arms = sorted(den)
    Nm = np.array([[num[a].get(p, 0) for p in b.pids] for a in arms], float)
    Dm = np.array([[den[a].get(p, 0) for p in b.pids] for a in arms], float)
    n, d = Nm.sum(), Dm.sum()
    if len(arms) > 1:
        W = b._arm_weights(arms)
        N, D = ((W @ Nm) * b.V).sum(1), ((W @ Dm) * b.V).sum(1)
    else:
        N, D = Nm[0][b.idx].sum(1), Dm[0][b.idx].sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        s = np.where(D > 0, N / np.where(D > 0, D, 1), np.nan)
    ci, how = (b._ci(s) if d else None), "bootstrap"
    if ci is not None and ci[1] - ci[0] < 1e-12:
        ci, how = O.wilson(n, d), "wilson"
    return {"share": float(n / d) if d else None, "num": int(n), "den": int(d), "ci": ci, "ci_method": how}


def run(reads, frames, n=O.B_RESAMPLES):
    tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
    tests = [(p["id"], p["domain"]) for p in frames["pairs"]]
    units = [(g, [a for a in arms if a in tables]) for g, arms in O.GROUPS.items()] + \
            [(a, [a]) for g in O.GROUPS.values() for a in g if a in tables]
    out = {}
    for kind, doms in KINDS.items():
        b = O.FastBoot({d: [p for p, dd in tests if dd == d] for d in doms}, n)
        cells = {}                                   # (arm, pid) -> category or "correct"
        for a in tables:
            for pid in b.pids:
                x = tables[a].get(pid, {}).get("B")
                if x and x["valid"]:
                    c = category(x["F"], x["O"])
                    assert (c is None) == bool(x["split"]), (a, pid, x)
                    cells[(a, pid)] = c or "correct"
        for u, arms in units:
            cnt = lambda f: {a: {p: int((a, p) in cells and f(cells[(a, p)])) for p in b.pids} for a in arms}
            valid, wrong = cnt(lambda c: True), cnt(lambda c: c != "correct")
            e = {"wrong": ratio(b, wrong, valid)}
            for c, _ in CATS:
                k = cnt(lambda x, c=c: x == c)
                e[c] = {"of_valid": ratio(b, k, valid), "of_wrong": ratio(b, k, wrong)}
            assert sum(e[c]["of_valid"]["num"] for c, _ in CATS) == e["wrong"]["num"]
            out[f"{u}|{kind}"] = e
    return {"definition": {"hi": A.HI, "lo": A.LO, "condition": "alone, bare (B)", "resamples": n, "seed": O.SEED,
                           "categories": dict(CATS)},
            "units": {u: arms for u, arms in units}, "stats": out}


def pc(e):
    if e["share"] is None:
        return f"n/a (0/{e['den']})"
    ci = f" [{100 * e['ci'][0]:.0f}, {100 * e['ci'][1]:.0f}]" if e["ci"] else ""
    return f"{100 * e['share']:.0f}%{ci} ({e['num']}/{e['den']})"


def markdown(res):
    L = ["# How alone cells are decided wrongly, run 259", "",
         "Generated by `analysis/wrong_kinds.py`. No new calls. A cell is one test pair on one model, alone and bare, with "
         "both parties' readings valid. Decided correctly: the party held to less at yes-rate >= 0.6 and the other party "
         "at <= 0.4. A wrongly decided cell is *both not met* (both <= 0.4), *both met* (both >= 0.6), *reversed* (the "
         "party held to less <= 0.4, the other >= 0.6) or *unclear* (a party strictly between 0.4 and 0.6). Shares with "
         "95% bootstrap intervals over pairs within domain (10,000 resamples, seed 259) and counts.", ""]
    for base, title in (("of_valid", "share of all valid cells"), ("of_wrong", "share of wrongly decided cells")):
        L += [f"## As a {title}", ""]
        for kind in KINDS:
            L += [f"### {PD.KIND_LABEL[kind].capitalize()}", "",
                  "| Models | Decided wrongly | " + " | ".join(c[1].capitalize() for c in CATS) + " |",
                  "|---|---|" + "---|" * len(CATS)]
            for u in res["units"]:
                e = res["stats"][f"{u}|{kind}"]
                lab = (O.GROUP_LABEL[u] + " (pooled)") if u in O.GROUPS else O.ARM_LABEL[u]
                L.append(f"| {lab} | {pc(e['wrong'])} | " + " | ".join(pc(e[c][base]) for c, _ in CATS) + " |")
            L.append("")
    return "\n".join(L)


def build_macros(res, src):
    v = {}

    def share(name, e, key):
        if e["share"] is not None:
            v[name] = {"value": e["share"], "kind": "pct", "source": f"{src}#{key}.share"}
            if e["ci"]:
                v[name + "Lo"] = {"value": e["ci"][0], "kind": "pct", "source": f"{src}#{key}.ci.0"}
                v[name + "Hi"] = {"value": e["ci"][1], "kind": "pct", "source": f"{src}#{key}.ci.1"}
        v[name + "Num"] = {"value": e["num"], "kind": "int", "source": f"{src}#{key}.num"}
        v[name + "Den"] = {"value": e["den"], "kind": "int", "source": f"{src}#{key}.den"}

    for key, e in res["stats"].items():
        u, kind = key.split("|")
        un = u if u in O.GROUPS else O.ARM_MACRO[u]
        k = f"stats.{key}"
        share(f"WronglyDecidedAlone{un}{kind}", e["wrong"], k + ".wrong")
        for c, _ in CATS:
            share(f"Wrong{c}{un}{kind}", e[c]["of_valid"], f"{k}.{c}.of_valid")
            share(f"Wrong{c}AmongWrong{un}{kind}", e[c]["of_wrong"], f"{k}.{c}.of_wrong")
    return v


def owned(x):
    return str(x.get("source", "")).startswith(tuple(f"{s}#" for s in OWN_SOURCES))


def apply(reads, frames, frames_path, n=O.B_RESAMPLES, root=ROOT, tex=M.TEX, sidecar=M.SIDECAR):
    res = run(reads, frames, n)
    res["inputs"] = {"frames259": os.path.basename(frames_path), "reads259": sorted(reads)}
    md = markdown(res)
    if O.vocabulary_hits(md):
        sys.exit(f"REFUSING: retired vocabulary {O.vocabulary_hits(md)}")
    pj, pm = os.path.join(root, OUT_JSON), os.path.join(root, OUT_MD)
    if os.path.exists(pj):
        old = json.load(open(pj))
        if any(json.dumps(old.get(k), sort_keys=True) != json.dumps(json.loads(json.dumps(res[k])), sort_keys=True)
               for k in ("definition", "units", "stats")):
            sys.exit(f"REFUSING: {OUT_JSON} exists and the recomputation differs; version the output before rewriting")
    else:
        with open(pj, "x") as f:
            json.dump(res, f, indent=1)
    if os.path.exists(pm):
        if open(pm).read() != md:
            sys.exit(f"REFUSING: {OUT_MD} exists and differs from the recomputation")
    else:
        with open(pm, "x") as f:
            f.write(md)
    v = build_macros(res, OUT_JSON)
    total = PD.add_macros(v, OUT_JSON, tex, sidecar, own=OWN_SOURCES)
    return res, md, total, len(v)


def selftest(frames_path):
    import tempfile
    assert category(0.6, 0.4) is None and category(0.4, 0.4) == "BothNotMet" and category(0.6, 0.6) == "BothMet"
    assert category(0.4, 0.6) == "Reversed" and category(0.5, 0.2) == "Unclear" and category(0.8, 0.5) == "Unclear"
    assert category(0.2, 0.41) == "Unclear" and category(0.59, 0.0) == "Unclear"
    print("  ok  categories: 60 / 40 boundaries; exclusive and exhaustive over wrong cells")
    frames = json.load(open(frames_path))
    good = lambda a, cond, pid, k, control: {"A": k == "F", "B": False, "C": k == "F", "D": k == "F"}.get(cond, k == "line")
    reads = A._fake_reads(frames, O.NO_R + O.WITH_R, good)
    res = run(reads, frames, n=200)
    e = res["stats"]["NoReasoning|Judgement"]
    assert e["wrong"]["share"] == 1.0 and e["wrong"]["den"] == 24 * 13
    assert e["BothNotMet"]["of_valid"]["share"] == 1.0 and e["BothNotMet"]["of_wrong"]["share"] == 1.0
    assert e["Reversed"]["of_wrong"]["num"] == 0 and res["stats"]["claude|FixedRule"]["wrong"]["den"] == 12
    print("  ok  alone both no: every cell wrong and 'both not met'; counts 24 x 13 and 12 per model")
    good2 = lambda a, cond, pid, k, control: {"B": k == "F"}.get(cond, k == "line")
    res2 = run(A._fake_reads(frames, O.NO_R + O.WITH_R, good2), frames, n=200)
    e2 = res2["stats"]["Reasoning|FixedRule"]
    assert e2["wrong"]["num"] == 0 and e2["BothMet"]["of_wrong"]["share"] is None
    v = build_macros(res2, "results/x.json")
    assert "WrongBothMetAmongWrongReasoningFixedRule" not in v and v["WrongBothMetAmongWrongReasoningFixedRuleDen"]["value"] == 0
    assert all(k.isalpha() for k in v) and "WrongReversedGptSixSolJudgementLo" in v
    assert not O.vocabulary_hits(" ".join(v)) and not O.vocabulary_hits(markdown(res2))
    print("  ok  all correct: no AmongWrong share written (Num, Den 0); macro names letters only")
    d = tempfile.mkdtemp(); t, s_ = os.path.join(d, "n.tex"), os.path.join(d, "n.json")
    M.write_macros({"Kept": {"value": 0.5, "kind": "pct", "source": "a#b"},
                    "PartyDiffX": {"value": 0.1, "kind": "pts", "source": f"{PD.OUT_JSON}#x"}}, t, s_)
    PD.add_macros({"WrongA": {"value": 3, "kind": "int", "source": f"{OUT_JSON}#n"}}, OUT_JSON, t, s_, own=OWN_SOURCES)
    PD.add_macros({"WrongA": {"value": 4, "kind": "int", "source": f"{OUT_JSON}#n"}}, OUT_JSON, t, s_, own=OWN_SOURCES)
    body = open(t).read()
    assert "{\\WrongA}{4}" in body and "{\\PartyDiffX}{+10}" in body and "{\\Kept}{50\\%}" in body
    PD.add_macros({"PartyDiffX": {"value": 0.2, "kind": "pts", "source": f"{PD.OUT_JSON}#x"}}, PD.OUT_JSON, t, s_)
    assert "{\\WrongA}{4}" in open(t).read()
    print("  ok  re-run: own macros replaced; party_difference.py's kept, and it keeps these")
    print("selftest 4/4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads"); ap.add_argument("--frames", required=True); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.frames)
    frames = json.load(open(a.frames))
    reads, _ = A.load_reads(a.reads)
    res, md, total, k = apply(reads, frames, a.frames)
    print(md)
    print(f"{OUT_JSON}, {OUT_MD}; {k} macros in paper/numbers.tex (now {total} entries)")


if __name__ == "__main__":
    main()
