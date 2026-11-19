# Rough Justice

Code, prompts and every banked model response for the paper *Rough Justice: Language Models Know the Standard but
Hold Us to a Stricter One* (Cassian Young, 2026).

Archived on Zenodo: [doi:10.5281/zenodo.24369486](https://doi.org/10.5281/zenodo.24369486). Source: https://github.com/cassianyoung/rough-justice.

Every number in the paper is a macro in `paper/numbers.tex`, and every macro can be regenerated from the banked
responses in this repository with one command (below). No step calls a model.

## What each folder holds

| Folder | Contents |
|---|---|
| `banked/records/` | The prompts and the responses as read. `*_FRAMES.json` are the frozen prompts of each session (system line, user message, and the hash each call was checked against). `RUN<N>_READ__<configuration>.json` hold every draw's answer text with its parsed verdict, per configuration. `RUN259_MATCHED_READS/` is the first session's readout as the paper reports it (five open models re-read by sampling in run 263). |
| `banked/runs/` | Every model call as logged when it was made, one JSON object per line (`runs/run<N>/logs/*.jsonl`; run 261 also `g_logs/`, `g_pilot/` and `pilot/`): the settings on the wire, the provider and model that served it, the raw answer, any reasoning text the provider returned, token usage and cost. The prompts themselves are in the frames, matched by hash. |
| `banked/data/` | The frozen item drafts (case texts, pairs, domains, rules) the frames were built from. |
| `items/` | The control items of run 260. |
| `discovery/` | The exploratory runs (248 to 255, and 262) behind the paper's exploratory figures (`paper/numbers_exploratory.tex`): their frames, reads and results. |
| `results/` | The analysis results the paper cites, one JSON file per analysis. `results/seven/` holds the paper's main figures, pooled over all seven domains. |
| `analysis/` | The analysis. `reproduce.py` regenerates everything; each other script computes one part (see its header). `macros.py` is the only path by which a number reaches the paper. |
| `paper/` | The LaTeX sources of both builds (arXiv and anonymised review), the generated `numbers*.tex` (with each number's provenance in `numbers*.json`), tables and figures, and `build.sh`. |
| `tools/` | `check_typed_numbers.py`, which refuses any digit typed into the paper's text. |
| `PREREG.md` | The pre-registration of the first session (run 259), as frozen, with its dated amendments. Paths there of the form `AI_Ethics records/X` are `banked/records/X` here. |

### Sessions and run numbers

| Run | What it is |
|---|---|
| 259 | The first session: six domains, 36 pairs, five conditions, 20 model configurations. |
| 260 | The control follow-up (the day of the week as an irrelevant change). |
| 261 | The second session: school work, the worked example, the direct question, a second wording, milder conduct, the stated jurisdiction, and a re-read of the first session's cases alone. |
| 263 | The five open models' first-session conditions re-read by sampling (the matched readout). |
| 266 | The third session: the direct question with the parties in reverse order. |
| 248 to 255, 262 | Exploratory runs (`discovery/`). |

Configuration names (`claude`, `gpt6s_r`, ...) map to models and settings in the model table of the supplementary material
and in the `served_model` and `provider_served` fields of every logged call.

## Regenerating every figure and table

Requirements: Python 3.12 with the packages in `requirements.txt`; Tectonic 0.17 for the PDFs.

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. Every results file recomputed from the banked responses and compared with the banked copy,
#    then paper/numbers.tex regenerated from the results and compared byte for byte (about five minutes).
.venv/bin/python analysis/reproduce.py

# 2. The tables (paper/tables/*.tex) and the figures (paper/figures/*.pdf) from the results.
.venv/bin/python analysis/seven_domains.py --tables

# 3. Figure 1, the worked insurance case, from the frames and the reads.
.venv/bin/python analysis/figure1.py --frames banked/records/RUN259_FRAMES.json \
    --reads banked/records/RUN259_MATCHED_READS --chosen d

# 4. The PDFs: paper/build/RoughJustice_{arxiv,review}.pdf and their supplementary material.
PYTHON=.venv/bin/python paper/build.sh
```

`reproduce.py` prints one line per results file and ends with `ALL REPRODUCED`. Numbers in the results files are
compared to within 1e-12 (some banked files carry last-bit differences such as 0.9999999999999999 for 1.0); every
other value exactly. Which builder supplies each macro is read from the provenance recorded for it in
`paper/numbers.json`; the values are not.

Results files are write-once: each analysis script refuses to overwrite a results file that differs from what it
computes. To write one anew, remove it and run the script named in its header, for example
`.venv/bin/python analysis/run266.py` for `results/run266.json`.

Two scripts are superseded first-session steps and refuse to overwrite by design: `analysis/haiku_void_check.py`
(its exact-text guard sees the last-bit differences above and so leaves `results/haiku55_void_check_v2.json` as it
is) and `analysis/review_checks.py` (its macro names now belong to the seven-domain results). Their figures are
reproduced by `reproduce.py`, which calls their functions without writing.

## Licence

- Code (`analysis/`, `tools/`, `paper/build.sh`): MIT, `LICENSE`.
- Data, prompts and model responses (`banked/`, `items/`, `discovery/`, `results/`): CC BY 4.0, `LICENSE-DATA`.
- The paper's sources (`paper/main.tex`, `paper/custom.bib`, `paper/numbers*`, `paper/tables/`, `paper/figures/`) and
  `PREREG.md`: CC BY 4.0, `LICENSE-DATA`.
- `paper/acl.sty` and `paper/acl_natbib.bst` are the ACL style files (acl-org/acl-style-files at d5adc823), under
  their own terms.

## Citation

See `CITATION.cff`. The archived release is [doi:10.5281/zenodo.24369486](https://doi.org/10.5281/zenodo.24369486).
