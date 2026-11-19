#!/usr/bin/env python3
"""analyse.py : every registered figure of run 259, and paper/numbers.tex.

    python analysis/analyse.py --selftest
    python analysis/analyse.py --reads DIR --frames FILE --out results/run259.json [--macros]
    python analysis/analyse.py --pilot FILE --frames FILE --out results/dry_run_pilot.json     # dry run on the pilot

Pre-registration: PREREG.md (Amendments 1 and 2). Reads the per-arm files RUN259_READ__<arm>.json written by the
reader (the reader that made the calls; not part of this release); only arms with status READ enter. Nothing here calls a model.

CELLS, AS REGISTERED
  A (side by side): read per order (side_FO, side_OF: each cell's own gate), and POOLED by taking each party's draws
    from both orders together. The pooled cell is valid when its pooled draws meet the definition of a valid cell
    (sampled: at least 80% parsed; reasoning arm: void count at most 10% of its draws). Each party's yes-rate is
    the share of yes among its parsed draws.
  B, C, D: a pair cell is the favoured cell F and the other cell O on one arm, valid when both are valid.
  E: the favoured party bare and with the line, valid when both are valid.
  Split: F >= 0.6 and O <= 0.4 (controls: either direction). Let through (E): bare <= 0.4 and line >= 0.6.
INTERVALS: bootstrap over pairs within domain (each domain's six test pairs resampled with replacement; a sampled
  pair keeps all its arms and conditions), 10,000 resamples, seed 259, 95% percentile; a difference is computed on
  the same resample; by-domain intervals resample that domain's pairs only. Controls are resampled the same way over
  the six control pairs.
ARM SETS: main non-reasoning (H1 to H4 pooled); main reasoning (H5, the five registered arms); additional arms, each
  reported beside by class (off beside the non-reasoning arms; adaptive-high beside the reasoning arms under H5;
  adaptive-default separately), never pooled into H1 to H4.
"""
import argparse, json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))

MAIN_OFF = ("claude", "gpt6s_s", "grok43_s", "gpt4o", "haiku_s", "kimi", "llama70b", "qwen80b", "gpt6l_s",
            "mistral24b", "gemma27b")
MAIN_R = ("grok43_r", "gemini_r", "gpt6s_r", "gpt6l_r", "haiku_r")
PILOT_ARMS = ("claude", "qwen80b")
ADD_CLASS = {"haiku55_off": "off", "sonnet55_off": "off", "haiku55_ah": "adaptive-high",
             "sonnet55_ah": "adaptive-high", "opus55_ad": "adaptive-default", "fable52_ad": "adaptive-default"}
HI, LO, PARSE, VOID = 0.6, 0.4, 0.80, 0.10
B_RESAMPLES, SEED = 10000, 259
DOMAINS = ("insurance", "thresholds", "seniority", "dismissal", "suitability", "vulnerable")
RULE_DOMAINS = ("insurance", "thresholds")


# ── CELL READING ────────────────────────────────────────────────────────────────────
def draw_vals(cell, lab=None):
    """Parsed yes values (1/0, or P(yes)) of a cell's draws; lab for side-by-side."""
    out = []
    for d in cell["draws"]:
        if lab is not None:
            if d.get("parsed"):
                out.append(1.0 if d["parsed"][lab] == "yes" else 0.0)
        elif d.get("p_yes") is not None:
            out.append(d["p_yes"])
        elif d.get("answer") in ("yes", "no"):
            out.append(1.0 if d["answer"] == "yes" else 0.0)
    return out


def valid(cell, reasoning):
    if cell is None:
        return False
    if reasoning and cell.get("n_void", 0) > VOID * cell["n_asked"]:
        return False
    return cell["gate"] == "PASSED"


def mean(v):
    return sum(v) / len(v) if v else None


def side_pooled(cells, labels, reasoning):
    fo, of = cells.get("side_FO"), cells.get("side_OF")
    if fo is None or of is None:
        return None
    n = fo["n_asked"] + of["n_asked"]
    parsed = sum(1 for c in (fo, of) for d in c["draws"] if d.get("parsed"))
    void = sum(c.get("n_void", 0) for c in (fo, of))
    if n == 0 or parsed == 0 or parsed < math.ceil(PARSE * n - 1e-9) or (reasoning and void > VOID * n):
        return None
    return {lab: mean(draw_vals(fo, lab) + draw_vals(of, lab)) for lab in labels}


def split(f, o, control=False):
    if f is None or o is None:
        return False
    s = f >= HI and o <= LO
    return s or (control and o >= HI and f <= LO)


def pair_cells(read, frames):
    """{pair id: {condition: record}} for one arm. Record: {'valid': bool, 'split': bool, ...}."""
    reasoning = read.get("reasoning", False)
    out = {}
    for uk, u in read["units"].items():
        cond, pid = uk.split("|")
        fl, ol = u["labels"]
        c = u["cells"]
        rec = out.setdefault(pid, {})
        if cond == "A":
            for k in ("side_FO", "side_OF"):
                if k in c:
                    v = valid(c[k], reasoning)
                    yr = c[k]["yes_rate"]
                    rec["A_" + k[-2:]] = {"valid": v, "F": yr[fl] if v else None, "O": yr[ol] if v else None,
                                          "split": v and split(yr[fl], yr[ol], u["control"])}
            p = side_pooled(c, (fl, ol), reasoning)
            rec["A"] = {"valid": p is not None, "F": p and p[fl], "O": p and p[ol],
                        "split": p is not None and split(p[fl], p[ol], u["control"])}
        elif cond in "BCD":
            v = valid(c.get("F"), reasoning) and valid(c.get("O"), reasoning)
            f, o = (c["F"]["yes_rate"], c["O"]["yes_rate"]) if v else (None, None)
            rec[cond] = {"valid": v, "F": f, "O": o, "split": v and split(f, o, u["control"]),
                         "F_valid": valid(c.get("F"), reasoning), "O_valid": valid(c.get("O"), reasoning),
                         "F_raw": c["F"]["yes_rate"] if "F" in c else None,
                         "O_raw": c["O"]["yes_rate"] if "O" in c else None}
        elif cond == "E":
            v = valid(c.get("bare"), reasoning) and valid(c.get("line"), reasoning)
            b, l = (c["bare"]["yes_rate"], c["line"]["yes_rate"]) if v else (None, None)
            rec["E"] = {"valid": v, "bare": b, "line": l, "let": v and b <= LO and l >= HI,
                        "subject": u.get("subject"), "line_valid": valid(c.get("line"), reasoning),
                        "line_yes": c["line"]["yes_rate"] if "line" in c else None}
    return out


# ── MEASURES: per pair, (numerator, denominator) summed over the arms of a set ───────
class ArmCounts(dict):
    """{pid: (num, den)} summed over arms, as before; .by_arm keeps {arm: {pid: (num, den)}} so that a bootstrap can
    resample models as well as pairs (analysis instruction after review, 2026-11-16)."""
    by_arm = None


def counts(tables, arms, pids, fn):
    """fn(rec) -> (num, den) for one pair on one arm. Returns {pid: (num, den)} (an ArmCounts)."""
    out = ArmCounts()
    out.by_arm = {a: {} for a in arms}
    for pid in pids:
        n = d = 0
        for a in arms:
            r = tables[a].get(pid)
            x = fn(r) if r is not None else (0, 0)
            out.by_arm[a][pid] = (x[0], x[1])
            n += x[0]; d += x[1]
        out[pid] = (n, d)
    return out


def m_split(cond):
    return lambda r: (int(r[cond]["split"]), int(r[cond]["valid"])) if cond in r else (0, 0)


def m_split_orders(r):
    """Amendment 2: each order its own cell (one prompt, one cell)."""
    n = d = 0
    for k in ("A_FO", "A_OF"):
        if k in r:
            n += r[k]["split"]; d += r[k]["valid"]
    return n, d


def m_let(subject=None, among_bare_low=False):
    def f(r):
        e = r.get("E")
        if e is None or not e["valid"] or (subject and e["subject"] != subject):
            return 0, 0
        if among_bare_low and e["bare"] > LO:
            return 0, 0
        return int(e["let"]), 1
    return f


def m_secondary(subject=None):
    """Amendment 1: among pair-arm cells with D favoured valid and >= 0.6 and E-with-line valid, share E line >= 0.6."""
    def f(r):
        d, e = r.get("D"), r.get("E")
        if d is None or e is None or (subject and e["subject"] != subject):
            return 0, 0
        if not (d["F_valid"] and d["F_raw"] is not None and d["F_raw"] >= HI and e["line_valid"]):
            return 0, 0
        return int(e["line_yes"] >= HI), 1
    return f


class Boot:
    def __init__(self, by_domain, n=B_RESAMPLES, seed=SEED):
        rng = random.Random(seed)
        self.by_domain = by_domain
        self.samples = []
        for _ in range(n):
            s = []
            for dom in DOMAINS:
                ps = by_domain.get(dom, [])
                s.extend(rng.choice(ps) for _ in ps)
            self.samples.append(s)

    @staticmethod
    def share(c, pids):
        n = sum(c[p][0] for p in pids if p in c)
        d = sum(c[p][1] for p in pids if p in c)
        return n / d if d else None

    def ci(self, fn):
        vals = sorted(v for v in (fn(s) for s in self.samples) if v is not None)
        if not vals:
            return None
        return [vals[int(0.025 * (len(vals) - 1))], vals[int(math.ceil(0.975 * (len(vals) - 1)))]]

    def est(self, c, pids_all):
        pt = self.share(c, pids_all)
        return {"share": pt, "num": sum(c[p][0] for p in pids_all), "den": sum(c[p][1] for p in pids_all),
                "ci": self.ci(lambda s: self.share(c, s))}

    def diff(self, c1, c2, pids_all):
        a, b = self.share(c1, pids_all), self.share(c2, pids_all)
        pt = None if a is None or b is None else a - b

        def f(s):
            x, y = self.share(c1, s), self.share(c2, s)
            return None if x is None or y is None else x - y
        return {"diff": pt, "ci": self.ci(f)}


def domain_boot(pids, dom_of, n=B_RESAMPLES):
    by = {}
    for p in pids:
        by.setdefault(dom_of[p], []).append(p)
    return Boot(by, n)


def by_domain(tables, arms, pids, dom_of, fn, n):
    out = {}
    for dom in DOMAINS:
        ps = [p for p in pids if dom_of[p] == dom]
        if not ps:
            continue
        b = Boot({dom: ps}, n)
        out[dom] = b.est(counts(tables, arms, ps, fn), ps)
    return out


# ── THE ANALYSIS ────────────────────────────────────────────────────────────────────
def analyse(reads, frames, n_boot=B_RESAMPLES):
    tables = {a: pair_cells(r, frames) for a, r in reads.items()}
    info = {p["id"]: p for p in frames["pairs"]}
    tests = [p["id"] for p in frames["pairs"]]
    ctrls = sorted({u["pair"] for u in frames["units"].values() if u["control"]})
    dom_of = {u["pair"]: u["domain"] for u in frames["units"].values()}
    boot, cboot = domain_boot(tests, dom_of, n_boot), domain_boot(ctrls, dom_of, n_boot)
    present = set(reads)
    off = [a for a in MAIN_OFF if a in present]
    rsn = [a for a in MAIN_R if a in present]
    res = {"arms_read": sorted(present), "main_off": off, "main_reasoning": rsn,
           "arms_registered_not_read": sorted(set(MAIN_OFF + MAIN_R) - present),
           "additional": {a: ADD_CLASS[a] for a in sorted(present & set(ADD_CLASS))}}

    def C(arms, fn, pids=tests):
        return counts(tables, arms, pids, fn)

    def block(arms, b=boot, pids=tests):
        """The condition shares and the registered contrasts for one arm set."""
        cA, cB, cC, cD = (C(arms, m_split(k), pids) for k in "ABCD")
        cFO, cOF, cOrd = C(arms, m_split("A_FO"), pids), C(arms, m_split("A_OF"), pids), C(arms, m_split_orders, pids)
        out = {k: b.est(c, pids) for k, c in (("A", cA), ("A_FO", cFO), ("A_OF", cOF), ("A_orders", cOrd),
                                               ("B", cB), ("C", cC), ("D", cD))}
        out["A_minus_B"] = b.diff(cA, cB, pids)
        out["Aorders_minus_B"] = b.diff(cOrd, cB, pids)
        out["C_minus_B"] = b.diff(cC, cB, pids)
        out["D_minus_B"] = b.diff(cD, cB, pids)
        out["D_minus_C"] = b.diff(cD, cC, pids)
        cl, cs, cdf = C(arms, m_let(), pids), C(arms, m_let("same"), pids), C(arms, m_let("different"), pids)
        out["E_let"] = b.est(cl, pids)
        out["E_let_same"], out["E_let_different"] = b.est(cs, pids), b.est(cdf, pids)
        out["E_same_minus_different"] = b.diff(cs, cdf, pids)
        out["E_let_among_bare_low"] = b.est(C(arms, m_let(among_bare_low=True), pids), pids)
        s2 = {k: C(arms, m_secondary(k), pids) for k in (None, "same", "different")}
        out["E_secondary"] = {"pooled": b.est(s2[None], pids), "same": b.est(s2["same"], pids),
                              "different": b.est(s2["different"], pids),
                              "same_minus_different": b.diff(s2["same"], s2["different"], pids),
                              "by_domain": by_domain(tables, arms, pids, dom_of, m_secondary(), n_boot)}
        out["by_domain"] = {k: by_domain(tables, arms, pids, dom_of, fn, n_boot)
                            for k, fn in (("A", m_split("A")), ("B", m_split("B")), ("C", m_split("C")),
                                          ("D", m_split("D")), ("E_let", m_let()), ("A_orders", m_split_orders))}
        return out

    def ctrl_block(arms):
        return {k: cboot.est(C(arms, m_split(k), ctrls), ctrls) for k in "ABCD"}

    def h_verdicts(x, ctrl):
        A, B, Cc, D = x["A"]["share"], x["B"]["share"], x["C"]["share"], x["D"]["share"]
        lo = lambda d: d["ci"][0] if d["ci"] else None
        v = {}
        dAB = x["A_minus_B"]
        v["H1"] = {"side_ge_60": A is not None and A >= 0.60, "alone_le_25": B is not None and B <= 0.25,
                   "diff_ge_35": dAB["diff"] is not None and dAB["diff"] >= 0.35,
                   "ci_excludes_zero": lo(dAB) is not None and lo(dAB) > 0}
        v["H2a"] = {"diff_ge_20": x["C_minus_B"]["diff"] is not None and x["C_minus_B"]["diff"] >= 0.20,
                    "ci_excludes_zero": lo(x["C_minus_B"]) is not None and lo(x["C_minus_B"]) > 0}
        v["H2b"] = {"D_ge_60": D is not None and D >= 0.60,
                    "diff_ge_35": x["D_minus_B"]["diff"] is not None and x["D_minus_B"]["diff"] >= 0.35}
        v["H3"] = {"above_zero": x["D_minus_C"]["diff"] is not None and x["D_minus_C"]["diff"] > 0,
                   "ci_excludes_zero": lo(x["D_minus_C"]) is not None and lo(x["D_minus_C"]) > 0}
        v["H4"] = {"share_ge_25": x["E_let"]["share"] is not None and x["E_let"]["share"] >= 0.25,
                   "same_higher": x["E_same_minus_different"]["diff"] is not None
                   and x["E_same_minus_different"]["diff"] > 0}
        for h in v:
            v[h]["PASSED"] = all(v[h].values())
        ctl = {k: c["share"] is not None and c["share"] <= 0.05 for k, c in ctrl.items()}
        rests = {"H1": "AB", "H2a": "BC", "H2b": "BD", "H3": "CD", "H4": "D"}
        for h, conds in rests.items():
            bad = [k for k in conds if not ctl.get(k, True)]
            v[h]["uninterpretable_controls"] = bad
        return v, ctl

    # main non-reasoning: H1 to H4
    main = block(off)
    ctrl = ctrl_block(off)
    verdicts, ctl_ok = h_verdicts(main, ctrl)
    res["H"] = {"main_off": main, "controls": ctrl, "controls_le_5pct": ctl_ok, "verdicts": verdicts}
    ex = [a for a in off if a not in PILOT_ARMS]
    mx = block(ex)
    res["H1_excluding_pilot_arms"] = {"arms": ex, "A": mx["A"], "B": mx["B"], "A_minus_B": mx["A_minus_B"],
                                      "verdict": h_verdicts(mx, ctrl_block(ex))[0]["H1"]}
    # Amendment 2: per-order cells, pooled and by arm, and the one-order description
    res["A2_orders_as_cells"] = {"pooled": {"A_orders": main["A_orders"], "B": main["B"],
                                            "Aorders_minus_B": main["Aorders_minus_B"]},
                                 "by_arm": {}}
    res["A2_one_order_splits"] = {}
    per_arm = {}
    for a in sorted(present):
        x = block([a])
        per_arm[a] = {k: x[k] for k in ("A", "A_FO", "A_OF", "A_orders", "B", "C", "D", "E_let", "E_let_same",
                                       "E_let_different", "E_let_among_bare_low", "A_minus_B", "C_minus_B",
                                       "D_minus_B", "D_minus_C", "E_secondary")}
        per_arm[a]["controls"] = ctrl_block([a])
        res["A2_orders_as_cells"]["by_arm"][a] = {"A_orders": x["A_orders"], "B": x["B"],
                                                  "Aorders_minus_B": x["Aorders_minus_B"]}
        one = [p for p in tests if all(k in tables[a].get(p, {}) and tables[a][p][k]["valid"] for k in ("A_FO", "A_OF"))
               and tables[a][p]["A_FO"]["split"] != tables[a][p]["A_OF"]["split"]]
        res["A2_one_order_splits"][a] = {"n_pairs": len(one), "pairs": one,
                                         "n_pairs_both_orders_valid": sum(
                                             all(k in tables[a].get(p, {}) and tables[a][p][k]["valid"]
                                                 for k in ("A_FO", "A_OF")) for p in tests)}
    res["per_arm"] = per_arm
    # H5: the five reasoning arms pooled, and per arm; H2a, H2b, H4 for them
    if rsn:
        r5 = block(rsn)
        b = r5["B"]["share"]
        reading = None if b is None else ("restores" if b >= 0.60 else "does not" if b <= 0.30 else "partly")
        v5, _ = h_verdicts(r5, ctrl_block(rsn))
        res["H5"] = {"arms": rsn, "B": r5["B"], "reading": reading, "A": r5["A"], "C": r5["C"], "D": r5["D"],
                     "H2a": {**r5["C_minus_B"], **v5["H2a"]}, "H2b": {"D": r5["D"], **r5["D_minus_B"], **v5["H2b"]},
                     "H4": {"E_let": r5["E_let"], "same_minus_different": r5["E_same_minus_different"], **v5["H4"]},
                     "controls": ctrl_block(rsn),
                     "per_arm": {a: {"B": per_arm[a]["B"], "reading": None if per_arm[a]["B"]["share"] is None else
                                     ("restores" if per_arm[a]["B"]["share"] >= 0.60 else "does not"
                                      if per_arm[a]["B"]["share"] <= 0.30 else "partly")} for a in rsn}}
    # additional arms: beside, by class; thought shares for adaptive arms
    res["additional_arms"] = {}
    for a, cls in res["additional"].items():
        x = {"class": cls, **{k: per_arm[a][k] for k in ("A", "B", "C", "D", "E_let", "A_minus_B")}}
        if cls != "off":
            x["H5_reading"] = per_arm[a]["B"]["share"] is not None and (
                "restores" if per_arm[a]["B"]["share"] >= 0.60 else "does not"
                if per_arm[a]["B"]["share"] <= 0.30 else "partly")
        x["thought"] = thought_stats(reads[a], frames)
        res["additional_arms"][a] = x
    # who is wronged (descriptive): domains 1 and 2, alone bare, by arm
    res["who_is_wronged"] = {}
    for a in sorted(present):
        fv = [tables[a][p]["B"] for p in tests if dom_of[p] in RULE_DOMAINS and "B" in tables[a].get(p, {})]
        fa = [r["F_raw"] for r in fv if r["F_valid"]]
        oa = [r["O_raw"] for r in fv if r["O_valid"]]
        res["who_is_wronged"][a] = {"favoured_below_half": (sum(x < 0.5 for x in fa) / len(fa)) if fa else None,
                                    "n_favoured": len(fa),
                                    "other_half_or_above": (sum(x >= 0.5 for x in oa) / len(oa)) if oa else None,
                                    "n_other": len(oa)}
    # excluded cells, per arm and condition
    res["excluded_cells"] = excluded(reads)
    res["calls"] = {a: r.get("calls") for a, r in reads.items()}
    res["spent_usd"] = {a: r.get("spent_usd") for a, r in reads.items()}
    res["served_model"] = {a: r.get("served_model") for a, r in reads.items()}
    res["served_model_constant"] = {a: r.get("served_model_constant") for a, r in reads.items()}
    return res


def excluded(reads):
    out = {}
    for a, r in reads.items():
        reasoning = r.get("reasoning", False)
        t = {}
        for uk, u in r["units"].items():
            cond = uk.split("|")[0]
            for k, c in u["cells"].items():
                s = t.setdefault(cond, {"cells": 0, "excluded": 0, "void_excluded": 0})
                s["cells"] += 1
                if not valid(c, reasoning):
                    s["excluded"] += 1
                    s["void_excluded"] += c.get("gate") == "EXCLUDED_VOID" or (
                        reasoning and c.get("n_void", 0) > VOID * c["n_asked"])
        out[a] = t
    return out


def thought_stats(read, frames):
    """Share of calls that thought; split shares from draws that thought and from draws that did not (descriptive)."""
    calls = th = 0
    for u in read["units"].values():
        for c in u["cells"].values():
            for d in c["draws"]:
                if "thinking_tokens" in d:
                    calls += 1; th += d["thinking_tokens"] > 0
    out = {"calls": calls, "share_thought": th / calls if calls else None}
    for which in (True, False):
        sub = {"units": {}, "reasoning": read.get("reasoning", False)}
        for uk, u in read["units"].items():
            cells = {}
            for k, c in u["cells"].items():
                ds = [d for d in c["draws"] if (d.get("thinking_tokens", 0) > 0) == which]
                vals = (draw_vals({"draws": ds}, None) if not k.startswith("side") else
                        [d for d in ds if d.get("parsed")])
                cc = dict(c, draws=ds, n_asked=len(ds), n_void=sum(1 for d in ds if d.get("void")),
                          gate="PASSED" if vals else "FAILED")
                if k.startswith("side"):
                    cc["yes_rate"] = {lab: mean(draw_vals({"draws": ds}, lab)) for lab in c["labels"]}
                else:
                    cc["yes_rate"] = mean(vals)
                cells[k] = cc
            sub["units"][uk] = {**{kk: vv for kk, vv in u.items() if kk != "cells"}, "cells": cells}
        t = pair_cells(sub, frames)
        tests = [p["id"] for p in frames["pairs"]]
        o = {}
        for cond in "ABCD":
            n = sum(t[p][cond]["split"] for p in tests if cond in t.get(p, {}))
            dd = sum(t[p][cond]["valid"] for p in tests if cond in t.get(p, {}))
            o[cond] = {"share": n / dd if dd else None, "num": n, "den": dd}
        out["thought" if which else "did_not_think"] = o
    out["note"] = ("descriptive only: a sub-cell uses only the draws that thought (or did not) and is counted when "
                   "each party has at least one parsed such draw")
    return out


# ── MACROS ──────────────────────────────────────────────────────────────────────────
def macros(res, src):
    import macros as M
    v = {}
    names = {"A": "Side", "B": "Bare", "C": "Standard", "D": "Line"}

    def put(name, value, kind, key):
        if value is not None:
            v[name] = {"value": value, "kind": kind, "source": f"{src}#{key}"}
    m = res["H"]["main_off"]
    for k, nm in names.items():
        put(f"Main{nm}Share", m[k]["share"], "pct", f"H.main_off.{k}.share")
        if m[k]["ci"]:
            put(f"Main{nm}Lo", m[k]["ci"][0], "pct", f"H.main_off.{k}.ci.0")
            put(f"Main{nm}Hi", m[k]["ci"][1], "pct", f"H.main_off.{k}.ci.1")
    for k, nm in (("A_minus_B", "SideMinusBare"), ("C_minus_B", "StandardMinusBare"), ("D_minus_B", "LineMinusBare"),
                  ("D_minus_C", "LineMinusStandard"), ("E_same_minus_different", "SameMinusDifferent"),
                  ("Aorders_minus_B", "OrdersMinusBare")):
        put(f"Main{nm}", m[k]["diff"], "pts", f"H.main_off.{k}.diff")
        if m[k]["ci"]:
            put(f"Main{nm}Lo", m[k]["ci"][0], "pts", f"H.main_off.{k}.ci.0")
            put(f"Main{nm}Hi", m[k]["ci"][1], "pts", f"H.main_off.{k}.ci.1")
    for k, nm in (("A_FO", "SideFO"), ("A_OF", "SideOF"), ("A_orders", "SideOrders"), ("E_let", "LetThrough"),
                  ("E_let_same", "LetSame"), ("E_let_different", "LetDifferent"), ("E_let_among_bare_low", "LetBareLow")):
        put(f"Main{nm}Share", m[k]["share"], "pct", f"H.main_off.{k}.share")
    put("MainSecondaryShare", m["E_secondary"]["pooled"]["share"], "pct", "H.main_off.E_secondary.pooled.share")
    for h, nm in (("H1", "HOne"), ("H2a", "HTwoA"), ("H2b", "HTwoB"), ("H3", "HThree"), ("H4", "HFour")):
        put(f"{nm}Verdict", "passed" if res["H"]["verdicts"][h]["PASSED"] else "failed", "str", f"H.verdicts.{h}.PASSED")
    x = res["H1_excluding_pilot_arms"]
    put("ExPilotSideShare", x["A"]["share"], "pct", "H1_excluding_pilot_arms.A.share")
    put("ExPilotBareShare", x["B"]["share"], "pct", "H1_excluding_pilot_arms.B.share")
    if "H5" in res:
        put("ReasBareShare", res["H5"]["B"]["share"], "pct", "H5.B.share")
        put("ReasReading", res["H5"]["reading"], "str", "H5.reading")
    put("NArmsMain", len(res["main_off"]), "int", "main_off")
    put("NArmsReasoning", len(res["main_reasoning"]), "int", "main_reasoning")
    calls = sum(c or 0 for c in res["calls"].values())
    put("NCalls", calls, "int", "calls")
    return v


def write_macros(res, src):
    import macros as M
    return M.write_macros(macros(res, src))


# ── INPUTS ──────────────────────────────────────────────────────────────────────────
def load_reads(d):
    out, skipped = {}, {}
    for f in sorted(os.listdir(d)):
        if f.startswith("RUN259_READ__") and f.endswith(".json"):
            r = json.load(open(os.path.join(d, f)))
            if r.get("status") == "READ":
                out[r["arm"]] = r
            else:
                skipped[r["arm"]] = r.get("unread_reason")
    return out, skipped


def pilot_as_reads(pilot, frames):
    """The pilot's condition-A draws in the reader's format (dry run only)."""
    out = {}
    U = frames["units"]
    for arm, a in pilot["arms"].items():
        units = {}
        for pid, p in a["pairs"].items():
            u = U[f"A|{pid}"]
            fl, ol = u["labels"]
            cells = {}
            for k, c in p["cells"].items():
                ds = [{"text": d["text"], "parsed": d["parsed"]} for d in c["draws"]]
                vals = [d for d in ds if d["parsed"]]
                cells[k] = {"key": k, "n_asked": len(ds), "n_parsed": len(vals), "n_void": 0, "draws": ds,
                            "gate": "PASSED" if len(vals) >= math.ceil(PARSE * len(ds) - 1e-9) else "FAILED",
                            "labels": [fl, ol],
                            "yes_rate": {lab: mean(draw_vals({"draws": ds}, lab)) for lab in (fl, ol)}}
            units[f"A|{pid}"] = {**{kk: vv for kk, vv in u.items() if kk != "prompts"}, "cells": cells}
        out[arm] = {"arm": arm, "status": "READ", "reasoning": False, "units": units, "calls": None}
    return out


# ── SELFTEST: OPENS AND REFUSES ─────────────────────────────────────────────────────
def _fake_reads(frames, arms, rule):
    """rule(arm, cond, pid, key, control) -> yes value for every draw."""
    out = {}
    for a in arms:
        reasoning = a in MAIN_R or ADD_CLASS.get(a, "off") != "off"
        n = 5 if reasoning else 10
        units = {}
        for uk, u in frames["units"].items():
            cond, pid = uk.split("|")
            fl, ol = u["labels"]
            cells = {}
            for k in u["prompts"]:
                if k.startswith("side"):
                    yf, yo = rule(a, cond, pid, "F", u["control"]), rule(a, cond, pid, "O", u["control"])
                    ds = [{"parsed": {fl: "yes" if yf else "no", ol: "yes" if yo else "no"},
                           "thinking_tokens": 10} for _ in range(n)]
                    cells[k] = {"key": k, "n_asked": n, "n_void": 0, "gate": "PASSED", "draws": ds, "labels": [fl, ol],
                                "yes_rate": {fl: float(yf), ol: float(yo)}}
                else:
                    y = rule(a, cond, pid, k, u["control"])
                    ds = [{"answer": "yes" if y else "no", "thinking_tokens": 0} for _ in range(n)]
                    cells[k] = {"key": k, "n_asked": n, "n_void": 0, "gate": "PASSED", "draws": ds, "yes_rate": float(y)}
            units[uk] = {**{kk: vv for kk, vv in u.items() if kk != "prompts"}, "cells": cells}
        out[a] = {"arm": a, "status": "READ", "reasoning": reasoning, "units": units, "calls": 1}
    return out


def selftest(frames_path):
    frames = json.load(open(frames_path))
    ok = 0
    arms = MAIN_OFF + MAIN_R + ("haiku55_ah",)

    # the claims hold: splits side by side, none alone bare, C and D restore, every E let through, controls flat
    def good(a, cond, pid, k, control):
        if control:
            return True
        if cond == "A":
            return k == "F"
        if cond == "B":
            return True
        if cond in "CD":
            return k == "F"
        return k == "line"
    r = analyse(_fake_reads(frames, arms, good), frames, n_boot=200)
    v = r["H"]["verdicts"]
    assert r["H"]["main_off"]["A"]["share"] == 1.0 and r["H"]["main_off"]["B"]["share"] == 0.0
    assert v["H1"]["PASSED"] and v["H2a"]["PASSED"] and v["H2b"]["PASSED"] and v["H4"]["share_ge_25"]
    assert not v["H3"]["PASSED"]                       # D equals C: not above zero
    assert r["H"]["controls_le_5pct"] == {k: True for k in "ABCD"} and r["H5"]["reading"] == "does not"
    assert r["H"]["main_off"]["E_let"]["den"] == 36 * 11 and r["H"]["main_off"]["E_secondary"]["pooled"]["share"] == 1.0
    assert r["additional_arms"]["haiku55_ah"]["thought"]["share_thought"] == 84 / 408
    ok += 1
    # refuses: nothing splits side by side, and controls that split make every hypothesis uninterpretable
    r = analyse(_fake_reads(frames, arms, lambda a, c, p, k, ctl: k == "F"), frames, n_boot=200)
    v = r["H"]["verdicts"]
    assert r["H"]["main_off"]["B"]["share"] == 1.0 and not v["H1"]["PASSED"] and not v["H2a"]["PASSED"]
    assert r["H"]["controls_le_5pct"]["A"] is False and v["H1"]["uninterpretable_controls"] == ["A", "B"]
    ok += 1
    # the order measure: favoured yes only when listed second splits one order only; pooled does not split
    def order(a, cond, pid, k, control):
        return good(a, cond, pid, k, control)
    reads = _fake_reads(frames, ("qwen80b",), order)
    for uk, u in reads["qwen80b"]["units"].items():
        if uk.startswith("A|") and not u["control"]:
            fl, ol = u["labels"]
            c = u["cells"]["side_FO"]
            for d in c["draws"]:
                d["parsed"] = {fl: "no", ol: "no"}
            c["yes_rate"] = {fl: 0.0, ol: 0.0}
    r = analyse(reads, frames, n_boot=200)
    assert r["A2_one_order_splits"]["qwen80b"]["n_pairs"] == 36
    assert r["per_arm"]["qwen80b"]["A"]["share"] == 0.0 and r["per_arm"]["qwen80b"]["A_orders"]["share"] == 0.5
    ok += 1
    # a void on a reasoning arm excludes the cell
    reads = _fake_reads(frames, ("grok43_r",), good)
    reads["grok43_r"]["units"]["B|I1"]["cells"]["F"]["n_void"] = 1
    r = analyse(reads, frames, n_boot=200)
    assert r["excluded_cells"]["grok43_r"]["B"]["excluded"] == 1 and r["per_arm"]["grok43_r"]["B"]["den"] == 35
    ok += 1
    print(f"selftest {ok}/4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads")
    ap.add_argument("--pilot")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out")
    ap.add_argument("--macros", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.frames)
    frames = json.load(open(a.frames))
    if a.pilot:
        reads, skipped = pilot_as_reads(json.load(open(a.pilot)), frames), {}
    else:
        reads, skipped = load_reads(a.reads)
    res = analyse(reads, frames)
    res["unread_arms"] = skipped
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if os.path.exists(a.out):
        sys.exit(f"write-once: {a.out} exists")
    with open(a.out, "x") as f:
        json.dump(res, f, indent=1)
    v = res["H"]["verdicts"]
    m = res["H"]["main_off"]
    fmt = lambda e: "n/a" if e.get("share") is None else f"{e['share']:.3f} ({e['num']}/{e['den']})"
    print(f"arms read {len(reads)}: {', '.join(sorted(reads))}")
    for k in ("A", "A_FO", "A_OF", "A_orders", "B", "C", "D", "E_let"):
        print(f"  {k:9s} {fmt(m[k])}  ci {m[k]['ci']}")
    for h in ("H1", "H2a", "H2b", "H3", "H4"):
        print(f"  {h:4s} {'PASSED' if v[h]['PASSED'] else 'failed'}  {v[h]}")
    if a.macros:
        sys.exit("REFUSING: paper/numbers.tex is now written by analysis/outcomes.py (macros named by what they "
                 "measure); results/run259.json is unaffected")
        n = write_macros(res, os.path.relpath(a.out, ROOT))
        print(f"wrote {n} macros to paper/numbers.tex")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
