#!/usr/bin/env python3
"""party_difference.py : the party difference per cell in runs 259 and 262. No new calls.

    python analysis/party_difference.py --reads259 DIR --frames259 FILE --reads262 DIR
    python analysis/party_difference.py --selftest --frames259 FILE

Party difference: in one cell (one pair on one model in one condition), the yes-rate of the party held to less minus the
yes-rate of the other party; a cell enters only if both parties' readings are valid (analyse.valid; side by side pools
both orders, analyse.side_pooled). "Party makes no difference": the difference below 0.2 (a negative difference counts).

Conditions. Run 259: side by side (both orders pooled), alone, alone told in principle, alone told a precise rule (the
four conditions that read both parties; the outside-the-rule condition reads only the party held to less). Run 262
(discovery; worked examples, not part of the registered results): alone with no example (re-read), alone with worked
example A (the party held to less, met, with its reason), alone with worked example B (A plus a counter-example).

Alone given split (run 259): the alone party difference restricted, per model, to the pairs that
model separates side by side (both orders pooled; analyse.split, 60 / 40), with the number of qualifying model-pair
combinations; the unconditional figures are kept for the appendix. Macros PartyDiffAloneGivenSplit{Group}{Kind} (with
Lo, Hi, Pairs, DistinctPairs, Of) and PartyNoDiffAloneGivenSplit{Group}{Kind} (with Num, Den, Lo, Hi).

Kinds: fixed-rule cases (insurance disclosure, statutory thresholds) and judgement cases (the other four domains).
Groups: run 259, the paper's two groups (13 models without reasoning, 7 with); run 262, its own six models (4 and 2).

Intervals: 95% percentile bootstrap over pairs, 10,000 resamples, seed 259; the mean is the mean over cells, so a
resample weights each drawn pair by its number of valid cells (as the shares in outcomes.py). Run 259 resamples pairs
within domain, as every other interval in the paper. Run 262 has one pair per domain, where resampling within domain
cannot vary, so it resamples pairs within kind: the four judgement pairs; the fixed-rule kind is one pair (I4) and has
no interval. Models are held fixed throughout, as elsewhere.

Writes results/party_difference_v2.json and results/PARTY_DIFFERENCE_v3.md (written once; a later call recomputes and
asserts it reproduces them, so outcomes.py can call this at its end). Macros:
  run 259 -> paper/numbers.tex, beside the existing macros: its own earlier macros (any version of its results file)
    are replaced, any other name is refused, and every other existing line is asserted unchanged;
  run 262 -> paper/numbers_exploratory.tex (sidecar numbers_exploratory.json), prefix Expl, no intervals.
Differences print in percentage points (kind "pts", signed); the cut-off prints unsigned ("ptsu").
"""
import argparse, hashlib, json, math, os, random, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                            # noqa: E402
import macros as M                                             # noqa: E402
import outcomes as O                                           # noqa: E402

NO_DIFF = 0.2
B_RESAMPLES, SEED = 10000, 259
KINDS = {"FixedRule": O.FIXED, "Judgement": O.JUDGEMENT}
KIND_LABEL = {"FixedRule": "fixed-rule cases", "Judgement": "judgement cases"}
COND259 = [("A", "SideBySide", "side by side"), ("B", "Alone", "alone"),
           ("C", "ToldPrinciple", "alone, told in principle"), ("D", "ToldRule", "alone, told a precise rule")]
COND262 = [("base_alone", "ExampleNone", "alone, no example (re-read)"), ("A_alone", "ExampleA", "alone, worked example A"),
           ("B_alone", "ExampleB", "alone, worked example B")]
GROUPS262 = {"NoReasoning": ("claude", "gpt6s_s", "qwen80b", "llama70b"), "Reasoning": ("gpt6s_r", "haiku_r")}
GLABEL = {"NoReasoning": "without reasoning", "Reasoning": "with reasoning"}


# ── CELLS ────────────────────────────────────────────────────────────────────────────
def cells259(reads, frames):
    """{(arm, pid, cond): diff} over valid cells."""
    out = {}
    for arm, r in reads.items():
        for pid, rec in A.pair_cells(r, frames).items():
            for c, _, _ in COND259:
                x = rec.get(c)
                if x and x["valid"]:
                    out[(arm, pid, c)] = x["F"] - x["O"]
    return out


def cells262(reads):
    out = {}
    for arm, r in reads.items():
        reasoning = r.get("reasoning", False)
        for uk, u in r["units"].items():
            cond, pid = uk.split("|")
            if cond not in {c for c, _, _ in COND262}:
                continue
            F, Ob = u["cells"]["F"], u["cells"]["O"]
            if A.valid(F, reasoning) and A.valid(Ob, reasoning):
                out[(arm, pid, cond)] = F["yes_rate"] - Ob["yes_rate"]
    return out


# ── BOOTSTRAP ────────────────────────────────────────────────────────────────────────
class Boot:
    def __init__(self, strata, n=B_RESAMPLES, seed=SEED):
        """strata: list of lists of pair ids; pairs are resampled with replacement within each stratum, and models too
        where a statistic pools more than one (outcomes.FastBoot's model draws, seed 260)."""
        rng = random.Random(seed)
        self.n = n
        self.pids = [p for s in strata for p in s]
        ix = {p: i for i, p in enumerate(self.pids)}
        self.idx = np.array([[ix[rng.choice(s)] for s in strata for _ in s] for _ in range(n)])
        self.varies = any(len(s) > 1 for s in strata)
        P = len(self.pids)
        self.V = np.array([np.bincount(r, minlength=P) for r in self.idx], float)
        self._W = {}

    _arm_weights = O.FastBoot._arm_weights

    @staticmethod
    def _ci(v):
        v = np.sort(v[~np.isnan(v)])
        return [float(v[int(0.025 * (len(v) - 1))]), float(v[int(math.ceil(0.975 * (len(v) - 1)))])]

    def stat(self, per_pair):
        """per_pair: {pid: list of (model, cell difference)}. Mean difference and share below NO_DIFF, with intervals."""
        arms = sorted({a for v in per_pair.values() for a, _ in v})
        mat = lambda f: np.array([[sum(f(d) for a2, d in per_pair.get(p, []) if a2 == a) for p in self.pids]
                                  for a in arms], float).reshape(len(arms), len(self.pids))
        Sm, Km, Zm = mat(lambda d: d), mat(lambda d: 1), mat(lambda d: d < NO_DIFF)
        s, k, z = Sm.sum(0), Km.sum(0), Zm.sum(0)
        if k.sum() == 0:
            return None
        if len(arms) > 1:
            W = self._arm_weights(arms)
            S, K, Z = (((W @ M_) * self.V).sum(1) for M_ in (Sm, Km, Zm))
        else:
            S, K, Z = s[self.idx].sum(1), k[self.idx].sum(1), z[self.idx].sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean_r, share_r = np.where(K > 0, S / K, np.nan), np.where(K > 0, Z / K, np.nan)
        return {"mean": float(s.sum() / k.sum()), "mean_ci": self._ci(mean_r) if self.varies else None,
                "no_diff": {"share": float(z.sum() / k.sum()), "num": int(z.sum()), "den": int(k.sum()),
                            "ci": self._ci(share_r) if self.varies else None},
                "n_cells": int(k.sum()), "n_pairs": int((k > 0).sum())}


def summarise(cells, conds, groups, pairs_by_kind, strata_by_kind, n):
    out = {}
    for g, arms in groups.items():
        for kind, pids in pairs_by_kind.items():
            b = Boot(strata_by_kind[kind], n)
            for c, cname, _ in conds:
                per = {}
                for (arm, pid, cc), d in cells.items():
                    if arm in arms and cc == c and pid in pids:
                        per.setdefault(pid, []).append((arm, d))
                out[f"{cname}|{g}|{kind}"] = b.stat(per)
    return out


def given_split(reads, frames, groups, pk, strata, n):
    """Alone, restricted per model to the pairs that model separates side by side (both orders pooled, the 60 / 40
    rule of analyse.split). A qualifying pair is one (model, pair) with a valid side-by-side cell that splits and a valid
    alone cell; a split pair whose alone cell is invalid is counted apart and left out."""
    tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
    out = {}
    for g, arms in groups.items():
        for kind, pids in pk.items():
            per, side_valid, split, split_alone_invalid = {}, 0, 0, 0
            for a in arms:
                for pid in pids:
                    rec = tables[a].get(pid, {})
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
                        split_alone_invalid += 1
            e = Boot(strata[kind], n).stat(per)
            if e:
                e.update(side_valid=side_valid, split=split, split_alone_invalid=split_alone_invalid,
                         qualifying=e["n_cells"])
            out[f"{g}|{kind}"] = e
    return out


def run(reads259, frames, reads262, n=B_RESAMPLES):
    dom = {p["id"]: p["domain"] for p in frames["pairs"]}
    tests = [p["id"] for p in frames["pairs"]]
    pk = {k: [p for p in tests if dom[p] in ds] for k, ds in KINDS.items()}
    strata259 = {k: [[p for p in tests if dom[p] == d] for d in A.DOMAINS if d in ds] for k, ds in KINDS.items()}
    present = set(reads259)
    groups259 = {g: tuple(a for a in arms if a in present) for g, arms in O.GROUPS.items()}
    res = {"definition": {"party_difference": "yes-rate of the party held to less minus that of the other party, per cell",
                          "no_difference_below": NO_DIFF, "resamples": n, "seed": SEED},
           "run259": {"groups": groups259, "stats": summarise(cells259(reads259, frames), COND259, groups259, pk,
                                                               strata259, n)},
           "run259_alone_given_split": given_split(reads259, frames, groups259, pk, strata259, n)}
    if reads262:
        c262 = cells262(reads262)
        p262 = sorted({pid for (_, pid, _) in c262})
        pk262 = {k: [p for p in p262 if dom[p] in ds] for k, ds in KINDS.items()}
        res["run262"] = {"groups": GROUPS262, "resampling": "pairs within kind (one pair per domain)",
                         "stats": summarise(c262, COND262, GROUPS262, pk262, {k: [v] for k, v in pk262.items()}, n)}
    return res


# ── REPORT AND MACROS ────────────────────────────────────────────────────────────────
def f2(x):
    """A difference of yes-rates in signed whole percentage points."""
    return f"{round(100 * x):+d}"


def markdown(res):
    L = ["# Party difference, runs 259 and 262", "",
         "Generated by `analysis/party_difference.py`; no new calls. **Party difference**: in one cell (one pair on one "
         "model in one condition), the yes-rate of the party held to less minus the yes-rate of the other party, in "
         "percentage points. "
         f"**Party makes no difference**: the difference below {round(100 * NO_DIFF)} points (negative differences count). "
         "Run 262's figures are exploratory (macros in numbers_exploratory.tex, prefix Expl, without intervals). Mean over cells "
         "with its 95% interval (bootstrap over pairs, 10,000 resamples, seed 259; run 259 within domain, run 262 within "
         "kind, since it has one pair per domain); share with its count. Models held fixed.", ""]
    gs = res.get("run259_alone_given_split")
    if gs:
        L += ["## Run 259, alone, among the pairs each model separates side by side", "",
              "Per model, only the pairs that model separates side by side (both orders pooled; the party held to less at "
              "least 0.6 and the other at most 0.4). *Qualifying*: model-pair combinations that split side by side and have "
              "a valid alone reading (distinct pairs in brackets); *of*: model-pair combinations with a valid side-by-side "
              "reading. The unconditional figures below are for the appendix.", "",
              "| Group | Cases | Mean difference alone, points [95%] | No difference alone (< 20 points) [95%] | Qualifying (pairs) | Of |",
              "|---|---|---|---|---|---|"]
        for g in ("NoReasoning", "Reasoning"):
            for kind in KINDS:
                e = gs.get(f"{g}|{kind}")
                if not e:
                    continue
                nd = e["no_diff"]
                L.append(f"| {GLABEL[g]} | {KIND_LABEL[kind]} | {f2(e['mean'])} [{f2(e['mean_ci'][0])}, {f2(e['mean_ci'][1])}] | "
                         f"{100 * nd['share']:.0f}% [{100 * nd['ci'][0]:.0f}, {100 * nd['ci'][1]:.0f}] ({nd['num']}/{nd['den']}) | "
                         f"{e['qualifying']} ({e['n_pairs']}) | {e['side_valid']} |")
        L.append("")
    for run, conds, title in [("run259", COND259, "Run 259, every pair (appendix; the paper's two groups: 13 models without reasoning, 7 with)"),
                              ("run262", COND262, "Run 262 (discovery; worked examples; 4 models without reasoning, 2 with; "
                                                  "not part of the registered results)")]:
        if run not in res:
            continue
        st = res[run]["stats"]
        L += [f"## {title}", "", "| Group | Cases | Condition | Mean difference, points [95%] | No difference (< 20 points) [95%] | Cells |",
              "|---|---|---|---|---|---|"]
        for g in ("NoReasoning", "Reasoning"):
            for kind in KINDS:
                for _, cname, clabel in conds:
                    e = st.get(f"{cname}|{g}|{kind}")
                    if not e:
                        continue
                    ci = f" [{f2(e['mean_ci'][0])}, {f2(e['mean_ci'][1])}]" if e["mean_ci"] else " (one pair, no interval)"
                    nd = e["no_diff"]
                    nci = f" [{100 * nd['ci'][0]:.0f}, {100 * nd['ci'][1]:.0f}]" if nd["ci"] else ""
                    L.append(f"| {GLABEL[g]} | {KIND_LABEL[kind]} | {clabel} | {f2(e['mean'])}{ci} | "
                             f"{100 * nd['share']:.0f}%{nci} ({nd['num']}/{nd['den']}) | {e['n_cells']} |")
        L.append("")
    return "\n".join(L) + "\n"


EXPL_TEX = os.path.join(ROOT, "paper", "numbers_exploratory.tex")
EXPL_SIDECAR = os.path.join(ROOT, "paper", "numbers_exploratory.json")
EXPL_NOTE = ("% EXPLORATORY: run 262 (discovery; worked examples), not part of the registered results. Prefix Expl,\n"
             "% no intervals. Written by analysis/party_difference.py.\n")
# v2 adds run259_alone_given_split; v3 is the matched readout (run 263 swapped in, 2026-11-16)
OUT_JSON = "results/party_difference_v4.json"     # v4: models resampled as well as pairs (2026-11-16)
OUT_MD = "results/PARTY_DIFFERENCE_v5.md"
OWN_SOURCES = ("results/party_difference.json", "results/party_difference_v2.json", "results/party_difference_v3.json",
               "results/party_difference_v4.json")   # every version this script wrote


def build_macros(res, src):
    """Returns (macros for numbers.tex: run 259, macros for numbers_exploratory.tex: run 262)."""
    main, expl = {}, {}

    def put(v, name, value, kind, key):
        v[name] = {"value": value, "kind": kind, "source": f"{src}#{key}"}

    for run, v, pre, with_ci in (("run259", main, "", True), ("run262", expl, "Expl", False)):
        if run not in res:
            continue
        for key, e in res[run]["stats"].items():
            if not e:
                continue
            cname, g, kind = key.split("|")
            base = f"{cname}{g}{kind}"
            k = f"{run}.stats.{key}"
            put(v, f"{pre}PartyDiff{base}", e["mean"], "pts", k + ".mean")
            nd = e["no_diff"]
            put(v, f"{pre}PartyNoDiff{base}", nd["share"], "pct", k + ".no_diff.share")
            put(v, f"{pre}PartyNoDiff{base}Num", nd["num"], "int", k + ".no_diff.num")
            put(v, f"{pre}PartyNoDiff{base}Den", nd["den"], "int", k + ".no_diff.den")
            if with_ci and e["mean_ci"]:
                put(v, f"{pre}PartyDiff{base}Lo", e["mean_ci"][0], "pts", k + ".mean_ci.0")
                put(v, f"{pre}PartyDiff{base}Hi", e["mean_ci"][1], "pts", k + ".mean_ci.1")
            if with_ci and nd["ci"]:
                put(v, f"{pre}PartyNoDiff{base}Lo", nd["ci"][0], "pct", k + ".no_diff.ci.0")
                put(v, f"{pre}PartyNoDiff{base}Hi", nd["ci"][1], "pct", k + ".no_diff.ci.1")
    for key, e in (res.get("run259_alone_given_split") or {}).items():
        if not e:
            continue
        g, kind = key.split("|")
        base, k = f"AloneGivenSplit{g}{kind}", f"run259_alone_given_split.{key}"
        put(main, f"PartyDiff{base}", e["mean"], "pts", k + ".mean")
        put(main, f"PartyDiff{base}Lo", e["mean_ci"][0], "pts", k + ".mean_ci.0")
        put(main, f"PartyDiff{base}Hi", e["mean_ci"][1], "pts", k + ".mean_ci.1")
        put(main, f"PartyDiff{base}Pairs", e["qualifying"], "int", k + ".qualifying")
        put(main, f"PartyDiff{base}DistinctPairs", e["n_pairs"], "int", k + ".n_pairs")
        put(main, f"PartyDiff{base}Of", e["side_valid"], "int", k + ".side_valid")
        nd = e["no_diff"]
        put(main, f"PartyNoDiff{base}", nd["share"], "pct", k + ".no_diff.share")
        put(main, f"PartyNoDiff{base}Num", nd["num"], "int", k + ".no_diff.num")
        put(main, f"PartyNoDiff{base}Den", nd["den"], "int", k + ".no_diff.den")
        put(main, f"PartyNoDiff{base}Lo", nd["ci"][0], "pct", k + ".no_diff.ci.0")
        put(main, f"PartyNoDiff{base}Hi", nd["ci"][1], "pct", k + ".no_diff.ci.1")
    put(main, "PartyNoDiffCut", NO_DIFF, "ptsu", "definition.no_difference_below")
    if expl:
        put(expl, "ExplPartyNoDiffCut", NO_DIFF, "ptsu", "definition.no_difference_below")
    return main, expl


def owned(x, src=None):
    """A macro this script wrote, under any of its output versions."""
    return str(x.get("source", "")).startswith(tuple(f"{s}#" for s in OWN_SOURCES + ((src,) if src else ())))


def add_macros(new, src, tex=M.TEX, sidecar=M.SIDECAR, own=None):
    """Puts this script's macros into numbers.tex: replaces its own earlier ones (source src), refuses a name owned by
    anything else, and asserts every line it does not own is unchanged. own: the caller's output files, when another
    script (wrong_kinds.py) uses this for its own macros."""
    meta = json.load(open(sidecar))
    mine = (lambda x: owned(x, src)) if own is None else \
        (lambda x: str(x.get("source", "")).startswith(tuple(f"{s}#" for s in own)))
    keep = {k: x for k, x in meta.items() if not k.startswith("_") and not mine(x)}
    clash = sorted(set(new) & set(keep))
    if clash:
        sys.exit(f"REFUSING: macro names already defined elsewhere: {clash[:5]} ({len(clash)})")
    kept_lines = {l for l in open(tex).read().splitlines() if not any(l.startswith(f"\\newcommand{{\\{k}}}")
                                                                      for k in meta if k not in keep)}
    values = {k: {"value": x["value"], "kind": x["kind"], "source": x["source"], **({"note": x["note"]} if "note" in x else {})}
              for k, x in keep.items()}
    values.update(new)
    extra = {k: x for k, x in meta.items() if k.startswith("_")}
    n = M.write_macros(values, tex, sidecar, extra=extra)
    lost = kept_lines - set(open(tex).read().splitlines())
    assert not lost, f"existing macro lines changed: {sorted(lost)[:3]}"
    return n


def write_exploratory(expl, tex=EXPL_TEX, sidecar=EXPL_SIDECAR):
    # Keep exploratory macros other scripts wrote (analysis/second_review.py, 2026-11-17): only this script's own
    # entries are replaced.
    if os.path.exists(sidecar):
        mine = tuple(f"{s}#" for s in OWN_SOURCES)
        foreign = {k: {"value": x["value"], "kind": x["kind"], "source": x["source"]}
                   for k, x in json.load(open(sidecar)).items()
                   if not k.startswith("_") and not str(x.get("source", "")).startswith(mine) and k not in expl}
        expl = {**foreign, **expl}
    n = M.write_macros(expl, tex, sidecar)
    body = open(tex).read()
    open(tex, "w").write(EXPL_NOTE + body.replace("paper/numbers.json", "paper/numbers_exploratory.json"))
    return n


def apply(reads259, frames, frames_path, reads262=None, reads262_dir=None, n=B_RESAMPLES, root=ROOT,
          tex=M.TEX, sidecar=M.SIDECAR, expl_tex=EXPL_TEX, expl_sidecar=EXPL_SIDECAR):
    """Compute; write the results once or assert they reproduce; put the macros in place. Called by main() and at the
    end of outcomes.py, whose rewrite of numbers.tex would otherwise drop these macros."""
    res = run(reads259, frames, reads262, n)
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
    res["inputs"] = {"frames259": os.path.basename(frames_path), "frames259_sha8": sha(frames_path),
                     "reads259": sorted(reads259), "reads262": sorted(reads262 or {}),
                     "reads262_sha8": {k: sha(os.path.join(reads262_dir, f"RUN262_READ__{k}.json")) for k in (reads262 or {})}}
    md = markdown(res)
    if O.vocabulary_hits(md):
        sys.exit(f"REFUSING: retired vocabulary {O.vocabulary_hits(md)}")
    pj, pm = os.path.join(root, OUT_JSON), os.path.join(root, OUT_MD)
    if os.path.exists(pj):
        old = json.load(open(pj))
        same = all(json.dumps(old.get(k), sort_keys=True) == json.dumps(json.loads(json.dumps(res.get(k))), sort_keys=True)
                   for k in ("definition", "run259", "run262", "run259_alone_given_split"))
        if not same:
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
    main_m, expl_m = build_macros(res, OUT_JSON)
    n_main = add_macros(main_m, OUT_JSON, tex, sidecar)
    n_expl = write_exploratory(expl_m, expl_tex, expl_sidecar) if expl_m else 0
    return res, md, n_main, n_expl, len(main_m), len(expl_m)


def load262(d):
    out = {}
    for f in sorted(os.listdir(d)):
        if f.startswith("RUN262_READ__") and f.endswith(".json"):
            r = json.load(open(os.path.join(d, f)))
            if r.get("status") == "READ":
                out[r["arm"]] = r
    return out


def selftest(frames_path):
    import tempfile
    frames = json.load(open(frames_path))
    good = lambda a, cond, pid, k, control: {"A": k == "F", "B": True, "C": k == "F", "D": k == "F"}.get(cond, k == "line")
    reads = A._fake_reads(frames, O.NO_R + O.WITH_R, good)
    res = run(reads, frames, None, n=200)
    st = res["run259"]["stats"]
    assert st["SideBySide|NoReasoning|Judgement"]["mean"] == 1.0 and st["Alone|Reasoning|FixedRule"]["mean"] == 0.0
    assert st["Alone|NoReasoning|Judgement"]["no_diff"]["share"] == 1.0 and st["ToldRule|Reasoning|FixedRule"]["no_diff"]["num"] == 0
    assert st["Alone|NoReasoning|Judgement"]["n_cells"] == 24 * 13 and st["Alone|Reasoning|FixedRule"]["n_cells"] == 12 * 7
    gs = res["run259_alone_given_split"]["NoReasoning|Judgement"]
    assert gs["qualifying"] == gs["split"] == gs["side_valid"] == 24 * 13 and gs["mean"] == 0.0 and gs["no_diff"]["share"] == 1.0
    print("  ok  definitions: side by side all split -> +1.00; alone both yes -> 0.00 and all 'no difference'; "
          "given split: every model-pair qualifies")
    # 0.2 itself is a difference; 0.19 and a negative difference are not
    b = Boot([["x", "y"]], n=50)
    e = b.stat({"x": [("m", 0.2), ("m", 0.19)], "y": [("m", -0.5)]})
    assert e["no_diff"]["num"] == 2 and abs(e["mean"] - (-0.11 / 3)) < 1e-12 and e["mean_ci"] is not None
    assert Boot([["x"]], n=10).stat({"x": [("m", 0.5)]})["mean_ci"] is None
    # two models: the model draws vary the mean even with the pairs fixed
    e2 = Boot([["x"]], n=200).stat({"x": [("m1", 0.0), ("m2", 1.0)]})
    assert e2["mean"] == 0.5
    print("  ok  cut-off: 0.2 counts as a difference, 0.19 and negatives do not; one pair gives no interval")
    res["run262"] = {"stats": {"ExampleA|NoReasoning|Judgement": st["Alone|NoReasoning|Judgement"],
                               "ExampleB|Reasoning|Judgement": st["SideBySide|Reasoning|Judgement"]}}
    v, ex = build_macros(res, "results/x.json")
    assert all(k.isalpha() for k in list(v) + list(ex)) and "PartyDiffSideBySideNoReasoningJudgementLo" in v
    assert v["PartyDiffSideBySideNoReasoningJudgement"]["kind"] == "pts" and M.fmt(1.0, "pts") == "+100"
    assert M.fmt(v["PartyNoDiffCut"]["value"], "ptsu") == "20"
    assert set(ex) and all(k.startswith("Expl") for k in ex) and not any(k.endswith(("Lo", "Hi")) for k in ex)
    assert not any("Example" in k for k in v)
    assert not O.vocabulary_hits(" ".join(v)) and not O.vocabulary_hits(markdown(res))
    print("  ok  macros: run 259 in points with intervals; run 262 under Expl, no intervals, none in numbers.tex")
    d = tempfile.mkdtemp(); t, s_ = os.path.join(d, "n.tex"), os.path.join(d, "n.json")
    M.write_macros({"Kept": {"value": 0.5, "kind": "pct", "source": "a#b"},
                    "PartyOld": {"value": 0.1, "kind": "f2", "source": "results/x.json#old"}}, t, s_, extra={"_x": 1})
    add_macros({"Added": {"value": 3, "kind": "int", "source": "results/x.json#n"}}, "results/x.json", t, s_)
    body = open(t).read(); meta = json.load(open(s_))
    assert "{\\Kept}{50\\%}" in body and "{\\Added}{3}" in body and "PartyOld" not in body and meta["_x"] == 1
    add_macros({"Added": {"value": 4, "kind": "int", "source": "results/x.json#n"}}, "results/x.json", t, s_)
    assert "{\\Added}{4}" in open(t).read()
    try:
        add_macros({"Kept": {"value": 0.1, "kind": "pct", "source": "results/x.json#k"}}, "results/x.json", t, s_)
        raise AssertionError("clash accepted")
    except SystemExit as e:
        assert "REFUSING" in str(e)
    print("  ok  re-run: own earlier macros replaced, others kept unchanged, extras kept, a clash refused")
    print("selftest 4/4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads259"); ap.add_argument("--frames259", required=True); ap.add_argument("--reads262")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.frames259)
    frames = json.load(open(a.frames259))
    reads259, _ = A.load_reads(a.reads259)
    reads262 = load262(a.reads262) if a.reads262 else None
    res, md, n, ne, km, ke = apply(reads259, frames, a.frames259, reads262, a.reads262)
    print(md)
    print(f"{OUT_JSON}, {OUT_MD}; {km} macros in paper/numbers.tex (now {n} entries), {ke} in paper/numbers_exploratory.tex")


if __name__ == "__main__":
    main()
