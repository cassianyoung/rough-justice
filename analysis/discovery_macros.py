#!/usr/bin/env python3
"""discovery_macros.py : the figures Appendix G (exploratory findings) quotes from the discovery runs before run 259. No new calls.

    python analysis/discovery_macros.py

Reads the run records copied byte for byte from banked/records/ into discovery/run<N>/ (results, frames, reads,
route checks, outcomes and pre-registrations) and writes macros with the prefix Expl into paper/numbers_exploratory.tex
(through party_difference.write_exploratory, which keeps the other scripts' exploratory macros). Every count the
appendix gives for the size of a run (pairs, models, draws) is read from the run's own frames or reads and asserted
where the outcomes file states it. Nothing here is a registered result.

Measures, as each run defines them (its outcomes file):
  runs 248, 251, 252  share = the alone gap / the side-by-side gap on a graded scale (digit 0-9 unless named), median
                      over models; "holds" = the alone gap is above that model's noise floor.
  run 253             the yes/no verdict: split side by side, and whether the split holds alone, per model.
  runs 254, 255       route checks: a cell matches when its mean over ten draws is within the band of the other read.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import party_difference as PD                                   # noqa: E402

SRC = "analysis/discovery_macros.py"
D = os.path.join(ROOT, "discovery")
WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()


def load(run, name):
    return json.load(open(os.path.join(D, f"run{run}", f"RUN{run}_{name}.json")))


def reads(run):
    return sorted(f for f in os.listdir(os.path.join(D, f"run{run}")) if f.startswith(f"RUN{run}_READ__"))


def main():
    v = {}

    def put(name, value, kind, src):
        assert name not in v, name
        v["Expl" + name] = {"value": value, "kind": kind, "source": f"{SRC}#{src}"}

    # Run numbers, from each result's own "run" field.
    for run, name in ((248, "AbsentComparison"), (251, "StandardsSurvey"), (252, "GradingVariations"),
                      (253, "Verdicts"), (254, "OrgVariations"), (255, "ScaleCeiling")):
        r = load(run, "RESULT")["run"]
        assert str(r).split()[0] == str(run), (run, r)
        put(f"Run{name}", run, "int", f"discovery/run{run}/RUN{run}_RESULT.json run")

    # Draws: ten per cell on every model without reasoning in runs 248 and 251 to 253, five on run 248's reasoning
    # models (each read records its draws).
    for run in (248, 251, 252, 253):
        ds = {}
        for f in reads(run):
            x = load(run, f[len(f'RUN{run}_'):-5])
            ds.setdefault(x.get("group", "off"), set()).add(x["draws"])
        assert ds.get("off", {10}) == {10} and all(d == {10} for g, d in ds.items() if g != "r"), (run, ds)
        if run == 248:
            assert ds.get("r") == {5}, ds
    put("DiscoveryDraws", "ten", "str", "RUN{248,251,252,253}_READ__*.json draws")
    put("AbsentDrawsReasoning", "five", "str", "RUN248_READ__*.json draws, group r")

    # ── Run 252: the subject (people, animals, eras, organisations) and the response format ──
    f252, r252 = load(252, "FRAMES"), load(252, "RESULT")
    arms252 = r252["arms_read"]
    assert len(arms252) == 4 and f252["draws"] == 10
    put("GradingVarModels", WORDS[len(arms252)], "str", "RUN252_RESULT arms_read")
    tests = [p for p in f252["b_pairs"] if p["cat"] == "animals" and not p.get("control") and not p["id"].endswith("C")]
    per_cat = {c: len([p for p in f252["b_pairs"] if p["cat"] == c]) for c in f252["categories"]}
    assert set(per_cat.values()) == {3}, per_cat                  # two test pairs and one control each (pre-registration)
    put("SubjectTestPairs", "two", "str", "RUN252_FRAMES b_pairs: two test pairs and one control per category")
    B = r252["pooled"]["B"]
    for c, nm in (("animals", "Animals"), ("eras", "Eras"), ("organisations", "Organisations")):
        put(f"Subject{nm}Share", B[c]["share"], "pct", f"RUN252_RESULT pooled.B.{c}.share")
        put(f"Subject{nm}Holds", WORDS[B[c]["holds"]], "str", f"RUN252_RESULT pooled.B.{c}.holds")
    A = r252["pooled"]["A"]
    for c, nm in (("digit", "Digit"), ("marks", "Marks"), ("letter", "Letter"), ("words", "Words"),
                  ("passfail", "PassFail"), ("decision", "Decision")):
        put(f"Format{nm}Share", A[c]["share"], "pct", f"RUN252_RESULT pooled.A.{c}.share")
        put(f"Format{nm}Holds", WORDS[A[c]["holds"]], "str", f"RUN252_RESULT pooled.A.{c}.holds")
    assert A["passfail"]["A"] == 0.0
    gp = [p for p in f252["grading_pairs"] if not p.get("control")]
    put("FormatTestPairs", WORDS[len(gp)], "str", "RUN252_FRAMES grading_pairs, controls excluded")

    # ── Run 248: grading and four other domains, eleven models without reasoning ──
    r248 = load(248, "RESULT")
    off, rs = r248["off"], r248["r"]
    put("AbsentModelsOff", WORDS[len(off["arms"])], "str", "RUN248_RESULT off.arms")
    put("AbsentModelsReasoning", WORDS[len(rs["arms"])], "str", "RUN248_RESULT r.arms")
    f248 = load(248, "FRAMES")
    pairs248 = [p for p in f248["pairs"] if not p.get("control")]
    by_dom = {}
    for p in pairs248:
        by_dom[p["domain"]] = by_dom.get(p["domain"], 0) + 1
    doms = {d: n for d, n in by_dom.items() if d in off["domains"]}
    assert len(doms) == 5 and set(doms.values()) == {4}, by_dom
    put("AbsentDomains", "five", "str", "RUN248_FRAMES pairs by domain")
    put("AbsentPairsPerDomain", "four", "str", "RUN248_FRAMES pairs by domain")
    for dom, nm in (("grading", "Grading"), ("effort", "Effort"), ("proportionality", "Proportionality"),
                    ("prices", "Prices"), ("performance", "Performance")):
        put(f"Absent{nm}ShareOff", off["domains"][dom]["median_share"], "pct", f"RUN248_RESULT off.domains.{dom}.median_share")
        put(f"Absent{nm}ShareReasoning", rs["domains"][dom]["median_share"], "pct", f"RUN248_RESULT r.domains.{dom}.median_share")

    # ── Run 251: twelve domains, two pairs each, four models ──
    r251, f251 = load(251, "RESULT"), load(251, "FRAMES")
    assert len(r251["pooled"]) == 12 and len(f251["arms"]) == 4
    put("SurveyDomains", "twelve", "str", "RUN251_RESULT pooled")
    tp = [p for p in f251["pairs"] if not p.get("control")]
    assert len(tp) == 24, len(tp)
    put("SurveyPairsPerDomain", "two", "str", "RUN251_FRAMES pairs, controls excluded (24 over twelve domains)")
    for dom, nm in (("seniority", "Seniority"), ("vulnerable", "Vulnerable"), ("grading", "Grading")):
        x = r251["pooled"][dom]
        put(f"Survey{nm}Share", x["share"]["median"], "pct", f"RUN251_RESULT pooled.{dom}.share.median")
        put(f"Survey{nm}Holds", WORDS[x["holds_alone_arms"]] if isinstance(x["holds_alone_arms"], int)
            else WORDS[len(x["holds_alone_arms"])], "str", f"RUN251_RESULT pooled.{dom}.holds_alone_arms")

    # ── Run 253: the yes/no verdict alone, eleven domains ──
    vd = load(253, "RESULT")["pooled"]["verdict"]
    assert len(vd) == 11
    put("VerdictDomains", "eleven", "str", "RUN253_RESULT pooled.verdict")
    units = json.load(open(os.path.join(D, "run253", "RUN253_READ__claude.json")))["units"]
    vt = [k for k, u in units.items() if k.startswith("V|") and not u["control"]]
    put("VerdictTestPairs", len(vt), "int", "RUN253_READ__claude units V| not control")
    put("VerdictModels", WORDS[len(reads(253))], "str", "RUN253_READ__*.json")
    split4 = sorted(d for d, x in vd.items() if sum(a.get("split_side_by_side", False) for a in x["per_arm"].values()) == 4)
    put("VerdictSplitAllModels", WORDS[len(split4)], "str", "RUN253_RESULT verdict per_arm split_side_by_side, 4 of 4")
    held = {d: x["holds"] for d, x in vd.items()}
    put("VerdictHoldsNoneDomains", WORDS[sum(1 for h in held.values() if h == 0)], "str", "RUN253_RESULT verdict holds == 0")
    put("VerdictHoldsGrading", WORDS[held["grading"]], "str", "RUN253_RESULT pooled.verdict.grading.holds")
    put("VerdictHoldsMax", WORDS[max(held.values())], "str", "RUN253_RESULT max verdict holds")

    # ── Route and session drift: runs 254 and 255 (Claude Sonnet 5) ──
    rc = load(254, "CLAUDE_ROUTE_CHECK")
    m = sum(1 for c in rc["cells"].values() if c.get("matches", c.get("within_band")))
    assert len(rc["cells"]) == 10 and rc["calls"] == 100, (len(rc["cells"]), rc["calls"])
    put("RouteCheckCells", "ten", "str", "RUN254_CLAUDE_ROUTE_CHECK cells")
    put("RouteCheckMatch", WORDS[m], "str", "RUN254_CLAUDE_ROUTE_CHECK cells matching")
    tri = load(255, "CLAUDE_ROUTE_TRIANGLE")
    assert len(tri["cells"]) == 10 and tri["calls"] == 100
    put("RouteTriangleMatchBanked", WORDS[tri["n_matches_banked"]], "str", "RUN255_CLAUDE_ROUTE_TRIANGLE n_matches_banked")
    put("RouteTriangleMatchDirect", WORDS[tri["n_matches_direct"]], "str", "RUN255_CLAUDE_ROUTE_TRIANGLE n_matches_direct")
    both = [k for k, c in tri["cells"].items() if not c["matches_banked"] and c["matches_direct"]]
    put("RouteTriangleOvernight", WORDS[len(both)], "str", "RUN255_CLAUDE_ROUTE_TRIANGLE cells changed on both routes")

    # ── Run 262: draws (the other figures are party_difference.py's) ──
    d262 = {load(262, f[len('RUN262_'):-5])["arm"]: load(262, f[len('RUN262_'):-5])["draws"] for f in reads(262)}
    assert {d for a, d in d262.items() if a.endswith("_r")} == {5} and {d for a, d in d262.items() if not a.endswith("_r")} == {10}, d262
    put("ExampleOnlyDrawsOff", "ten", "str", "RUN262_READ__*.json draws (models without reasoning)")
    put("ExampleOnlyDrawsReasoning", "five", "str", "RUN262_READ__*.json draws (models with reasoning)")
    put("RunExampleOnly", 262, "int", "discovery/run262/RUN262_RESULT.json")

    print(json.dumps({k: x["value"] for k, x in v.items()}, indent=1))
    print(f"exploratory macros now {write(v)}")


def write(new):
    """Adds these macros to paper/numbers_exploratory.tex: replaces this script's earlier ones, refuses a name another
    script owns, and asserts every other line is unchanged."""
    side = json.load(open(PD.EXPL_SIDECAR))
    mine = lambda x: str(x.get("source", "")).startswith(f"{SRC}#")
    keep = {k: x for k, x in side.items() if not k.startswith("_") and not mine(x)}
    clash = sorted(set(new) & set(keep))
    if clash:
        sys.exit(f"REFUSING: exploratory macros already defined elsewhere: {clash[:5]}")
    before = {l for l in open(PD.EXPL_TEX).read().splitlines()
              if l.startswith("\\newcommand") and not any(l.startswith(f"\\newcommand{{\\{k}}}") for k in side if k not in keep)}
    vals = {k: {f: x[f] for f in ("value", "kind", "source") if f in x} for k, x in keep.items()}
    vals.update(new)
    n = PD.M.write_macros(vals, PD.EXPL_TEX, PD.EXPL_SIDECAR, extra={k: x for k, x in side.items() if k.startswith("_")})
    body = open(PD.EXPL_TEX).read()
    open(PD.EXPL_TEX, "w").write(PD.EXPL_NOTE + body.replace("paper/numbers.json", "paper/numbers_exploratory.json"))
    lost = before - set(open(PD.EXPL_TEX).read().splitlines())
    assert not lost, f"existing exploratory lines changed: {sorted(lost)[:3]}"
    return n


if __name__ == "__main__":
    main()
