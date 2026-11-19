#!/usr/bin/env python3
"""check_typed_numbers.py : refuse a paper whose text carries a typed digit.

Every number in the paper comes from paper/numbers.tex (written by analysis/macros.py). This scans every .tex file in
paper/, paper/tables/ and paper/figures/ except numbers.tex and DATA files (first line "% DATA:", which quote the cases,
provisions and served model strings as read and are listed as skipped), from \\begin{document} on, after removing comments and the arguments of commands that
carry identifiers rather than numbers (labels, references, citations, inputs, environments, float placement), and
fails if any digit is left.

It also fails on any PLACEHOLDER WITHOUT A MACRO: a command whose name starts with a capital letter
(the form of every number macro) that is defined neither in paper/numbers.tex nor paper/numbers_exploratory.tex, nor by
newcommand, renewcommand or def in paper/main.tex, nor on the short list of standard LaTeX commands below. This check
covers every scanned file, data files included, so a typo in a macro name or a macro the analysis no longer writes
fails here rather than at LaTeX time.

DRAFT PLACEHOLDERS: \\Prov{Name} (a provisional figure from discovery run 262, defined as
\\ProvName in paper/numbers_provisional.tex), \\Pending{Name} (no figure yet) and \\Check{...} (a fact to verify)
are refused unless --draft is given. With or without --draft, every \\Prov{Name} must name a macro
numbers_provisional.tex defines. \\DraftBox (the reviewers' note on page 1) is not checked: since 2026-11-18 it prints
in draft builds only and a final build leaves it out.

    python tools/check_typed_numbers.py              # exit 1 and list the hits if any digit is typed
    python tools/check_typed_numbers.py --draft      # the same, but allows the draft placeholders above
    python tools/check_typed_numbers.py --selftest
"""
import glob, os, re, sys

NUMBER_FILES = ("numbers.tex", "numbers_exploratory.tex", "numbers_provisional.tex")
STANDARD = {"LaTeX", "TeX", "LaTeXe", "Large", "LARGE", "Huge", "Cref", "Box", "Delta", "Gamma", "Lambda", "Omega",
            "Phi", "Pi", "Psi", "Sigma", "Theta", "Upsilon", "Xi", "S", "P", "AA", "AE", "OE", "O", "L", "PackageError", "AtBeginDocument", "DeclareRobustCommand",
            "LetLtxMacro",
            "RaggedRight", "PassOptionsToPackage"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_ARGS = r"\\(?:label|ref|cref|Cref|autoref|eqref|cite|citet|citep|citealp|citeauthor|citepalias|citetalias|input|include|begin|end|" \
            r"includegraphics|bibliography|bibliographystyle|url|href|hspace|vspace|setlength|resizebox|" \
            r"multicolumn|multirow|cline|cmidrule|model|pairid|Check)\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})+"


def scrub(tex):
    body = tex.split("\\begin{document}", 1)[-1]
    body = re.sub(r"(?<!\\)%.*", "", body)
    body = re.sub(SKIP_ARGS, " ", body)
    body = re.sub(r"\\begin\{(?:figure|table)\*?\}\[[^\]]*\]", " ", body)
    body = re.sub(r"\{[0-9.]+\\(?:linewidth|textwidth|columnwidth)\}", " ", body)   # widths, not numbers
    body = re.sub(r"\\[A-Za-z]+", " ", body)              # macro names (numbers.tex macros are letters only)
    body = re.sub(r"\[[0-9.]+(?:pt|em|cm|mm|in)\]", " ", body)
    return body


def hits(tex):
    out = []
    for i, line in enumerate(scrub(tex).splitlines(), 1):
        if re.search(r"[0-9]", line):
            out.append(line.strip())
    return out


def defined(root):
    """Command names defined by the generated number files and by main.tex."""
    names = set()
    for f in [os.path.join(root, "paper", n) for n in NUMBER_FILES] + [os.path.join(root, "paper", "main.tex")]:
        if os.path.exists(f):
            t = open(f).read()
            names |= set(re.findall(r"\\(?:newcommand|renewcommand|providecommand)\*?\{?\\([A-Za-z]+)", t))
            names |= set(re.findall(r"\\def\\([A-Za-z]+)", t))
    return names


def placeholders(tex, names):
    """Capitalised command names used in tex (comments removed) that nothing defines."""
    body = re.sub(r"(?<!\\)%.*", "", tex)
    return sorted({m for m in re.findall(r"\\([A-Z][A-Za-z]*)", body) if m not in names and m not in STANDARD})


DRAFT_ONLY = r"\\(Prov|Pending|Check)\{([^{}]*)\}"


def draft_marks(tex):
    """Draft-only placeholders in tex (comments removed): [(command, argument)]."""
    body = re.sub(r"(?<!\\)%.*", "", tex)
    return [(m.group(1), m.group(2)) for m in re.finditer(DRAFT_ONLY, body)]


def main(argv):
    if "--selftest" in argv:
        ok = "\\begin{document}\nWe read \\sfvNArms{} arms (Table~\\ref{tab:results1}).% 12 in a comment\n" \
             "\\begin{figure}[t]\\fbox{\\parbox{0.9\\linewidth}{x}}\\label{fig:x}\\end{figure}\\cite{smith2020}"
        bad = "\\begin{document}\nWe read 12 arms."
        assert not hits(ok + "\\model{GPT-4o} on \\pairid{K2}"), hits(ok)
        assert hits(bad) == ["We read 12 arms."], hits(bad)
        names = {"AloneNoReasoning"}
        assert placeholders("\\AloneNoReasoning{} and \\LaTeX{} % \\Commented", names) == []
        assert placeholders("we read \\AloneNoReasonin{} cases", names) == ["AloneNoReasonin"]
        assert draft_marks("a \\Prov{ExampleAloneNoReasoning} b \\Pending{AskedDirectlyYes} % \\Prov{X}\n\\DraftBox") == \
            [("Prov", "ExampleAloneNoReasoning"), ("Pending", "AskedDirectlyYes")]
        assert draft_marks("\\Provenance{} and \\AloneNoReasoning{}") == []
        print("selftest 4/4")
        return 0
    found, missing, marks = {}, {}, {}
    draft = "--draft" in argv
    names = defined(ROOT)
    files = sorted(glob.glob(os.path.join(ROOT, "paper", "*.tex")) + glob.glob(os.path.join(ROOT, "paper", "tables", "*.tex"))
                   + glob.glob(os.path.join(ROOT, "paper", "figures", "*.tex")))
    for f in files:
        if os.path.basename(f) in NUMBER_FILES:
            continue
        dm = draft_marks(open(f).read())
        if dm:
            marks[os.path.relpath(f, ROOT)] = dm
        ph = placeholders(open(f).read(), names)
        ph += [f"Prov{a}" for c, a in dm if c == "Prov" and f"Prov{a}" not in names]
        if ph:
            missing[os.path.relpath(f, ROOT)] = ph
        if open(f).readline().startswith("% DATA:"):
            print(f"{os.path.relpath(f, ROOT)}: skipped (data quoted as read)")
            continue
        h = hits(open(f).read())
        if h:
            found[os.path.relpath(f, ROOT)] = h
    for f, h in found.items():
        for line in h:
            print(f"{f}: typed digit: {line[:120]}")
    for f, ph in missing.items():
        print(f"{f}: placeholder without a macro: {', '.join(ph[:10])}{' ...' if len(ph) > 10 else ''}")
    n_marks = sum(len(v) for v in marks.values())
    if marks and not draft:
        for f, dm in marks.items():
            print(f"{f}: draft placeholders: {', '.join(c + ('{' + a + '}' if a else '') for c, a in dm[:8])}"
                  f"{' ...' if len(dm) > 8 else ''}")
    print("NO TYPED NUMBERS" if not found else "TYPED NUMBERS FOUND")
    print(f"DRAFT PLACEHOLDERS: {n_marks}" + (" (allowed: --draft)" if draft else
                                              (" REFUSED: final build" if n_marks else "")))
    print("EVERY PLACEHOLDER HAS A MACRO" if not missing else "PLACEHOLDERS WITHOUT A MACRO FOUND")
    return 1 if found or missing or (marks and not draft) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
