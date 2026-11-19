#!/usr/bin/env python3
"""controls.py : how often a change of no relevance (the day of the week) flips a verdict. Run 260, with run 259's
control cells beside it. Committed, with the item file (items/run260_items.json), before run 260's first call.

    python analysis/controls.py --selftest --items items/run260_items.json
    python analysis/controls.py --reads260 DIR --reads259 DIR --items items/run260_items.json \
        --frames259 FILE --out results/controls_run260.json

CELL: one control pair on one arm in one condition: the Tuesday reading and the Thursday reading, each a yes-rate (share
of yes among parsed draws, or P(yes) on log-probability arms), valid when both are valid by run 259's definitions (at
least 80% of draws parsed; mean yes + no mass of at least 0.70).
FLIP: the verdict differs between the two days by the same rule as a split, in either direction: one day's yes-rate
at least 0.6 and the other's at most 0.4. Reported as "verdicts flipped by the day of the week alone": the share of
valid cells that flip, pooled over the eleven non-reasoning arms and by arm, with the mean absolute difference in
yes-rate between the two days.
INTERVALS: bootstrap over pairs within domain (each domain's pairs resampled with replacement, a sampled pair keeps
all its arms), 10,000 resamples, seed 259, 95% percentile.
RUN 259 BESIDE IT: run 259's six control pairs (one per domain) on the same eleven arms, by condition (side by side,
both orders pooled; alone bare; standard stated; line stated); and the alone-bare cells of both runs together (24 pairs,
four per domain).
"""
import argparse, json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                            # noqa: E402

ARMS = A.MAIN_OFF
B_RESAMPLES, SEED = 10000, 259


def cells_alone(read, cond="B"):
    """{pair: (tue, thu)} for valid alone cells of one arm in one condition."""
    out = {}
    for uk, u in read["units"].items():
        c, pid = uk.split("|")
        if c != cond or not u.get("control"):
            continue
        f, o = u["cells"].get("F"), u["cells"].get("O")
        out[pid] = (f["yes_rate"], o["yes_rate"]) if A.valid(f, False) and A.valid(o, False) else None
    return out


def cells_side(read):
    out = {}
    for uk, u in read["units"].items():
        c, pid = uk.split("|")
        if c != "A" or not u.get("control"):
            continue
        fl, ol = u["labels"]
        p = A.side_pooled(u["cells"], (fl, ol), False)
        out[pid] = (p[fl], p[ol]) if p else None
    return out


def flip(t, h):
    return (t >= A.HI and h <= A.LO) or (h >= A.HI and t <= A.LO)


def per_pair(tables, arms, pids):
    """{pid: [n_flip, n_valid, sum_absdiff]} over the arms."""
    out = {p: [0, 0, 0.0] for p in pids}
    for a in arms:
        for p in pids:
            x = tables[a].get(p)
            if x is None:
                continue
            out[p][0] += flip(*x); out[p][1] += 1; out[p][2] += abs(x[0] - x[1])
    return out


def estimate(pp, by_domain, n=B_RESAMPLES):
    pids = [p for ps in by_domain.values() for p in ps]
    nf, nv, sd = (sum(pp[p][i] for p in pids) for i in range(3))
    rng = random.Random(SEED)
    rs, ms = [], []
    for _ in range(n):
        s = [rng.choice(ps) for dom in A.DOMAINS for ps in [by_domain.get(dom, [])] for _ in ps]
        v = sum(pp[p][1] for p in s)
        if v:
            rs.append(sum(pp[p][0] for p in s) / v); ms.append(sum(pp[p][2] for p in s) / v)
    ci = lambda xs: (lambda z: [z[int(0.025 * (len(z) - 1))], z[int(math.ceil(0.975 * (len(z) - 1)))]])(sorted(xs)) if xs else None
    return {"flip_share": nf / nv if nv else None, "n_flip": nf, "n_valid": nv, "ci": ci(rs),
            "mean_abs_diff": sd / nv if nv else None, "mean_abs_diff_ci": ci(ms)}


def analyse(r260, r259, items, frames259, n=B_RESAMPLES):
    arms = [a for a in ARMS if a in r260]
    dom260 = {it["id"]: it["domain"] for it in items["items"]}
    by260 = {}
    for p, d in dom260.items():
        by260.setdefault(d, []).append(p)
    t260 = {a: cells_alone(r260[a]) for a in arms}
    res = {"arms": arms, "run260": {"pooled": estimate(per_pair(t260, arms, list(dom260)), by260, n),
                                    "by_arm": {a: estimate(per_pair(t260, [a], list(dom260)), by260, n) for a in arms},
                                    "by_domain": {d: estimate(per_pair(t260, arms, ps), {d: ps}, n)
                                                  for d, ps in by260.items()},
                                    "cells": {a: {p: v for p, v in t260[a].items()} for a in arms}}}
    if r259:
        a59 = [a for a in ARMS if a in r259]
        dom259 = {u["pair"]: u["domain"] for u in frames259["units"].values() if u["control"]}
        by259 = {}
        for p, d in dom259.items():
            by259.setdefault(d, []).append(p)
        res["run259"] = {}
        for cond in "ABCD":
            t = {a: (cells_side(r259[a]) if cond == "A" else cells_alone(r259[a], cond)) for a in a59}
            res["run259"][cond] = {"pooled": estimate(per_pair(t, a59, list(dom259)), by259, n),
                                   "by_arm": {a: estimate(per_pair(t, [a], list(dom259)), by259, n) for a in a59}}
        both = {a: {**{p: v for p, v in cells_alone(r259[a], "B").items()}, **t260.get(a, {})} for a in a59}
        byb = {d: by260.get(d, []) + by259.get(d, []) for d in A.DOMAINS}
        res["alone_bare_both_runs"] = {"pooled": estimate(per_pair(both, a59, [p for ps in byb.values() for p in ps]),
                                                          byb, n),
                                       "by_arm": {a: estimate(per_pair(both, [a], [p for ps in byb.values() for p in ps]),
                                                              byb, n) for a in a59}}
    return res


SETTLED_DEF = ("a cell is settled when both days' yes-rates are at most 0.1, or both at least 0.9; a settled cell has no "
               "room to flip. Descriptive, added after run 260 was read.")


def settled(res, r259, items):
    """results/controls_run260_settled.json: how clear-cut the control cells were (descriptive, after run 260's read)."""
    st = lambda t, h: (t <= 0.1 and h <= 0.1) or (t >= 0.9 and h >= 0.9)

    def count(cells, by_item=None):
        out = {"cells": 0, "unsettled": 0, "flips_among_unsettled": 0}
        for pid, x in cells:
            if x is None:
                continue
            out["cells"] += 1
            if not st(*x):
                out["unsettled"] += 1
                out["flips_among_unsettled"] += flip(*x)
                if by_item is not None:
                    by_item[pid] += 1
        return out
    ids = [it["id"] for it in items["items"]]
    by = {p: 0 for p in ids}
    r = count([(p, tuple(x) if x else None) for a in res["arms"] for p, x in res["run260"]["cells"][a].items()], by)
    out = {"definition": SETTLED_DEF, "run260": dict(r, unsettled_by_item=by), "run259": {}}
    a59 = [a for a in ARMS if a in r259]
    for cond in "BCD":
        out["run259"][cond] = count([(p, x) for a in a59 for p, x in cells_alone(r259[a], cond).items()])
    return out


def load(d, prefix):
    out = {}
    for f in sorted(os.listdir(d)):
        if f.startswith(prefix) and f.endswith(".json"):
            r = json.load(open(os.path.join(d, f)))
            if r.get("status") == "READ" and r["arm"] in ARMS:
                out[r["arm"]] = r
    return out


def selftest(items_path):
    items = json.load(open(items_path))

    def fake(rule):
        units = {}
        for uk, u in items["units"].items():
            t, h = rule(u["pair"])
            units[uk] = {**{k: v for k, v in u.items() if k != "prompts"},
                         "cells": {"F": {"gate": "PASSED", "n_asked": 10, "yes_rate": t, "draws": []},
                                   "O": {"gate": "PASSED", "n_asked": 10, "yes_rate": h, "draws": []}}}
        return {"arm": "claude", "status": "READ", "units": units}
    r = analyse({"claude": fake(lambda p: (0.9, 0.9))}, None, items, None, n=200)
    assert r["run260"]["pooled"]["flip_share"] == 0.0 and r["run260"]["pooled"]["mean_abs_diff"] == 0.0
    r = analyse({"claude": fake(lambda p: (0.8, 0.2) if p in ("N1", "N2") else (0.5, 0.5))}, None, items, None, n=200)
    assert abs(r["run260"]["pooled"]["flip_share"] - 2 / 18) < 1e-12 and r["run260"]["pooled"]["n_valid"] == 18
    r = analyse({"claude": fake(lambda p: (0.6, 0.45))}, None, items, None, n=200)     # 0.45 is not <= 0.4: no flip
    assert r["run260"]["pooled"]["flip_share"] == 0.0 and abs(r["run260"]["pooled"]["mean_abs_diff"] - 0.15) < 1e-9
    print("selftest 3/3")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads260"); ap.add_argument("--reads259"); ap.add_argument("--items", required=True)
    ap.add_argument("--frames259"); ap.add_argument("--out"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.items)
    items = json.load(open(a.items))
    res = analyse(load(a.reads260, "RUN260_READ__"), load(a.reads259, "RUN259_READ__") if a.reads259 else None, items,
                  json.load(open(a.frames259)) if a.frames259 else None)
    if os.path.exists(a.out):
        sys.exit(f"write-once: {a.out} exists")
    with open(a.out, "x") as f:
        json.dump(res, f, indent=1)
    p = res["run260"]["pooled"]
    print(f"run 260 flipped {p['flip_share']:.3f} ({p['n_flip']}/{p['n_valid']}) ci {p['ci']}; mean |diff| "
          f"{p['mean_abs_diff']:.3f} ci {p['mean_abs_diff_ci']}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
