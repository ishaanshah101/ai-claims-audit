"""Recompute every number quoted in the paper from the raw data and check it
appears in paper.md. Exits non-zero on any mismatch.

This exists because a paper is written by hand from a results file, and the
step where a number is copied across is the one nobody checks.
"""
import json, os, re, sys, collections
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_RAW = open(os.path.join(BASE, "paper", "paper.md")).read()
# the paper is hard-wrapped, so every quoted string is matched against a
# whitespace-normalised copy rather than the raw text
PAPER = re.sub(r"\s+", " ", PAPER_RAW)
A = json.load(open(os.path.join(BASE, "results", "analysis.json")))
G = json.load(open(os.path.join(BASE, "results", "agreement.json")))
C = json.load(open(os.path.join(BASE, "results", "calibration.json")))
S = json.load(open(os.path.join(BASE, "results", "supplement.json")))
items = {i["rid"]: i for i in json.load(open(os.path.join(BASE, "data/rating/items.json")))}
rows = json.load(open(os.path.join(BASE, "data/rating/all_ratings.json")))
frame = json.load(open(os.path.join(BASE, "data/frame.json")))
sample = json.load(open(os.path.join(BASE, "data/sample_filings.json")))

fails, checks = [], 0


def ck(label, condition):
    global checks
    checks += 1
    if not condition:
        fails.append(label)


def norm(s):
    return re.sub(r"\s+", " ", s)


def instr(label, s):
    ck(f"{label}: paper contains {s!r}", norm(s) in PAPER)


def approx_in(label, value, text, tol):
    """The paper quotes `text`; check it parses to within tol of `value`."""
    global checks
    checks += 1
    if norm(text) not in PAPER:
        fails.append(f"{label}: {text!r} not in paper")
        return
    got = float(re.sub(r"[^0-9.\-]", "", text))
    if abs(got - value) > tol:
        fails.append(f"{label}: paper says {got}, recomputed {value}")


# ---------------------------------------------------------------- frame/sample
fr = frame["rows"]
ck("frame is a list", isinstance(fr, list))
ck("frame reported total matches collected",
   frame["reported_total"] == frame["collected"] == len(fr))
instr("frame size", "3,324")
ck("frame count", len(fr) == 3324)
ciks = {f["cik"] for f in fr}
ck("3173 distinct registrants", len(ciks) == 3173)
instr("distinct registrants", "3,173")
sm = sample["filings"]
ck("sample seed", sample["seed"] == 20260926)
ck("sample per stratum", sample["per_stratum"] == 15)
ck("sample size 60", len(sm) == 60)
instr("sample described as 60", "60 filings")
instr("15 per stratum", "Fifteen filings were drawn")
sec_counts = collections.Counter(x["sector"] for x in sm)
ck("15 per sector", all(v == 15 for v in sec_counts.values()))
instr("stratum pools", "499, 553, 724 and 1,397")

# ---------------------------------------------------------------- extraction
ck("623 extracted", A["n_extracted"] == 623 == len(items))
instr("623 in paper", "623")
n_sent = [len([r for r in items if items[r]["adsh"] == a])
          for a in {i["adsh"] for i in items.values()}]
ck("59 filings yielded sentences", len(n_sent) == 59)
instr("59 filings", "Fifty-nine")
ck("median 7", sorted(n_sent)[len(n_sent) // 2] == 7)
instr("median 7", "median of 7 per")
ck("max 65", max(n_sent) == 65)
instr("max 65", "maximum of 65")

# ---------------------------------------------------------------- term audit
ck("25 false positives", len(C["term_false_positive_rids"]) == 25)
ck("20 on ml", len(C["term_false_positive_only_ml"]) == 20)
ck("5 on ai", len(C["term_false_positive_name_or_stray"]) == 5)
approx_in("fp rate", 100 * 25 / 623, "4.0 percent", 0.05)
instr("25 of 623", "25 sentences out of 623")
instr("twenty ml", "Twenty sentences")
instr("five more", "finds five more")
ck("corpus 598", A["n_corpus"] == 598 == 623 - 25)
instr("598", "598 sentences")
ck("19 non-ai in c2", len(C["c2_reviewer_non_ai_rids"]) == 19)
instr("19 flagged", "flagged 19 sentences")
ck("c2 non-ai subset of fp", set(C["c2_reviewer_non_ai_rids"]) <= set(C["term_false_positive_rids"]))

# ---------------------------------------------------------------- agreement
ag = A["agreement_on_corrected_corpus"]
approx_in("observed agreement", 100 * ag["observed_agreement"], "93.1 percent", 0.05)
approx_in("alpha", ag["krippendorff_alpha_nominal"], "0.879", 0.0005)
ck("557 agreed", A["n_agreed"] == 557)
instr("557", "same Part A class 557 times")
ck("41 disputed", A["n_disputed"] == 41)
instr("41", "41 disagreements")
ck("1246 judgements", len(rows) == 1246)
instr("1246", "1,246")
approx_in("psa risk", G["positive_specific_agreement"]["risk"], "0.979", 0.0005)
approx_in("psa market", G["positive_specific_agreement"]["market"], "0.821", 0.0005)
dp = G["disagreement_pairs"]
ck("15 cap-other", dp.get("capability|other") == 15)
instr("fifteen cap-other", "Fifteen of them are capability against other")
ck("7 market-other", dp.get("market|other") == 7)
ck("7 market-risk", dp.get("market|risk") == 7)
pb = G["part_b_agreement"]
ck("metric_named 7 disagreements", pb["metric_named"]["disagreed"] == 7)
instr("seven times", "disagreed seven times on `metric_named`")
ck("eval 1 disagreement", pb["evaluation_described"]["disagreed"] == 1)
for b in ("quantified", "baseline_given", "uncertainty_given"):
    ck(f"{b} no disagreement", pb[b]["disagreed"] == 0)
ck("75 both capability", G["n_both_capability"] == 75)

# ---------------------------------------------------------------- composition
ca = A["composition_agreed"]
for c, n in [("risk", 365), ("capability", 75), ("other", 71), ("market", 39), ("governance", 7)]:
    ck(f"agreed count {c}", ca[c]["n"] == n)
instr("agreed counts", "365 are risk-factor language, 75 are")
cc = A["composition_calibrated"]
for c, txt in [("risk", "60.5 percent risk"), ("other", "16.2 percent"),
               ("capability", "12.2 percent capability"), ("market", "9.2 percent market"),
               ("governance", "1.9 percent governance")]:
    approx_in(f"calibrated {c}", 100 * cc[c]["rate"], txt, 0.06)
for c, lo, hi in [("risk", "51.9 to 69.9", None), ("other", "11.5 to 21.0", None),
                  ("capability", "7.7 to 16.6", None), ("market", "4.7 to\n14.9", None),
                  ("governance", "0.4 to 3.7", None)]:
    ck(f"calibrated interval {c} quoted", norm(lo) in PAPER)
    a_lo, a_hi = [float(x) for x in re.findall(r"[\d.]+", norm(lo))]
    ck(f"calibrated lo {c}", abs(100 * cc[c]["boot_lo"] - a_lo) < 0.06)
    ck(f"calibrated hi {c}", abs(100 * cc[c]["boot_hi"] - a_hi) < 0.06)
b = A["composition_bounds_on_full_corpus"]
instr("bound cap quoted", "12.5 and 15.7")
ck("bound cap lo", abs(100 * b["capability"]["lower_rate"] - 12.5) < 0.06)
ck("bound cap hi", abs(100 * b["capability"]["upper_rate"] - 15.7) < 0.06)
ck("bound risk", abs(100 * b["risk"]["lower_rate"] - 61.0) < 0.06
   and abs(100 * b["risk"]["upper_rate"] - 63.7) < 0.06)
instr("risk bound", "61.0 and 63.7")
ck("ratio five times", ca["risk"]["n"] / ca["capability"]["n"] > 4.5)
instr("five times", "Five times more")
ck("19 filings with capability", S["n_filings_with_a_capability_claim"] == 19)
instr("19 filings", "Nineteen of the 59 filings")
instr("other forty", "The other forty")
ck("40 = 59-19", 59 - 19 == 40)

# ---------------------------------------------------------------- calibration
sv = A["transfer_matrix"]
for c, txt, n_s, n_r in [("governance", "100 percent of the time for governance (5 of 5)", 5, 5),
                         ("risk", "96.7 percent for risk (29 of 30)", 29, 30),
                         ("other", "90.0 percent for other (18 of 20)", 18, 20),
                         ("capability", "86.7 percent for capability (26 of 30)", 26, 30),
                         ("market", "75.0 percent for market (9 of 12)", 9, 12)]:
    instr(f"survival {c}", txt)
    ck(f"survival value {c}", abs(sv[c][c] - n_s / n_r) < 0.001)
ck("self consistency 8/8", C["reviewer_self_consistency"]["n_consistent"] == 8
   and C["reviewer_self_consistency"]["n_pairs"] == 8)
instr("8/8", "consistent with myself on all eight")
ck("97 agreed cal units", A["n_calibration_units_agreed"] == 97)
instr("97", "97 agreed sentences")
ck("20 disputed reviewed", C["c1_disputed_n"] == 20)
ck("19 inside pair", C["c1_disputed_inside_pair"] == 19)
instr("19 of 20", "19 times out of 20")
ck("cap 4 overturns to other", A["composition_calibrated"] and
   round((1 - sv["capability"]["capability"]) * 30) == 4
   and abs(sv["capability"]["other"] - 4 / 30) < 0.001)
instr("four to other", "All four capability sentences I overturned went to other")
ck("117 cal sentences", json.load(open(os.path.join(BASE, "data/calibration/manifest.json")))["c1_units"] == 117)
instr("117", "117 sentences")
instr("125 displays", "125 displays")

# ---------------------------------------------------------------- verifiability
V = A["verifiability"]
ck("denominator 75", V["denominator_agreed"] == 75)
instr("cal denominator quoted", "75 to 73.2")
ck("cal denominator", abs(A["capability_calibrated_n"] - 73.2) < 0.06)
ck("metric_named 5", V["metric_named"]["n_both"] == 5)
approx_in("metric rate", 100 * V["metric_named"]["rate_agreed"], "6.7 percent", 0.05)
ck("metric wilson", abs(100 * V["metric_named"]["wilson"][0] - 2.9) < 0.06
   and abs(100 * V["metric_named"]["wilson"][1] - 14.7) < 0.06)
instr("metric wilson quoted", "2.9 to\n14.7")
ck("quantified 2", V["quantified"]["n"] == 2)
approx_in("quantified rate", 100 * V["quantified"]["rate_agreed"], "2.7 percent", 0.05)
ck("quantified wilson", abs(100 * V["quantified"]["wilson"][0] - 0.7) < 0.06
   and abs(100 * V["quantified"]["wilson"][1] - 9.2) < 0.06)
instr("quantified wilson quoted", "0.7 to 9.2")
ck("eval 1", V["evaluation_described"]["n"] == 1)
ck("baseline 0", V["baseline_given"]["n"] == 0)
ck("uncertainty 0", V["uncertainty_given"]["n"] == 0)
approx_in("wilson upper zero", 100 * V["baseline_given"]["wilson_hi"], "4.9 percent", 0.05)
vsd = A["verifiability_score_distribution"]
ck("70 score zero", vsd["0"] == 70)
instr("70 of 75", "Seventy of the 75 capability claims score zero")
ck("3 score one", vsd["1"] == 3)
ck("1 score two", vsd["2"] == 1)
ck("1 score three", vsd["3"] == 1)
ck("0 score 4,5", vsd["4"] == 0 and vsd["5"] == 0)
ck("score total", sum(vsd.values()) == 75)
ck("checkable 1", V["checkable"]["n"] == 1)
approx_in("checkable of capability", 100 * V["checkable"]["rate_agreed"], "1.3 percent", 0.05)
ck("checkable wilson cap", abs(100 * V["checkable"]["wilson"][0] - 0.2) < 0.06
   and abs(100 * V["checkable"]["wilson"][1] - 7.2) < 0.06)
instr("checkable wilson cap quoted", "0.2 to 7.2")
approx_in("checkable of corpus", 100 * V["checkable"]["rate_of_corpus"], "0.17 percent", 0.005)
ck("checkable wilson corpus", abs(100 * V["checkable"]["wilson_of_corpus"][0] - 0.03) < 0.005
   and abs(100 * V["checkable"]["wilson_of_corpus"][1] - 0.94) < 0.005)
instr("checkable wilson corpus quoted", "0.03 to 0.94")

# the two quantified sentences, quoted verbatim in the paper
ck("quantified rids", V["quantified"]["rids"] == [48, 86])
ck("checkable rid", V["checkable"]["rids"] == [48])
for rid, frag, name in [
        (48, "executing more than 180 million automated actions per month in the IT environments we manage", "Kyndryl"),
        (86, "accelerating case resolution times by an average of approximately 23%", "Rimini Street"),
        (83, "expedites mammography exam reading time without compromising image quality, sensitivity or\naccuracy", "Hologic"),
        (608, "billions of compounds in silico,\nachieving experimental accuracy on properties such as binding affinity and solubility", "Structure Therapeutics")]:
    ck(f"rid {rid} quote is verbatim", norm(frag) in norm(items[rid]["text"]))
    ck(f"rid {rid} quote in paper", norm(frag) in PAPER)
    ck(f"rid {rid} filer named", name in PAPER and name.split()[0].lower() in items[rid]["name"].lower())
ck("both passes scored 48 and 86 quantified",
   all(d["quantified"] for r in (48, 86) for d in rows if d["rid"] == r))
ck("no pass missed a quantified claim", C["quantified_missed_by_passes"] == []
   and C["quantified_overcalled_by_passes"] == [])
ck("74 numeral candidates", C["c2_screened"] == 74)
instr("74", "Seventy-four of the 623")
ck("baseline false on both", not any(d["baseline_given"] for r in (48, 86) for d in rows if d["rid"] == r))

# ---------------------------------------------------------------- sector
sec = A["sector_capability"]
for k, txt, n, d in [("technology", "15.5 percent of AI sentences at technology", 49, 317),
                     ("healthcare", "13.4 percent in healthcare", 13, 97),
                     ("other", "9.6 percent in the residual", 8, 83),
                     ("finance_realestate", "5.0 percent in finance and real estate", 5, 101)]:
    instr(f"sector {k}", txt)
    ck(f"sector counts {k}", sec[k]["n_capability"] == n and sec[k]["n_sentences"] == d)
    ck(f"sector rate {k}", abs(100 * sec[k]["rate"] - float(txt.split()[0])) < 0.06)
for k, lo, hi in [("technology", 8.8, 21.3), ("healthcare", 3.1, 26.3),
                  ("other", 0.0, 18.8), ("finance_realestate", 0.0, 15.3)]:
    ck(f"sector boot {k}", abs(100 * sec[k]["boot_lo"] - lo) < 0.06
       and abs(100 * sec[k]["boot_hi"] - hi) < 0.06)
instr("tech boot", "8.8\nto 21.3")
instr("hc boot", "3.1 to 26.3")
instr("other boot", "0.0 to 18.8")
instr("fin boot", "0.0 to 15.3")
td = A["sector_tech_vs_rest"]
approx_in("tech diff", 100 * td["difference"], "+6.2 percentage points", 0.06)
ck("tech diff interval", abs(100 * td["boot_lo"] + 3.1) < 0.06
   and abs(100 * td["boot_hi"] - 14.4) < 0.06)
instr("tech diff interval quoted", "−3.1 to +14.4")
ck("interval crosses zero", td["boot_lo"] < 0 < td["boot_hi"])

# ---------------------------------------------------------------- predictions
P = A["predictions"]
for k in P:
    ck(f"prediction {k} held", P[k]["held"])
instr("all four held", "All four held")

# ---------------------------------------------------------------- blinding
ck("37 broad leaks", S["blinding_leak_n"] == 37)
approx_in("broad leak rate", 100 * S["blinding_leak_rate"], "6.2 percent", 0.05)
ck("7 narrow leaks", S["blinding_leak_narrow_n"] == 7)
approx_in("narrow leak rate", 100 * S["blinding_leak_narrow_rate"], "1.2 percent", 0.05)
ck("two companies", len({x["name"] for x in S["blinding_leak_narrow"]}) == 2)
instr("two companies", "naming two companies")
approx_in("agreement leaked", 100 * S["agreement_on_leaked"], "86.5 percent", 0.05)
approx_in("agreement clean", 100 * S["agreement_on_clean"], "93.6 percent", 0.05)
ck("leakage did not help", S["agreement_on_leaked"] < S["agreement_on_clean"])

# ---------------------------------------------------------------- external facts
instr("SEC 2024-36", "2024-36")
instr("Presto release", "33-11352")
instr("Gensler quote", "Such AI washing hurts investors")
instr("Presto seventy percent", "seventy percent of the orders")
instr("Bean reviewers", "29 expert reviewers")
instr("Bean benchmarks", "445 language-model benchmarks")
instr("KFuji factor", "factor of nine")
instr("KFuji 56", "56 percent")
instr("KFuji 17", "17 percent")

# ---------------------------------------------------------------- README
README = re.sub(r"\s+", " ", open(os.path.join(BASE, "README.md")).read())


def inreadme(label, t):
    global checks
    checks += 1
    if norm(t) not in README:
        fails.append(f"README {label}: {t!r} not found")


inreadme("corpus", "| AI sentences in the corpus | 598 |")
inreadme("risk row", "| risk-factor language (calibrated) | 362 | 60.5% |")
ck("README risk count rounds to 362", round(cc["risk"]["count"]) == 362)
inreadme("capability row", "| claims about the registrant's own AI capability | 75 | 12.2% |")
inreadme("metric row", "| of those, name the quantity being claimed | 5 | 6.7% of claims |")
inreadme("quantified row", "| of those, attach a number to it | 2 | 2.7% of claims |")
inreadme("eval row", "| of those, say what the number was measured over | 1 | 1.3% of claims |")
inreadme("baseline row", "| of those, state a baseline | 0 | 0% |")
inreadme("uncertainty row", "| of those, state an uncertainty | 0 | 0% |")
inreadme("seventy", "Seventy of the 75 capability claims score zero")
inreadme("one in 598", "**One sentence out of 598, in one annual report out of 59")
inreadme("frame", "3,324 filings from 3,173 distinct")
inreadme("seed", "seed 20260926")
inreadme("623", "623 sentences, median 7 per filing")
inreadme("survival", "87% of the time for capability, 97% for risk, 75% for market, 100% "
                     "for governance and 90% for other")
for c, pct in [("capability", 87), ("risk", 97), ("market", 75), ("governance", 100), ("other", 90)]:
    ck(f"README survival {c}", abs(100 * sv[c][c] - pct) < 0.75)
inreadme("74", "Seventy-four candidates; all 74 read blind")
inreadme("25", "Twenty-five of the 623 extracted sentences — exactly 4.0%")
inreadme("agreement", "93.1% observed agreement on the five-class task over 598 sentences")
inreadme("alpha", "0.879 for nominal data")
inreadme("disagreements", "capability against other (15), market against other (7), market "
                          "against risk (7)")
inreadme("19 of 20", "19 times")
inreadme("checks", "**247 checks with zero failures**")
inreadme("pred2", "| 2 | fewer than 10% of capability claims quantified | held, 2.7% |")
inreadme("pred3", "| 3 | fewer than 2% checkable | held, 1.3% |")
inreadme("pred4", "+6.2pp, bootstrap −3.1 to +14.4")
ck("README check count matches", True)  # the count below is asserted at the end

# ---------------------------------------------------------------- figures exist
for f in ["fig1_composition.png", "fig2_funnel.png", "fig3_sector.png", "fig4_calibration.png"]:
    ck(f"figure {f} exists", os.path.exists(os.path.join(BASE, "figures", f)))
    ck(f"figure {f} referenced", f in PAPER_RAW)

# the README advertises the number of checks; keep it honest
if f"**{checks} checks with zero failures**" not in README and not fails:
    fails.append(f"README advertises the wrong check count; it is now {checks}")

print(f"{checks} checks run, {len(fails)} failed")
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)
