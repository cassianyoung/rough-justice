#!/usr/bin/env python3
"""bootstrap_macros.py : the bootstrap's constants as macros, read from the code that uses them (the review,
2026-11-18). No new calls. Appendix B states the design with these, so the text cannot drift from the code.

    python analysis/bootstrap_macros.py
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import outcomes as O                                            # noqa: E402
import party_difference as PD                                   # noqa: E402

SRC = "analysis/bootstrap_macros.py"   # its own tag: the values are read from analysis/outcomes.py
LOW, HIGH = 0.025, 0.975        # FastBoot._ci's percentiles; checked below against the code


def build():
    import inspect
    code = inspect.getsource(O.FastBoot._ci)
    assert f"int({LOW} *" in code and f"ceil({HIGH} *" in code, "FastBoot._ci's percentiles have changed"
    pct = lambda x: f"{100 * x:g}th"
    v = {"BootstrapReplicates": {"value": O.B_RESAMPLES, "kind": "int", "source": SRC + "#B_RESAMPLES"},
         "BootstrapSeedPairs": {"value": O.SEED, "kind": "int", "source": SRC + "#SEED"},
         "BootstrapSeedModels": {"value": O.ARM_SEED, "kind": "int", "source": SRC + "#ARM_SEED"},
         "BootstrapLowPctile": {"value": pct(LOW), "kind": "str", "source": SRC + "#FastBoot._ci"},
         "BootstrapHighPctile": {"value": pct(HIGH), "kind": "str", "source": SRC + "#FastBoot._ci"}}
    return v


def main():
    v = build()
    print(f"macros into paper/numbers.tex (now {PD.add_macros(v, SRC, own=(SRC,))})")


if __name__ == "__main__":
    main()
