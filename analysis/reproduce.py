#!/usr/bin/env python3
"""reproduce.py : every figure in the paper from the banked model responses. No calls.

    python analysis/reproduce.py                 # all parts; default: banked/
    python analysis/reproduce.py --ai DIR        # the banked responses elsewhere
    python analysis/reproduce.py --part NAME     # one part (each part runs in its own process)

TWO STAGES.
  1. RESULTS. Each results file the paper cites is recomputed from the banked responses (banked/records, the read
     records; banked/data, the frozen items) by the script that wrote it, and compared with the banked file:
     numbers to within 1e-12 (the banked files carry last-bit differences such as 0.9999999999999999 for 1.0), every
     other value exactly.
  2. MACROS. paper/numbers.tex is regenerated from the results files by each script's own macro builder and compared
     with the committed file byte for byte. Which builder supplies each macro is read from the source recorded for it
     in paper/numbers.json (its file and path); the value never is. A macro whose recorded source no builder produces
     is reported missing, and the stage fails.
Each part runs in a fresh process, because the seven-domain pooling extends the analysis modules' domain lists in
process (analysis/seven_domains.py, extend_domains).
"""
import argparse, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
DEFAULT_AI = os.path.join(ROOT, "banked")
TOL = 1e-12
RESULTS_PARTS = ("first_session", "seven_domains", "second_session", "school_work", "second_review", "file_verdicts",
                 "held_to_less", "controls", "mirror")


def canon(x):
    return json.loads(json.dumps(x, default=lambda v: None))


def bank(p):
    return json.load(open(os.path.join(ROOT, p)))


def compare(got, path, keys=None):
    import seven_domains as SD
    b, g = bank(path), canon(got)
    keys = keys or sorted(set(b) | set(g))
    bad = []
    for k in keys:
        if k not in b or k not in g:
            bad.append(f"{k}: missing on one side")
            continue
        bad += SD.differs(g[k], b[k], k, TOL)
    print(f"  {'ok  ' if not bad else 'FAIL'} {path}" + ("" if keys is None else f" ({', '.join(keys)})"))
    for x in bad[:5]:
        print(f"         {x}")
    return not bad


# ── stage 1: results ──────────────────────────────────────────────────────────────────
def part_first_session(ai):
    """The first session's six domains: outcomes, party difference, wrong kinds, review checks, domain drop, void check."""
    import seven_domains as SD
    reads, frames, controls, settled, lp = SD.load(ai)
    got = SD.compute(reads, frames, controls, settled, lp)
    ok = compare(got["outcomes"], "results/outcomes_run259_v6.json",
                 ["main", "cut_half", "consensus", "wrong_verdicts", "one_order"])
    ok &= compare(got["party_difference"], "results/party_difference_v4.json", ["run259", "run259_alone_given_split"])
    ok &= compare(got["wrong_kinds"], "results/wrong_kinds_v3.json", ["stats"])
    rest = SD.compute_rest(reads, frames, lp, canon(got["outcomes"]))
    ok &= compare(rest["review_checks"], "results/review_checks_v2.json")
    # the first session's file was written by analysis/draft_macros.py, which keeps the domain names capitalised
    dd = rest["domain_drop"]["drop"]
    ok &= compare(dict(rest["domain_drop"], min=min(dd, key=dd.get), max=max(dd, key=dd.get)),
                  "results/domain_drop_v4.json", ["drop", "ci", "min", "max"])
    ok &= compare(rest["haiku_void_check"], "results/haiku55_void_check_v2.json",
                  ["excluded", "pair_records_removed", "figures"])
    return ok


def part_seven_domains(ai):
    """The paper's main figures: both sessions' reads pooled over seven domains (analysis/seven_domains.py)."""
    import seven_domains as SD
    reads0, frames0, controls, settled, lp = SD.load(ai)
    reads, frames, _, _ = SD.merge(ai, reads0, frames0)
    SD.extend_domains()
    res = SD.compute(reads, frames, controls, settled, lp)
    res.update(SD.compute_rest(reads, frames, lp, canon(res["outcomes"])))
    res["frames_seven_domains"] = frames
    ok = True
    for k, p in SD.F.items():
        ok &= compare(res[k], p)
    return ok


def part_second_session(ai):
    import run261 as R61
    argv, sys.argv = sys.argv, ["run261.py", "--ai", ai, "--dry"]
    try:
        res = R61.main()
    finally:
        sys.argv = argv
    return compare(res, R61.OUT_JSON)


def part_school_work(ai):
    import school_work as SW
    return compare(SW.run(ai), SW.OUT)


def part_second_review(ai):
    import second_review as SR
    return compare(SR.run(ai), SR.OUT)


def part_file_verdicts(ai):
    import file_verdicts as FV
    return compare(FV.run(ai), FV.OUT)


def part_held_to_less(ai):
    import held_to_less as HL
    return compare(HL.run(ai), HL.OUT)


def part_controls(ai):
    import controls as CT
    rec = os.path.join(ai, "records")
    items = json.load(open(os.path.join(ROOT, "items/run260_items.json")))
    r259 = CT.load(rec, "RUN259_READ__")
    res = CT.analyse(CT.load(rec, "RUN260_READ__"), r259, items, json.load(open(os.path.join(rec, "RUN259_FRAMES.json"))))
    ok = compare(res, "results/controls_run260.json")
    return ok & compare(CT.settled(canon(res), r259, items), "results/controls_run260_settled.json")


def part_mirror(ai):
    import run266 as R66
    return compare(R66.compute(ai), R66.OUT_JSON)


# ── stage 2: macros ───────────────────────────────────────────────────────────────────
def part_macros(ai):
    import analyse as A
    import macros as M
    import outcomes as O
    import party_difference as PD
    import wrong_kinds as WK
    import review_checks as RC
    import draft_macros as DM
    import haiku_void_check as HV
    import seven_domains as SD
    import run261 as R61
    import school_work as SW
    import second_review as SR
    import file_verdicts as FV
    import held_to_less as HL
    import run266 as R66
    import bootstrap_macros as BM
    import review_counts as RCN
    import low_consensus as LC

    spec = {k: x for k, x in bank("paper/numbers.json").items() if not k.startswith("_")}
    cands = {}

    def add(d, prefix=""):
        for n, x in d.items():
            cands.setdefault(prefix + n, []).append({k: x[k] for k in ("value", "kind", "source")})

    # the first session's design (six domains): the builders on the first session's results. Only the names the
    # seven-domain swap copied to FirstSession<Name> keep these values (results/seven/swap_log.json).
    reads0, frames0, *_ = SD.load(ai)
    settled_src = "results/controls_run260_settled.json"
    six = {}
    v6 = bank("results/outcomes_run259_v6.json")
    v, _ = O.build_macros(v6, "results/outcomes_run259_v6.json", bank(settled_src), settled_src, None, regrouped=False)
    six.update(v)
    main, _ = PD.build_macros(bank("results/party_difference_v4.json"), "results/party_difference_v4.json")
    six.update(main)
    six.update(WK.build_macros(bank("results/wrong_kinds_v3.json"), "results/wrong_kinds_v3.json"))
    six.update(RC.macros(bank("results/review_checks_v2.json")))
    six.update(DM.drop_macros(v6)[1])
    hv = bank("results/haiku55_void_check_v2.json")
    six.update(HV.macros(hv["excluded"], reads0[HV.ARM], hv["pair_records_removed"], hv["figures"]))
    firsts = bank("results/seven/swap_log.json")["first_session_copies"]
    add({n: six[n[len(SD.FIRST):]] for n in firsts if n[len(SD.FIRST):] in six})
    add({n: x for n, x in six.items()})        # names not swapped keep the first session's builders

    # the paper's main figures, seven domains
    reads, frames, _, _ = SD.merge(ai, reads0, frames0)
    SD.extend_domains()
    res7 = {k: bank(p) for k, p in SD.F.items()}
    res7["_haiku_read"] = reads[HV.ARM]
    add(SD.all_macros(res7))

    # the second session, school work, the second review, the files, held to less, the mirror, the method constants
    r61 = bank(R61.OUT_JSON)
    add(R61.macros(r61))
    draft = json.load(open(os.path.join(ai, "data/sfv_261/draft_v2.json")))
    add({"NumPairsEducation": {"value": len(draft["education"]["pairs"]), "kind": "word",
                               "source": "data/sfv_261/draft_v2.json#education.pairs"},
         "NumPairsAllSeven": {"value": len(draft["example_of"]), "kind": "int", "source": "data/sfv_261/draft_v2.json#example_of"}})
    add(SW.macros(bank(SW.OUT)))
    add(SR.macros(bank(SR.OUT))[0])
    add(FV.macros(bank(FV.OUT)))
    add(HL.macros(bank(HL.OUT)))
    add(R66.macros(bank(R66.OUT_JSON)))
    add(BM.build())

    def choose(names):
        out, missing, conflict = {}, [], []
        for n in names:
            want = spec[n]["source"]
            hit = [x for x in cands.get(n, []) if x["source"] == want]
            if not hit:
                missing.append(n)
                continue
            if len({M.fmt(x["value"], x["kind"]) for x in hit}) > 1:
                conflict.append(n)
            out[n] = hit[-1]
        return out, missing, conflict

    later = {n for n, x in spec.items() if x["source"].startswith(("analysis/review_counts.py#", "analysis/low_consensus.py#"))}
    vals, missing, conflict = choose(sorted(set(spec) - later))
    # the counts asserted against the paper's other macros, and the low-consensus maximum, from the values just built
    add(RCN.build(ai, vals, bank("results/seven/outcomes.json")))
    add(LC.build(vals)[0])
    v2, m2, c2 = choose(sorted(later))
    vals.update(v2); missing += m2; conflict += c2
    print(f"  macros: {len(spec)} in the paper; {len(vals)} rebuilt; {len(missing)} with no builder; {len(conflict)} in conflict")
    for n in missing[:10]:
        print(f"    no builder: {n} ({spec[n]['source'][:90]})")
    for n in conflict[:10]:
        print(f"    conflict: {n}")
    d = tempfile.mkdtemp()
    t, s = os.path.join(d, "numbers.tex"), os.path.join(d, "numbers.json")
    M.write_macros(vals, t, s)
    same = open(t, "rb").read() == open(os.path.join(ROOT, "paper", "numbers.tex"), "rb").read()
    print(f"  {'ok  ' if same else 'FAIL'} paper/numbers.tex {'reproduced byte for byte' if same else 'differs'}")
    if not same:
        a, b = open(t).read().splitlines(), open(os.path.join(ROOT, "paper", "numbers.tex")).read().splitlines()
        diff = sorted(set(a) ^ set(b))
        for x in diff[:10]:
            print(f"    {'+' if x in a else '-'} {x[:140]}")
    return same and not missing and not conflict


PARTS = {k: globals()[f"part_{k}"] for k in RESULTS_PARTS + ("macros",)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=DEFAULT_AI, help="the banked responses (default: banked/)")
    ap.add_argument("--part", choices=sorted(PARTS))
    a = ap.parse_args()
    ai = os.path.abspath(a.ai)
    if a.part:
        print(f"[{a.part}]", flush=True)
        return 0 if PARTS[a.part](ai) else 1
    fails = []
    for p in PARTS:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--ai", ai, "--part", p], cwd=ROOT)
        if r.returncode:
            fails.append(p)
    print("ALL REPRODUCED" if not fails else f"NOT REPRODUCED: {', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
