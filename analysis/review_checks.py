#!/usr/bin/env python3
"""review_checks.py : the analyses of CC_instruction_analysis_and_rewrite.md, sections 1 to 4, on run 259's existing
responses. No new calls.

    python analysis/review_checks.py --reads DIR --logprob-reads DIR --frames FILE

  --reads           the paper's reads (the matched readout: banked/records/RUN259_MATCHED_READS)
  --logprob-reads   run 259's reads as banked (five open models read alone by log-probability: banked/records)

1. How wrongly decided alone pairs divide, fixed-rule and judgement cases: the table is analysis/wrong_kinds.py's; this
   adds the pooled share of all 20 configurations' valid judgement cells in which both parties pass alone (the ceiling
   explanation's largest possible share, which replaces block G's harsher arm in the paper).
2. A graded check: for the five models banked with log-probabilities, the party difference alone (P(yes) of the party
   held to less minus that of the other party) in judgement cases, in cells where neither P(yes) is below 0.05 or above
   0.95; and the same among the pairs the model splits side by side.
3. Robustness: the judgement-case figures without the pairs fewer than four of the seven reasoning models split side by
   side; the log-probability readout's main figures beside the paper's (sampled) readout; configurations and models
   counted.
4. The main figures pooled without the models that split fewer than half of all pairs side by side.

Intervals as the paper's (outcomes.FastBoot, party_difference.Boot): pairs within domain and models resampled together.
Writes results/review_checks.json and results/REVIEW_CHECKS.md (write-once unless unchanged) and its macros into
paper/numbers.tex (own source results/review_checks.json).
"""
import argparse, copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402

OUT_JSON = "results/review_checks_v2.json"      # v2 adds D2's let-through (the introduction's example)
OUT_MD = "results/REVIEW_CHECKS_v2.md"
LOGPROB_ARMS = ("gpt4o", "llama70b", "qwen80b", "mistral24b", "gemma27b")
CONDS = (("A", "SideBySide"), ("B", "Alone"), ("C", "ToldPrinciple"), ("D", "ToldRule"), ("E", "LetThrough"))
GRADED_LO, GRADED_HI = 0.05, 0.95
DISTINCT_MODELS = {  # configuration -> model (one model read with and without reasoning counts once)
    "claude": "Claude Sonnet 5", "gpt6s_s": "GPT-6 Sol", "gpt6s_r": "GPT-6 Sol", "grok43_s": "Grok 4.3",
    "grok43_r": "Grok 4.3", "gpt4o": "GPT-4o", "haiku_s": "Claude Haiku 4.5", "haiku_r": "Claude Haiku 4.5",
    "kimi": "Kimi K3", "llama70b": "Llama 3.3 70B", "qwen80b": "Qwen3-Next-80B", "gpt6l_s": "GPT-6 Luna",
    "gpt6l_r": "GPT-6 Luna", "mistral24b": "Mistral Small 3.2 24B", "gemma27b": "Gemma 3 27B",
    "sonnet55_off": "Claude Sonnet 5.5", "haiku55_off": "Claude Haiku 5.5", "haiku55_ah": "Claude Haiku 5.5",
    "gemini_r": "Gemini 3.8 Flash", "opus55_ad": "Claude Opus 5.5"}


def pick(e):
    return {"share": e["share"], "ci": e["ci"], "num": e["num"], "den": e["den"], "ci_method": e.get("ci_method")}


def main_figs(reads, frames, groups=("NoReasoning", "Reasoning"), extra_arms=()):
    main, _ = O.compute(reads, frames)
    return {g: {ds: {k: pick(main[g][ds][k]) for k, _ in CONDS} for ds in ("", "FixedRule", "Judgement")}
            for g in list(groups) + list(extra_arms) if g in main}


def both_met_all(reads, frames):
    tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
    jp = [p["id"] for p in frames["pairs"] if p["domain"] in O.JUDGEMENT]
    b = O.FastBoot({d: [p["id"] for p in frames["pairs"] if p["domain"] == d] for d in O.JUDGEMENT})
    f = lambda r: ((int(r["B"]["F"] >= A.HI and r["B"]["O"] >= A.HI), 1) if "B" in r and r["B"]["valid"] else (0, 0))
    g = lambda r: ((int(r["B"]["F"] <= A.LO and r["B"]["O"] <= A.LO), 1) if "B" in r and r["B"]["valid"] else (0, 0))
    arms = sorted(tables)
    return {"both_met": pick(b.est(A.counts(tables, arms, jp, f))),
            "both_not_met": pick(b.est(A.counts(tables, arms, jp, g)))}


def graded(lp_reads, frames):
    """Log-probability models, judgement cases, alone: P(yes) differences in cells with both P(yes) in [0.05, 0.95]."""
    strata = [[p["id"] for p in frames["pairs"] if p["domain"] == d] for d in O.JUDGEMENT]
    jp = {p for s in strata for p in s}
    per_all, per_split, n_cells, n_judge = {}, {}, 0, 0
    by_arm = {}
    for a in LOGPROB_ARMS:
        r = lp_reads[a]
        t = A.pair_cells(r, frames)
        for uk, u in r["units"].items():
            cond, pid = uk.split("|")
            if cond != "B" or pid not in jp:
                continue
            F, Ob = u["cells"]["F"], u["cells"]["O"]
            assert F["readout"] == "logprob" and Ob["readout"] == "logprob", (a, uk)
            if F["gate"] != "PASSED" or Ob["gate"] != "PASSED":
                continue
            n_judge += 1
            pf, po = F["yes_rate"], Ob["yes_rate"]
            if not (GRADED_LO <= pf <= GRADED_HI and GRADED_LO <= po <= GRADED_HI):
                continue
            n_cells += 1
            by_arm[a] = by_arm.get(a, 0) + 1
            per_all.setdefault(pid, []).append((a, pf - po))
            s_ = t.get(pid, {}).get("A")
            if s_ and s_["valid"] and s_["split"]:
                per_split.setdefault(pid, []).append((a, pf - po))
    b = PD.Boot(strata)
    return {"all": b.stat(per_all), "given_split": b.stat(per_split), "cells_in_band": n_cells,
            "judgement_cells_valid": n_judge, "in_band_by_model": by_arm,
            "band": [GRADED_LO, GRADED_HI]}


def pair_let(reads, frames, pid="D2"):
    """One pair's failing outside the rule let through, by group: a share of models, models resampled (one pair)."""
    tables = {a: A.pair_cells(r, frames) for a, r in reads.items()}
    dom = next(p["domain"] for p in frames["pairs"] if p["id"] == pid)
    b = O.FastBoot({dom: [pid]})
    return {g: pick(b.est(A.counts(tables, [a for a in arms if a in tables], [pid], A.m_let())))
            for g, arms in O.GROUPS.items()}


def drop_pairs(frames, pids):
    f = copy.deepcopy(frames)
    f["pairs"] = [p for p in f["pairs"] if p["id"] not in pids]
    return f


def weak_side(reads, frames):
    main, _ = O.compute(reads, frames)
    return sorted(a for a in reads if main[a][""]["A"]["share"] is not None and main[a][""]["A"]["share"] < 0.5)


# the pair codes' first letter names the domain; the main text describes pairs by domain, and the codes stay in the
# appendix, where Table 1 defines them
PAIR_DOMAIN = {"I": "insurance disclosure", "T": "statutory thresholds", "K": "seniority", "D": "dismissal procedure",
               "S": "suitability of advice", "V": "vulnerable customers", "W": "school work"}


def pairs_by_domain(pids):
    """['K2', 'W2', 'W4', 'W6'] -> 'three in school work and one in seniority' (most first)."""
    words = "zero one two three four five six seven eight nine ten".split()
    n = {}
    for p in pids:
        n[PAIR_DOMAIN[p[0]]] = n.get(PAIR_DOMAIN[p[0]], 0) + 1
    parts = [f"{words[c]} in {d}" for d, c in sorted(n.items(), key=lambda x: (-x[1], x[0]))]
    return "none" if not parts else parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def macros(res):
    src = f"{OUT_JSON}#"
    v = {}

    def share(name, e, path):
        if e is None or e["share"] is None:
            return
        v[name] = {"value": e["share"], "kind": "pct", "source": src + path}
        v[name + "Num"] = {"value": e["num"], "kind": "int", "source": src + path + ".num"}
        v[name + "Den"] = {"value": e["den"], "kind": "int", "source": src + path + ".den"}
        if e.get("ci"):
            v[name + "Lo"] = {"value": e["ci"][0], "kind": "pct", "source": src + path + ".ci0"}
            v[name + "Hi"] = {"value": e["ci"][1], "kind": "pct", "source": src + path + ".ci1"}
    share("BothMetAloneAllConfigsJudgement", res["s1"]["both_met"], "s1.both_met")
    share("BothNotMetAloneAllConfigsJudgement", res["s1"]["both_not_met"], "s1.both_not_met")
    for key, nm in (("all", "GradedDiffLogProbJudgement"), ("given_split", "GradedDiffLogProbJudgementGivenSplit")):
        e = res["s2"][key]
        if e:
            v[nm] = {"value": e["mean"], "kind": "pts", "source": src + f"s2.{key}.mean"}
            if e["mean_ci"]:
                v[nm + "Lo"] = {"value": e["mean_ci"][0], "kind": "pts", "source": src + f"s2.{key}.mean_ci0"}
                v[nm + "Hi"] = {"value": e["mean_ci"][1], "kind": "pts", "source": src + f"s2.{key}.mean_ci1"}
            v[nm + "Cells"] = {"value": e["n_cells"], "kind": "int", "source": src + f"s2.{key}.n_cells"}
    v["GradedBandCells"] = {"value": res["s2"]["cells_in_band"], "kind": "int", "source": src + "s2.cells_in_band"}
    v["GradedJudgementCells"] = {"value": res["s2"]["judgement_cells_valid"], "kind": "int",
                                 "source": src + "s2.judgement_cells_valid"}
    for tag, figs in (("ExclLowConsensus", res["s3_low_consensus"]["figures"]),
                      ("LogProbReadout", res["s3_logprob"]), ("StrongSide", res["s4_strong_side"]["figures"])):
        for g, per in figs.items():
            gm = O.ARM_MACRO.get(g, g)
            for ds, ks in per.items():
                for k, mname in CONDS:
                    nm = f"{tag}{mname}{gm}{ds}" if tag == "LogProbReadout" else f"{mname}{gm}{ds}{tag}"
                    share(nm, ks[k], f"{tag}.{g}.{ds or 'all'}.{k}")
    for g, e in res["d2_let"].items():
        share(f"LetThroughDTwo{g}", e, f"d2_let.{g}")
    lc = res["s3_low_consensus"]["pairs"]
    v["LowConsensusPairs"] = {"value": ", ".join(f"\\pairid{{{p}}}" for p in lc) or "none", "kind": "str",
                              "source": src + "s3_low_consensus.pairs"}
    v["LowConsensusPairsCount"] = {"value": len(lc), "kind": "word", "source": src + "s3_low_consensus.pairs"}
    v["LowConsensusPairsDomains"] = {"value": pairs_by_domain(lc), "kind": "str", "source": src + "s3_low_consensus.pairs"}
    ws = res["s4_strong_side"]["dropped"]
    v["WeakSideModels"] = {"value": ", ".join(f"\\model{{{O.ARM_LABEL[a]}}}" for a in ws), "kind": "str",
                           "source": src + "s4_strong_side.dropped"}
    v["WeakSideModelsCount"] = {"value": len(ws), "kind": "word", "source": src + "s4_strong_side.dropped"}
    v["NumConfigurations"] = {"value": res["s3_counts"]["configurations"], "kind": "int", "source": src + "s3_counts.configurations"}
    v["NumDistinctModels"] = {"value": res["s3_counts"]["models"], "kind": "int", "source": src + "s3_counts.models"}
    v["NumModelsBothWays"] = {"value": len(res["s3_counts"]["both_ways"]), "kind": "word", "source": src + "s3_counts.both_ways"}
    return v


def pc(e):
    if not e or e["share"] is None:
        return "n/a"
    lo, hi = e["ci"] or (e["share"], e["share"])
    return f"{100 * e['share']:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}] ({e['num']}/{e['den']})" + \
        (" W" if e.get("ci_method") == "wilson" else "")


def markdown(res):
    L = ["# Checks after review (analysis instruction, sections 1 to 4)", "",
         "Run 259's responses; no new calls. Generated by `analysis/review_checks.py`. Intervals: 95% bootstrap over "
         "pairs within domain and models together (10,000 resamples); W marks a Wilson interval replacing a degenerate "
         "bootstrap one.", "", "## 1. Judgement cases alone, all 20 configurations", "",
         f"- Both parties fail: {pc(res['s1']['both_not_met'])} of valid cells.",
         f"- Both parties pass: {pc(res['s1']['both_met'])} of valid cells.", "",
         "The full three-way split by group and model is in results/WRONG_KINDS_v3.md.", "",
         "## 2. Graded check (log-probability models, judgement cases, alone)", ""]
    s2 = res["s2"]
    for key, lab in (("all", "all cells in the band"), ("given_split", "pairs the model splits side by side")):
        e = s2[key]
        L.append(f"- {lab}: mean party difference {100 * e['mean']:+.1f} points "
                 f"[{100 * e['mean_ci'][0]:+.1f}, {100 * e['mean_ci'][1]:+.1f}], {e['n_cells']} cells" if e and e["mean_ci"]
                 else f"- {lab}: {e}")
    L += [f"- Cells with both P(yes) in [{GRADED_LO}, {GRADED_HI}]: {s2['cells_in_band']} of "
          f"{s2['judgement_cells_valid']} valid judgement cells; by model {s2['in_band_by_model']}.", "",
          "## 3. Robustness", "",
          f"Judgement pairs split by fewer than four of the seven reasoning models: "
          f"{', '.join(res['s3_low_consensus']['pairs']) or 'none'}.", "",
          "| Group | Condition | All judgement pairs | Without them |", "|---|---|---|---|"]
    for g in ("NoReasoning", "Reasoning"):
        for k, mname in CONDS[:4]:
            L.append(f"| {g} | {mname} | {pc(res['s3_full'][g]['Judgement'][k])} | "
                     f"{pc(res['s3_low_consensus']['figures'][g]['Judgement'][k])} |")
    L += ["", "Readouts: the log-probability readout (run 259 as banked) beside the paper's sampled readout.", "",
          "| Unit | Cases | Condition | Log-probability readout | Sampled (paper) |", "|---|---|---|---|---|"]
    for g, per in res["s3_logprob"].items():
        for ds in ("", "FixedRule", "Judgement"):
            for k, mname in CONDS:
                L.append(f"| {g} | {ds or 'all'} | {mname} | {pc(per[ds][k])} | {pc(res['s3_sampled'][g][ds][k])} |")
    c = res["s3_counts"]
    L += ["", f"Configurations {c['configurations']}, distinct models {c['models']}; read both ways: "
          f"{', '.join(c['both_ways'])}.", "", "## 4. Without the models that split fewer than half of pairs side by side",
          "", f"Dropped: {', '.join(O.ARM_LABEL[a] for a in res['s4_strong_side']['dropped'])}.", "",
          "| Group | Cases | Condition | All models | Without them |", "|---|---|---|---|---|"]
    for g in ("NoReasoning", "Reasoning"):
        for ds in ("", "FixedRule", "Judgement"):
            for k, mname in CONDS[:4]:
                L.append(f"| {g} | {ds or 'all'} | {mname} | {pc(res['s3_full'][g][ds][k])} | "
                         f"{pc(res['s4_strong_side']['figures'][g][ds][k])} |")
    return "\n".join(L) + "\n"


def run(reads, lp_reads, frames):
    full = main_figs(reads, frames)
    main, tables = O.compute(reads, frames)
    low = O.consensus(tables, frames)["fewer_than_four"]
    ws = weak_side(reads, frames)
    strong = {a: r for a, r in reads.items() if a not in ws}
    both_ways = sorted({m for a, m in DISTINCT_MODELS.items() if a in reads
                        and sum(1 for b, mm in DISTINCT_MODELS.items() if mm == m and b in reads) > 1})
    return {"s1": both_met_all(reads, frames), "s2": graded(lp_reads, frames), "s3_full": full,
            "d2_let": pair_let(reads, frames),
            "s3_low_consensus": {"pairs": low, "figures": main_figs(reads, drop_pairs(frames, set(low)))},
            "s3_logprob": main_figs(lp_reads, frames, extra_arms=LOGPROB_ARMS),
            "s3_sampled": main_figs(reads, frames, extra_arms=LOGPROB_ARMS),
            "s3_counts": {"configurations": len(reads), "models": len({DISTINCT_MODELS[a] for a in reads}),
                          "both_ways": both_ways},
            "s4_strong_side": {"dropped": ws, "figures": main_figs(strong, frames)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads", required=True); ap.add_argument("--logprob-reads", required=True)
    ap.add_argument("--frames", required=True)
    a = ap.parse_args()
    frames = json.load(open(a.frames))
    reads, _ = A.load_reads(a.reads)
    lp, _ = A.load_reads(a.logprob_reads)
    res = run(reads, lp, frames)
    md = markdown(res)
    for p, body in ((OUT_JSON, json.dumps(res, indent=1)), (OUT_MD, md)):
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            if open(fp).read() != body:
                sys.exit(f"REFUSING: {p} exists and differs")
        else:
            open(fp, "x").write(body)
    n = PD.add_macros(macros(res), OUT_JSON, own=(OUT_JSON, "results/review_checks.json"))
    print(md)
    print(f"macros into paper/numbers.tex (now {n})")


if __name__ == "__main__":
    main()
