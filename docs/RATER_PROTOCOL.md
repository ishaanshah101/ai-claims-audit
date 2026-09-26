# Rating protocol

This file records what the six rating passes were given and what they returned, so a
replication can reconstruct the procedure.

## Setup

Six independent passes ran as subagents of the orchestrating model, on Claude Sonnet, with
no shared context and no ability to see one another's output. Each pass was given exactly
one input file, `data/rating/rater_N_items.json`, containing only the sentences assigned to
it, each as `{"rid": <int>, "text": <string>}`. Rater 0 through rater 3 received 208
sentences each and raters 4 and 5 received 207, for 1,246 judgements over 623 sentences,
each sentence assigned to exactly two passes.

No pass received the company name, the ticker, the sector, the SIC code, the filing date,
the accession number, the sentence's position in its filing, the rubric's motivation, the
study's hypotheses, or any other pass's output. The `rid` values are post-shuffle indices,
so consecutive `rid`s are not consecutive sentences in a filing.

## Instruction content

Each pass was instructed to apply the preregistered rubric, reproduced verbatim from
`docs/PREREGISTRATION.md` section 4, and to write one JSON object per line to
`data/rating/rater_N.jsonl` in this schema:

```json
{"rater": 0, "rid": 17, "class": "capability",
 "quantified": false, "metric_named": false, "evaluation_described": false,
 "baseline_given": false, "uncertainty_given": false}
```

with `class` one of `capability`, `risk`, `market`, `governance`, `other`, and the five
Part B fields set to `null` on any sentence whose class is not `capability`, since the
preregistration records Part B only for capability claims.

`src/validate_ratings.py` enforces every element of that schema after the fact: the rater
field, that each `rid` was assigned to that rater, no duplicates, no omissions, a legal
class, booleans on capability rows and nulls elsewhere, and that every sentence in the
corpus carries exactly two judgements. It passes with zero problems on the published
output.

## A reproducibility caveat

The six passes were dispatched interactively and the literal prompt strings were not
written to disk at the time. What is recorded above is the content of the instruction, not
a byte-exact transcript of it, and a replication should treat the preregistered rubric plus
the schema above as the specification rather than assume identical wording. The inputs, the
outputs and the validator are all published, so the thing that can be checked exactly is
what the passes were shown and what they returned.

## The calibration reviewer

The composition calibration and the numeral-candidate review were performed by the
orchestrating model, Claude Opus 5, reading `data/calibration/c1_blind.json` and
`data/calibration/c2_blind.json`. Those files contain display identifiers and sentence text
only. The corresponding key files, which map a display identifier back to a `rid` and to the
verdicts being checked, were not read until the reviewer's judgements had been written to
`data/calibration/c1_reviewer.jsonl` and `data/calibration/c2_reviewer.jsonl`. Eight
sentences appear twice in the C1 blind file under different display identifiers as
self-consistency controls; the reviewer was consistent on all eight.
