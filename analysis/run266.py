#!/usr/bin/env python3
"""run266.py : the direct question in both directions (run 261 original, run 266 mirror). No calls.

    python analysis/run266.py --ai DIR        # results/run266.json and results/RUN266_OUTCOMES.md (write-once)
    python analysis/run266.py --macros        # the macros from the written results into paper/numbers.tex

ORIGINAL (run 261, block B): the party held to more named first. "Should {more} be held to more than {less} when ...?"
and "how much more should be expected of {more} than of {less}" (0-9). A model holding the principle says yes, and a
high digit. MIRROR (run 266): the same sentences with the two parties swapped and nothing else; a model holding the
principle says no, and 0.
DEFINITIONS, the same as run 261's (analysis/run261.py block_B): a model-domain's yes-rate is its yes/no cell's yes-rate
when the cell is valid (analyse.valid); its 0-9 mean is the mean first digit over draws neither void nor refused. A
group's figure is the mean over its model-domains. A model-domain is ANSWERED YES BY MAJORITY when its yes-rate is above
0.5. GROUPS as run 261: without reasoning the 12 configurations other than Kimi K3, which is reported apart; with
reasoning the 7.
"""
import argparse, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import outcomes as O                                            # noqa: E402
import run261 as R61                                            # noqa: E402

OUT_JSON, OUT_MD = "results/run266.json", "results/RUN266_OUTCOMES.md"
GROUPS, GM, DOM7 = R61.GROUPS, R61.GM, R61.DOM7
LABEL = {"original": "party held to more named first (run 261)", "mirror": "party held to less named first (run 266)"}


def cells(read):
    rs = R61.reasoning(read)
    out = {}
    for dom in DOM7:
        u = read["units"].get(f"B|{dom}")
        if not u:
            continue
        digits = [R61.first_digit(d.get("text")) for d in u["cells"]["digit"]["draws"]
                  if not d.get("void") and not d.get("refused")]
        digits = [x for x in digits if x is not None]
        out[dom] = {"yes_rate": R61.yes(u["cells"]["yn"], rs), "digit_mean": statistics.mean(digits) if digits else None,
                    "digit_n": len(digits), "yn_gate": u["cells"]["yn"].get("gate")}
    return out


def summary(per, arms):
    ys = [per[a][d]["yes_rate"] for a in arms for d in per[a] if per[a][d]["yes_rate"] is not None]
    dg = [per[a][d]["digit_mean"] for a in arms for d in per[a] if per[a][d]["digit_mean"] is not None]
    maj = sorted(f"{a}|{d}" for a in arms for d in per[a] if (per[a][d]["yes_rate"] or 0) > 0.5)
    return {"yes_rate_mean": statistics.mean(ys) if ys else None, "digit_mean": statistics.mean(dg) if dg else None,
            "cells": len(ys), "digit_cells": len(dg), "yes_by_majority": maj, "yes_by_majority_n": len(maj)}


def compute(ai):
    arms = [a for g in GROUPS.values() for a in g]
    rec = lambda p: json.load(open(os.path.join(ai, p)))
    r61 = {a: rec(f"records/RUN261_READ__{a}.json") for a in arms}
    r66 = {a: rec(f"records/RUN266_READ__{a}.json") for a in arms}
    bad = [a for a in arms if r66[a].get("status") != "READ"]
    if [a for a in bad if a != R61.KIMI]:
        sys.exit(f"REFUSING: run 266 arms not READ: {bad}")
    # Kimi K3 is reported apart; if its provider is gone it is unread and its group has no mirror figures
    groups = {g: v for g, v in GROUPS.items() if not set(v) & set(bad)}
    unread = {a: r66[a].get("unread_reason") for a in bad}
    per = {"original": {a: cells(r61[a]) for a in arms},
           "mirror": {a: cells(r66[a]) for a in arms if a not in bad}}
    res = {"definitions": __doc__.split("DEFINITIONS")[1].strip(), "groups": {g: list(v) for g, v in GROUPS.items()},
           "unread": unread,
           "per_config": {d: {a: {"cells": per[d][a], **summary(per[d], [a])} for a in per[d]} for d in per},
           "by_group": {"original": {g: summary(per["original"], v) for g, v in GROUPS.items()},
                        "mirror": {g: summary(per["mirror"], v) for g, v in groups.items()}},
           "spent_usd": {a: r66[a]["spent_usd"] for a in arms}, "calls": {a: r66[a]["calls"] for a in arms},
           "served": {a: r66[a].get("provider_served") for a in arms}}
    # the run 261 side must reproduce what the paper already reports (results/run261_v2.json, B)
    old = json.load(open(os.path.join(ROOT, R61.OUT_JSON)))["B"]["groups"]
    for g in GROUPS:
        for k in ("yes_rate_mean", "digit_mean"):
            assert abs(old[g][k] - res["by_group"]["original"][g][k]) < 1e-12, (g, k)
    return res


def pct(x):
    return "" if x is None else f"{100 * x:.0f}%"


def f1(x):
    return "" if x is None else f"{x:.1f}"


def markdown(res):
    L = ["# Run 266: the direct question in both directions", "",
         "Original (run 261): party held to more named first; mirror (run 266): the parties swapped, nothing else.",
         "Share answering yes (mean over model-domains) and mean 0-9; mirror model-domains answered yes by majority "
         "(yes-rate above 0.5).", "", "## By group", "",
         "| Group | Configs | Yes, original | Yes, mirror | 0-9, original | 0-9, mirror | Mirror yes by majority |",
         "|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        o, m = res["by_group"]["original"][g], res["by_group"]["mirror"].get(g)
        if m is None:
            L.append(f"| {g} | {len(GROUPS[g])} | {pct(o['yes_rate_mean'])} | unread | {f1(o['digit_mean'])} | unread | |")
            continue
        L.append(f"| {g} | {len(GROUPS[g])} | {pct(o['yes_rate_mean'])} | {pct(m['yes_rate_mean'])} | {f1(o['digit_mean'])} | "
                 f"{f1(m['digit_mean'])} | {m['yes_by_majority_n']} of {m['cells']}: {', '.join(m['yes_by_majority']) or 'none'} |")
    L += ["", "## By configuration", "",
          "| Config | Group | Yes, original | Yes, mirror | 0-9, original | 0-9, mirror | Mirror yes by majority | Spent |",
          "|---|---|---|---|---|---|---|---|"]
    for g, arms in GROUPS.items():
        for a in arms:
            o, m = res["per_config"]["original"][a], res["per_config"]["mirror"].get(a)
            if m is None:
                L.append(f"| {O.ARM_LABEL[a]} | {g} | {pct(o['yes_rate_mean'])} | unread | {f1(o['digit_mean'])} | unread | "
                         f"{res['unread'][a]} | $0 |")
                continue
            doms = ", ".join(x.split("|")[1] for x in m["yes_by_majority"]) or "none"
            L.append(f"| {O.ARM_LABEL[a]} | {g} | {pct(o['yes_rate_mean'])} | {pct(m['yes_rate_mean'])} | {f1(o['digit_mean'])} | "
                     f"{f1(m['digit_mean'])} | {doms} | ${res['spent_usd'][a]:.4f} |")
    L += ["", f"Total spent: ${sum(res['spent_usd'].values()):.4f} over {sum(res['calls'].values())} calls."]
    return "\n".join(L) + "\n"


def macros(res):
    src = f"{OUT_JSON}#"
    v = {}
    for g, gm in GM.items():
        if g not in res["by_group"]["mirror"]:
            continue
        m = res["by_group"]["mirror"][g]
        v[f"MirrorYesRate{gm}"] = {"value": m["yes_rate_mean"], "kind": "pct", "source": src + f"by_group.mirror.{g}.yes_rate_mean"}
        v[f"MirrorDigit{gm}"] = {"value": m["digit_mean"], "kind": "f1", "source": src + f"by_group.mirror.{g}.digit_mean"}
        v[f"MirrorYesMajority{gm}Num"] = {"value": m["yes_by_majority_n"], "kind": "int",
                                         "source": src + f"by_group.mirror.{g}.yes_by_majority_n"}
        v[f"MirrorYesMajority{gm}Den"] = {"value": m["cells"], "kind": "int", "source": src + f"by_group.mirror.{g}.cells"}
        v[f"MirrorYesMajorityList{gm}"] = {"value": "; ".join(f"\\model{{{O.ARM_LABEL[x.split('|')[0]]}}} on {x.split('|')[1]}"
                                                             for x in m["yes_by_majority"]) or "none",
                                          "kind": "str", "source": src + f"by_group.mirror.{g}.yes_by_majority"}
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    ap.add_argument("--macros", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.macros:
        import party_difference as PD
        res = json.load(open(os.path.join(ROOT, OUT_JSON)))
        n = PD.add_macros(macros(res), OUT_JSON, own=(OUT_JSON,))
        return print(f"run 266 macros into paper/numbers.tex (now {n})")
    res = compute(a.ai)
    if a.dry:
        return print(markdown(res))
    for p in (OUT_JSON, OUT_MD):
        if os.path.exists(os.path.join(ROOT, p)):
            sys.exit(f"write-once: {p} exists")
    with open(os.path.join(ROOT, OUT_JSON), "x") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(ROOT, OUT_MD), "x") as f:
        f.write(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
