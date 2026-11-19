#!/usr/bin/env python3
"""outcomes.py : what the models do in run 259, condition by condition, with intervals; the numbers behind the paper's figures; the
cut-off robustness table; and run 260's control follow-up beside run 259's controls. Writes results/OUTCOMES.md,
results/outcomes_run259.json and paper/numbers.tex (macros named by what they measure; provenance in
paper/numbers.json). No new calls. At its end it calls analysis/party_difference.py's apply() and analysis/wrong_kinds.py's apply(),
because writing numbers.tex from scratch would otherwise drop their macros (the first also rewrites
paper/numbers_exploratory.tex).

    python analysis/outcomes.py --reads DIR --frames FILE [--controls results/controls_run260.json] [--items FILE]

Definitions (as analysis/analyse.py, whose cell reading this reuses):
  split: the yes-rate of the party held to less at least 0.6 and the other party's at most 0.4. A side-by-side cell pools both
    orders' draws; "party held to less first" and "second" are the two orders read as cells of their own.
  let through (beyond the line): the failing's yes-rate at most 0.4 read bare and at least 0.6 with the line stated.
  still cleared: among cases the line clears (the party held to less at least 0.6 with the line), the share still at least 0.6
    once the failing is added (with the line).
  wrong verdicts (insurance and thresholds, alone bare): against the party held to less, its yes-rate below 0.5; in the
    other party's favour, its yes-rate 0.5 or above.
  intervals: bootstrap over pairs within domain, 10,000 resamples, seed 259, 95% percentile (as analyse.py).
  cut-off robustness: a single 0.5 cut-off in place of 0.6 / 0.4: a verdict is yes above 0.5 and no below it, so a
    split needs the party held to less above 0.5 and the other below 0.5 (a rate of exactly 0.5 does not split).
"""
import argparse, json, math, os, random, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                            # noqa: E402
import macros as M                                             # noqa: E402

NR, RS = A.MAIN_OFF, A.MAIN_R
ADD = ("haiku55_off", "sonnet55_off", "haiku55_ah", "opus55_ad")
# The paper's two groups: the Claude 5.5 models join the group their setting belongs to.
NO_R = NR + ("sonnet55_off", "haiku55_off")
WITH_R = RS + ("haiku55_ah", "opus55_ad")
GROUPS = {"NoReasoning": NO_R, "Reasoning": WITH_R}
REF_GROUPS = {"MainNoReasoning": NR, "MainReasoning": RS}       # the earlier 11 / 5 grouping, kept for reference
ALL_GROUPS = {**GROUPS, **REF_GROUPS}
GROUP_LABEL = {"NoReasoning": "Without reasoning (13 models)", "Reasoning": "With reasoning (7 models)",
               "MainNoReasoning": "Earlier grouping: the 11 main models without reasoning",
               "MainReasoning": "Earlier grouping: the 5 main models with reasoning"}
ARM_LABEL = {"claude": "Claude Sonnet 5", "gpt6s_s": "GPT-6 Sol", "grok43_s": "Grok 4.3", "gpt4o": "GPT-4o",
             "haiku_s": "Claude Haiku 4.5", "kimi": "Kimi K3", "llama70b": "Llama 3.3 70B",
             "qwen80b": "Qwen3-Next-80B", "gpt6l_s": "GPT-6 Luna", "mistral24b": "Mistral Small 3.2 24B",
             "gemma27b": "Gemma 3 27B", "sonnet55_off": "Claude Sonnet 5.5 (thinking off)",
             "haiku55_off": "Claude Haiku 5.5 (thinking off)", "grok43_r": "Grok 4.3 (reasoning)",
             "gemini_r": "Gemini 3.8 Flash (reasoning)", "gpt6s_r": "GPT-6 Sol (reasoning)",
             "gpt6l_r": "GPT-6 Luna (reasoning)", "haiku_r": "Claude Haiku 4.5 (reasoning)",
             "haiku55_ah": "Claude Haiku 5.5 (max effort)", "opus55_ad": "Claude Opus 5.5 (default effort)"}
ADD_LABEL = {a: ARM_LABEL[a] for a in ADD}
ARM_MACRO = {"claude": "ClaudeSonnetFive", "gpt6s_s": "GptSixSol", "grok43_s": "GrokFourThree", "gpt4o": "GptFourO",
             "haiku_s": "ClaudeHaikuFourFive", "kimi": "KimiKThree", "llama70b": "LlamaSeventyB",
             "qwen80b": "QwenEightyB", "gpt6l_s": "GptSixLuna", "mistral24b": "MistralTwentyFourB",
             "gemma27b": "GemmaTwentySevenB", "grok43_r": "GrokFourThreeReasoning",
             "gemini_r": "GeminiFlashReasoning", "gpt6s_r": "GptSixSolReasoning", "gpt6l_r": "GptSixLunaReasoning",
             "haiku_r": "ClaudeHaikuFourFiveReasoning", "haiku55_off": "HaikuFiveFiveOff",
             "sonnet55_off": "SonnetFiveFiveOff", "haiku55_ah": "HaikuFiveFiveMaxEffort",
             "opus55_ad": "OpusFiveFiveDefaultEffort"}
FIXED, JUDGEMENT = ("insurance", "thresholds"), ("seniority", "dismissal", "suitability", "vulnerable")
DOMSETS = {"": A.DOMAINS, "FixedRule": FIXED, "Judgement": JUDGEMENT, **{d.capitalize(): (d,) for d in A.DOMAINS}}
KINDS = (("FixedRule", "fixed-rule cases"), ("Judgement", "judgement cases"))
DOM_LABEL = {"insurance": "Insurance disclosure", "thresholds": "Statutory thresholds", "seniority": "Seniority",
             "dismissal": "Dismissal procedure", "suitability": "Suitability of advice",
             "vulnerable": "Vulnerable customers"}
MEASURES = [  # (key, macro name, label, fn factory)
    ("A", "SideBySide", "side by side (both orders pooled)", lambda: A.m_split("A")),
    ("A_FO", "SideBySideHeldToLessFirst", "side by side, party held to less first", lambda: A.m_split("A_FO")),
    ("A_OF", "SideBySideHeldToLessSecond", "side by side, party held to less second", lambda: A.m_split("A_OF")),
    ("A_orders", "SideBySideOrdersAsCells", "side by side, each order its own cell", lambda: A.m_split_orders),
    ("B", "Alone", "alone", lambda: A.m_split("B")),
    ("C", "ToldPrinciple", "alone, told in principle", lambda: A.m_split("C")),
    ("D", "ToldRule", "alone, told a precise rule", lambda: A.m_split("D")),
    ("E", "LetThrough", "outside the rule: let through", lambda: A.m_let()),
    ("E_same", "LetThroughSameSubject", "let through, failing on the rule's own subject", lambda: A.m_let("same")),
    ("E_diff", "LetThroughOtherSubject", "let through, failing on another subject", lambda: A.m_let("different")),
    ("E_still", "StillCleared", "still cleared once the failing is added", lambda: A.m_secondary()),
    ("E_still_same", "StillClearedSameSubject", "still cleared, own subject", lambda: A.m_secondary("same")),
    ("E_still_diff", "StillClearedOtherSubject", "still cleared, another subject", lambda: A.m_secondary("different")),
]
DIFFS = [("C", "B", "ToldPrincipleMinusAlone"), ("D", "B", "ToldRuleMinusAlone"),
         ("D", "C", "ToldRuleMinusToldPrinciple"), ("A", "B", "SideBySideMinusAlone")]
COND4 = (("A", "Side by side"), ("B", "Alone"), ("C", "Alone, told in principle"), ("D", "Alone, told a precise rule"))
# Figure 3's display rules, defined here so the caption's numbers come from numbers.tex
FIG3 = {"band_green": 0.95, "band_amber": 0.80, "rank_from": 0.50}
CONFIDENCE = 0.95
# the macros that move together under the vocabulary of 2026-11-13: old fragment -> new fragment, applied in order
RENAME = [("CutHalf", "CutoffHalf"), ("WrongAgainstProtected", "ProtectedWronglyFailed"),
          ("ProtectedWronglyFailed", "HeldToLessWronglyFailed"), ("SideBySideProtected", "SideBySideHeldToLess"),
          ("WrongForOther", "OtherWronglyPassed"), ("LineLetThrough", "LetThrough"), ("LineStillCleared", "StillCleared"),
          ("StandardStated", "ToldPrinciple"), ("LineStated", "ToldRule"), ("AloneBare", "Alone"),
          ("NonReasoning", "NoReasoning"), ("RuleFixed", "FixedRule"), ("StandardsDomains", "Judgement"),
          ("NumArms", "NumModels"), ("NumCallsRunMain", "NumCalls")]
B_RESAMPLES, SEED = 10000, 259


def wilson(k, n, z=1.959964):
    """Wilson score interval for k of n; used only where the bootstrap interval is degenerate (zero width)."""
    if not n:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [min(max(0.0, c - h), p), max(min(1.0, c + h), p)]


ARM_SEED = SEED + 1


class FastBoot:
    """Pairs resampled within domain (analyse.Boot's resamples: same generator, same order) and, where a figure pools
    more than one model, MODELS resampled with replacement too, independently (seed 260, one set of draws per set of
    models, so two figures over the same models share their model draws and a difference stays paired). A share is
    the resampled cells' numerator over their denominator. Where the interval is degenerate (zero width), a Wilson
    interval on the cell count replaces it and the estimate is flagged ci_method = "wilson"."""
    def __init__(self, by_domain, n=B_RESAMPLES, seed=SEED, models=True):
        rng = random.Random(seed)
        self.n, self.models = n, models
        self.pids = [p for d in A.DOMAINS for p in by_domain.get(d, [])]
        ix = {p: i for i, p in enumerate(self.pids)}
        rows = []
        for _ in range(n):
            s = []
            for dom in A.DOMAINS:
                ps = by_domain.get(dom, [])
                s.extend(ix[rng.choice(ps)] for _ in ps)
            rows.append(s)
        self.idx = np.array(rows)
        P = len(self.pids)
        self.V = np.zeros((n, P))
        for r in range(n):
            self.V[r] = np.bincount(self.idx[r], minlength=P)
        self._W = {}

    def _arm_weights(self, arms):
        key = tuple(arms)
        if key not in self._W:
            rng = np.random.default_rng([ARM_SEED, len(arms)] + [sum(map(ord, a)) for a in arms])
            draws = rng.integers(0, len(arms), size=(self.n, len(arms)))
            W = np.zeros((self.n, len(arms)))
            for r in range(self.n):
                W[r] = np.bincount(draws[r], minlength=len(arms))
            self._W[key] = W
        return self._W[key]

    def _arr(self, c):
        return (np.array([c[p][0] for p in self.pids], float), np.array([c[p][1] for p in self.pids], float))

    def _resampled(self, c):
        """(N, D) per resample: pairs (and models, when the counts carry more than one model)."""
        ba = getattr(c, "by_arm", None)
        if self.models and ba and len(ba) > 1:
            arms = sorted(ba)
            Nm = np.array([[ba[a][p][0] for p in self.pids] for a in arms], float)
            Dm = np.array([[ba[a][p][1] for p in self.pids] for a in arms], float)
            W = self._arm_weights(arms)
            return ((W @ Nm) * self.V).sum(1), ((W @ Dm) * self.V).sum(1)
        n, d = self._arr(c)
        return n[self.idx].sum(1), d[self.idx].sum(1)

    @staticmethod
    def _ci(v):
        v = np.sort(v[~np.isnan(v)])
        if not len(v):
            return None
        return [float(v[int(0.025 * (len(v) - 1))]), float(v[int(math.ceil(0.975 * (len(v) - 1)))])]

    def _shares(self, c):
        n, d = self._arr(c)
        N, D = self._resampled(c)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(D > 0, N / np.where(D > 0, D, 1), np.nan), n.sum(), d.sum()

    def est(self, c):
        s, n, d = self._shares(c)
        ci, how = self._ci(s), "bootstrap"
        if ci is not None and d and ci[1] - ci[0] < 1e-12:
            ci, how = wilson(n, d), "wilson"
        return {"share": (n / d) if d else None, "num": int(n), "den": int(d), "ci": ci, "ci_method": how}

    def diff(self, c1, c2):
        s1, n1, d1 = self._shares(c1)
        s2, n2, d2 = self._shares(c2)
        return {"diff": (n1 / d1 - n2 / d2) if d1 and d2 else None, "ci": self._ci(s1 - s2)}




def compute(reads, frames, hi=0.6, lo=0.4, n=B_RESAMPLES, with_arms=True):
    saved = A.HI, A.LO
    A.HI, A.LO = hi, lo
    try:
        tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
        tests = [p["id"] for p in frames["pairs"]]
        dom_of = {p["id"]: p["domain"] for p in frames["pairs"]}
        boots = {ds: FastBoot({d: [p for p in tests if dom_of[p] == d] for d in doms}, n) for ds, doms in DOMSETS.items()}
        present = set(reads)
        sets = {g: [a for a in arms if a in present] for g, arms in ALL_GROUPS.items()}
        if with_arms:
            sets.update({a: [a] for a in sorted(present)})
        out = {}
        for name, arms in sets.items():
            if not arms:
                continue
            per = {}
            for ds, b in boots.items():
                cs = {k: A.counts(tables, arms, b.pids, f()) for k, _, _, f in MEASURES}
                e = {k: b.est(cs[k]) for k in cs}
                e.update({f"{x}-{y}": b.diff(cs[x], cs[y]) for x, y, _ in DIFFS})
                per[ds] = e
            out[name] = per
        return out, tables
    finally:
        A.HI, A.LO = saved


def wrongful(tables, frames, n=B_RESAMPLES):
    tests = [p["id"] for p in frames["pairs"] if p["domain"] in A.RULE_DOMAINS]
    b = FastBoot({d: [p for p in tests if p[0] == d[0].upper()] for d in A.RULE_DOMAINS}, n)
    fav = lambda r: (int(r["B"]["F_raw"] < 0.5), 1) if "B" in r and r["B"]["F_valid"] else (0, 0)
    oth = lambda r: (int(r["B"]["O_raw"] >= 0.5), 1) if "B" in r and r["B"]["O_valid"] else (0, 0)
    out = {}
    for name, arm_list in [(g, [a for a in arms if a in tables]) for g, arms in ALL_GROUPS.items()] + \
                          [(a, [a]) for a in tables]:
        out[name] = {"against_held_to_less": b.est(A.counts(tables, arm_list, b.pids, fav)),
                     "for_other": b.est(A.counts(tables, arm_list, b.pids, oth))}
    return out


def one_order(tables, frames):
    tests = [p["id"] for p in frames["pairs"]]
    out = {}
    for a, t in tables.items():
        both = [p for p in tests if all(k in t.get(p, {}) and t[p][k]["valid"] for k in ("A_FO", "A_OF"))]
        one = [p for p in both if t[p]["A_FO"]["split"] != t[p]["A_OF"]["split"]]
        first = [p for p in one if t[p]["A_FO"]["split"]]
        out[a] = {"pairs_both_orders_valid": len(both), "split_one_order_only": len(one),
                  "only_when_first": len(first), "only_when_second": len(one) - len(first), "pairs": one}
    for g, arms in ALL_GROUPS.items():
        xs = [out[a] for a in arms if a in out]
        out[g] = {k: sum(x[k] for x in xs) for k in ("pairs_both_orders_valid", "split_one_order_only",
                                                       "only_when_first", "only_when_second")}
    return out


def excluded(reads):
    out = {}
    for a, r in reads.items():
        reasoning = r.get("reasoning", False)
        t = {}
        for uk, u in r["units"].items():
            cond = uk.split("|")[0]
            s = t.setdefault(cond, {"cells": 0, "parse_below_80pct": 0, "yes_no_mass_below_070": 0,
                                    "truncation_void": 0})
            for c in u["cells"].values():
                s["cells"] += 1
                if reasoning and c.get("n_void", 0) > A.VOID * c["n_asked"]:
                    s["truncation_void"] += 1
                elif c["gate"] == "FAILED":
                    s["yes_no_mass_below_070" if c.get("readout") == "logprob" else "parse_below_80pct"] += 1
        out[a] = t
    return out


def thought(reads):
    out = {}
    for a in ADD:
        if a not in reads:
            continue
        calls = th = 0
        for u in reads[a]["units"].values():
            for c in u["cells"].values():
                for d in c["draws"]:
                    if "thinking_tokens" in d:
                        calls += 1; th += d["thinking_tokens"] > 0
        out[a] = {"calls": calls, "thought": th, "share": th / calls if calls else None}
    return out


CONSENSUS_FROM = 5          # "split by at least five of the seven"
NUM_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}


def consensus(tables, frames, n=B_RESAMPLES):
    """Judgement cases: for each pair, how many of the models with reasoning split it side by side in the designed
    direction (both orders pooled), out of those with a valid side-by-side cell. Added after the outcomes
    were read."""
    arms = [a for a in GROUPS["Reasoning"] if a in tables]
    pairs = [p for p in frames["pairs"] if p["domain"] in JUDGEMENT]
    per = {}
    for p in pairs:
        recs = {a: tables[a].get(p["id"], {}).get("A") for a in arms}
        valid = [a for a, r in recs.items() if r and r["valid"]]
        per[p["id"]] = {"domain": p["domain"], "split": sum(recs[a]["split"] for a in valid), "valid": len(valid),
                        "models_split": [a for a in valid if recs[a]["split"]],
                        "models_not_split": [a for a in valid if not recs[a]["split"]],
                        "models_invalid": [a for a in arms if a not in valid]}
    dist = {k: sum(1 for x in per.values() if x["split"] == k) for k in range(len(arms) + 1)}
    b = FastBoot({d: [p["id"] for p in pairs if p["domain"] == d] for d in JUDGEMENT}, n)
    share = b.est({pid: (int(x["split"] >= CONSENSUS_FROM), 1) for pid, x in per.items()})
    return {"models": arms, "per_pair": per, "distribution": dist, "at_least": CONSENSUS_FROM, "share_at_least": share,
            "fewer_than_four": [pid for pid, x in per.items() if x["split"] < 4]}


def cutoff_change(main, half):
    """Largest absolute change, in share, between the 0.6 / 0.4 definition and a single 0.5 cut-off, over the figures
    the paper reports for its two groups: Figure 2 (four conditions x fixed-rule and judgement cases), the six-domain
    pooled shares of the same four conditions, and Figure 4 (let through, all failings and by subject)."""
    best = None
    for g in GROUPS:
        for ds in ("", "FixedRule", "Judgement"):
            for k in ("A", "B", "C", "D") + (("E", "E_same", "E_diff") if ds == "" else ()):
                a, b = main[g][ds][k]["share"], half[g][ds][k]["share"]
                if a is None or b is None:
                    continue
                if best is None or abs(b - a) > best["abs_change"]:
                    best = {"abs_change": abs(b - a), "group": g, "domains": ds or "all", "measure": k,
                            "main": a, "cutoff_half": b}
    return best


# ── MARKDOWN ────────────────────────────────────────────────────────────────────────
def pc(e):
    if e is None or e.get("share") is None:
        return "n/a"
    ci = e["ci"]
    return (f"{100 * e['share']:.1f}% [{100 * ci[0]:.1f}, {100 * ci[1]:.1f}] ({e['num']}/{e['den']})" if ci
            else f"{100 * e['share']:.1f}% ({e['num']}/{e['den']})")


def pt(e):
    if e is None or e.get("diff") is None:
        return "n/a"
    ci = e["ci"]
    return f"{100 * e['diff']:+.1f} [{100 * ci[0]:+.1f}, {100 * ci[1]:+.1f}]" if ci else f"{100 * e['diff']:+.1f}"


def table(header, rows):
    s = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    return s + "".join("| " + " | ".join(r) + " |\n" for r in rows)


def kinds_table(o, groups):
    rows = []
    for g in groups:
        for ds, lab in KINDS:
            rows.append([GROUP_LABEL[g], lab] + [pc(o[g][ds][k]) for k, _ in COND4])
    return table(["Models", "Cases"] + [lab for _, lab in COND4], rows)


def let_table(o, names):
    rows = []
    for g in names:
        e = o[g][""]
        rows.append([GROUP_LABEL.get(g) or ARM_LABEL[g], pc(e["E"]), pc(e["E_same"]), pc(e["E_diff"]), pc(e["E_still"]),
                     pc(e["E_still_same"]), pc(e["E_still_diff"])])
    return table(["Models", "Let through", "Rule's own subject", "Another subject",
                  "Still cleared once the failing is added", "Still cleared, own subject",
                  "Still cleared, another subject"], rows)


def markdown(res, reads):
    o, rob, w, oo, ex, th = (res[k] for k in ("main", "cut_half", "wrong_verdicts", "one_order", "excluded", "thought"))
    arms_in = lambda arms: [a for a in arms if a in o]
    order = arms_in(NO_R) + arms_in(WITH_R)
    out = ["# Run 259: outcomes\n",
           "What the models do, condition by condition. Every figure is a share of cells with its 95% interval "
           "(bootstrap over pairs within domain, 10,000 resamples) and its count. A cell is one pair on one model. "
           "Generated by `analysis/outcomes.py` from the run's responses; no new calls. Vocabulary as in the paper; "
           "the prompts and responses are quoted as read.\n",
           "**Groups of models.** *Without reasoning* (13): " + ", ".join(ARM_LABEL[a] for a in NO_R) + ". "
           "*With reasoning* (7): " + ", ".join(ARM_LABEL[a] for a in WITH_R) + ". Section 1.4 keeps the earlier "
           "grouping (the 11 and 5 main models, with the four Claude 5.5 models apart) for reference.\n",
           "**Vocabulary.** *Fixed-rule cases*: insurance disclosure and statutory thresholds, where a rule of law "
           "fixes the correct verdict. *Judgement cases*: seniority, dismissal procedure, suitability of advice and "
           "vulnerable customers. *Side by side*: both parties in one prompt; *alone*: one party's file on its own; "
           "*told in principle*: one sentence before the case saying in general terms which party is held to more; "
           "*told a precise rule*: the same content as a precise rule that decides the case by a fact the case "
           "states.\n",
           "**Definitions.** A pair *splits* (the party is treated correctly) when the yes-rate of the party held to "
           "less is at least 0.6 and the other party's at most 0.4. The party held to less is the householder, the company "
           "below the statutory size threshold, the junior analyst, the small employer, the firm advising a "
           "professional client, and the firm dealing with an ordinary customer. Side by side pools both orders "
           "unless an order is named. A failing *outside the rule* is *let through* when it is judged not to meet "
           "the standard alone (yes-rate at most 0.4) and to meet it once the precise rule is given (at least "
           "0.6).\n"]
    out.append("## 1. The figures the paper rests on\n")
    out.append("### 1.1 Fixed-rule cases against judgement cases\n")
    out.append(kinds_table(o, GROUPS))
    out.append("\nDifferences in percentage points (same resample):\n")
    rows = []
    for g in GROUPS:
        for ds, lab in (("", "all six domains"),) + KINDS:
            rows.append([GROUP_LABEL[g], lab] + [pt(o[g][ds][f"{x}-{y}"]) for x, y, _ in DIFFS])
    out.append(table(["Models", "Cases", "Told in principle minus alone", "Told a precise rule minus alone",
                      "Told a precise rule minus told in principle", "Side by side minus alone"], rows))
    out.append("\nAll six domains pooled:\n")
    out.append(table(["Models"] + [lab for _, lab in COND4],
                     [[GROUP_LABEL[g]] + [pc(o[g][""][k]) for k, _ in COND4] for g in GROUPS]))
    out.append("\n### 1.2 Wrong verdicts in fixed-rule cases (each file alone)\n")
    out.append("Insurance disclosure and statutory thresholds, where the law fixes the verdict: the party held to less "
               "meets its standard and the other party does not. Party held to less, wrongly judged not to meet it: its "
               "yes-rate below 0.5. Other party wrongly held to meet it: its yes-rate 0.5 or above.\n")
    rows = [[GROUP_LABEL[g] + " (pooled)", pc(w[g]["against_held_to_less"]), pc(w[g]["for_other"])] for g in GROUPS]
    rows += [[ARM_LABEL[a], pc(w[a]["against_held_to_less"]), pc(w[a]["for_other"])] for a in order]
    out.append(table(["Models", "Party held to less, wrongly judged not to meet its standard",
                      "Other party wrongly held to meet it"], rows))
    out.append("\n### 1.3 What a precise rule lets through\n")
    out.append(let_table(o, list(GROUPS)))
    out.append("\nBy model:\n\n" + let_table(o, order))
    cs = res["consensus"]
    out.append("\n### 1.4 Judgement cases: how many models with reasoning split each pair side by side\n")
    out.append(f"For each of the {len(cs['per_pair'])} judgement-case pairs, the number of the {len(cs['models'])} "
               "models with reasoning that split it side by side in the designed direction (both orders pooled), out of "
               "those whose side-by-side cell is valid. Added after the outcomes were read.\n")
    out.append(table(["Models splitting the pair", "Pairs"], [[str(k), str(v)] for k, v in cs["distribution"].items()]))
    out.append(f"\nPairs split by at least {cs['at_least']} of {len(cs['models'])}: {pc(cs['share_at_least'])}. Pairs "
               f"split by fewer than four: {', '.join(cs['fewer_than_four']) or 'none'}.\n")
    rows = [[pid, DOM_LABEL[x["domain"]], f"{x['split']} of {x['valid']}",
             ", ".join(ARM_LABEL[a] for a in x["models_not_split"]) or "none",
             ", ".join(ARM_LABEL[a] for a in x["models_invalid"]) or "none"] for pid, x in cs["per_pair"].items()]
    out.append("\n" + table(["Pair", "Domain", "Split by", "Not split by", "Cell not valid"], rows))
    out.append("\n### 1.5 For reference: the earlier grouping\n")
    out.append("The figures of the outcomes written on 2026-11-12, on the 11 main models without reasoning and the 5 "
               "main models with reasoning, the four Claude 5.5 models not pooled.\n")
    out.append(kinds_table(o, REF_GROUPS))
    out.append("\n" + table(["Models"] + [lab for _, lab in COND4],
                            [[GROUP_LABEL[g] + ", all six domains"] + [pc(o[g][""][k]) for k, _ in COND4]
                             for g in REF_GROUPS]))
    rows = [[GROUP_LABEL[g], pc(w[g]["against_held_to_less"]), pc(w[g]["for_other"])] for g in REF_GROUPS]
    out.append("\n" + table(["Models", "Party held to less, wrongly judged not to meet its standard",
                             "Other party wrongly held to meet it"], rows))
    out.append("\n" + let_table(o, list(REF_GROUPS)))
    out.append("\n## 2. By condition\n")
    for k, lab in COND4 + (("E", "Outside the rule: let through"),):
        out.append(f"### {lab}\n")
        rows = [[GROUP_LABEL[g], pc(o[g][""][k])] + [pc(o[g][ds][k]) for ds, _ in KINDS] +
                [pc(o[g][d.capitalize()][k]) for d in A.DOMAINS] for g in GROUPS]
        hdr = ["Models", "All six", "Fixed-rule", "Judgement"] + [DOM_LABEL[d] for d in A.DOMAINS]
        out.append(table(hdr, rows))
        rows = [[ARM_LABEL[a], pc(o[a][""][k])] + [pc(o[a][ds][k]) for ds, _ in KINDS] +
                [pc(o[a][d.capitalize()][k]) for d in A.DOMAINS] for a in order]
        out.append("\nBy model:\n\n" + table(hdr, rows) + "\n")
    out.append("### Order, side by side\n")
    rows = []
    for g in list(GROUPS) + order:
        e = o[g][""]
        lab = GROUP_LABEL[g] + " (pooled)" if g in GROUPS else ARM_LABEL[g]
        x = oo.get(g)
        rows.append([lab, pc(e["A_FO"]), pc(e["A_OF"]), pc(e["A_orders"]),
                     f"{x['split_one_order_only']} of {x['pairs_both_orders_valid']} "
                     f"({x['only_when_first']} first, {x['only_when_second']} second)" if x else ""])
    out.append(table(["Models", "Party held to less first", "Party held to less second", "Each order its own cell",
                      "Pairs split in one order only"], rows))
    out.append("\n## 3. The Claude 5.5 models: calls that thought\n")
    out.append("Each is pooled with the group its setting belongs to (thinking off: without reasoning; max effort "
               "and default effort: with reasoning).\n")
    rows = [[ARM_LABEL[a], f"{100 * th[a]['share']:.1f}% ({th[a]['thought']}/{th[a]['calls']})"] +
            [pc(o[a][""][k]) for k in "ABCDE"] for a in ADD if a in o]
    out.append(table(["Model", "Calls that thought", "Side by side", "Alone", "Told in principle",
                      "Told a precise rule", "Let through"], rows))
    out.append("\n## 4. Robustness: a single 0.5 cut-off\n")
    out.append("The same responses with a split counted when the yes-rate of the party held to less is above 0.5 and the "
               "other's below 0.5 (and let through when alone is below 0.5 and with the precise rule above 0.5).\n")
    rows = []
    for g in ALL_GROUPS:
        for ds, dl in (("", "all six"),) + KINDS:
            for k, lab in COND4 + ((("E", "Let through"),) if ds == "" else ()):
                rows.append([GROUP_LABEL[g], dl, lab, pc(o[g][ds][k]), pc(rob[g][ds][k])])
    out.append(table(["Models", "Cases", "Condition", "0.6 / 0.4 (the definition used)", "Single 0.5 cut-off"], rows))
    cc = res["cutoff_change"]
    out.append(f"\nLargest change over the figures the paper reports for its two groups: "
               f"{100 * cc['abs_change']:.1f} points ({GROUP_LABEL[cc['group']]}, {cc['domains']}, "
               f"{dict((k, l) for k, _, l, _ in MEASURES)[cc['measure']]}: {100 * cc['main']:.1f}% against "
               f"{100 * cc['cutoff_half']:.1f}%).\n")
    if res.get("controls"):
        c = res["controls"]
        out.append("\n## 5. Verdicts flipped by the day of the week alone\n")
        out.append("A control pair is one case read twice, differing only in the day of the week. A cell *flips* when "
                   "one day's yes-rate is at least 0.6 and the other's at most 0.4. Read on the 11 main models "
                   "without reasoning only.\n")
        p = c["run260"]["pooled"]
        rows = [["Run 260, 18 new control pairs, alone", pc({"share": p["flip_share"], "num": p["n_flip"],
                                                            "den": p["n_valid"], "ci": p["ci"]}),
                 f"{p['mean_abs_diff']:.3f} [{p['mean_abs_diff_ci'][0]:.3f}, {p['mean_abs_diff_ci'][1]:.3f}]"]]
        for cond, lab in (("A", "side by side"), ("B", "alone"), ("C", "alone, told in principle"),
                          ("D", "alone, told a precise rule")):
            q = c["run259"][cond]["pooled"]
            rows.append([f"Run 259, six control pairs, {lab}", pc({"share": q["flip_share"], "num": q["n_flip"],
                                                                 "den": q["n_valid"], "ci": q["ci"]}),
                         f"{q['mean_abs_diff']:.3f}"])
        q = c["alone_bare_both_runs"]["pooled"]
        rows.append(["Both runs, alone (24 pairs)", pc({"share": q["flip_share"], "num": q["n_flip"],
                                                        "den": q["n_valid"], "ci": q["ci"]}),
                     f"{q['mean_abs_diff']:.3f} [{q['mean_abs_diff_ci'][0]:.3f}, {q['mean_abs_diff_ci'][1]:.3f}]"])
        out.append(table(["Cells", "Flipped", "Mean absolute difference in yes-rate"], rows))
        rows = [[ARM_LABEL[a], pc({"share": v["flip_share"], "num": v["n_flip"], "den": v["n_valid"], "ci": v["ci"]}),
                 f"{v['mean_abs_diff']:.3f}"] for a, v in c["run260"]["by_arm"].items()]
        out.append("\nRun 260 by model:\n\n" + table(["Model", "Flipped", "Mean absolute difference"], rows))
        if res.get("settled"):
            st = res["settled"]
            u, f = st["run260"]["unsettled"] + st["run259"]["B"]["unsettled"], \
                st["run260"]["flips_among_unsettled"] + st["run259"]["B"]["flips_among_unsettled"]
            out.append(f"\nHow clear-cut the controls were (`results/controls_run260_settled.json`; a cell is settled "
                       f"when both days are at most 0.1 or both at least 0.9): read alone, {u} cells across both runs "
                       f"were not settled, and {f} of them flipped. See `OUTCOMES_controls_addendum.md`.\n")
        if res.get("items"):
            out.append("\nThe 18 control pairs (Tuesday shown; the other reading has Thursday):\n")
            rows = [[it["id"], DOM_LABEL[it["domain"]], "held to less" if it["party"] == "favoured" else "other",
                     it["text"]] for it in res["items"]["items"]]
            out.append(table(["Pair", "Domain", "Party", "Case"], rows))
    out.append("\n## 6. Excluded cells\n")
    out.append("A cell is excluded when under 80% of its draws parsed, when its mean yes + no probability mass is "
               "below 0.70 (log-probability models), or, on models with reasoning, when any of its five draws ran "
               "out of tokens. Conditions: A side by side, B alone, C told in principle, D told a precise rule, E "
               "outside the rule.\n")
    rows = []
    for a in order:
        if a not in ex:
            continue
        t = ex[a]
        tot = {k: sum(v[k] for v in t.values()) for k in ("cells", "parse_below_80pct", "yes_no_mass_below_070",
                                                          "truncation_void")}
        by = "; ".join(f"{c}: {sum(v for k, v in t[c].items() if k != 'cells')}" for c in "ABCDE"
                       if c in t and sum(v for k, v in t[c].items() if k != 'cells'))
        rows.append([ARM_LABEL[a], str(tot["cells"]), str(tot["parse_below_80pct"]), str(tot["yes_no_mass_below_070"]),
                     str(tot["truncation_void"]), by or "none"])
    out.append(table(["Model", "Cells", "Under 80% parsed", "Mass below 0.70", "Out of tokens", "By condition"], rows))
    return "\n".join(out) + "\n"


BANNED = [r"\bline\b", r"\blines\b", r"bright line", r"stated standard", r"standard stated", r"standards domain",
          r"beyond the line", r"line stated", r"rule-fixed", r"\bH[1-5]\b", r"hypothes", r"pre-?regist",
          r"protected party", r"\bprotected\b", r"\bstandards\b", r"\bconventions?\b",
          r"\bpassed\b", r"\bfailed\b"]


def vocabulary_hits(text, case_texts=()):
    """Banned words outside the quoted case texts (which are data and stay as read)."""
    import re
    for t in case_texts:
        text = text.replace(t, "")
    text = re.sub(r"statutory (size )?threshold", "", text, flags=re.I)
    hits = [b for b in BANNED + [r"threshold"] if re.search(b, text, flags=re.I)]
    return hits


# ── MACROS ──────────────────────────────────────────────────────────────────────────
def build_macros(res, src, settled=None, settled_src=None, old=None, regrouped=True):
    """regrouped: the old names were computed on the earlier 11 / 5 grouping (false once they are already on the
    two groups, so a value that is unchanged is reported as such)."""
    v, group_level = {}, set()

    def put(name, value, kind, key, note=None, source=None):
        if value is not None:
            v[name] = {"value": value, "kind": kind, "source": source or f"{src}#{key}", **({"note": note} if note else {})}

    def share(name, e, key):
        if e and e.get("share") is not None:
            put(name, e["share"], "pct", key + ".share")
            put(name + "Num", e["num"], "int", key + ".num")
            put(name + "Den", e["den"], "int", key + ".den")
            if e["ci"]:
                put(name + "Lo", e["ci"][0], "pct", key + ".ci.0")
                put(name + "Hi", e["ci"][1], "pct", key + ".ci.1")

    o = res["main"]
    names = list(GROUPS) + [a for a in o if a not in ALL_GROUPS]
    for g in names:
        gname = g if g in GROUPS else ARM_MACRO[g]
        before = set(v)
        for ds, e in o[g].items():
            for k, mname, _, _ in MEASURES:
                share(f"{mname}{gname}{ds}", e[k], f"main.{g}.{ds or 'all'}.{k}")
            if ds in ("", "FixedRule", "Judgement"):
                for x, y, mname in DIFFS:
                    d = e[f"{x}-{y}"]
                    put(f"{mname}{gname}{ds}", d["diff"], "pts", f"main.{g}.{ds or 'all'}.{x}-{y}.diff")
                    if d["ci"]:
                        put(f"{mname}{gname}{ds}Lo", d["ci"][0], "pts", f"main.{g}.{ds or 'all'}.{x}-{y}.ci.0")
                        put(f"{mname}{gname}{ds}Hi", d["ci"][1], "pts", f"main.{g}.{ds or 'all'}.{x}-{y}.ci.1")
        if g in GROUPS:
            group_level |= set(v) - before
    for g in GROUPS:
        before = set(v)
        for ds in ("", "FixedRule", "Judgement"):
            for k, mname, _, _ in MEASURES:
                share(f"CutoffHalf{mname}{g}{ds}", res["cut_half"][g][ds][k], f"cut_half.{g}.{ds or 'all'}.{k}")
        group_level |= set(v) - before
    cc = res["cutoff_change"]
    put("CutoffMaxChange", cc["abs_change"], "ptsu", "cutoff_change.abs_change",
        note="largest absolute change, in percentage points, between the 0.6 / 0.4 definition and a single 0.5 cut-off "
             "over Figure 2, the six-domain pooled shares of its four conditions and Figure 4, both groups "
             f"(here {cc['group']}, {cc['domains']}, {cc['measure']})")
    group_level.add("CutoffMaxChange")
    for n, e in res["wrong_verdicts"].items():
        if n in REF_GROUPS:
            continue
        gname = n if n in GROUPS else ARM_MACRO[n]
        before = set(v)
        share(f"HeldToLessWronglyFailed{gname}", e["against_held_to_less"], f"wrong_verdicts.{n}.against_held_to_less")
        share(f"OtherWronglyPassed{gname}", e["for_other"], f"wrong_verdicts.{n}.for_other")
        if n in GROUPS:
            group_level |= set(v) - before
    for a, x in res["one_order"].items():
        if a in REF_GROUPS:
            continue
        put(f"PairsSplitOneOrderOnly{a if a in GROUPS else ARM_MACRO[a]}", x["split_one_order_only"], "int",
            f"one_order.{a}.split_one_order_only")
        if a in GROUPS:
            group_level.add(f"PairsSplitOneOrderOnly{a}")
    for a, x in res["thought"].items():
        put(f"CallsThought{ARM_MACRO[a]}", x["share"], "pct", f"thought.{a}.share")
    # the skeleton's order placeholders name no group: they are the models without reasoning
    for side in ("First", "Second"):
        base = f"SideBySideHeldToLess{side}NoReasoning"
        for suf in ("", "Num", "Den", "Lo", "Hi"):
            if base + suf in v:
                put(f"SideBySideHeldToLess{side}{suf}", v[base + suf]["value"], v[base + suf]["kind"], None,
                    note=f"the skeleton's name; same number as {base}{suf} (models without reasoning)",
                    source=v[base + suf]["source"])
                group_level.add(f"SideBySideHeldToLess{side}{suf}")
    cs = res["consensus"]
    share("JudgementConsensusShare", cs["share_at_least"], "consensus.share_at_least")
    put("JudgementConsensusFrom", cs["at_least"], "int", "consensus.at_least")
    put("JudgementConsensusModels", len(cs["models"]), "int", "consensus.models")
    put("JudgementConsensusFewerThanFour", len(cs["fewer_than_four"]), "int", "consensus.fewer_than_four")
    for k, c in cs["distribution"].items():
        n = int(k)                  # the keys are strings once the results have been through JSON
        put(f"JudgementConsensusPairsSplitBy{NUM_WORD.get(n, 'Zero' if n == 0 else 'Seven')}", c, "int",
            f"consensus.distribution.{k}")
    for pid, x in cs["per_pair"].items():
        tag = pid[0] + NUM_WORD[int(pid[1:])]
        put(f"JudgementConsensusSplit{tag}", x["split"], "int", f"consensus.per_pair.{pid}.split")
        put(f"JudgementConsensusValid{tag}", x["valid"], "int", f"consensus.per_pair.{pid}.valid")
    b = o["NoReasoning"][""]["B"]["share"]
    put("OneInN", round(1 / b), "int", "main.NoReasoning.all.B.share",
        note="one case in N: the reciprocal of AloneNoReasoning (all six domains), rounded to a whole number")
    group_level.add("OneInN")
    if res.get("controls"):
        c = res["controls"]

        def ctl(name, e, key):
            share(name, {"share": e["flip_share"], "num": e["n_flip"], "den": e["n_valid"], "ci": e["ci"]}, key)
            put(name + "MeanAbsDiff", e["mean_abs_diff"], "f3", key + ".mean_abs_diff")
        ctl("DayFlipNewControls", c["run260"]["pooled"], "controls.run260.pooled")
        for a, e in c["run260"]["by_arm"].items():
            ctl(f"DayFlipNewControls{ARM_MACRO[a]}", e, f"controls.run260.by_arm.{a}")
        for cond, nm in (("A", "SideBySide"), ("B", "Alone"), ("C", "ToldPrinciple"), ("D", "ToldRule")):
            ctl(f"DayFlipFirstRunControls{nm}", c["run259"][cond]["pooled"], f"controls.run259.{cond}.pooled")
        ctl("DayFlipAloneBothRuns", c["alone_bare_both_runs"]["pooled"], "controls.alone_bare_both_runs.pooled")
        for suf in ("", "Num", "Den", "Lo", "Hi", "MeanAbsDiff"):
            x = v.get("DayFlipAloneBothRuns" + suf)
            if x:
                put("DayFlipAllControls" + suf, x["value"], x["kind"], None, source=x["source"],
                    note=f"the skeleton's name; same number as DayFlipAloneBothRuns{suf}: the control pairs of both "
                         "runs read alone, the 11 main models without reasoning")
        n_pairs = len(c["run260"]["cells"][next(iter(c["run260"]["cells"]))]) + 6
        put("ControlPairsTotal", n_pairs, "int", "controls.run260.cells",
            note="the 18 control pairs of run 260 plus the 6 of run 259 (one per domain)")
    if settled:
        st = settled
        u = st["run260"]["unsettled"] + st["run259"]["B"]["unsettled"]
        f = st["run260"]["flips_among_unsettled"] + st["run259"]["B"]["flips_among_unsettled"]
        ss = settled_src
        put("DayFlipUnsettled", f / u, "pct", None, source=f"{ss}#(run260+run259.B).flips_among_unsettled / unsettled",
            note="control cells read alone, both runs, that were not settled (both days at most 0.1 or both at least "
                 "0.9): the share that flipped")
        put("DayFlipUnsettledNum", f, "int", None, source=f"{ss}#run260.flips_among_unsettled+run259.B.flips_among_unsettled")
        put("DayFlipUnsettledDen", u, "int", None, source=f"{ss}#run260.unsettled+run259.B.unsettled")
        put("DayFlipNewControlsCells", st["run260"]["cells"], "int", None, source=f"{ss}#run260.cells")
        put("DayFlipNewControlsUnsettled", st["run260"]["unsettled"], "int", None, source=f"{ss}#run260.unsettled")
        put("DayFlipNewControlsSettled", st["run260"]["cells"] - st["run260"]["unsettled"], "int", None,
            source=f"{ss}#run260.cells-run260.unsettled")
    put("NumModelsNoReasoning", len(GROUPS["NoReasoning"]), "int", None, source="analysis/outcomes.py#GROUPS.NoReasoning")
    put("NumModelsReasoning", len(GROUPS["Reasoning"]), "int", None, source="analysis/outcomes.py#GROUPS.Reasoning")
    put("NumModels", len(GROUPS["NoReasoning"]) + len(GROUPS["Reasoning"]), "int", None,
        source="analysis/outcomes.py#GROUPS")
    put("NumDomains", len(res["domains"]), "int", "domains")
    put("NumDomainsWord", len(res["domains"]), "word", "domains")
    put("ModelsTotal", len(GROUPS["NoReasoning"]) + len(GROUPS["Reasoning"]), "int", None,
        source="analysis/outcomes.py#GROUPS", note="the models in the paper's two groups (13 without reasoning, 7 with)")
    put("NumModelsMainNoReasoning", len(NR), "int", None, source="analysis/outcomes.py#REF_GROUPS.MainNoReasoning",
        note="the run's controls were read on these 11 models only")
    put("SplitHigh", A.HI, "pct", None, source="analysis/analyse.py#HI")
    put("SplitLow", A.LO, "pct", None, source="analysis/analyse.py#LO")
    put("NumCalls", res["calls"], "int", "calls")
    put("NumPairs", res["n_pairs"], "int", "n_pairs")
    put("ConfidenceLevel", CONFIDENCE, "pct", None, source="analysis/outcomes.py#CONFIDENCE")
    put("BandGreenFrom", FIG3["band_green"], "pct", None, source="analysis/outcomes.py#FIG3.band_green")
    put("BandAmberFrom", FIG3["band_amber"], "pct", None, source="analysis/outcomes.py#FIG3.band_amber")
    put("RankFromSideBySide", FIG3["rank_from"], "pct", None, source="analysis/outcomes.py#FIG3.rank_from")
    mapping = {}
    for name in sorted(old or ()):
        new = name
        for a, b2 in RENAME:
            new = new.replace(a, b2)
        if new not in v:
            mapping[name] = {"new": None, "status": "retired"}
        elif regrouped and (new in group_level or new.startswith(("NumModels",))):
            mapping[name] = {"new": new, "status": "renamed; recomputed on the two groups (13 / 7 models)"}
        elif abs((old[name]["value"] or 0) - v[new]["value"]) > 1e-12:
            mapping[name] = {"new": new, "status": "renamed; VALUE DIFFERS", "old_value": old[name]["value"],
                             "new_value": v[new]["value"]}
        else:
            mapping[name] = {"new": new, "status": "renamed; value unchanged"}
    return v, mapping


def run(reads, frames, controls=None, items=None, settled=None, n=B_RESAMPLES):
    main, tables = compute(reads, frames, n=n)
    half, _ = compute(reads, frames, hi=0.5 + 1e-9, lo=0.5 - 1e-9, n=n, with_arms=False)
    return {"groups": {g: list(a) for g, a in ALL_GROUPS.items()}, "main": main, "cut_half": half,
            "cutoff_change": cutoff_change(main, half), "wrong_verdicts": wrongful(tables, frames, n),
            "consensus": consensus(tables, frames, n),
            "one_order": one_order(tables, frames), "excluded": excluded(reads), "thought": thought(reads),
            "controls": controls, "settled": settled, "items": items, "n_pairs": len(frames["pairs"]),
            "calls": sum(r.get("calls") or 0 for r in reads.values()),
            "domains": sorted({p["domain"] for p in frames["pairs"]})}


def selftest(frames_path):
    frames = json.load(open(frames_path))
    good = lambda a, cond, pid, k, control: (True if control else
                                            {"A": k == "F", "B": True, "C": k == "F", "D": k == "F"}.get(cond, k == "line"))
    reads = A._fake_reads(frames, NO_R + WITH_R, good)
    res = run(reads, frames, n=100)
    o = res["main"]
    assert o["NoReasoning"][""]["A"]["share"] == 1.0 and o["NoReasoning"][""]["B"]["share"] == 0.0
    assert o["Reasoning"]["Judgement"]["C"]["den"] == 24 * 7 and o["Reasoning"]["Judgement"]["C"]["share"] == 1.0
    assert o["MainReasoning"]["Judgement"]["C"]["den"] == 24 * 5 and o["NoReasoning"]["FixedRule"]["A"]["den"] == 12 * 13
    assert o["NoReasoning"][""]["D-B"]["diff"] == 1.0 and res["cut_half"]["NoReasoning"][""]["A"]["share"] == 1.0
    assert res["wrong_verdicts"]["NoReasoning"]["for_other"]["share"] == 1.0          # alone: both yes
    assert res["wrong_verdicts"]["NoReasoning"]["against_held_to_less"]["share"] == 0.0
    # the single 0.5 cut-off counts 0.5 as no split, and 0.55 / 0.45 as a split that 0.6 / 0.4 does not
    for r in reads.values():
        for uk, u in r["units"].items():
            if uk.startswith("B|") and not u["control"]:
                u["cells"]["F"]["yes_rate"], u["cells"]["O"]["yes_rate"] = 0.55, 0.45
    res = run(reads, frames, n=100)
    assert res["main"]["NoReasoning"][""]["B"]["share"] == 0.0 and res["cut_half"]["NoReasoning"][""]["B"]["share"] == 1.0
    assert abs(res["cutoff_change"]["abs_change"] - 1.0) < 1e-12
    cs = res["consensus"]                                           # every model splits every pair side by side
    assert len(cs["per_pair"]) == 24 and cs["distribution"][7] == 24 and cs["share_at_least"]["share"] == 1.0
    md = markdown(res, reads)
    assert not vocabulary_hits(md), vocabulary_hits(md)
    assert vocabulary_hits("the line stated") and vocabulary_hits("standards domains") and not vocabulary_hits("deadline")
    assert vocabulary_hits("the protected party") and vocabulary_hits("by convention") and not vocabulary_hits("held to less")
    res["main"]["NoReasoning"][""]["B"]["share"] = 0.1
    v, mp = build_macros(res, "x.json", old={"StandardStatedReasoningStandardsDomains": {"value": 0.5},
                                              "AloneBareGptFourO": {"value": -1}, "WrongForOtherNonReasoning": {"value": 0}})
    assert all(k.isalpha() for k in v) and "ToldPrincipleReasoningJudgement" in v and v["OneInN"]["value"] == 10
    assert mp["StandardStatedReasoningStandardsDomains"]["new"] == "ToldPrincipleReasoningJudgement"
    assert mp["StandardStatedReasoningStandardsDomains"]["status"].startswith("renamed; recomputed")
    assert mp["AloneBareGptFourO"]["status"] == "renamed; VALUE DIFFERS"
    assert mp["WrongForOtherNonReasoning"]["new"] == "OtherWronglyPassedNoReasoning"
    bad = [k for k in v if vocabulary_hits(k.replace("Rule", " rule ").replace("Line", " line ").replace("Thresholds", "")
                                .replace("Protected", " protected "))]
    assert not bad, bad[:5]
    print("selftest 4/4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads"); ap.add_argument("--frames", required=True); ap.add_argument("--controls")
    ap.add_argument("--settled"); ap.add_argument("--items")
    ap.add_argument("--reads262", help="run 262's reads (exploratory macros); default: the --reads directory")
    ap.add_argument("--out", default="results/outcomes_run259_v6.json")
    ap.add_argument("--md", default="results/OUTCOMES.md"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.frames)
    frames = json.load(open(a.frames))
    reads, _ = A.load_reads(a.reads)
    controls = json.load(open(a.controls)) if a.controls else None
    settled = json.load(open(a.settled)) if a.settled else None
    items = json.load(open(a.items)) if a.items else None
    for p in (a.out, a.md):
        if os.path.exists(p):
            sys.exit(f"write-once: {p} exists")
    res = run(reads, frames, controls, items, settled)
    md = markdown(res, reads)
    hits = vocabulary_hits(md, [it["text"] for it in (items or {}).get("items", [])])
    if hits:
        sys.exit(f"REFUSING: outcomes text uses retired vocabulary: {hits}")
    with open(a.out, "x") as f:
        json.dump({k: v for k, v in res.items() if k != "items"}, f, indent=1)
    with open(a.md, "x") as f:
        f.write(md)
    sidecar = json.load(open(M.SIDECAR))
    import party_difference as PD
    import wrong_kinds as WK
    # party_difference.py's and wrong_kinds.py's macros are their own: they are re-added at the end, so they are not
    # "old" names to rename
    old = {k: x for k, x in sidecar.items() if not k.startswith("_") and not PD.owned(x) and not WK.owned(x)}
    v, step = build_macros(res, os.path.relpath(a.out, ROOT), settled,
                           os.path.relpath(a.settled, ROOT) if a.settled else None, old,
                           regrouped=not sidecar.get("_old_to_new"))
    # the first renaming (vocabulary instruction) is kept keyed by the original names and carried through this one;
    # this step (the addendum: "protected party" becomes "the party held to less") is recorded on its own as well
    first = sidecar.get("_old_to_new", {})
    mapping = {k: dict(e, new=(step[e["new"]]["new"] if e["new"] in step else e["new"])) for k, e in first.items()}
    for k, e in step.items():
        if k not in mapping and e["new"] != k:
            mapping[k] = e
    held = {k: e for k, e in step.items() if e["new"] != k} or sidecar.get("_old_to_new_held_to_less", {})
    n = M.write_macros(v, extra={"_old_to_new": mapping, "_old_to_new_held_to_less": held,
                                 "_renamed_on": "2026-11-13, the paper's vocabulary and its addendum"})
    # numbers.tex has just been rewritten from scratch; put party_difference.py's macros back (it recomputes, asserts
    # its banked results reproduce, and writes paper/numbers_exploratory.tex for run 262)
    r262 = a.reads262 or a.reads
    pd = PD.apply(reads, frames, a.frames, PD.load262(r262) or None, r262)
    n = pd[2]
    print(f"party_difference.py: {pd[4]} macros back in paper/numbers.tex, {pd[5]} in paper/numbers_exploratory.tex")
    wk = WK.apply(reads, frames, a.frames)
    n = wk[2]
    print(f"wrong_kinds.py: {wk[3]} macros back in paper/numbers.tex")
    st = {}
    for x in held.values():
        st[x["status"]] = st.get(x["status"], 0) + 1
    print(f"wrote {a.out}, {a.md}, {n} macros to paper/numbers.tex; renamed in this step: {st}; "
          f"original names carried: {len(first)}, of which retired: {sum(1 for e in mapping.values() if not e['new'])}")


if __name__ == "__main__":
    main()
