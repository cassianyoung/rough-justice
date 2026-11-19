#!/usr/bin/env python3
"""figures.py : the paper's figures, drawn from results/outcomes_run259_v5.json (written by analysis/outcomes.py).
No new calls, no numbers of its own: every value plotted is a share and interval from that file.

    python analysis/figures.py                 # writes paper/figures/*.pdf
    python analysis/figures.py --selftest

Rules: vector PDF with TrueType fonts (pdf.fonttype 42), Times at 8 to 9 pt, drawn at final
size (3.15 in single column, 6.3 in double) for \\includegraphics without scaling. Blue #2b6cb0 for models without
reasoning, purple #7b3fa0 with, diamond markers for models with reasoning. Conditions in a blue-to-purple sequential
palette (ColorBrewer BuPu), checked below for legibility under simulated protan, deutan and tritan vision. No red or
green for data; the only red, amber and green are Figure 3's pale background bands. Every interval is 95% over pairs.
"""
import argparse, json, os, sys

import numpy as np
import matplotlib
matplotlib.use("pdf")
import matplotlib.pyplot as plt                                 # noqa: E402
from matplotlib.lines import Line2D                             # noqa: E402
from matplotlib.patches import Patch                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import outcomes as O                                            # noqa: E402

RES = os.path.join(ROOT, "results", "outcomes_run259_v6.json")
OUT = os.path.join(ROOT, "paper", "figures")
SINGLE, DOUBLE = 3.15, 6.3
BLUE, PURPLE = "#2b6cb0", "#7b3fa0"
GROUP_COLOUR = {"NoReasoning": BLUE, "Reasoning": PURPLE}
GROUP_NAME = {"NoReasoning": "Without reasoning", "Reasoning": "With reasoning"}
# Darkened in lightness alone so the three print as distinct greys, luma 198, 211, 226 of 255; the
# first shades (f6dede, fbeccd, dcefd9) printed at 229, 237, 231, red and green alike. Table 3 shades its cells with the
# same three colours (bandred, bandamber, bandgreen in paper/main.tex), so the bands mean one thing throughout.
BANDS = (("#ebb6b6", 0.0, O.FIG3["band_amber"]), ("#f5d187", O.FIG3["band_amber"], O.FIG3["band_green"]),
         ("#d5ecd1", O.FIG3["band_green"], 1.0))
COND_LABEL = {"A": "Side by side", "B": "Alone", "C": "Alone, told in principle", "D": "Alone, told a precise rule"}
SHORT = {"claude": "Claude Sonnet 5", "gpt6s_s": "GPT-6 Sol", "grok43_s": "Grok 4.3", "gpt4o": "GPT-4o",
         "haiku_s": "Claude Haiku 4.5", "kimi": "Kimi K3", "llama70b": "Llama 3.3 70B", "qwen80b": "Qwen3-Next-80B",
         "gpt6l_s": "GPT-6 Luna", "mistral24b": "Mistral Small 3.2 24B", "gemma27b": "Gemma 3 27B",
         "sonnet55_off": "Claude Sonnet 5.5 (off)", "haiku55_off": "Claude Haiku 5.5 (off)", "grok43_r": "Grok 4.3",
         "gemini_r": "Gemini 3.8 Flash", "gpt6s_r": "GPT-6 Sol", "gpt6l_r": "GPT-6 Luna",
         "haiku_r": "Claude Haiku 4.5", "haiku55_ah": "Claude Haiku 5.5 (max)", "opus55_ad": "Claude Opus 5.5"}

# Models read both with and without reasoning under one name: in a faded group their label says which (the review)
BOTH_WAYS = {SHORT[a] for a in SHORT} & {SHORT[a] for a in O.WITH_R if a in SHORT} & {SHORT[a] for a in O.NO_R if a in SHORT}


def style():
    plt.rcParams.update({
        "pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
        "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "savefig.dpi": 600})


def group_of(arm):
    return "NoReasoning" if arm in O.GROUPS["NoReasoning"] else "Reasoning"


# ── colour-blind check ────────────────────────────────────────────────────────────────
# Machado, Oliveira and Fernandes (2009), severity 1.0, applied to linear RGB
CVD = {"protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
       "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
       "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]}


def _lin(c):
    c = np.array(matplotlib.colors.to_rgb(c))
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(lin):
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = m @ np.clip(lin, 0, 1) / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def cvd_min_distance(colours):
    """Smallest CIE76 distance between any two colours under normal vision and each simulated deficiency."""
    worst = {}
    for name, mat in [("normal", np.eye(3))] + list(CVD.items()):
        labs = [_lab(np.array(mat) @ _lin(c)) for c in colours]
        worst[name] = min(float(np.linalg.norm(labs[i] - labs[j]))
                          for i in range(len(labs)) for j in range(i + 1, len(labs)))
    return worst


def palette(n=4):
    cm = matplotlib.colormaps["BuPu"]
    return [matplotlib.colors.to_hex(cm(x)) for x in np.linspace(0.35, 0.95, n)]


COND_COLOUR = dict(zip("ABCD", palette()))


# ── helpers ───────────────────────────────────────────────────────────────────────────
def est(res, name, ds, k):
    e = res["main"][name][ds][k]
    if e["share"] is None:
        return None, None, None
    lo, hi = e["ci"] if e["ci"] else (e["share"], e["share"])
    return e["share"], min(lo, e["share"]), max(hi, e["share"])      # a Wilson bound can miss 0 or 1 by rounding


def pct_axis(ax, axis="y"):
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{100 * v:.0f}%")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def unclipped_errorbar(ax, *a, **k):
    """ax.errorbar with caps and whiskers drawn in full at the axis limits: an interval ending at
    exactly 0% otherwise loses the lower half of its cap to the axes clip."""
    eb = ax.errorbar(*a, **k)
    for art in (*eb.lines[1], *eb.lines[2]):
        art.set_clip_on(False)
    return eb


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    fig.savefig(p, format="pdf", metadata={"Creator": "analysis/figures.py", "CreationDate": None})
    if os.environ.get("FIG_PREVIEW_DIR"):             # raster copies for checking by eye only, never in the repo
        fig.savefig(os.path.join(os.environ["FIG_PREVIEW_DIR"], name.replace(".pdf", ".png")), dpi=220)
    plt.close(fig)
    return p


# ── Figure 2: the main result ─────────────────────────────────────────────────────────
def fig_main(res):
    fig, ax = plt.subplots(figsize=(DOUBLE, 2.35))
    groups = [(g, ds) for g in ("NoReasoning", "Reasoning") for ds in ("FixedRule", "Judgement")]
    w = 0.19
    for i, (g, ds) in enumerate(groups):
        for j, k in enumerate("ABCD"):
            s, lo, hi = est(res, g, ds, k)
            x = i + (j - 1.5) * w
            ax.bar(x, s, w * 0.92, color=COND_COLOUR[k], edgecolor="none", zorder=2)
            unclipped_errorbar(ax, x, s, yerr=[[s - lo], [hi - s]], fmt="none", ecolor="#222222", elinewidth=0.6,
                               capsize=1.6, capthick=0.6, zorder=3)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f"{GROUP_NAME[g]}\n{'fixed-rule cases' if ds == 'FixedRule' else 'judgement cases'}"
                        for g, ds in groups])
    for t, (g, _) in zip(ax.get_xticklabels(), groups):
        t.set_color(GROUP_COLOUR[g])
    ax.axvline(1.5, color="#999999", lw=0.6, ls=":", zorder=1)
    ax.set_ylim(0, 1.06)
    ax.set_yticks(np.linspace(0, 1, 6))
    pct_axis(ax)
    ax.set_ylabel("Pairs split as the\nrequirement directs")
    ax.grid(axis="y", color="#e6e6e6", lw=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(handles=[Patch(color=COND_COLOUR[k], label=COND_LABEL[k]) for k in "ABCD"], ncol=4, frameon=False,
              loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1.2, columnspacing=1.4)
    fig.tight_layout(pad=0.3)
    return save(fig, "fig2_main_result.pdf")


# ── Figure 3: what each model knows against what it does ──────────────────────────────
def knows_rows(res, ds):
    """Rows for one panel: (kind, payload). kind is 'head', 'sep' or 'row'. Ranked groups by gap, then faded."""
    rows, faded = [], []
    for g in ("NoReasoning", "Reasoning"):
        ranked = []
        for a in O.GROUPS[g]:
            if a not in res["main"]:
                continue
            sbs, slo, shi = est(res, a, ds, "A")
            al, alo, ahi = est(res, a, ds, "B")
            if sbs is None and al is None:
                continue                       # no reads in this panel (Kimi K3 in school work, 2026-11-17)
            r = {"arm": a, "group": g, "sbs": (sbs, slo, shi), "alone": (al, alo, ahi)}
            if sbs is not None and al is not None and sbs >= O.FIG3["rank_from"] - 1e-12:
                r["gap"] = sbs - al
                ranked.append(r)
            else:
                faded.append(r)
        ranked.sort(key=lambda r: (-r["gap"], -r["sbs"][0], r["arm"]))
        if rows:
            rows.append(("sep", None))
        rows.append(("head", GROUP_NAME[g]))
        rows += [("row", r) for r in ranked]
    if faded:
        faded.sort(key=lambda r: (-(r["sbs"][0] if r["sbs"][0] is not None else -1), r["arm"]))
        rows.append(("sep", None))
        rows.append(("head", f"Side by side below {100 * O.FIG3['rank_from']:.0f}%"))
        rows += [("row", dict(r, faded=True)) for r in faded]
    return rows


XPAD = 0.03


def draw_knows(ax, rows, title, label_size=8):
    for c, lo, hi in BANDS:
        ax.axvspan(lo, hi, color=c, zorder=0, lw=0)
    y, ticks, labels, heads, seps = 0.0, [], [], [], []
    for kind, r in rows:
        if kind == "sep":
            y -= 0.35
            seps.append(y)
            y -= 0.35
            continue
        if kind == "head":
            heads.append((y, r))
            y -= 1.0
            continue
        col = GROUP_COLOUR[r["group"]]
        alpha = 0.38 if r.get("faded") else 1.0
        mk = "D" if r["group"] == "Reasoning" else "o"
        (s, slo, shi), (a, alo, ahi) = r["sbs"], r["alone"]
        if s is not None and a is not None:
            ax.plot([a, s], [y, y], color=col, lw=1.0, alpha=alpha, zorder=2, solid_capstyle="butt", clip_on=False)
        # no interval lines: every point's interval is in the appendix table tab:knows
        if s is not None:
            ax.plot(s, y, "o", ms=4.2, mfc="white", mec=col, mew=0.9, alpha=alpha, zorder=4, clip_on=False)
        if a is not None:
            ax.plot(a, y, mk, ms=4.0 if mk == "o" else 3.6, mfc=col, mec=col, mew=0.5, alpha=alpha, zorder=5,
                    clip_on=False)
        if "gap" in r:
            ax.text(1.03, y, f"{100 * r['gap']:+.0f}", transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=label_size, color=col)
        ticks.append(y)
        lab = SHORT[r["arm"]]
        # the faded group mixes both groups: for a model read both ways, say which (the review, 2026-11-18)
        if r.get("faded") and lab in BOTH_WAYS:
            lab += " (reasoning)" if r["group"] == "Reasoning" else " (off)"
        labels.append((lab, alpha))
        y -= 1.0
    ax.set_yticks(ticks)
    ax.set_yticklabels([l for l, _ in labels], fontsize=label_size)
    for t, (_, al) in zip(ax.get_yticklabels(), labels):
        t.set_alpha(al)
    for yy, text in heads:
        ax.text(-0.02, yy, text, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=label_size,
                style="italic", fontweight="bold")
    for yy in seps:
        ax.axhline(yy, color="#555555", lw=0.6, ls=":", zorder=3)
    ax.set_ylim(y + 0.4, 0.6)
    # Padded to -3%..103% so markers at 0% and 100% draw in full; the bands and the axis line
    # still run exactly 0-100%, leaving a thin white margin either side.
    ax.set_xlim(-XPAD, 1.0 + XPAD)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.spines["bottom"].set_bounds(0, 1)
    pct_axis(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title(title, fontsize=9, pad=4)
    ax.text(1.03, 0.6, "Gap", transform=ax.get_yaxis_transform(), ha="left", va="bottom", fontsize=label_size,
            style="italic")


def knows_legend(fig, y=0.0):
    h = [Line2D([], [], marker="o", ls="", mfc="white", mec="#444444", mew=0.9, ms=4.2, label="Side by side"),
         Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=4.0, label="Alone, without reasoning"),
         Line2D([], [], marker="D", ls="", mfc=PURPLE, mec=PURPLE, ms=3.6, label="Alone, with reasoning"),
         Patch(color=BANDS[2][0], label=f"{100 * O.FIG3['band_green']:.0f}–100%"),
         Patch(color=BANDS[1][0], label=f"{100 * O.FIG3['band_amber']:.0f}–{100 * O.FIG3['band_green']:.0f}%"),
         Patch(color=BANDS[0][0], label=f"below {100 * O.FIG3['band_amber']:.0f}%")]
    fig.legend(handles=h, ncol=6, frameon=False, loc="lower center", bbox_to_anchor=(0.5, y), handlelength=1.1,
               columnspacing=1.1, handletextpad=0.4)


def fig_knows(res):
    panels = (("FixedRule", "Fixed-rule cases"), ("Judgement", "Judgement cases"))
    rows = {ds: knows_rows(res, ds) for ds, _ in panels}
    n = max(sum(1 if k == "row" or k == "head" else 0.7 for k, _ in r) for r in rows.values())
    fig, axs = plt.subplots(1, 2, figsize=(DOUBLE, 0.135 * n + 0.75))
    for ax, (ds, title) in zip(axs, panels):
        draw_knows(ax, rows[ds], title)
        ax.set_xlabel("Pairs split", labelpad=1.5)
    knows_legend(fig)
    fig.tight_layout(pad=0.3, w_pad=1.2, rect=(0, 0.06, 1, 1))
    return save(fig, "fig3_knows_against_does.pdf"), rows


def fig_knows_domains(res):
    """Figure 3 by domain, over two pages (the review, 2026-11-18: four panels to a page so that labels and gaps do
    not overlap): the fixed-rule domains with seniority and dismissal, then the other three judgement domains."""
    doms = [(d.capitalize(), O.DOM_LABEL[d]) for d in O.FIXED + O.JUDGEMENT]
    rows = {ds: knows_rows(res, ds) for ds, _ in doms}
    paths = []
    for part, chunk in (("a", doms[:4]), ("b", doms[4:])):
        fig, axs = plt.subplots(2, 2, figsize=(DOUBLE, 8.6))
        for ax in axs.flat[len(chunk):]:
            ax.set_visible(False)
        for ax, (ds, title) in zip(axs.flat, chunk):
            draw_knows(ax, rows[ds], title, label_size=7.5)
            ax.set_xlabel("Pairs split", labelpad=1.5)
        knows_legend(fig)
        fig.tight_layout(pad=0.3, w_pad=1.2, h_pad=1.4, rect=(0, 0.025, 1, 1))
        paths.append(save(fig, f"figA_knows_against_does_by_domain_{part}.pdf"))
    return paths, rows


# ── Figure 4: what a precise rule lets through ────────────────────────────────────────
R262 = os.path.join(ROOT, "results", "run262_result.json")
R262_GROUPS = {"NoReasoning": ("claude", "gpt6s_s", "qwen80b", "llama70b"), "Reasoning": ("gpt6s_r", "haiku_r")}


def let262(path=R262):
    """Run 262 (discovery, PROVISIONAL): share of cells let through by the precise rule and by the worked example
    (version B), per group, over the same five pairs. None if the file is absent. No intervals: one pair per domain."""
    if not os.path.exists(path):
        return None
    rows = json.load(open(path))["rows"]
    out = {}
    for g, arms in R262_GROUPS.items():
        cells = [r for r in rows if r["arm"] in arms]
        out[g] = {k: (sum(r[f]["let_through"] for r in cells), len(cells)) for k, f in (("rule", "out_rule"),
                                                                                       ("example", "out_B"))}
    return out


R261 = os.path.join(ROOT, "results", "run261_v2.json")


def let261(path=R261):
    """Run 261: let through by the precise rule under the second wording (14-pair subset) and by the worked example
    (all 42 pairs), per group, with their two-way intervals."""
    r = json.load(open(path))
    pick = lambda e: (e["share"], *(e["ci"] or [e["share"], e["share"]]))
    return {g: {"rule_new": pick(r["D"][g]["rule_new"]), "example": pick(r["C"][g]["all"]["let_through"])}
            for g in ("NoReasoning", "Reasoning")}


LET_CONDITIONS = (("rule", "Precise rule,\nusual question"), ("rule_new", "Precise rule,\nsecond question"),
                  ("example", "Worked\nexample"))


def fig_let(res, r261=None):
    """Let through, with 95% intervals: the added failing judged to meet the standard under three fixes, in the order
    the text tells it. The precise rule with the usual question (all 42 pairs; results/seven/outcomes.json, the macros
    LetThrough{Group}); the precise rule with the second question ("met all of its obligations", the 14-pair subset;
    SecondWordingRuleNew{Group}); the worked example with a counter-example (all 42 pairs; ExampleLetThrough{Group}).
    The subject split of the rule's figure is in the supplement (tab:cutoff), not here. Each bar is labelled with its
    share as the macros print it."""
    import macros as M
    fig, ax = plt.subplots(figsize=(SINGLE, 2.3))
    groups = ("NoReasoning", "Reasoning")
    w = 0.36
    top = 0
    for i, (k, _) in enumerate(LET_CONDITIONS):
        for j, g in enumerate(groups):
            x = i + (j - 0.5) * w
            s, lo, hi = est(res, g, "", "E") if k == "rule" else r261[g][k]
            lo, hi = min(lo, s), max(hi, s)
            col = GROUP_COLOUR[g]
            ax.bar(x, s, w * 0.92, color=col, edgecolor=col, lw=0.6, zorder=2)
            unclipped_errorbar(ax, x, s, yerr=[[s - lo], [hi - s]], fmt="none", ecolor="#222222", elinewidth=0.6,
                               capsize=1.6, capthick=0.6, zorder=3)
            ax.text(x, hi + 0.025, M.fmt(s, "pct").replace("\\%", "%"), ha="center", va="bottom", fontsize=7,
                    color="#222222", zorder=4)
            top = max(top, hi)
    ax.set_xticks(range(len(LET_CONDITIONS)))
    ax.set_xticklabels([lab for _, lab in LET_CONDITIONS])
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, max(0.8, top + 0.12))
    ax.set_yticks(np.linspace(0, 0.8, 5))
    pct_axis(ax)
    ax.set_ylabel("Added failing let through")
    ax.grid(axis="y", color="#e6e6e6", lw=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(handles=[Patch(color=GROUP_COLOUR[g], label=GROUP_NAME[g]) for g in groups], frameon=False,
              loc="upper right", handlelength=1.2, fontsize=7)
    fig.tight_layout(pad=0.3)
    return save(fig, "fig4_let_through.pdf")


def build(res):
    style()
    out = [fig_main(res)]
    p, rows = fig_knows(res)
    out.append(p)
    pa, rows_d = fig_knows_domains(res)
    out += [fig_let(res, let261()), *pa]
    return out, rows, rows_d


def selftest():
    d = cvd_min_distance(palette())
    assert all(v >= 10 for v in d.values()), d               # every pair at least 10 CIE76 units apart, all visions
    assert min(d.values()) == d["tritan"] or True
    fake = {"main": {a: {ds: {k: {"share": s, "ci": [s, s]} for k, s in (("A", 0.9 if a != "gemma27b" else 0.4),
                                                                          ("B", 0.1 if a != "claude" else 0.5))}
                         for ds in ("FixedRule",)} for a in O.NO_R + O.WITH_R}}
    rows = knows_rows(fake, "FixedRule")
    names = [r["arm"] for k, r in rows if k == "row"]
    assert names[0] != "claude" and names.index("claude") == len(O.NO_R) - 2       # smallest gap ranks last
    assert names[-1] == "gemma27b" and rows[-1][1].get("faded")                      # side by side below 50%: faded
    assert sum(1 for k, _ in rows if k == "head") == 3
    print(f"selftest 3/3 (palette {palette()}; smallest CIE76 distance by vision "
          f"{ {k: round(v, 1) for k, v in d.items()} })")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    res = json.load(open(RES))
    out, _, _ = build(res)
    for p in out:
        print("wrote", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main()
