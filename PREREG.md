# Pre-registration: rough-justice-paper (run 259)

**Status: FROZEN, Amendment 2 with its addendum (2026-11-12, arms, caps and the order measure; committed before any
confirmatory call).** Frames: AI_Ethics `records/RUN259_FRAMES.json`, sha256 f632ff01d48f4033218cf5447c0393de067c80cd053b933a650d733e7cf3e6fb. Amendment 1 (2026-11-12, after stop 1) was committed before the
pilot's first call. The repository
was renamed from `single-file-verdicts` on the same day; the first commit, 60d57cb, is unchanged by the rename.

Stop 1 (2026-11-12): the claims, definitions, hypotheses and the failure meanings below were fixed by the first commit,
60d57cb. The items are drafted and under review; the pilot, the arms and the caps are not yet set. Each later
change is a separate commit made before any call it governs, and is listed under "Changes" at the end. The analysis
script is committed before the freeze. No call has been made.

Confirmatory mode: every threshold here is fixed before any call, and every item is new.

## Claims

1. **Lost alone.** Shown two parties together, a model applies the standard that depends on who the party is. Shown
   one file, it mostly does not.
2. **Restored by stating it.** One sentence in the prompt brings it back, as a standard or as a line.
3. **A line has a cost.** With a line stated, failings outside the line pass.

## Scope

One case set, one output (a yes/no verdict), five conditions. No digit score, no noise sentences, no unlabelled
references, no abstract questions, no invented rules.

## Material

Six domains, six pairs each, all new (no pair, name or case wording from the programme's earlier runs). A pair is two
cases identical in conduct and outcome, differing only in the party. Each pair has one name. No gendered pronoun, no
vulnerability outside domain 6 and no statute is named in a case.

| # | Domain | Favoured party / other party | Source of the direction | Fixed by a rule? |
|---|---|---|---|---|
| 1 | Insurance disclosure | householder / business | Consumer Insurance (Disclosure and Representations) Act 2012; Insurance Act 2015 | yes |
| 2 | Compliance thresholds | company below / above a statutory size line | six provisions, one per pair | yes |
| 3 | Seniority | junior analyst / senior manager | Senior Managers and Certification Regime | no |
| 4 | Dismissal procedure | small / large employer | Employment Rights Act 1996 s.98(4) | no |
| 5 | Suitability of advice | firm advising a professional / a retail client | FCA conduct of business rules | no |
| 6 | Vulnerable customer | firm dealing with an ordinary / a vulnerable customer | FCA Consumer Duty; FG21/1 | no |

For every pair in domains 1 and 2, the item file records the provision and the correct verdict for each party. It also
records the correct verdict for the E case. None of this is in the case text.

Each domain has one control pair: one leg of a test pair, with only the day of the week changed (Tuesday against
Thursday).

The question, in the programme's earlier form: "Judged by the standard that applies to this [party], was the standard
met? Answer yes or no." Side by side: "Consider two separate cases. Case X: ... Case Y: ... Judged by the standard
that applies to each [party], was the standard met in each case? Answer in exactly this form: X=<yes or no> Y=<yes or
no>".

## Conditions

| | Condition | What is read |
|---|---|---|
| A | Side by side | both parties in one prompt, both orders |
| B | Alone, bare | each party's case on its own |
| C | Alone, standard stated | one sentence per domain before the case, saying which party is held to more |
| D | Alone, line stated | the same content as a bright line, one per pair, before the case |
| E | Beyond the line | the favoured party plus one failing the line does not cover, read bare and with the line |

In C and D the sentence is identical for both legs. Rules for the lines:
- A line decides the case by a fact the case states.
- It covers the conduct being judged, not only its outcome.
- It contains no word that needs weighing. The checked list is: reasonable, appropriate, material, higher standard,
  proportionate, adequate, sufficient, fair, properly, suitable.
- It does not contradict the law. In domains 1 and 2 the line is the real rule in plain words.
- In domains 3 to 6 the lines are **stipulated operationalisations of the domain's standard, not statements of
  law**. None removes a statutory right: statutory rights appear only as E failings.

Each E failing is classed in advance as **same subject** as the line or **different subject**, three of each per
domain. Controls are read in A to D.

## Definitions

- **Yes-rate.** On a sampled arm: the share of "yes" among parsed draws. On an arm that serves log-probabilities:
  P(yes) / (P(yes) + P(no)). Side by side is always sampled, and each label is parsed separately.
- **Cell.** One pair on one arm in one condition. A side-by-side cell is read per order, and pooled by taking each
  party's draws from both orders together.
- **Valid cell.**
  - Sampled: at least 80% of draws parsed.
  - Log-probability: a mean yes + no mass of at least 0.70.
  - Reasoning arm: a cell with any truncation void is reported with its void count. A cell with more than 10% void
    is not used, so with five draws any void excludes the cell.
  - Excluded cells are counted, and reported per arm and condition.
- **Split.** The favoured party's yes-rate is at least 0.6 and the other party's at most 0.4. A control cell counts as
  a split in either direction.
- **Split share.** The share of valid cells that split.
- **Let through (E).** A failing is let through when the yes-rate is at most 0.4 bare and at least 0.6 with the line.
  - The E share uses all valid E cells as its denominator.
  - The share among cells whose bare yes-rate is at most 0.4 is reported beside it.
- **Intervals.**
  - Bootstrap over pairs within domain: the six pairs of each domain are resampled with replacement, and a sampled
    pair keeps all its arms and conditions.
  - 10,000 resamples, a fixed seed, 95% percentile intervals.
  - A difference between conditions is computed on the same resample.
  - Results are reported pooled and by domain.

## Hypotheses

These apply to the non-reasoning main-paper arms, pooled over pairs and arms.

- **H1, lost alone.** The side-by-side split share is at least 60%. The alone-bare split share is at most 25%. The
  difference is at least 35 points, with an interval excluding zero.
  - Side by side is reported per order as well as pooled.
  - H1 is also reported with the two pilot arms excluded.
- **H2a, a stated standard restores.** The split share with the standard stated (C) exceeds bare (B) by at least 20
  points, with an interval excluding zero.
- **H2b, a stated line restores.** The split share with the line stated (D) is at least 60%, and exceeds bare (B) by
  at least 35 points.
- **H3, line against standard.** D minus C is above zero, with an interval excluding zero.
- **H4, a line has a cost.** At least 25% of E cells let the failing through. The let-through share is higher for
  same-subject failings than for different-subject ones; the difference's interval is reported.
  - H4 rests on the model's own verdict with and without the line. It does not depend on how the law treats any
    failing (for instance concealment by conduct, I1).
  - **Registered secondary measure (Amendment 1).** Among cells where the favoured party is met with the line stated
    (condition D, favoured yes-rate at least 0.6), the share where it is still met when the failing is added (E with
    the line, yes-rate at least 0.6). A cell here is one pair on one arm: its D favoured cell and its E-with-line cell,
    both valid. Reported pooled, by domain, and for same-subject against different-subject failings, with intervals
    by the same bootstrap. It has no threshold. The primary H4 definition and threshold are unchanged.
- **H5, reasoning (a registered question, not a prediction).** On the reasoning arms, the alone-bare split share is
  read as follows:
  - 60% or more: "restores";
  - 30% or less: "does not";
  - in between: "partly".
  - H2a, H2b and H4 are also reported for these arms.
- **Additional Claude arms** are reported beside the main-paper arms. They do not enter the pooled figures of H1 to
  H4. Any with thinking on are reported with the reasoning arms under H5.
- **Controls.** Control pairs split in at most 5% of cells in every condition.
- **Who is wronged (descriptive).** For domains 1 and 2, alone bare, by arm:
  - the share of favoured-party cells with a yes-rate below 0.5 (a wrong verdict against the favoured party);
  - the share of other-party cells with a yes-rate of 0.5 or above (a wrong verdict in its favour).

## What the failure of each hypothesis would mean

- **H1 fails on the side-by-side arm (below 60%).** The items do not carry a party-relative standard that the models
  apply even when the contrast is in front of them. Claim 1 then has no base: nothing is shown to be lost. The paper
  reports a failure of the material, not a finding about single files.
- **H1 fails on the alone arm (above 25%), or the difference falls short of 35 points or its interval includes
  zero.** Models keep the standard when reading one file. Claim 1 is false for this material and these arms, and the
  paper says so.
- **H2a fails.** Stating the standard does not bring the distinction back. Claim 2 holds at most for lines (if H2b
  holds). A deployer cannot repair single-file reading by writing the standard into the prompt.
- **H2b fails.** Even a bright line does not restore the distinction to the side-by-side level. Claim 2 fails in its
  strong form. The paper reports how far each sentence moves the split share, without the claim that a sentence
  restores it.
- **H3 fails.** A line restores no more than the standard does. The paper cannot recommend lines over standards for
  restoring the distinction, and claim 3's cost would then come with no offsetting gain.
- **H4 fails on the share (below 25%).** Claim 3 is not supported: with a line stated, failings outside it are mostly
  still caught.
- **H4 fails on the comparison (same subject not higher).** Any leakage is not tied to the line's own subject. The
  paper may report general leniency after a stated rule, but not that a line passes failings within its subject.
- **H5** is a question, so no outcome fails it. Each reading is reported as worded above.
- **Controls fail (above 5% in a condition).** That condition splits on a meaningless difference at that rate. Its
  split share is not read as party-relative, and every hypothesis resting on it is reported as uninterpretable.
- **Who is wronged** is descriptive and has no failure condition.

## Arms

To be listed at stop 3 with provider and model string; Cassian chooses the arms and sets the caps.
- Main-paper arms: on their banked routes. Claude Sonnet 5 without reasoning goes through OpenRouter on run 253's
  settings. haiku_r goes through the Anthropic API, after its ten-cell route check is repeated and matches.
- Additional Claude arms: through the Anthropic API, with thinking set explicitly (off, or on with a recorded budget),
  never by default and with no fallback to another route.
- Every arm: all conditions in one session and one route, with the served model recorded. Ten draws on sampled arms,
  P(yes) from log-probabilities where served, five draws on reasoning arms. Every response kept verbatim.

## Pilot (item validity only)

Side by side only, two arms, three draws. A pair that splits side by side on neither pilot arm is revised or replaced
before the freeze, and this file records which.

Fixed by Amendment 1, before the pilot's first call:
- **Arms.** Claude Sonnet 5 without reasoning through OpenRouter (`claude`) and Qwen3-Next-80B (`qwen80b`), each on its
  banked side-by-side wire (sampled, max_tokens 256, reasoning off).
- **Material.** Condition A of the 36 pairs in draft v2 (`data/sfv_259/draft_v2.json`, c3bcad34): both orders, three
  draws each, so six draws per party per arm. Controls are not piloted.
- **Criterion.** A pair splits on an arm when, pooling both orders, the favoured party's yes-rate is at least 0.6 and the
  other party's at most 0.4, among parsed draws, with at least four of six parsed for each party. A pair that splits on
  neither arm is revised or replaced; Cassian sees the replacements before the freeze.
- The pilot's responses are kept and reported, and enter no hypothesis. H1 is also reported with these two arms
  excluded, as registered above.

## Amendment 2 (2026-11-12): design, arms, caps, the order effect

Committed before any confirmatory call. Cassian's instruction "run 259, arms, caps and freeze" replaces any earlier
arms instruction. The revised rows are approved as they stand in draft v3 (`data/sfv_259/draft_v3.json`, ff18bf00;
prompts identical to v2), and the pilot needed no replacements.

### Design

The full design: six pairs per domain (36 test pairs, 6 controls, 408 prompts), ten draws on sampled non-reasoning
arms (log-probability arms: ten reads), five on reasoning arms and on every adaptive-thinking arm.

### Main-paper arms (the registered pool for H1 to H5)

Every main arm runs on its banked route and wire (AI_Ethics `scripts/read_run248.py`, `wires()`, never retyped). Side by
side (A) is sampled at max_tokens 256 and both labels are parsed. Alone (B to E), on the non-reasoning arms, uses run
258's verdict wire: P(yes) from log-probabilities on gpt4o, llama70b, qwen80b, mistral24b and gemma27b, sampled on the
others (kimi sampled, as ruled in run 248). Reasoning arms use their banked side and alone wires.

| Arm | Model string | Route, provider | Class |
|---|---|---|---|
| claude | anthropic/claude-sonnet-5, reasoning off | OpenRouter, Anthropic | non-reasoning |
| gpt6s_s | openai/gpt-6-sol, reasoning off | OpenRouter, OpenAI | non-reasoning |
| grok43_s | x-ai/grok-4.3, reasoning off | OpenRouter, xAI | non-reasoning |
| gpt4o | openai/gpt-4o | OpenRouter, OpenAI | non-reasoning |
| haiku_s | anthropic/claude-haiku-4.5, reasoning off | OpenRouter, Anthropic | non-reasoning |
| kimi | moonshotai/kimi-k3, reasoning off | OpenRouter, Sail Research | non-reasoning |
| llama70b | meta-llama/llama-3.3-70b-instruct | OpenRouter, CoreWeave | non-reasoning |
| qwen80b | qwen/qwen3-next-80b-a3b-instruct | OpenRouter, Parasail | non-reasoning |
| gpt6l_s | openai/gpt-6-luna, reasoning off | OpenRouter, OpenAI | non-reasoning |
| mistral24b | mistralai/mistral-small-3.2-24b-instruct | OpenRouter, Parasail | non-reasoning |
| gemma27b | google/gemma-3-27b-it | OpenRouter, Parasail | non-reasoning |
| grok43_r | x-ai/grok-4.3, reasoning on | OpenRouter, xAI | reasoning |
| gemini_r | google/gemini-3.8-flash, reasoning on | OpenRouter, Google | reasoning |
| gpt6s_r | openai/gpt-6-sol, reasoning on | OpenRouter, OpenAI | reasoning |
| gpt6l_r | openai/gpt-6-luna, reasoning on | OpenRouter, OpenAI | reasoning |
| haiku_r | claude-haiku-4-5, thinking budget 1,024 | Anthropic API (route check MATCH 10 of 10) | reasoning |

- **H5 is read on the five reasoning arms above.**
- **Gemini Pro is not read in this run.** It is deferred for cost. Any arm read later on the frozen frames is reported
  separately, as a later reading, and does not enter the figures registered here.
- **Not read and not substituted** (their banked providers no longer serve them): deepseek, deepseek_s, deepseek_r,
  qwen235b, qwen30b.

### Additional Claude arms (Anthropic API)

Reported beside the main arms and never pooled into H1 to H4. **The rule "thinking on with a fixed budget, or off" is
replaced** (the newer models accept no budget, and Opus 5.5 and Fable 5.2 cannot turn thinking off): each arm uses the
setting the model allows, fixed for the whole arm and recorded, and **every call logs whether the model thought**
(thinking tokens above zero, from the API's usage record).

| Arm | Model | Setting | Class | Draws |
|---|---|---|---|---|
| haiku55_off | claude-haiku-5-5 | thinking `disabled` | off | 10 |
| haiku55_ah | claude-haiku-5-5 | thinking `adaptive`, effort `max` (the highest of low, medium, high, xhigh, max) | adaptive-high | 5 |
| sonnet55_off | claude-sonnet-5-5 | thinking `between_tools` (the API's stated way to turn thinking off on this model: "The model does not think before responding") | off | 10 |
| sonnet55_ah | claude-sonnet-5-5 | thinking `adaptive`, effort `max` | adaptive-high | 5 (open, below) |
| opus55_ad | claude-opus-5-5 | thinking `adaptive`, no effort sent (the API's default) | adaptive-default | 5 (open, below) |

Off arms: max_tokens 256. Adaptive arms: max_tokens 64,000, as a ceiling. Temperature 1.0 throughout. Sonnet 5 and
Haiku 4.5 are not added through the Anthropic API (they duplicate main arms), and no older model is added.

**Reporting.** Off arms beside the non-reasoning arms. Adaptive-high arms beside the reasoning arms under H5, with the
share of calls on which the model thought. Adaptive-default arms separately, with the same share. For every adaptive
arm, the split shares are also given separately for calls that thought and calls that did not (descriptive only: a
sub-cell uses only those draws and counts when each party has at least one parsed such draw).

**Pricing probe** (AI_Ethics `records/RUN259_ADAPTIVE_PROBE.json`; pricing data only, not analysed, not part of the
run). Twenty prompts of draft v3, four from each of A to E, test pairs from four different domains per condition,
seed 259, each read once at the arm's setting; 80 calls, $0.71.

| Arm | Calls that thought | Mean output tokens (max) | Probe cost | Re-priced full arm | Rule | Outcome |
|---|---|---|---|---|---|---|
| opus55_ad | 19 of 20 | 162 (332) | $0.08 | $8.36 | add if at most $10 | qualifies |
| fable52_ad | 20 of 20 | 270 (507) | $0.25 | $25.46 | add if at most $18 | **left out** |
| haiku55_ah | 20 of 20 | 7,445 (20,983) | $0.07 | $7.64 | added unless above $15 | added |
| sonnet55_ah | 20 of 20 | 1,465 (9,986) | $0.30 | $30.77 | added unless above $15 | **above $15: stop** |

The probe streamed its calls, and a streamed response carries no thinking-token count, so its log reads 0 throughout;
the "thought" column above is recomputed from the thinking blocks each response carries (AI_Ethics
`records/RUN259_ADAPTIVE_PROBE_THOUGHT_NOTE.json`). The run's calls are not streamed, and a call without the count is
refused rather than recorded as 0. Costs are unaffected.

**Open.** Sonnet 5.5 at max effort re-prices above $15, so by Cassian's rule the run stops for his ruling. With it, the
Anthropic side cannot fit the cap even without Opus 5.5; without it, Opus 5.5 fits. The arm list is settled by his
ruling, recorded as an addendum to this amendment before the freeze.

### Addendum to Amendment 2: Cassian's ruling on the open point (2026-11-12, before the freeze)

Option (a). **Sonnet 5.5 at max effort (sonnet55_ah) is not read.** The additional Claude arms are:

| Arm | Setting | Class | Draws | Price (full arm) |
|---|---|---|---|---|
| haiku55_off | Haiku 5.5, thinking `disabled` | off | 10 | $0.10 |
| sonnet55_off | Sonnet 5.5, thinking `between_tools` | off | 10 | $2.02 |
| haiku55_ah | Haiku 5.5, adaptive, effort `max` | adaptive-high | 5 | $7.64 |
| opus55_ad | Opus 5.5, adaptive, no effort sent (the API's default) | adaptive-default | 5 | $8.36 |

- **Fable 5.2 (fable52_ad) is deferred for cost** (re-priced at $25.46). It may be read later on the frozen frames, and
  is then reported separately as a later reading.
- The adaptive-high arm under H5 is haiku55_ah alone.
- Anthropic side: estimate $22.15 (haiku_r and the four arms); with the start margin and the probe, $28.39 against the
  $55 cap. OpenRouter: $22.56 with the margin against $24.
- Frozen frames: AI_Ethics `records/RUN259_FRAMES.json` (draft v3's prompts with their messages), sha256
  f632ff01d48f4033218cf5447c0393de067c80cd053b933a650d733e7cf3e6fb; reader `scripts/read_run259.py` pins it.

### Caps

- **OpenRouter: $24.** Estimate for the fifteen OpenRouter arms $18.05; with the guard's start margin (x1.25) $22.56.
  Balance on 2026-11-12, 14:33 GMT: $26.73.
- **Anthropic: $55**, covering haiku_r, every additional arm and the probes, with the start margin in the preflight.
- The spend guard is run 248's: before every call, if a group's projected total exceeds its cap, its most expensive
  running arm stops and is reported unread. Each arm also carries a backstop of three times its estimate.

### The order effect (no change to H1)

The pilot showed Qwen3-Next-80B separating the parties in one order and not the other on 13 pairs. Pooling the two
orders, as H1's registered definition does, counts those as not splitting.

- **H1 stays exactly as committed** and is judged as committed.
- **Registered secondary measure.** The side-by-side split share with each order counted as its own cell (one prompt,
  one cell), pooled over the non-reasoning main arms and by arm, with the same alone-bare comparison (difference and
  interval by the registered bootstrap). It has no threshold.
- **Registered description.** For each arm, the number of pairs that split in one order and not the other, among pairs
  whose two order cells are both valid.
- These were added after the pilot, which read the side-by-side condition on two arms (claude and qwen80b). H1 is also
  reported with those two arms excluded, as already registered.

### Clarifications of reading (no threshold changed)

- **Pooled side-by-side cell.** Its draws are both orders' draws together, and the definition of a valid cell applies
  to them as they stand (sampled: at least 80% parsed; reasoning arm: void count at most 10% of the pooled draws).
- **Alone verdicts** are parsed as the single word, else a leading yes or no, else a yes or no closing the text (for
  reasoning arms that write more than the word). Log-probability arms: P(yes) / (P(yes) + P(no)).
- **Truncation void.** On reasoning and adaptive arms, a draw stopped at max_tokens, or with an empty answer after
  reasoning.

### Analysis

`analysis/analyse.py` produces every registered figure and `paper/numbers.tex` (via `analysis/macros.py`). Selftest 4
of 4. Dry run on the pilot's responses (`results/dry_run_pilot.json`): it executes end to end, reproduces the pilot's
pooled splits (claude 35 of 36, qwen80b 21 of 36) and the 13 one-order pairs on qwen80b, and leaves B to E empty, as
the pilot read only A.

## Changes

- 2026-11-12, stop 1: drafted. Items under review (AI_Ethics `records/RUN259_REVIEW_draft.xlsx`, draft
  `data/sfv_259/draft_v1.json` a8e716b2).
- 2026-11-12, Amendment 1 (Cassian's rulings on stop 1), before the pilot's first call:
  - Repository renamed `single-file-verdicts` to `rough-justice-paper`; working title set in `paper/main.tex` only.
  - Items revised to draft v2 (`data/sfv_259/draft_v2.json`, c3bcad34; 44 of 408 prompts changed):
    - I4 and I5: the fact not mentioned is now a feature of the property or its use that reflects no carelessness
      (I4 a bungalow empty two months each winter, a pipe bursts; I5 scaffolding for works next door, thieves climb it),
      with each line and E failing fitted to the new case.
    - V3: the E failing's deadline is now a week later than the real one.
    - V3 and V4: neutral openers for the ordinary customer (a birthday; taking up gardening).
    - K6: the shared sentence reads "passed the figures on without comment".
  - Domains 3 to 6: lines registered as stipulated operationalisations, not statements of law.
  - H4: the note that it rests on the model's own verdicts, and the registered secondary measure.
  - Pilot arms, material and criterion fixed.
  - Still to come before the freeze: every provision checked against legislation.gov.uk (or HMRC) with its URL; the
    pilot's revisions; arms and caps (stop 3); the analysis script.
- 2026-11-12, pilot read (13:12 to 13:19 GMT, 432 calls, $0.188; AI_Ethics `records/RUN259_PILOT.json`): pairs split on
  claude 35 of 36 (K2 not) and on qwen80b 21 of 36. **Every pair splits on at least one arm, so no pair is revised or
  replaced.** Served model constant on both arms. On qwen80b, 13 of its 15 non-splits are order effects (the favoured party
  gets yes in one order and no in the other, all three draws), reported, not acted on.
- 2026-11-12, provisions checked against legislation.gov.uk (current versions) and HMRC's manual; URLs recorded in the item
  file. Every threshold stands. Citations corrected: T5 (Sch 46 para 15(2) carries the thresholds; para 16 defines the
  officer; para 18 'company'); T6 (s.414CA(A1), (1A), (2A)(a), (3), (4) and s.414CB(A1), (2A)); T5's E (FSH(E)R 2013 reg
  19(1) with Sch 2 and Regulation 178/2002 art 14(1)); T3 ('250 or more employees'); insurance ('unasked' rests on IA 2015
  s.3(5)). The reserves are kept with their URLs.
- 2026-11-12, haiku_r's ten-cell route check repeated through the Anthropic API: MATCH, 10 of 10 within band
  (AI_Ethics `records/RUN259_HAIKU_ROUTE_CHECK.json`, $0.22).
- 2026-11-12, Amendment 2 (Cassian's "arms, caps and freeze"), before any confirmatory call: full design; sixteen main
  arms and their routes; gemini_pro deferred and five arms named as not read; additional Claude arms with the thinking
  rule replaced and the pricing probe's figures (Fable 5.2 left out; Sonnet 5.5 at max effort above $15, open for
  Cassian's ruling); caps ($24 OpenRouter, $55 Anthropic); the order effect's secondary measure and description;
  reading clarifications; the analysis script and its dry run on the pilot.
- 2026-11-12, addendum to Amendment 2 (Cassian's option (a)), before the freeze: sonnet55_ah not read; opus55_ad added;
  fable52_ad deferred for cost ($25.46); frames frozen (f632ff01).
