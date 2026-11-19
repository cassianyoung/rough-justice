#!/usr/bin/env python3
"""figure1.py : candidates for Figure 1, the worked insurance case. Each candidate is an insurance pair on which one
model split the parties side by side (in each order) and, reading the householder's file alone, wrongly held that the
householder did not meet the standard (its yes-rate below one half, the measure of Table 2). Writes, for the author to
choose from:

    results/FIGURE1_CANDIDATES.md                  both cases, every prompt and response verbatim, the rule, the provision
    paper/figures/fig1_candidate_{a,b,c}.tex       the boxed LaTeX panels (DATA; removed once (a) was chosen)
    paper/figures/preview/fig1_candidates.pdf      the three panels drawn without TeX, for reading only

Every case text, question and answer in the panel is taken from the frames and the read files by the code below;
nothing in them is retyped. The one sentence written by hand is the rule (RULE_PLAIN for the candidates, RULE for
the chosen figure).

With --chosen KEY it writes the figure itself instead (the author's choice and rule sentence):

    paper/figures/fig1_worked.tex                  the boxed panel; each result summarised by code from the responses
    paper/figures/preview/fig1_worked.pdf          the panel drawn without TeX, for reading only

    python analysis/figure1.py --frames FRAMES --reads DIR [--chosen d]
"""
import argparse, collections, json, os, sys, textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import outcomes as O                                            # noqa: E402
from tables import tex_escape                                   # noqa: E402

# The author asked for models readers know (Claude Sonnet 5, GPT-4o, GPT-6 Sol). GPT-6 Sol holds the householder to meet
# the standard alone on all six insurance pairs, so it supplies none; Claude Sonnet 5 qualifies on I6 only.
CANDIDATES = [("a", "claude", "I6"), ("b", "gpt4o", "I5"), ("c", "gpt4o", "I1")]
# drafted from the provision recorded for the pair (identical for all six insurance pairs); for the author to approve
RULE_PLAIN = ("Someone insuring their own home need only take reasonable care not to give the insurer false "
              "information; a business must tell the insurer every material fact, whether asked or not.")


# The author's choice and wording, checked against CIDRA 2012 s.2 and IA 2015 s.3 on legislation.gov.uk.
# 2026-11-18: (a), Claude Sonnet 5 on I6, reverses the parties alone (it passes the business), the rare pattern; the author
# chose (d), the same pair on Claude Haiku 5.5 (thinking off), which fails both files alone, the dominant pattern.
FINAL = {"d": ("d", "haiku55_off", "I6")}
CHOSEN = "d"
RULE = ("Someone insuring their own home need only take reasonable care not to give the insurer false information; a "
        "business must tell the insurer every material circumstance it knows or ought to know, whether asked or not.")


def yes_rate(cell):
    """The measure the paper uses: mean P(yes) where the model was read by log-probability, else the share of yes."""
    ds = cell["draws"]
    if any(d.get("p_yes") is not None for d in ds):
        return sum(d["p_yes"] for d in ds) / len(ds), True
    v = [d.get("answer") for d in ds if d.get("answer") in ("yes", "no")]
    return sum(x == "yes" for x in v) / len(v), False


def side_rate(cell, lab):
    v = [d["parsed"][lab] for d in cell["draws"] if d.get("parsed")]
    return sum(x == "yes" for x in v) / len(v)


def verbatim(cell):
    """Each distinct response exactly as returned, with its count, most common first."""
    return collections.Counter(d["text"] for d in cell["draws"]).most_common()


def counted(cell):
    n = len(cell["draws"])
    return "; ".join(f"`{t}` ({k} of {n})" for t, k in verbatim(cell))


def pyes(cell):
    ps = [d["p_yes"] for d in cell["draws"] if d.get("p_yes") is not None]
    return f"P(yes) {min(ps):.3f} to {max(ps):.3f}, mean {sum(ps) / len(ps):.3f}" if ps else None


def texts(frames, pid):
    side = frames["units"][f"A|{pid}"]["prompts"]
    fo, of = side["side_FO"]["user"], side["side_OF"]["user"]
    lead, body = fo.split("Case HOUSEHOLDER: ", 1)
    hh, rest = body.split(" Case BUSINESS: ", 1)
    bus, question = rest.split(" Judged by", 1)
    question = "Judged by" + question
    alone = frames["units"][f"B|{pid}"]["prompts"]
    a_case, a_q = alone["F"]["user"].split(" Judged by", 1)
    assert of == f"{lead}Case BUSINESS: {bus} Case HOUSEHOLDER: {hh} " + question.replace(
        "HOUSEHOLDER=<yes or no> BUSINESS=<yes or no>", "BUSINESS=<yes or no> HOUSEHOLDER=<yes or no>"), pid
    return dict(lead=lead.strip(), hh=hh, bus=bus, question=question, fo=fo, of=of, system=side["side_FO"]["system"],
                alone=alone["F"]["user"], alone_case=a_case, alone_q="Judged by" + a_q, alone_o=alone["O"]["user"])


def panel_tex(key, arm, pid, t, A, B):
    m = tex_escape(O.ARM_LABEL[arm])
    n = len(B["F"]["draws"])

    def answers(cell, order=""):
        return "; ".join(f"\\texttt{{{tex_escape(x)}}} ({k} of {len(cell['draws'])}{order})" for x, k in verbatim(cell))
    lp = pyes(B["F"])
    return ("% DATA: material quoted as read; exempt from the typed-digit check (tools/check_typed_numbers.py).\n"
            f"% Figure 1 candidate ({key}): {O.ARM_LABEL[arm]}, pair {pid}. Written by analysis/figure1.py; the case "
            "texts, questions and answers are copied from the frames and the responses by code.\n"
            "\\fbox{\\parbox{0.96\\linewidth}{\\footnotesize\\raggedright\n"
            "\\textbf{Case HOUSEHOLDER.} " + tex_escape(t["hh"]) + "\\\\[2pt]\n"
            "\\textbf{Case BUSINESS.} " + tex_escape(t["bus"]) + "\\\\[3pt]\n"
            "\\textbf{Side by side.} \\emph{" + tex_escape(t["question"]) + "}\\\\[1pt]\n"
            "\\model{" + m + "}: " + answers(B["side_FO"], ", householder first") + "; " +
            answers(B["side_OF"], ", business first") + ".\\\\[3pt]\n"
            "\\textbf{The householder's file alone}, the policyholder named: \\emph{" + tex_escape(t["alone_q"]) +
            "}\\\\[1pt]\n"
            "\\model{" + m + "}: " + answers(B["F"]) + (f"; the probability it gave to yes {tex_escape(lp[7:])}"
                                                          if lp else "") + ".\\\\[3pt]\n"
            "\\textbf{The rule.} " + tex_escape(RULE_PLAIN) + "\n}}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True); ap.add_argument("--reads", required=True)
    ap.add_argument("--chosen")
    a = ap.parse_args()
    frames = json.load(open(a.frames))
    if a.chosen:
        return worked(frames, a.reads, a.chosen)
    md = ["# Figure 1: three candidates\n",
          "Insurance pairs on which one model split the parties side by side in each order (householder at least "
          "0.6, business at most 0.4) and, reading the householder's file alone, wrongly held that the householder "
          "did not meet the standard (yes-rate below 0.5, the measure of Table 2). Every prompt and response below is "
          "as sent and as returned in run 259, copied by `analysis/figure1.py`; the counts are over the ten readings "
          "of each cell. GPT-4o was read by log-probability as well as by its sampled text, and the paper's measure "
          "for it is the mean probability of yes, so both are given.\n",
          "Models the author named: GPT-6 Sol held the householder to meet the standard alone on all six insurance pairs "
          "(yes-rate 0.8 to 1.0), so it supplies no candidate. Claude Sonnet 5 qualifies on I6 only. GPT-4o qualifies "
          "on I1, I3, I4 and I5; I3 is left out because four of its ten sampled answers alone were \"Yes\" (mean "
          "P(yes) 0.42), and I4 because three of ten were \"Yes\" and one business-first answer held neither party to meet the standard.\n",
          f"**The rule, in one sentence (drafted from the provision; identical for all six insurance pairs, for the author to "
          f"approve or replace):** {RULE_PLAIN}\n",
          "The LaTeX panels are `paper/figures/fig1_candidate_*.tex`; `paper/main.tex` shows (a) until one is chosen.\n"]
    panels = []
    for key, arm, pid in CANDIDATES:
        r = json.load(open(os.path.join(a.reads, f"RUN259_READ__{arm}.json")))
        A, B = r["units"][f"A|{pid}"]["cells"], r["units"][f"B|{pid}"]["cells"]
        split = all(side_rate(A[c], "HOUSEHOLDER") >= O.A.HI and side_rate(A[c], "BUSINESS") <= O.A.LO
                    for c in ("side_FO", "side_OF"))
        hh_alone, lp = yes_rate(B["F"])
        if not (split and hh_alone < 0.5):
            sys.exit(f"REFUSING: candidate {key} ({arm} {pid}) does not split side by side and fail the householder alone")
        pair = next(p for p in frames["pairs"] if p["id"] == pid)
        t = texts(frames, pid)
        cells = {"side_FO": A["side_FO"], "side_OF": A["side_OF"], "F": B["F"], "O": B["O"]}
        md += [f"## ({key}) {O.ARM_LABEL[arm]}, pair {pid}\n",
               f"Served model `{', '.join(r['served_model'])}` via {', '.join(r['provider_served'])}.\n",
               f"**Case HOUSEHOLDER:** {t['hh']}\n",
               f"**Case BUSINESS:** {t['bus']}\n",
               f"**System prompt (every call):** {t['system']}\n",
               f"**Side-by-side prompt, householder first:**\n\n> {t['fo']}\n",
               f"- Answers: {counted(A['side_FO'])}\n",
               f"**Side-by-side prompt, business first:**\n\n> {t['of']}\n",
               f"- Answers: {counted(A['side_OF'])}\n",
               f"**The householder's file alone:**\n\n> {t['alone']}\n",
               f"- Answers: {counted(B['F'])}" + (f"\n- Log-probability reading: {pyes(B['F'])}" if lp else "") +
               f"\n- Yes-rate as the paper measures it: {hh_alone:.3f}\n",
               f"**The business's file alone** (for completeness):\n\n> {t['alone_o']}\n",
               f"- Answers: {counted(B['O'])}" + (f"\n- Log-probability reading: {pyes(B['O'])}" if lp else "") + "\n",
               f"**Provision (as recorded for the pair):** {pair['provision']}\n"]
        open(os.path.join(ROOT, "paper", "figures", f"fig1_candidate_{key}.tex"), "w").write(
            panel_tex(key, arm, pid, t, A, cells))
        panels.append((key, arm, pid, t, cells))
    out = "\n".join(md) + "\n"
    hits = O.vocabulary_hits(out, [x for _, _, _, t, _ in panels for x in t.values()] +
                             [p.get("provision", "") for p in frames["pairs"]])
    if hits:
        sys.exit(f"REFUSING: candidates text uses retired vocabulary: {hits}")
    open(os.path.join(ROOT, "results", "FIGURE1_CANDIDATES.md"), "w").write(out)
    preview(panels)
    print("wrote results/FIGURE1_CANDIDATES.md, paper/figures/fig1_candidate_{a,b,c}.tex, "
          "paper/figures/preview/fig1_candidates.pdf")


def counts(vals):
    """{verdict: count} over the parsed verdicts of one cell (layout, case and a trailing full stop do not count)."""
    return collections.Counter(vals)


def worked(frames, reads, key):
    """Figure 1 as chosen. Each result is derived here from the PARSED verdicts (a line break
    between the labels or a trailing full stop is the same answer), refusing unless every reading of every cell gave
    the same verdict: side by side HOUSEHOLDER=yes, BUSINESS=no in both orders; alone, no for both files."""
    if key != CHOSEN:
        sys.exit(f"REFUSING: the author chose ({CHOSEN}); change CHOSEN to use another candidate")
    _, arm, pid = FINAL[key]
    r = json.load(open(os.path.join(reads, f"RUN259_READ__{arm}.json")))
    A, B = r["units"][f"A|{pid}"]["cells"], r["units"][f"B|{pid}"]["cells"]
    if any(d.get("p_yes") is not None for c in ("F", "O") for d in B[c]["draws"]):
        sys.exit("REFUSING: the alone cells were read by log-probability")
    t = texts(frames, pid)
    side = {c: counts((d.get("parsed") or {}).get("HOUSEHOLDER", "?") + "/" + (d.get("parsed") or {}).get("BUSINESS", "?")
                      for d in A[c]["draws"]) for c in ("side_FO", "side_OF")}
    alone = {c: counts((d.get("answer") or "?").strip().rstrip(".").lower() for d in B[c]["draws"]) for c in ("F", "O")}
    n = {c: len(A[c]["draws"]) for c in side} | {c: len(B[c]["draws"]) for c in alone}
    if not (all(side[c] == {"yes/no": n[c]} for c in side) and all(alone[c] == {"no": n[c]} for c in alone)
            and len(set(n.values())) == 1):
        sys.exit(f"REFUSING: the chosen pair is not unanimous in every cell: {side} {alone}")
    k = n["side_FO"]
    # The name the alone files use in place of the label (the review, 2026-11-18: say it in the heading); it must be
    # the only change from the side-by-side text, which says "The policyholder".
    name = t["alone_case"].split(" took out", 1)[0]
    assert t["alone_case"] == t["hh"].replace("The policyholder", name).replace("the policyholder", name), (name, pid)
    alone_head = f"Each file alone (the policyholder named {name} instead of labelled):"
    side_s = f"HOUSEHOLDER=yes, BUSINESS=no ({k} of {k}, in both orders)"
    single_s = f"HOUSEHOLDER=no, BUSINESS=no ({k} of {k} each)"
    m = tex_escape(O.ARM_LABEL[arm])
    tex = ("% DATA: material quoted as read; exempt from the typed-digit check (tools/check_typed_numbers.py).\n"
           f"% Figure 1: {O.ARM_LABEL[arm]}, pair {pid} (the author's choice, ({key})). Written by "
           "analysis/figure1.py --chosen; the case texts and questions are copied from the frames by code, and each "
           "result is summarised by code from the parsed verdicts.\n"
           "\\fbox{\\parbox{0.96\\linewidth}{\\footnotesize\\raggedright\n"
           "\\textbf{Case HOUSEHOLDER.} " + tex_escape(t["hh"]) + "\\\\[2pt]\n"
           "\\textbf{Case BUSINESS.} " + tex_escape(t["bus"]) + "\\\\[3pt]\n"
           "\\textbf{Side by side.} \\emph{" + tex_escape(t["question"]) + "}\\\\[1pt]\n"
           "\\textbf{\\model{" + m + "}:} \\textup{" + side_s + ".}\\\\[3pt]\n"
           "\\textbf{" + alone_head + "} \\emph{" +
           tex_escape(t["alone_q"]) + "}\\\\[1pt]\n"
           "\\textbf{\\model{" + m + "}:} \\textup{" + single_s + ".}\\\\[3pt]\n"
           "\\textbf{The rule.} " + tex_escape(RULE) + "\n}}\n")
    open(os.path.join(ROOT, "paper", "figures", "fig1_worked.tex"), "w").write(tex)
    blocks = [("Case HOUSEHOLDER. " + t["hh"], None), ("Case BUSINESS. " + t["bus"], None),
              ("Side by side. " + t["question"], "italic"), (f"{O.ARM_LABEL[arm]}: {side_s}.", "bold"),
              (alone_head + " " + t["alone_q"], "italic"),
              (f"{O.ARM_LABEL[arm]}: {single_s}.", "bold"), ("The rule. " + RULE, None)]
    draw(os.path.join(ROOT, "paper", "figures", "preview", "fig1_worked.pdf"), [blocks])
    print(f"wrote paper/figures/fig1_worked.tex and its preview: {side_s}; {single_s}")


def draw(path, pages):
    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    plt.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.serif": ["Times New Roman", "Times"]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with PdfPages(path, metadata={"Creator": "analysis/figure1.py", "CreationDate": None}) as pdf:
        for blocks in pages:
            text = [(textwrap.fill(s, 62), st) for s, st in blocks]
            n = sum(s.count("\n") + 1.5 for s, _ in text)
            fig = plt.figure(figsize=(3.15, 0.125 * n + 0.25))
            fig.add_artist(plt.Rectangle((0.01, 0.01), 0.98, 0.98, fill=False, lw=0.6, transform=fig.transFigure))
            y = 1 - 0.1 / fig.get_figheight()
            for s, st in text:
                fig.text(0.04, y, s, va="top", ha="left", fontsize=7, fontweight="bold" if st == "bold" else "normal",
                         style="italic" if st == "italic" else "normal")
                y -= (s.count("\n") + 1.5) * 0.125 / fig.get_figheight()
            pdf.savefig(fig)
            plt.close(fig)


def preview(panels):
    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    plt.rcParams.update({"pdf.fonttype": 42, "font.family": "serif", "font.serif": ["Times New Roman", "Times"]})
    os.makedirs(os.path.join(ROOT, "paper", "figures", "preview"), exist_ok=True)
    w = 62

    def ans(cell, order=""):
        return "; ".join(f"{x} ({k} of {len(cell['draws'])}{order})" for x, k in verbatim(cell))
    with PdfPages(os.path.join(ROOT, "paper", "figures", "preview", "fig1_candidates.pdf"),
                  metadata={"Creator": "analysis/figure1.py", "CreationDate": None}) as pdf:
        for key, arm, pid, t, c in panels:
            m = O.ARM_LABEL[arm]
            lp = pyes(c["F"])
            blocks = [(f"Candidate ({key}): {m}, pair {pid}", "bold"),
                      ("Case HOUSEHOLDER. " + t["hh"], None), ("Case BUSINESS. " + t["bus"], None),
                      ("Side by side. " + t["question"], "italic"),
                      (f"{m}: {ans(c['side_FO'], ', householder first')}; {ans(c['side_OF'], ', business first')}.", "bold"),
                      ("The householder's file alone, the policyholder named. " + t["alone_q"], "italic"),
                      (f"{m}: {ans(c['F'])}" + (f"; the probability it gave to yes {lp[7:]}" if lp else "") + ".",
                       "bold"),
                      ("The rule. " + RULE_PLAIN, None)]
            text = [(textwrap.fill(s, w), st) for s, st in blocks]
            n = sum(s.count("\n") + 1.5 for s, _ in text)
            fig = plt.figure(figsize=(3.15, 0.125 * n + 0.25))
            fig.add_artist(plt.Rectangle((0.01, 0.01), 0.98, 0.98, fill=False, lw=0.6, transform=fig.transFigure))
            y = 1 - 0.1 / fig.get_figheight()
            for s, st in text:
                fig.text(0.04, y, s, va="top", ha="left", fontsize=7, fontweight="bold" if st == "bold" else "normal",
                         style="italic" if st == "italic" else "normal")
                y -= (s.count("\n") + 1.5) * 0.125 / fig.get_figheight()
            pdf.savefig(fig)
            plt.close(fig)


if __name__ == "__main__":
    main()
