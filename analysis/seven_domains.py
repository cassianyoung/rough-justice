#!/usr/bin/env python3
"""seven_domains.py : the paper's main figures pooled over all seven domains and 42 pairs.
No new calls.

    python analysis/seven_domains.py --ai DIR --check     # reproduce the banked six-domain results; write nothing
    python analysis/seven_domains.py --ai DIR             # compute, write results/seven/*, swap the main macros

INPUTS. The first session's reads (the matched readout, banked/records/RUN259_MATCHED_READS) and frames
(records/RUN259_FRAMES.json), with school work added from the second session (records/RUN261_READ__<arm>.json, block
A: its units "A.<cond>|W<n>" become "<cond>|W<n>", conditions A side by side, B alone, C told in principle, D told a
precise rule, E outside the rule). Both sessions read every one of these by sampling. Two exclusions, both stated in
the paper's method:
  - Kimi K3 has no school-work reads: its second session was read on a new provider and is reported apart, so in the
    group without reasoning it contributes the six domains only.
  - school work's control pair (W1C) is not added; the controls stay those of the first session.
The school-work pairs and their domain (data/sfv_261/draft_v2.json) are added to the frames.

DOMAINS. Every module's domain list is extended in this process only (analyse.DOMAINS, outcomes.JUDGEMENT and DOMSETS
and DOM_LABEL, party_difference.KINDS, wrong_kinds.KINDS, draft_macros.DOMAINS); school work is a judgement domain.
The code that computes each figure is the existing code, unchanged. --check runs the same path with nothing merged and
nothing extended and asserts it reproduces results/outcomes_run259_v6.json, party_difference_v4.json and
wrong_kinds_v3.json exactly, so any difference in the seven-domain figures is the school work and nothing else.

RECOMPUTED (the main figures): outcomes.run (Table 3, the by-domain and per-model figures, consensus, order, cut-off,
wrong verdicts), party_difference (the party-difference measure, alone given a side-by-side split), wrong_kinds, the
domain-drop range (draft_macros), review_checks (both met alone, the low-consensus and strong-side checks, counts), and
the Claude Haiku 5.5 void check. NOT recomputed, and why: the log-probability readout checks (review_checks s2,
s3_logprob, s3_sampled) compare two readouts of the first session's six domains, and school work was read one way
only; the first session's controls; file_verdicts.py and the second-session figures (run261.py, second_review.py,
school_work.py), which are session-specific by design.

MACROS. Every recomputed macro keeps its name and takes the seven-domain value (its source becomes results/seven/...).
Before that, each recomputed macro the main results table or the text uses is copied, with its six-domain value and
original source, to FirstSession<Name>, for the appendix table of the first session's design.
"""
import argparse, copy, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import analyse as A                                             # noqa: E402
import macros as M                                              # noqa: E402
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402
import wrong_kinds as WK                                        # noqa: E402
import review_checks as RC                                      # noqa: E402
import draft_macros as DM                                       # noqa: E402
import haiku_void_check as HV                                   # noqa: E402

OUTDIR = "results/seven"
F = {k: f"{OUTDIR}/{k}.json" for k in ("outcomes", "party_difference", "wrong_kinds", "review_checks", "domain_drop",
                                         "haiku_void_check", "frames_seven_domains")}
KIMI = "kimi"
EDU = "education"
FIRST = "FirstSession"


# ── inputs ─────────────────────────────────────────────────────────────────────────
def load(ai):
    reads, _ = A.load_reads(os.path.join(ai, "records/RUN259_MATCHED_READS"))
    frames = json.load(open(os.path.join(ai, "records/RUN259_FRAMES.json")))
    controls = json.load(open(os.path.join(ROOT, "results/controls_run260.json")))
    settled = json.load(open(os.path.join(ROOT, "results/controls_run260_settled.json")))
    lp, _ = A.load_reads(os.path.join(ai, "records"))
    return reads, frames, controls, settled, lp


def merge(ai, reads, frames):
    reads, frames = copy.deepcopy(reads), copy.deepcopy(frames)
    draft = json.load(open(os.path.join(ai, "data/sfv_261/draft_v2.json")))
    edu = draft["education"]
    W = [p["id"] for p in edu["pairs"]]
    added = {}
    for a in reads:
        if a == KIMI:
            continue
        r61 = json.load(open(os.path.join(ai, f"records/RUN261_READ__{a}.json")))
        assert bool(r61.get("reasoning")) == bool(reads[a].get("reasoning")), a
        n = 0
        for uk, u in r61["units"].items():
            if not uk.startswith("A."):
                continue
            cond_pid = uk[2:]
            cond, pid = cond_pid.split("|")
            if pid not in W:                                   # the control W1C stays out
                assert u.get("control"), uk
                continue
            assert cond_pid not in reads[a]["units"] and u["domain"] == EDU and not u.get("control")
            reads[a]["units"][cond_pid] = u
            n += 1
        added[a] = n
    frames["pairs"] = frames["pairs"] + [dict(p) for p in edu["pairs"]]
    frames["domains"] = dict(frames["domains"], **{EDU: edu["domain"]})
    r61f = json.load(open(os.path.join(ai, "records/RUN261_FRAMES.json")))
    for uk, u in r61f["units"].items():
        if uk.startswith("A.") and u["pair"] in W:
            frames["units"][uk[2:]] = {k: u[k] for k in ("pair", "domain", "control", "labels", "cond", "prompts")}
    return reads, frames, added, W


def extend_domains():
    """In this process only: school work becomes the seventh domain, a judgement domain."""
    A.DOMAINS = A.DOMAINS + (EDU,)
    O.JUDGEMENT = O.JUDGEMENT + (EDU,)
    O.DOMSETS = {"": A.DOMAINS, "FixedRule": O.FIXED, "Judgement": O.JUDGEMENT,
                 **{d.capitalize(): (d,) for d in A.DOMAINS}}
    O.DOM_LABEL = dict(O.DOM_LABEL, **{EDU: "School work"})
    PD.KINDS = {"FixedRule": O.FIXED, "Judgement": O.JUDGEMENT}
    WK.KINDS = {"FixedRule": O.FIXED, "Judgement": O.JUDGEMENT}
    DM.DOMAINS = DM.DOMAINS + ("Education",)


# ── compute ────────────────────────────────────────────────────────────────────────
def compute(reads, frames, controls, settled, lp):
    out = {"outcomes": O.run(reads, frames, controls, None, settled)}
    out["outcomes"].pop("items", None)
    out["party_difference"] = PD.run(reads, frames, None)
    out["wrong_kinds"] = WK.run(reads, frames)
    return out


def compute_rest(reads, frames, lp, outcomes):
    res = {"review_checks": RC.run(reads, lp, frames)}
    dd, dm = DM.drop_macros(outcomes)
    res["domain_drop"] = {"drop": dd, "ci": DM.drop_ci(outcomes),
                          "min": min(dd, key=dd.get).lower(), "max": max(dd, key=dd.get).lower()}
    ex = HV.excluded(reads[HV.ARM])
    res["haiku_void_check"] = {"excluded": ex, "pair_records_removed": HV.pair_losses(reads[HV.ARM], frames),
                               "figures": {"Excluded": HV.compute(reads, frames, False),
                                           "Wrong": HV.compute(reads, frames, True)}}
    return res


def canon(x):
    return json.loads(json.dumps(x, default=lambda v: None))


def differs(x, y, path, tol=1e-12):
    """Paths where x and y differ, floats compared to within tol (the banked files carry last-bit differences such as
    0.9999999999999999 for 1.0 in Wilson upper bounds)."""
    if isinstance(x, dict) and isinstance(y, dict):
        if set(x) != set(y):
            return [f"{path}: keys {sorted(set(x) ^ set(y))[:4]}"]
        return [d for k in x for d in differs(x[k], y[k], f"{path}.{k}", tol)]
    if isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            return [f"{path}: lengths"]
        return [d for i, (u, w) in enumerate(zip(x, y)) for d in differs(u, w, f"{path}[{i}]", tol)]
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        return [] if abs(x - y) <= tol else [f"{path}: {x} != {y}"]
    return [] if x == y else [f"{path}: {x!r} != {y!r}"]


def check(ai):
    """Nothing merged, nothing extended: the path must reproduce the banked six-domain results exactly."""
    reads, frames, controls, settled, lp = load(ai)
    got = compute(reads, frames, controls, settled, lp)
    bank = {"outcomes": "results/outcomes_run259_v6.json", "party_difference": "results/party_difference_v4.json",
            "wrong_kinds": "results/wrong_kinds_v3.json"}
    for k, p in bank.items():
        b = json.load(open(os.path.join(ROOT, p)))
        g = canon(got[k])
        keys = ("main", "cut_half", "consensus", "wrong_verdicts", "one_order") if k == "outcomes" else \
            (("run259", "run259_alone_given_split") if k == "party_difference" else ("stats",))
        for key in keys:
            bad = differs(g[key], b[key], f"{k}.{key}")
            assert not bad, f"{k}.{key} does not reproduce {p}: {bad[:3]}"
        print(f"reproduces {p} ({', '.join(keys)})")


# ── macros ─────────────────────────────────────────────────────────────────────────
def first_session_names():
    """The macros the main results table uses, and every macro the text cites: their six-domain values are kept as
    FirstSession<Name> so the appendix table and any sentence about the first session's design can cite them."""
    names = set()
    for f in ("paper/tables/table_main.tex", "paper/main.tex"):
        names |= set(re.findall(r"\\([A-Za-z]+)\{\}", open(os.path.join(ROOT, f)).read()))
    return sorted(names)


def swap(new, first_names):
    """new: {name: macro}. Names that exist take the new value and source; new names are added. Before that, each name in
    first_names is copied with its current value and source to FirstSession<Name>. Every other line is asserted
    unchanged."""
    meta = json.load(open(M.SIDECAR))
    vals = {k: {kk: x[kk] for kk in ("value", "kind", "source", "note") if kk in x}
            for k, x in meta.items() if not k.startswith("_")}
    extra = {k: x for k, x in meta.items() if k.startswith("_")}
    firsts = {}
    for n in first_names:
        if n not in vals:
            continue
        x = dict(vals[n])
        x["note"] = "the first session's design: six domains, 36 pairs (seven_domains.py copied it before the swap)"
        firsts[FIRST + n] = x
    clash = sorted(set(firsts) & set(vals))
    keep_before = {l for l in open(M.TEX).read().splitlines()
                   if not any(l.startswith(f"\\newcommand{{\\{k}}}") for k in list(new) + list(firsts))}
    changed = sorted(n for n in new if n in vals and vals[n]["value"] != new[n]["value"])
    added = sorted(n for n in new if n not in vals)
    for n, x in new.items():
        vals[n] = dict(x, note="seven domains, 42 pairs (analysis/seven_domains.py, 2026-11-17)")
    for n, x in firsts.items():
        if n in vals and not vals[n]["source"] == x["source"] and n not in clash:
            sys.exit(f"REFUSING: {n} exists with another source")
        vals[n] = x
    n = M.write_macros(vals, extra=extra)
    lost = keep_before - set(open(M.TEX).read().splitlines())
    assert not lost, f"lines changed that this script does not own: {sorted(lost)[:3]}"
    return n, changed, added, sorted(firsts)


def all_macros(res):
    v, _ = O.build_macros(res["outcomes"], F["outcomes"], res["outcomes"]["settled"],
                          "results/controls_run260_settled.json", None, regrouped=False)
    main, _ = PD.build_macros(res["party_difference"], F["party_difference"])
    v.update(main)
    v.update(WK.build_macros(res["wrong_kinds"], F["wrong_kinds"]))
    rc = RC.macros(res["review_checks"])
    # the readout checks compare two readouts of the first session only (see the docstring): their macros stay
    readout = {n for n, x in rc.items() if any(f"#{k}" in x["source"] for k in ("s2", "s3_logprob", "s3_sampled"))}
    for n, x in rc.items():
        if n not in readout:
            v[n] = dict(x, source=x["source"].replace(RC.OUT_JSON, F["review_checks"]))
    _, dm = DM.drop_macros(res["outcomes"])
    v.update({n: dict(x, source=x["source"].replace(DM.DROP_JSON, F["domain_drop"])) for n, x in dm.items()})
    hv = res["haiku_void_check"]
    hm = HV.macros(hv["excluded"], res["_haiku_read"], hv["pair_records_removed"], hv["figures"])
    v.update({n: dict(x, source=x["source"].replace(HV.OUT_JSON, F["haiku_void_check"])) for n, x in hm.items()})
    return v


def build_tables(ai):
    """The paper's tables and figures on seven domains: the merged reads and frames, the domain lists extended, the
    seven-domain outcomes (results/seven/outcomes.json), and the macros as swapped."""
    import tables as T
    import figures as FG
    reads0, frames0, _, _, _ = load(ai)
    reads, frames, _, _ = merge(ai, reads0, frames0)
    extend_domains()
    res = json.load(open(os.path.join(ROOT, F["outcomes"])))
    nums = json.load(open(M.SIDECAR))
    ts = T.build(frames, reads, res, nums) + [T.table_main(), T.table_both_ways(), T.table_first_session()] + T.tables_run261(nums)
    miss = T.check_macros(ts, nums)
    if miss:
        sys.exit(f"REFUSING: tables use undefined macros: {sorted(miss)[:12]}")
    T.write(ts, nums)
    out, _, _ = FG.build(res)
    print("tables:", ", ".join(t.name for t in ts))
    print("figures:", ", ".join(os.path.basename(p) for p in out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default=os.path.join(ROOT, "banked"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--tables", action="store_true", help="write the tables and figures on seven domains; nothing else")
    a = ap.parse_args()
    if a.check:
        return check(a.ai)
    if a.tables:
        return build_tables(a.ai)
    reads0, frames0, controls, settled, lp = load(a.ai)
    reads, frames, added, W = merge(a.ai, reads0, frames0)
    extend_domains()
    res = compute(reads, frames, controls, settled, lp)
    res.update(compute_rest(reads, frames, lp, res["outcomes"]))
    res["frames_seven_domains"] = frames
    os.makedirs(os.path.join(ROOT, OUTDIR), exist_ok=True)
    for k, p in F.items():
        body = json.dumps(res[k], indent=1, default=lambda v: None)
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            if open(fp).read() != body:
                sys.exit(f"REFUSING: {p} exists and differs")
        else:
            open(fp, "x").write(body)
    res = {k: json.loads(json.dumps(v, default=lambda x: None)) for k, v in res.items()}
    res["_haiku_read"] = reads[HV.ARM]
    v = all_macros(res)
    n, changed, new, firsts = swap(v, sorted(n for n in first_session_names() if n in v))
    json.dump({"added_units": added, "school_work_pairs": W, "macros_changed": changed, "macros_added": new,
               "first_session_copies": firsts}, open(os.path.join(ROOT, OUTDIR, "swap_log.json"), "w"), indent=1)
    print(f"units added per arm: {added}")
    print(f"macros: {len(changed)} changed value, {len(new)} added, {len(firsts)} FirstSession copies; numbers.tex now {n}")


if __name__ == "__main__":
    main()
