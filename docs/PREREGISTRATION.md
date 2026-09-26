# Preregistration

**Study.** An audit of what public companies actually claim about artificial
intelligence in their annual reports, and whether a reader outside the company could
check any of it.

**Status.** Written after the corpus was built and before any sentence in it was
read or scored. Every later change is recorded as a numbered, dated amendment at the
bottom of this file, with the reason.

---

## 1. Why this question

Two things are true at once. Public companies describe AI capabilities in filings
that are legally required to be accurate and that investors price on, and the SEC has
brought enforcement actions against registrants for overstating AI capability, the
practice the Commission itself calls AI washing. What nobody has measured is the base
rate: across ordinary annual reports, how much AI language is a claim about the
company's own capability at all, and of that, how much is stated precisely enough
that a reader could in principle check it.

This matters commercially because the same number that appears in a filing appears in
a sales deck. A buyer evaluating an AI vendor, an investor pricing an AI story and a
regulator assessing a disclosure are all doing the same thing, which is asking whether
a stated capability can be verified, and this study measures how often the answer is
no.

## 2. Research questions

- **RQ1 (composition).** Of the sentences in a 10-K that mention AI, what fraction
  assert a capability of the registrant's own AI, as opposed to describing risk, the
  market, or governance?
- **RQ2 (verifiability).** Of those capability claims, what fraction carry a
  quantitative performance figure, a named metric, a described evaluation, a stated
  baseline and a statement of uncertainty?
- **RQ3 (checkability).** What fraction of capability claims meet the minimum bar at
  which an outside reader could even attempt verification?
- **RQ4 (sector).** Do these rates differ between technology, healthcare, finance and
  real estate, and everything else?

## 3. Corpus and sampling

- **Frame.** Every 10-K filed between 2025-01-01 and 2025-12-31 whose full text
  matches the exact phrase "artificial intelligence" in EDGAR full-text search. The
  frame was enumerated completely rather than sampled: 3,324 filings from 3,173
  distinct registrants. `src/frame.py` reproduces it.
- **One filing per registrant**, so that a single company filing several documents
  cannot dominate.
- **Stratification.** Four strata assigned from the SEC's own SIC code: technology,
  healthcare, finance and real estate, and other. AI language in filings is not
  confined to technology companies, and an unstratified draw would be dominated by
  pharmaceutical and financial registrants, who are the largest groups in the frame.
- **Draw.** 15 filings per stratum without replacement under seed 20260926, giving 60
  filings.
- **Sentence extraction.** Each filing is converted to text and split by a fixed
  deterministic splitter. A sentence enters the corpus when it matches a fixed AI term
  list, is between 60 and 1,200 characters, and is less than 25 percent digits, the
  last two rules excluding table fragments and headings rather than prose. The term
  list and the splitter were fixed before any filing was downloaded and are in
  `src/fetch_and_extract.py`.
- **All extracted sentences are scored.** There is no second-stage sampling.

## 4. What gets recorded for each sentence

**Part A, classification.** Exactly one of:

- `capability` — asserts that the registrant's own product, service or operation uses
  AI, and attributes a capability, benefit, efficiency or performance level to it
- `risk` — risk-factor language: competition, regulation, security, reputational or
  ethical risk arising from AI
- `market` — describes AI in the industry, in the market, or at competitors, rather
  than at the registrant
- `governance` — describes policy, board oversight, internal controls or responsible
  use programmes for AI
- `other` — definitions, cross-references, forward-looking boilerplate and anything
  that fits none of the above

**Part B, verifiability.** Recorded only when Part A is `capability`. Five
independent yes or no judgements, deliberately binary rather than scaled:

1. `quantified` — a specific numeric performance figure is attributed to the AI
2. `metric_named` — the quantity being reported is named, for example accuracy,
   precision, error rate, hours saved, cost per claim
3. `evaluation_described` — the filing says what data, population or period the figure
   was measured over
4. `baseline_given` — it says what the figure is being compared against, such as a
   prior period, a manual process or a competing method
5. `uncertainty_given` — an interval, a sample size, or any error estimate is stated

**Derived measures, fixed now.**

- `verifiability_score` = the count of the five that are yes, from 0 to 5
- `checkable` = `quantified` AND `metric_named` AND `evaluation_described`, the
  minimum at which an outside reader could attempt verification at all

## 5. Blinding

Raters see the sentence text and nothing else. They are not told the company, the
sector, the filing date or the position of the sentence in the document, and the
registrant's own name and ticker are removed from the sentence text where they appear.
Sentences are presented in a seeded shuffle that mixes filings together, so a rater
cannot reconstruct a company from a run of consecutive sentences.

Each sentence is rated by two independent raters who cannot see each other's output.
Assignment is fixed before rating begins.

## 6. Adjudication and calibration

Where two raters disagree on Part A, the sentence is recorded as `disputed` and
excluded from the headline composition rate, with its effect reported as a bound
rather than resolved by a third party who knows the design.

A calibration pass then re-reads a seeded sample of scored sentences, blind to the
verdicts being checked and mixed with controls, exactly as in the companion audit of
the KFuji RGB-DS dataset. This exists because in that study a chained pair of
automated passes produced a confident and internally consistent number that was wrong
by nearly a factor of nine, and the only thing that caught it was a cheap blinded
re-check. If the calibration pass here shows a systematic bias in either direction,
every rate in the paper is corrected against it and the correction is reported.

## 7. Statistics

- Proportions with Wilson score intervals at 95 percent.
- Because sentences within a filing are not independent, all filing-level uncertainty
  comes from a percentile bootstrap that resamples filings rather than sentences,
  10,000 replicates under a fixed seed.
- Sector comparisons use the bootstrap difference in rates, not a chi-squared test on
  sentences, for the same clustering reason.

## 8. Who the raters are

The raters and the calibration pass are AI language models, not people. This study
therefore does not measure human inter-rater agreement and no figure in it should be
read that way. What it measures is whether independent, protocol-driven passes over
the same text reach the same classification, and how far each pass survives review by
a more careful one. Every sentence and every judgement is published, so any reader who
disputes a call can look at the sentence and say so.

## 9. Predictions, stated in advance

1. Risk-factor mentions will outnumber capability claims.
2. Fewer than 10 percent of capability claims will be quantified.
3. Fewer than 2 percent of capability claims will be checkable.
4. Technology registrants will make capability claims at a higher rate than the other
   three strata.

## 10. What would falsify the thesis

If most capability claims turn out to be quantified, with a named metric and a
described evaluation, then AI disclosure in annual reports is in good shape, the
premise of this study is wrong, and that result will be reported in those words and
with the same prominence.

## 11. Amendments

**Amendment 1, 2026-09-26. The calibration pass was extended with a component
that enumerates instead of sampling.**

Section 6 committed to a calibration pass over a seeded sample. A sample can only
bound the bias on a rate statistically, and the rate that carries the paper,
`quantified`, gates the derived `checkable` measure, so a false negative there
would inflate the headline in the direction the study expects. A numeric figure
is a necessary condition for `quantified`, so every sentence in the corpus was
screened mechanically for a numeral capable of expressing a performance figure,
and all 74 candidates were read blind, with the matched numerals shown and no
verdicts. Because the screen is exhaustive, the resulting count of quantified
claims is exact rather than estimated, and any claim the automated passes missed
would necessarily have appeared in the candidate set. The sampled composition
calibration described in Section 6 was run as written, in addition, not instead.

**Amendment 2, 2026-09-26. Term-list false positives are removed from every
denominator.**

The AI term list was fixed before any filing was downloaded, as Section 3
required, which meant its failure modes could only be measured afterwards. An
audit recording which pattern matched each sentence found that `\bml\b` also
matches mL, the millilitre, and that `\bai\b` matches the letters AI inside
entity names, a .ai web address, and a stray token left by text extraction. The
screen is exhaustive over the corpus and flags 25 of the 623 extracted sentences,
every one of which was confirmed by reading to contain no reference to artificial
intelligence. Those 25 are removed from every denominator; the analysis reports
the extracted count, the removed count and the corrected count separately so that
the correction can be undone by a reader who disagrees with it. The 19 sentences
independently flagged as non-AI by the blinded review of the numeral candidates
all fall inside the same set of 25.

**Amendment 3, 2026-09-26. The raters are specified.**

Section 8 stated that the raters and the calibration pass are language models
rather than people. To make that reproducible: the six rating passes ran on Claude
Sonnet as independent subagents with no shared context, and the composition
calibration, the numeral-candidate review and the adjudication were performed by
Claude Opus 5, the model orchestrating the study, which is also the more capable
of the two and is treated throughout as the reviewing pass rather than a peer.

**Amendment 4, 2026-09-26. Blinding leakage is measured and reported rather than
repaired.**

Section 5 stated that the registrant's name and ticker are removed from the
sentence text where they appear. The redaction matched the full name and the
ticker, not individual distinctive tokens, and page headers survive text
extraction, so some sentences still contain the filer's name. Rather than
re-redact and re-rate, which would require discarding the completed passes, the
leakage was measured: a screen for any name token of four or more characters
flags 37 of 598 corpus sentences (6.2 percent), and restricting to tokens that
actually identify a filer rather than generic words such as Health or Technology
leaves 7 sentences (1.2 percent) naming two companies. Agreement on the flagged
sentences is lower than on the rest, 86.5 against 93.6 percent, so the leakage did
not help the raters agree. The deviation is reported in the paper's limitations.
