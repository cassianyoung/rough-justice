#!/usr/bin/env python3
"""run261.py : run 261's outcomes, blocks A to E and G. No new calls.

    python analysis/run261.py --ai DIR     # DIR = the banked responses (default banked/)

Writes results/run261.json and results/RUN261_OUTCOMES.md (write-once). Does NOT write paper/numbers.tex.

DEFINITIONS (the paper's, analysis/analyse.py): a cell is valid by analyse.valid (gate passed; on a reasoning arm, voids at
most 10% of draws); a pair is SPLIT when the party held to less is at yes-rate >= 0.6 and the other at <= 0.4; side by
side pools both orders (analyse.side_pooled). A failing is LET THROUGH when read without the fix at <= 0.4 and with it
at >= 0.6. INTERVALS: pairs within domain and models resampled together (outcomes.FastBoot), 95%, Wilson where degenerate.
GROUPS: without reasoning, the 12 configurations other than Kimi K3, whose run 261 reads are on a new provider and are
reported apart (records/RUN261_KIMI_ROUTE_CHECK.json); with reasoning, the 7. Claude Haiku 5.5 at maximum effort: void
cells excluded (analyse.valid), and the main figures also with them counted as wrong.
BLOCKS
  A  education (W1-W6): the five conditions, beside the six run-259 domains; six- and seven-domain pooled figures.
  B  asked directly: yes-rate per model and domain (yes/no), mean digit (0-9); the B FILTER: judgement-case alone figures
     restricted to model-domain cells whose direct yes-rate is >= 0.6, and the cells where it is below.
  C  worked example on all 42 pairs: split alone with the example against the same-session bare baseline (Cbase; for
     education, A's alone); let through (bare outside failing <= 0.4, with the example >= 0.6), unconditionally and
     among the cells the example splits (conditional: of those, the failing still rejected, <= 0.4, with the example).
  D  14-pair subset: let through with the rule and with the example, original and second wording; controls (new wording):
     the plain case with the rule (share judged met, >= 0.6), the outside case without the rule (share rejected, <= 0.4).
  E  "UK law applies.": split alone, fixed-rule pairs and the judgement pairs of D's subset, against C's baseline on the
     same pairs; models whose fixed-rule figure moves more than 10 points.
  G  milder conduct, in the cells that were both not met alone: party-sensitive (held to less met, other not met),
     still both not met, overshot (both met), unclear (anything else; reversed counted here and shown). With and without
     the five variants that split on only two of three pilot arms (K1, K2, K5, D4, W2).
"""
import argparse, json, math, os, statistics, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402

OUT_JSON, OUT_MD = "results/run261_v2.json", "results/RUN261_OUTCOMES_v2.md"   # v2 adds C's six-domain judgement kind
DOM7 = A.DOMAINS + ("education",)
FIXED, JUDG6 = O.FIXED, O.JUDGEMENT
JUDG7 = JUDG6 + ("education",)
KIMI = "kimi"
TWO_OF_THREE = ("K1", "K2", "K5", "D4", "W2")
GROUPS = {"NoReasoning": tuple(a for a in O.NO_R if a != KIMI), "Reasoning": O.WITH_R, "Kimi": (KIMI,)}
HAIKU = "haiku55_ah"


# ── loading ─────────────────────────────────────────────────────────────────────────
def load(ai):
    rec = lambda p: json.load(open(os.path.join(ai, p)))
    arms = list(O.NO_R + O.WITH_R)
    r61 = {a: rec(f"records/RUN261_READ__{a}.json") for a in arms}
    g61 = {a: rec(f"records/RUN261_G_READ__{a}.json") for a in arms
           if os.path.exists(os.path.join(ai, f"records/RUN261_G_READ__{a}.json"))}
    r59 = {a: rec(f"records/RUN259_MATCHED_READS/RUN259_READ__{a}.json") for a in arms}
    draft = rec("data/sfv_261/draft_v2.json")
    d259 = rec("data/sfv_259/draft_v3.json")
    pairs = {p["id"]: p for p in d259["pairs"] + draft["education"]["pairs"]}
    return r61, g61, r59, draft, pairs


def reasoning(read):
    return bool(read.get("reasoning"))


def yes(cell, rs, wrong_void=None):
    """A cell's yes-rate if valid, else None. wrong_void: for the worst case, a void-excluded cell's 'wrong' value."""
    if A.valid(cell, rs):
        return cell["yes_rate"]
    if wrong_void is not None and cell and cell.get("gate") == "EXCLUDED_VOID":
        return wrong_void
    return None


# ── bootstrap over pairs (within domain) and models ─────────────────────────────────
def boot(cells, pids_by_dom, arms):
    """cells: {(arm, pid): (num, den)}. Share with the paper's two-way interval."""
    doms = {d: ps for d, ps in pids_by_dom.items() if ps}
    saved = A.DOMAINS
    A.DOMAINS = tuple(d for d in DOM7 if d in doms)
    try:
        b = O.FastBoot(doms)
    finally:
        A.DOMAINS = saved
    c = A.ArmCounts()
    c.by_arm = {a: {p: cells.get((a, p), (0, 0)) for p in b.pids} for a in arms}
    for p in b.pids:
        c[p] = (sum(c.by_arm[a][p][0] for a in arms), sum(c.by_arm[a][p][1] for a in arms))
    e = b.est(c)
    return {k: e[k] for k in ("share", "num", "den", "ci", "ci_method")}


def by_dom(pids, pairs):
    out = {}
    for p in pids:
        out.setdefault(pairs[p]["domain"], []).append(p)
    return out


def pc(e):
    if not e or e["share"] is None:
        return "n/a"
    lo, hi = e["ci"] or (e["share"], e["share"])
    return f"{100 * e['share']:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}] ({e['num']}/{e['den']})"


# ── A: education beside the six domains ─────────────────────────────────────────────
def edu_records(read):
    """run 261 block A in run 259's layout: {pid: {cond: record}} via analyse.pair_cells."""
    units = {}
    for uk, u in read["units"].items():
        if uk.startswith("A."):
            units[uk[2:]] = u
    return A.pair_cells({"units": units, "reasoning": read.get("reasoning")}, None)


def cond_cells(tables, arms, pids, cond, what="split"):
    out = {}
    for a in arms:
        for p in pids:
            r = tables[a].get(p, {}).get(cond)
            if r is None:
                continue
            if cond == "E":
                out[(a, p)] = (int(r["let"]), int(r["valid"]))
            else:
                out[(a, p)] = (int(r["split"]), int(r["valid"]))
    return out


def block_A(r61, r59, pairs):
    W = [p for p in pairs if p.startswith("W")]
    six = [p for p in pairs if not p.startswith("W")]
    tab = {}
    for a in r61:
        t = {pid: rec for pid, rec in A.pair_cells(r59[a], None).items() if pid in six}
        t.update(edu_records(r61[a]))
        tab[a] = t
    out = {}
    for g, arms in GROUPS.items():
        out[g] = {}
        for cond in ("A", "B", "C", "D", "E"):
            out[g][cond] = {
                "education": boot(cond_cells(tab, arms, W, cond), by_dom(W, pairs), arms),
                "six_domains": boot(cond_cells(tab, arms, six, cond), by_dom(six, pairs), arms),
                "seven_domains": boot(cond_cells(tab, arms, six + W, cond), by_dom(six + W, pairs), arms),
                "judgement_six": boot(cond_cells(tab, arms, [p for p in six if pairs[p]["domain"] in JUDG6], cond),
                                      by_dom([p for p in six if pairs[p]["domain"] in JUDG6], pairs), arms),
                "judgement_seven": boot(cond_cells(tab, arms, [p for p in six + W if pairs[p]["domain"] in JUDG7], cond),
                                        by_dom([p for p in six + W if pairs[p]["domain"] in JUDG7], pairs), arms)}
    return out, tab


# ── B: asked directly, and the filter ───────────────────────────────────────────────
def first_digit(t):
    import re
    m = re.search(r"\b([0-9])\b", t or "")
    return int(m.group(1)) if m else None


def block_B(r61, tab, pairs):
    direct = {}
    for a, r in r61.items():
        rs = reasoning(r)
        for dom in DOM7:
            u = r["units"].get(f"B|{dom}")
            if not u:
                continue
            yn = u["cells"]["yn"]
            digits = [first_digit(d.get("text")) for d in u["cells"]["digit"]["draws"]
                      if not d.get("void") and not d.get("refused")]
            digits = [x for x in digits if x is not None]
            direct[(a, dom)] = {"yes_rate": yes(yn, rs), "digit_mean": statistics.mean(digits) if digits else None,
                                "digit_n": len(digits)}
    out = {"per_model_domain": {f"{a}|{d}": v for (a, d), v in direct.items()}, "groups": {}, "filter": {}}
    for g, arms in GROUPS.items():
        ys = [direct[(a, d)]["yes_rate"] for a in arms for d in DOM7 if (a, d) in direct and direct[(a, d)]["yes_rate"] is not None]
        dg = [direct[(a, d)]["digit_mean"] for a in arms for d in DOM7 if (a, d) in direct and direct[(a, d)]["digit_mean"] is not None]
        out["groups"][g] = {"yes_rate_mean": statistics.mean(ys) if ys else None, "cells_at_least_0_6":
                            sum(1 for y in ys if y >= 0.6), "cells": len(ys), "digit_mean": statistics.mean(dg) if dg else None}
        # the filter: judgement-case alone (split), model-domain cells whose direct yes-rate >= 0.6
        jp = [p for p in pairs if pairs[p]["domain"] in JUDG7]
        keep = {(a, d) for a in arms for d in JUDG7 if (a, d) in direct and (direct[(a, d)]["yes_rate"] or 0) >= 0.6}
        cells_all = cond_cells(tab, arms, jp, "B")
        cells_kept = {k: v for k, v in cells_all.items() if (k[0], pairs[k[1]]["domain"]) in keep}
        out["filter"][g] = {"alone_judgement_all": boot(cells_all, by_dom(jp, pairs), arms),
                            "alone_judgement_where_direct_says_differ": boot(cells_kept, by_dom(jp, pairs), arms),
                            "model_domains_kept": len(keep),
                            "model_domains_say_no_difference": sorted(f"{a}|{d}" for a in arms for d in JUDG7
                                                                      if (a, d) in direct and direct[(a, d)]["yes_rate"] is not None
                                                                      and direct[(a, d)]["yes_rate"] < 0.6)}
    return out


# ── C: worked example ───────────────────────────────────────────────────────────────
def block_C(r61, pairs, worst=False):
    cells = {k: {} for k in ("split_example", "split_bare", "let_through", "still_rejected_given_split")}
    for a, r in r61.items():
        rs = reasoning(r)
        wv = (lambda v: v) if not (worst and a == HAIKU) else None
        for pid in pairs:
            c = r["units"].get(f"C|{pid}")
            if pid.startswith("W"):
                bF, bO = r["units"][f"A.B|{pid}"]["cells"]["F"], r["units"][f"A.B|{pid}"]["cells"]["O"]
                bE = r["units"][f"A.E|{pid}"]["cells"]["bare"]
            else:
                b = r["units"][f"Cbase|{pid}"]["cells"]
                bF, bO, bE = b["F"], b["O"], b["bare"]
            g = (lambda cell, bad: yes(cell, rs, bad if (worst and a == HAIKU) else None))
            f, o, ex = g(c["cells"]["F"], 0.0), g(c["cells"]["O"], 1.0), g(c["cells"]["ex"], 1.0)
            fb, ob, eb = g(bF, 0.0), g(bO, 1.0), g(bE, 0.0)
            if f is not None and o is not None:
                cells["split_example"][(a, pid)] = (int(A.split(f, o)), 1)
            if fb is not None and ob is not None:
                cells["split_bare"][(a, pid)] = (int(A.split(fb, ob)), 1)
            if eb is not None and ex is not None:
                cells["let_through"][(a, pid)] = (int(eb <= A.LO and ex >= A.HI), 1)
            if f is not None and o is not None and A.split(f, o) and ex is not None:
                cells["still_rejected_given_split"][(a, pid)] = (int(ex <= A.LO), 1)
    out = {}
    for g, arms in GROUPS.items():
        out[g] = {}
        for kind, doms in (("all", DOM7), ("FixedRule", FIXED), ("Judgement", JUDG7), ("six_domains", A.DOMAINS),
                           ("judgement_six", JUDG6)):
            pids = [p for p in pairs if pairs[p]["domain"] in doms]
            out[g][kind] = {k: boot({kk: v for kk, v in cs.items() if kk[1] in pids and kk[0] in arms},
                                    by_dom(pids, pairs), arms) for k, cs in cells.items()}
    return out


# ── D: second wording on the subset ─────────────────────────────────────────────────
def block_D(r61, pairs, subset):
    names = ("rule_orig", "rule_new", "example_orig", "example_new", "ctrl_plain_rule_new_met", "ctrl_outside_norule_new_rejected")
    cells = {k: {} for k in names}
    for a, r in r61.items():
        rs = reasoning(r)
        for pid in subset:
            d = r["units"][f"D|{pid}"]["cells"]
            if pid.startswith("W"):
                bare = yes(r["units"][f"A.E|{pid}"]["cells"]["bare"], rs)
                rule_o = yes(r["units"][f"A.E|{pid}"]["cells"]["line"], rs)
            else:
                bare = yes(r["units"][f"Cbase|{pid}"]["cells"]["bare"], rs)
                rule_o = yes(d["rule_orig"], rs)
            ex_o = yes(r["units"][f"C|{pid}"]["cells"]["ex"], rs)
            nb = yes(d["outside_norule_new"], rs)
            rn, en, pn = yes(d["rule_new"], rs), yes(d["example_new"], rs), yes(d["plain_rule_new"], rs)
            lt = lambda b0, f0: None if b0 is None or f0 is None else (int(b0 <= A.LO and f0 >= A.HI), 1)
            for k, v in (("rule_orig", lt(bare, rule_o)), ("rule_new", lt(nb, rn)), ("example_orig", lt(bare, ex_o)),
                         ("example_new", lt(nb, en)),
                         ("ctrl_plain_rule_new_met", None if pn is None else (int(pn >= A.HI), 1)),
                         ("ctrl_outside_norule_new_rejected", None if nb is None else (int(nb <= A.LO), 1))):
                if v is not None:
                    cells[k][(a, pid)] = v
    out = {}
    bd = by_dom(subset, pairs)
    for g, arms in GROUPS.items():
        out[g] = {k: boot({kk: v for kk, v in cs.items() if kk[0] in arms}, bd, arms) for k, cs in cells.items()}
        for x, y in (("rule_new", "rule_orig"), ("example_new", "example_orig")):
            out[g][f"{x}-{y}"] = diff(cells[x], cells[y], bd, arms)
    return out


def diff(c1, c2, bd, arms):
    saved = A.DOMAINS
    A.DOMAINS = tuple(d for d in DOM7 if d in bd)
    try:
        b = O.FastBoot(bd)
    finally:
        A.DOMAINS = saved

    def ac(cs):
        c = A.ArmCounts()
        c.by_arm = {a: {p: cs.get((a, p), (0, 0)) for p in b.pids} for a in arms}
        for p in b.pids:
            c[p] = (sum(c.by_arm[a][p][0] for a in arms), sum(c.by_arm[a][p][1] for a in arms))
        return c
    return b.diff(ac({k: v for k, v in c1.items() if k[0] in arms}), ac({k: v for k, v in c2.items() if k[0] in arms}))


# ── E: jurisdiction stated ──────────────────────────────────────────────────────────
def block_E(r61, pairs, subset):
    fixed = [p for p in pairs if pairs[p]["domain"] in FIXED]
    judg = [p for p in subset if pairs[p]["domain"] in JUDG7]
    cells = {"uk": {}, "base": {}, "uk_held_failed": {}, "base_held_failed": {}}
    for a, r in r61.items():
        rs = reasoning(r)
        for pid in fixed + judg:
            u = r["units"][f"E|{pid}"]["cells"]
            f, o = yes(u["F"], rs), yes(u["O"], rs)
            if pid.startswith("W"):
                bF, bO = (yes(r["units"][f"A.B|{pid}"]["cells"][k], rs) for k in ("F", "O"))
            else:
                bF, bO = (yes(r["units"][f"Cbase|{pid}"]["cells"][k], rs) for k in ("F", "O"))
            if f is not None and o is not None:
                cells["uk"][(a, pid)] = (int(A.split(f, o)), 1)
            if bF is not None and bO is not None:
                cells["base"][(a, pid)] = (int(A.split(bF, bO)), 1)
            if f is not None:
                cells["uk_held_failed"][(a, pid)] = (int(f < 0.5), 1)
            if bF is not None:
                cells["base_held_failed"][(a, pid)] = (int(bF < 0.5), 1)
    out = {}
    for g, arms in GROUPS.items():
        out[g] = {}
        for kind, pids in (("FixedRule", fixed), ("Judgement", judg)):
            bd = by_dom(pids, pairs)
            sel = lambda cs: {k: v for k, v in cs.items() if k[1] in pids and k[0] in arms}
            out[g][kind] = {k: boot(sel(cs), bd, arms) for k, cs in cells.items()}
            out[g][kind]["uk-base"] = diff(sel(cells["uk"]), sel(cells["base"]), bd, arms)
    per_model = {}
    for a in r61:
        u = [cells["uk"][(a, p)][0] for p in fixed if (a, p) in cells["uk"]]
        b = [cells["base"][(a, p)][0] for p in fixed if (a, p) in cells["base"]]
        if u and b:
            per_model[a] = {"uk": sum(u) / len(u), "base": sum(b) / len(b), "change": sum(u) / len(u) - sum(b) / len(b)}
    out["per_model_fixed_rule"] = per_model
    out["models_moving_more_than_10_points"] = sorted(a for a, v in per_model.items() if abs(v["change"]) > 0.10)
    return out


# ── G: milder conduct ───────────────────────────────────────────────────────────────
def outcome(f, o):
    if f >= A.HI and o <= A.LO:
        return "party_sensitive"
    if f <= A.LO and o <= A.LO:
        return "still_both_not_met"
    if f >= A.HI and o >= A.HI:
        return "overshot"
    return "reversed" if (f <= A.LO and o >= A.HI) else "unclear"


def block_G(g61, pairs, worst=False):
    cells = {}
    for a, r in g61.items():
        rs = bool(r.get("reasoning")) or a in O.WITH_R
        for uk, u in r.get("units", {}).items():
            pid = uk.split("|")[1]
            F, Ob = u["cells"]["F"], u["cells"]["O"]
            f, o = yes(F, rs), yes(Ob, rs)
            if (f is None or o is None) and worst and a == HAIKU:
                cells[(a, pid)] = "still_both_not_met"          # a void cell counted as wrong: no party sensitivity
                continue
            cells[(a, pid)] = outcome(f, o) if f is not None and o is not None else "invalid"
    cats = ("party_sensitive", "still_both_not_met", "overshot", "unclear", "reversed")
    out = {}
    for label, drop in (("all_variants", ()), ("without_two_of_three", TWO_OF_THREE)):
        out[label] = {}
        for g, arms in GROUPS.items():
            pids = [p for p in pairs if pairs[p]["domain"] in JUDG7 and p not in drop]
            bd = by_dom(pids, pairs)
            valid = {k: v for k, v in cells.items() if k[0] in arms and k[1] in pids and v != "invalid"}
            out[label][g] = {"cells_read": sum(1 for k, v in cells.items() if k[0] in arms and k[1] in pids),
                             "cells_valid": len(valid)}
            for cat in cats:
                out[label][g][cat] = boot({k: (int(v == cat), 1) for k, v in valid.items()}, bd, arms)
            out[label][g]["unclear_incl_reversed"] = boot({k: (int(v in ("unclear", "reversed")), 1) for k, v in valid.items()},
                                                          bd, arms)
    out["per_variant"] = {p: {c: sum(1 for (a, q), v in cells.items() if q == p and v == c) for c in cats + ("invalid",)}
                          for p in pairs if pairs[p]["domain"] in JUDG7}
    return out


def markdown(res):
    G = ("NoReasoning", "Reasoning", "Kimi")
    lab = {"NoReasoning": "Without reasoning (12; Kimi apart)", "Reasoning": "With reasoning (7)", "Kimi": "Kimi K3 (new provider)"}
    L = ["# Run 261: outcomes", "", "Generated by `analysis/run261.py`; no new calls. " + res["definitions"].replace("\n", " "), ""]
    L += ["## A. Education beside the six domains (split / let through)", "",
          "| Group | Condition | Education | Six domains | Seven domains | Judgement, six | Judgement, seven |", "|---|---|---|---|---|---|---|"]
    names = {"A": "side by side", "B": "alone", "C": "told in principle", "D": "told a precise rule", "E": "let through"}
    for g in G:
        for c, n in names.items():
            e = res["A"][g][c]
            L.append(f"| {lab[g]} | {n} | {pc(e['education'])} | {pc(e['six_domains'])} | {pc(e['seven_domains'])} | "
                     f"{pc(e['judgement_six'])} | {pc(e['judgement_seven'])} |")
    L += ["", "## B. Asked directly, and the filter", "", "| Group | Mean yes-rate | Cells at >= 0.6 | Mean digit (0-9) | "
          "Judgement alone, all | Judgement alone, where the model says the parties differ | Model-domains saying no difference |",
          "|---|---|---|---|---|---|---|"]
    for g in G:
        b, f = res["B"]["groups"][g], res["B"]["filter"][g]
        L.append(f"| {lab[g]} | {b['yes_rate_mean']:.2f} | {b['cells_at_least_0_6']}/{b['cells']} | "
                 f"{(b['digit_mean'] or float('nan')):.1f} | {pc(f['alone_judgement_all'])} | "
                 f"{pc(f['alone_judgement_where_direct_says_differ'])} | {', '.join(f['model_domains_say_no_difference']) or 'none'} |")
    L += ["", "## C. Worked example (all 42 pairs)", "", "| Group | Cases | Split, bare | Split, with the example | "
          "Let through | Still rejected, of those the example splits | Let through, Haiku 5.5 voids as wrong |",
          "|---|---|---|---|---|---|---|"]
    for g in G:
        for k in ("all", "FixedRule", "Judgement", "six_domains"):
            e, w = res["C"][g][k], res["C_haiku_void_wrong"][g][k]
            L.append(f"| {lab[g]} | {k} | {pc(e['split_bare'])} | {pc(e['split_example'])} | {pc(e['let_through'])} | "
                     f"{pc(e['still_rejected_given_split'])} | {pc(w['let_through'])} |")
    L += ["", "## D. Second wording (14-pair subset)", "", "| Group | Rule, original | Rule, new | Change | Example, original | "
          "Example, new | Change | Control: plain case with rule judged met (new) | Control: outside case without rule rejected (new) |",
          "|---|---|---|---|---|---|---|---|---|"]
    ch = lambda d: f"{100 * d['diff']:+.0f} [{100 * d['ci'][0]:+.0f}, {100 * d['ci'][1]:+.0f}]" if d and d.get("diff") is not None else "n/a"
    for g in G:
        d = res["D"][g]
        L.append(f"| {lab[g]} | {pc(d['rule_orig'])} | {pc(d['rule_new'])} | {ch(d['rule_new-rule_orig'])} | "
                 f"{pc(d['example_orig'])} | {pc(d['example_new'])} | {ch(d['example_new-example_orig'])} | "
                 f"{pc(d['ctrl_plain_rule_new_met'])} | {pc(d['ctrl_outside_norule_new_rejected'])} |")
    L += ["", "## E. \"UK law applies.\" against C's baseline (split alone)", "", "| Group | Cases | UK law stated | Baseline | Change | "
          "Held to less failed: stated | baseline |", "|---|---|---|---|---|---|---|"]
    for g in G:
        for k in ("FixedRule", "Judgement"):
            e = res["E"][g][k]
            L.append(f"| {lab[g]} | {k} | {pc(e['uk'])} | {pc(e['base'])} | {ch(e['uk-base'])} | {pc(e['uk_held_failed'])} | "
                     f"{pc(e['base_held_failed'])} |")
    L += ["", "Models whose fixed-rule figure moves more than 10 points: " +
          (", ".join(f"{a} ({100 * res['E']['per_model_fixed_rule'][a]['base']:.0f}% to {100 * res['E']['per_model_fixed_rule'][a]['uk']:.0f}%)"
                     for a in res["E"]["models_moving_more_than_10_points"]) or "none") + "."]
    if res.get("G"):
        L += ["", "## G. Milder conduct, cells both not met alone (judgement pairs only; block G has no fixed-rule pairs)", ""]
        for label in ("all_variants", "without_two_of_three"):
            L += [f"### {label.replace('_', ' ')}", "", "| Group | Cells read / valid | Party-sensitive | Still both not met | "
                  "Overshot (both met) | Unclear (incl. reversed) | Reversed | Party-sensitive, Haiku 5.5 voids as wrong |",
                  "|---|---|---|---|---|---|---|---|"]
            for g in G:
                e, w = res["G"][label][g], res["G_haiku_void_wrong"][label][g]
                L.append(f"| {lab[g]} | {e['cells_read']} / {e['cells_valid']} | {pc(e['party_sensitive'])} | "
                         f"{pc(e['still_both_not_met'])} | {pc(e['overshot'])} | {pc(e['unclear_incl_reversed'])} | "
                         f"{pc(e['reversed'])} | {pc(w['party_sensitive'])} |")
            L.append("")
        L += ["Per variant (cells): " + "; ".join(f"{p}{'*' if p in TWO_OF_THREE else ''} " +
              "/".join(str(v[c]) for c in ("party_sensitive", "still_both_not_met", "overshot", "unclear", "reversed"))
              for p, v in res["G"]["per_variant"].items()) + " (party-sensitive/still/overshot/unclear/reversed; * split on "
              "two of three pilot arms)."]
    return "\n".join(L) + "\n"


# ── macros (paper/numbers.tex, own source results/run261_v2.json) ─────────────────
GM = {"NoReasoning": "NoReasoning", "Reasoning": "Reasoning", "Kimi": "KimiKThree"}
KM = {"all": "", "six_domains": "SixDomains", "FixedRule": "FixedRule", "Judgement": "Judgement",
      "judgement_six": "JudgementSix", "education": "Education", "seven_domains": "SevenDomains",
      "judgement_seven": "JudgementSeven"}


def macros(res):
    import macros as M
    src = f"{OUT_JSON}#"
    v = {}

    def share(name, e, path):
        if not e or e.get("share") is None:
            return
        v[name] = {"value": e["share"], "kind": "pct", "source": src + path}
        v[name + "Num"] = {"value": e["num"], "kind": "int", "source": src + path + ".num"}
        v[name + "Den"] = {"value": e["den"], "kind": "int", "source": src + path + ".den"}
        if e.get("ci"):
            v[name + "Lo"] = {"value": e["ci"][0], "kind": "pct", "source": src + path + ".ci0"}
            v[name + "Hi"] = {"value": e["ci"][1], "kind": "pct", "source": src + path + ".ci1"}

    def change(name, d, path):
        if not d or d.get("diff") is None:
            return
        v[name] = {"value": d["diff"], "kind": "pts", "source": src + path}
        if d.get("ci"):
            v[name + "Lo"] = {"value": d["ci"][0], "kind": "pts", "source": src + path + ".ci0"}
            v[name + "Hi"] = {"value": d["ci"][1], "kind": "pts", "source": src + path + ".ci1"}
    cnames = {"split_example": "ExampleSplit", "split_bare": "ExampleBareSplit", "let_through": "ExampleLetThrough",
              "still_rejected_given_split": "ExampleStillRejected"}
    anames = {"A": "SideBySide", "B": "Alone", "C": "ToldPrinciple", "D": "ToldRule", "E": "LetThrough"}
    for g, gm in GM.items():
        for k, km in KM.items():
            for c, cn in cnames.items():
                if k in res["C"][g]:
                    share(f"{cn}{gm}{km}", res["C"][g][k][c], f"C.{g}.{k}.{c}")
                    share(f"{cn}{gm}{km}HaikuVoidWrong", res["C_haiku_void_wrong"][g][k][c], f"C_haiku_void_wrong.{g}.{k}.{c}")
        for c, an in anames.items():
            for k in ("education", "six_domains", "seven_domains", "judgement_six", "judgement_seven"):
                share(f"RunTwoSixOne{an}{gm}{KM[k]}", res["A"][g][c][k], f"A.{g}.{c}.{k}")
        b, f = res["B"]["groups"][g], res["B"]["filter"][g]
        v[f"DirectYesRate{gm}"] = {"value": b["yes_rate_mean"], "kind": "pct", "source": src + f"B.groups.{g}.yes_rate_mean"}
        v[f"DirectYesCells{gm}Num"] = {"value": b["cells_at_least_0_6"], "kind": "int", "source": src + f"B.groups.{g}.cells_at_least_0_6"}
        v[f"DirectYesCells{gm}Den"] = {"value": b["cells"], "kind": "int", "source": src + f"B.groups.{g}.cells"}
        v[f"DirectDigit{gm}"] = {"value": b["digit_mean"], "kind": "f1", "source": src + f"B.groups.{g}.digit_mean"}
        share(f"FilterAloneAll{gm}JudgementSeven", f["alone_judgement_all"], f"B.filter.{g}.alone_judgement_all")
        share(f"FilterAloneSaysDiffer{gm}JudgementSeven", f["alone_judgement_where_direct_says_differ"],
              f"B.filter.{g}.alone_judgement_where_direct_says_differ")
        nd = [O.ARM_LABEL[x.split("|")[0]] + " on " + x.split("|")[1] for x in f["model_domains_say_no_difference"]]
        v[f"NoDifferenceList{gm}"] = {"value": "; ".join(f"\\model{{{x.split(' on ')[0]}}} on {x.split(' on ')[1]}" for x in nd) or "none",
                                      "kind": "str", "source": src + f"B.filter.{g}.model_domains_say_no_difference"}
        # All seven domains (the review, 2026-11-18): the model-domains of DirectYesCells that fall below 0.6, from the
        # per-model-domain yes-rates already in the results (the list above covers judgement domains only).
        pm = res["B"]["per_model_domain"]
        nd7 = [k for k, x in sorted(pm.items()) if k.split("|")[0] in GROUPS[g] and x["yes_rate"] is not None
               and x["yes_rate"] < 0.6]
        v[f"NoDifferenceListAll{gm}"] = {"value": "; ".join(f"\\model{{{O.ARM_LABEL[k.split('|')[0]]}}} on {k.split('|')[1]}"
                                                          for k in nd7) or "none",
                                         "kind": "str", "source": src + "B.per_model_domain"}
        v[f"DirectConfigs{gm}"] = {"value": len(GROUPS[g]), "kind": "int", "source": src + "B.groups (configurations)"}
        # the configurations behind every second-session group figure (Kimi K3 apart): Tables S20, S21, Figure 3
        v[f"SecondSessionConfigs{gm}"] = {"value": len(res["groups"][g]), "kind": "int", "source": src + f"groups.{g}"}
        d = res["D"][g]
        for k, nm in (("rule_orig", "RuleOriginal"), ("rule_new", "RuleNew"), ("example_orig", "ExampleOriginal"),
                      ("example_new", "ExampleNew"), ("ctrl_plain_rule_new_met", "ControlPlainMet"),
                      ("ctrl_outside_norule_new_rejected", "ControlOutsideRejected")):
            share(f"SecondWording{nm}{gm}", d[k], f"D.{g}.{k}")
        change(f"SecondWordingRuleChange{gm}", d["rule_new-rule_orig"], f"D.{g}.rule_new-rule_orig")
        change(f"SecondWordingExampleChange{gm}", d["example_new-example_orig"], f"D.{g}.example_new-example_orig")
        for k in ("FixedRule", "Judgement"):
            e = res["E"][g][k]
            for x, nm in (("uk", "UkLawSplit"), ("base", "UkLawBaseSplit"), ("uk_held_failed", "UkLawHeldFailed"),
                          ("base_held_failed", "UkLawBaseHeldFailed")):
                share(f"{nm}{gm}{k}", e[x], f"E.{g}.{k}.{x}")
            change(f"UkLawChange{gm}{k}", e["uk-base"], f"E.{g}.{k}.uk-base")
        if res.get("G"):
            for lab, sfx in (("all_variants", ""), ("without_two_of_three", "WithoutTwoOfThree")):
                e = res["G"][lab][g]
                for x, nm in (("party_sensitive", "PartySensitive"), ("still_both_not_met", "StillBothNotMet"),
                              ("overshot", "Overshot"), ("unclear_incl_reversed", "Unclear"), ("reversed", "Reversed")):
                    share(f"Milder{nm}{gm}{sfx}", e[x], f"G.{lab}.{g}.{x}")
                v[f"MilderCellsRead{gm}{sfx}"] = {"value": e["cells_read"], "kind": "int", "source": src + f"G.{lab}.{g}.cells_read"}
                share(f"MilderPartySensitive{gm}{sfx}HaikuVoidWrong", res["G_haiku_void_wrong"][lab][g]["party_sensitive"],
                      f"G_haiku_void_wrong.{lab}.{g}.party_sensitive")
    mv = res["E"]["models_moving_more_than_10_points"]
    pm = res["E"]["per_model_fixed_rule"]
    v["UkLawMovers"] = {"value": "; ".join(f"\\model{{{O.ARM_LABEL[a]}}} from {round(100 * pm[a]['base'])}\\% to "
                                            f"{round(100 * pm[a]['uk'])}\\%" for a in mv) or "none",
                        "kind": "str", "source": src + "E.models_moving_more_than_10_points"}
    v["UkLawMoversCount"] = {"value": len(mv), "kind": "word", "source": src + "E.models_moving_more_than_10_points"}
    v["SecondWordingPairs"] = {"value": len(res["D_subset"]), "kind": "int", "source": src + "D_subset"}
    # "the average answer is about N" (§4.2): one whole number for both groups, or refuse
    dr = {round(res["B"]["groups"][g]["digit_mean"]) for g in ("NoReasoning", "Reasoning")}
    if len(dr) != 1:
        raise SystemExit(f"REFUSING: the direct-question means round to different whole numbers: {sorted(dr)}")
    v["DirectDigitRounded"] = {"value": dr.pop(), "kind": "int",
                               "source": src + "B.groups.{NoReasoning,Reasoning}.digit_mean, rounded to a whole number"}
    return v


# ── report ──────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    ap.add_argument("--dry", action="store_true", help="compute and print, write nothing")
    ap.add_argument("--macros", action="store_true", help="write the macros from the written results; nothing else")
    a = ap.parse_args()
    if a.macros:
        import party_difference as PD
        res = json.load(open(os.path.join(ROOT, OUT_JSON)))
        mv = macros(res)
        draft = json.load(open(os.path.join(a.ai, "data/sfv_261/draft_v2.json")))
        ne = len(draft["education"]["pairs"])
        mv["NumPairsEducation"] = {"value": ne, "kind": "word", "source": "data/sfv_261/draft_v2.json#education.pairs"}
        mv["NumPairsAllSeven"] = {"value": len(draft["example_of"]), "kind": "int", "source": "data/sfv_261/draft_v2.json#example_of"}
        n = PD.add_macros(mv, OUT_JSON, own=(OUT_JSON, "data/sfv_261/draft_v2.json"))
        return print(f"run 261 macros into paper/numbers.tex (now {n})")
    for p in (OUT_JSON, OUT_MD):
        if os.path.exists(os.path.join(ROOT, p)) and not a.dry:
            sys.exit(f"write-once: {p} exists")
    r61, g61, r59, draft, pairs = load(a.ai)
    subset = draft["D_subset"]
    resA, tab = block_A(r61, r59, pairs)
    res = {"definitions": __doc__.split("DEFINITIONS")[1].split("BLOCKS")[0].strip(), "groups": {g: list(v) for g, v in GROUPS.items()},
           "A": resA, "B": block_B(r61, tab, pairs), "C": block_C(r61, pairs), "C_haiku_void_wrong": block_C(r61, pairs, worst=True),
           "D": block_D(r61, pairs, subset), "E": block_E(r61, pairs, subset),
           "G": block_G(g61, pairs) if g61 else None, "G_haiku_void_wrong": block_G(g61, pairs, worst=True) if g61 else None,
           "G_arms_read": sorted(g61), "D_subset": subset}
    if a.dry:
        return res
    with open(os.path.join(ROOT, OUT_JSON), "x") as f:
        json.dump(res, f, indent=1, default=lambda x: None)
    with open(os.path.join(ROOT, OUT_MD), "x") as f:
        f.write(markdown(json.loads(json.dumps(res, default=lambda x: None))))
    print(json.dumps({"written": OUT_JSON, "G_arms": len(g61)}))


if __name__ == "__main__":
    main()
