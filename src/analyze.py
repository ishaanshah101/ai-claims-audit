"""Main analysis. Produces results/analysis.json, from which the paper is written.

Order of operations, and why:

1. The term-list false positives found by the whole-corpus screen are removed
   first. They are not AI language at all, so leaving them in would inflate
   every denominator. The screen enumerates them exhaustively, so this is a
   deterministic correction with no uncertainty attached.
2. Composition is reported on the sentences both passes agreed on, as
   preregistered, with the disputed set reported as a bound rather than resolved.
3. Composition is then reported again corrected by the calibration transfer
   matrix, which is the number the paper leads with.
4. Verifiability is reported on the corrected capability denominator. The
   numerators for `quantified` and `checkable` come from the whole-corpus numeral
   screen and its blinded review, so they are exact counts, not estimates.
"""
import json, os, collections
import numpy as np
from stats import (wilson, cluster_bootstrap_rate, cluster_bootstrap_diff,
                   transfer_matrix, calibrate_counts)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "results")
CLASSES = ["capability", "risk", "market", "governance", "other"]
SECTORS = ["technology", "healthcare", "finance_realestate", "other"]
NBOOT, SEED = 10_000, 20260926

items = {i["rid"]: i for i in json.load(open(os.path.join(BASE, "data/rating/items.json")))}
ratings = json.load(open(os.path.join(BASE, "data/rating/all_ratings.json")))
split = json.load(open(os.path.join(OUT, "partA_split.json")))
cal = json.load(open(os.path.join(OUT, "calibration.json")))
agree = {int(k): v for k, v in split["agreed"].items()}
disp = {int(k): v for k, v in split["disputed"].items()}
by_rid = collections.defaultdict(list)
for d in ratings:
    by_rid[d["rid"]].append(d)

# ---- 1. term-list correction -------------------------------------------------
fp = set(cal["term_false_positive_rids"])
corpus = [r for r in sorted(items) if r not in fp]
N = len(corpus)
res = {"n_extracted": len(items), "n_term_false_positive": len(fp), "n_corpus": N,
       "term_false_positive_rate": len(fp) / len(items)}

agree_c = {r: c for r, c in agree.items() if r not in fp}
disp_c = {r: v for r, v in disp.items() if r not in fp}
res["n_agreed"] = len(agree_c)
res["n_disputed"] = len(disp_c)
res["agreement_on_corpus"] = len(agree_c) / N

# agreement recomputed on the corrected corpus, since results/agreement.json is
# computed before the term correction and its denominator is the extracted set
_pairs = {r: tuple(sorted(d["class"] for d in by_rid[r])) for r in corpus}
_Do = sum(1 for p in _pairs.values() if p[0] != p[1]) / N
_marg = collections.Counter(d["class"] for r in corpus for d in by_rid[r])
_NJ = sum(_marg.values())
_De = 1 - sum(c * (c - 1) for c in _marg.values()) / (_NJ * (_NJ - 1))
res["agreement_on_corrected_corpus"] = {
    "n": N, "n_judgements": _NJ, "observed_agreement": 1 - _Do,
    "expected_disagreement": _De, "krippendorff_alpha_nominal": 1 - _Do / _De}

# ---- per-filing clusters -----------------------------------------------------
filings = sorted({items[r]["adsh"] for r in corpus})
sec_of = {items[r]["adsh"]: items[r]["sector"] for r in corpus}
def clusters(rids_true, rids_den):
    t, d = set(rids_true), set(rids_den)
    out = []
    for f in filings:
        ids = [r for r in corpus if items[r]["adsh"] == f]
        out.append((sum(1 for r in ids if r in t), sum(1 for r in ids if r in d)))
    return out

# ---- 2. composition, agreed only --------------------------------------------
ac = collections.Counter(agree_c.values())
comp = {}
for c in CLASSES:
    p, lo, hi = wilson(ac[c], len(agree_c))
    br = cluster_bootstrap_rate(clusters({r for r in agree_c if agree_c[r] == c},
                                         set(agree_c)), NBOOT, SEED)
    comp[c] = {"n": ac[c], "denominator": len(agree_c), "rate": p,
               "wilson_lo": lo, "wilson_hi": hi,
               "boot_rate": br[0], "boot_lo": br[1], "boot_hi": br[2]}
res["composition_agreed"] = comp

# bound from the disputed set: all disputed counted into the class, then none
bounds = {}
for c in CLASSES:
    could = sum(1 for r, v in disp_c.items() if c in v)
    bounds[c] = {"lower_rate": ac[c] / N, "upper_rate": (ac[c] + could) / N,
                 "n_disputed_could_be": could}
res["composition_bounds_on_full_corpus"] = bounds

# ---- 3. calibrated composition ----------------------------------------------
key1 = {d["did"]: d for d in json.load(open(os.path.join(BASE, "data/calibration/c1_key.json")))}
rev1 = {json.loads(l)["did"]: json.loads(l)["class"]
        for l in open(os.path.join(BASE, "data/calibration/c1_reviewer.jsonl"))}
prior_by_rid, rev_by_rid = {}, {}
for did, k in key1.items():
    prior_by_rid[k["rid"]] = k["prior"]
    rev_by_rid.setdefault(k["rid"], set()).add(rev1[did])
rev_by_rid = {r: list(v)[0] for r, v in rev_by_rid.items() if len(v) == 1}
cal_units = [(prior_by_rid[r], rev_by_rid[r]) for r in rev_by_rid
             if isinstance(prior_by_rid[r], str)]
M = transfer_matrix([a for a, _ in cal_units], [b for _, b in cal_units], CLASSES)
res["transfer_matrix"] = {CLASSES[i]: {CLASSES[j]: float(M[i, j]) for j in range(5)}
                          for i in range(5)}
res["n_calibration_units_agreed"] = len(cal_units)

# disputed sentences: distributed by how the blinded reviewer resolved the
# 20 that were reviewed, applied to all disputed sentences in the corpus
disp_units = [rev_by_rid[r] for r in rev_by_rid if isinstance(prior_by_rid[r], list)]
dc = collections.Counter(disp_units)
disp_frac = np.array([dc[c] / len(disp_units) for c in CLASSES])
res["n_calibration_units_disputed"] = len(disp_units)
res["disputed_resolution_fractions"] = {c: float(x) for c, x in zip(CLASSES, disp_frac)}

agreed_vec = np.array([ac[c] for c in CLASSES], dtype=float)
corrected = calibrate_counts(agreed_vec, M) + len(disp_c) * disp_frac
assert abs(corrected.sum() - N) < 1e-6, (corrected.sum(), N)
res["composition_calibrated"] = {
    c: {"count": float(corrected[i]), "rate": float(corrected[i] / N)}
    for i, c in enumerate(CLASSES)}

# bootstrap the calibrated rate: resample filings for the corpus and resample
# calibration units within each prior class for the matrix
rng = np.random.default_rng(SEED)
fil_ids = {f: [r for r in corpus if items[r]["adsh"] == f] for f in filings}
by_prior = collections.defaultdict(list)
for a, b in cal_units:
    by_prior[a].append(b)
disp_pool = list(disp_units)
boot = np.zeros((NBOOT, 5))
for t in range(NBOOT):
    pick = rng.integers(0, len(filings), len(filings))
    ids = [r for i in pick for r in fil_ids[filings[i]]]
    av = np.zeros(5); nd = 0
    for r in ids:
        if r in agree_c:
            av[CLASSES.index(agree_c[r])] += 1
        else:
            nd += 1
    Mb = np.zeros((5, 5))
    for i, c in enumerate(CLASSES):
        pool = by_prior.get(c)
        if not pool:
            Mb[i, i] = 1.0
            continue
        s = rng.integers(0, len(pool), len(pool))
        for j in s:
            Mb[i, CLASSES.index(pool[j])] += 1
        Mb[i] /= Mb[i].sum()
    s = rng.integers(0, len(disp_pool), len(disp_pool))
    df = np.zeros(5)
    for j in s:
        df[CLASSES.index(disp_pool[j])] += 1
    df /= df.sum()
    tot = av.sum() + nd
    boot[t] = (av @ Mb + nd * df) / max(tot, 1)
lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
for i, c in enumerate(CLASSES):
    res["composition_calibrated"][c].update({"boot_lo": float(lo[i]),
                                             "boot_hi": float(hi[i])})

# ---- 4. verifiability -------------------------------------------------------
cap_rids = sorted(r for r, c in agree_c.items() if c == "capability")
cap_cal = float(corrected[CLASSES.index("capability")])
q_rids = [r for r in cal["c2_true_quantified_rids"] if r not in fp]
checkable_rids = [48]   # quantified AND metric_named AND evaluation_described
res["capability_agreed_n"] = len(cap_rids)
res["capability_calibrated_n"] = cap_cal

# metric_named has no mechanical screen, so it stays a pass-based estimate on
# the agreed-capability set, where both passes scored it true
mn = [r for r in cap_rids if all(d["metric_named"] for d in by_rid[r])]
mn_either = [r for r in cap_rids if any(d["metric_named"] for d in by_rid[r])]
res["verifiability"] = {
    "denominator_agreed": len(cap_rids),
    "denominator_calibrated": cap_cal,
    "quantified": {"n": len(q_rids), "rids": q_rids, "source": "whole-corpus numeral screen + blinded review",
                   "rate_agreed": len(q_rids) / len(cap_rids),
                   "wilson": wilson(len(q_rids), len(cap_rids))[1:],
                   "rate_calibrated": len(q_rids) / cap_cal},
    "metric_named": {"n_both": len(mn), "n_either": len(mn_either),
                     "rids_both": mn, "source": "both passes agreed",
                     "rate_agreed": len(mn) / len(cap_rids),
                     "wilson": wilson(len(mn), len(cap_rids))[1:]},
    "evaluation_described": {"n": 1, "rids": [48], "source": "blinded review of every numeral candidate",
                             "rate_agreed": 1 / len(cap_rids)},
    "baseline_given": {"n": 0, "rate_agreed": 0.0,
                       "wilson_hi": wilson(0, len(cap_rids))[2]},
    "uncertainty_given": {"n": 0, "rate_agreed": 0.0,
                          "wilson_hi": wilson(0, len(cap_rids))[2]},
    "checkable": {"n": len(checkable_rids), "rids": checkable_rids,
                  "rate_agreed": len(checkable_rids) / len(cap_rids),
                  "wilson": wilson(len(checkable_rids), len(cap_rids))[1:],
                  "rate_calibrated": len(checkable_rids) / cap_cal,
                  "rate_of_corpus": len(checkable_rids) / N,
                  "wilson_of_corpus": wilson(len(checkable_rids), N)[1:]},
}

# verifiability score distribution on the agreed-capability set (pass-based,
# scoring a dimension true only when both passes said true)
BOOLS = ["quantified", "metric_named", "evaluation_described",
         "baseline_given", "uncertainty_given"]
vs = collections.Counter(
    sum(1 for b in BOOLS if all(d[b] for d in by_rid[r])) for r in cap_rids)
res["verifiability_score_distribution"] = {str(k): vs[k] for k in range(6)}

# ---- 5. sector --------------------------------------------------------------
sec = {}
for s in SECTORS:
    fs = [f for f in filings if sec_of[f] == s]
    cl = []
    for f in fs:
        ids = [r for r in corpus if items[r]["adsh"] == f]
        cl.append((sum(1 for r in ids if agree_c.get(r) == "capability"), len(ids)))
    n_cap = sum(a for a, _ in cl); n_tot = sum(b for _, b in cl)
    br = cluster_bootstrap_rate(cl, NBOOT, SEED)
    sec[s] = {"n_filings": len(fs), "n_sentences": n_tot, "n_capability": n_cap,
              "rate": n_cap / n_tot, "boot_lo": br[1], "boot_hi": br[2],
              "wilson": wilson(n_cap, n_tot)[1:]}
res["sector_capability"] = sec
def sec_cl(s):
    out = []
    for f in [f for f in filings if sec_of[f] == s]:
        ids = [r for r in corpus if items[r]["adsh"] == f]
        out.append((sum(1 for r in ids if agree_c.get(r) == "capability"), len(ids)))
    return out
tech = sec_cl("technology")
rest = [c for s in SECTORS if s != "technology" for c in sec_cl(s)]
d, dlo, dhi = cluster_bootstrap_diff(tech, rest, NBOOT, SEED)
res["sector_tech_vs_rest"] = {"difference": d, "boot_lo": dlo, "boot_hi": dhi}

# ---- 6. preregistered predictions -------------------------------------------
risk_r = res["composition_calibrated"]["risk"]["rate"]
cap_r = res["composition_calibrated"]["capability"]["rate"]
res["predictions"] = {
    "1_risk_exceeds_capability": {"statement": "Risk-factor mentions will outnumber capability claims.",
        "risk_rate": risk_r, "capability_rate": cap_r, "held": risk_r > cap_r},
    "2_under_10pct_quantified": {"statement": "Fewer than 10 percent of capability claims will be quantified.",
        "value": res["verifiability"]["quantified"]["rate_agreed"], "held": res["verifiability"]["quantified"]["rate_agreed"] < 0.10},
    "3_under_2pct_checkable": {"statement": "Fewer than 2 percent of capability claims will be checkable.",
        "value": res["verifiability"]["checkable"]["rate_agreed"], "held": res["verifiability"]["checkable"]["rate_agreed"] < 0.02},
    "4_tech_highest_capability": {"statement": "Technology registrants will make capability claims at a higher rate than the other three strata.",
        "tech_rate": sec["technology"]["rate"],
        "others": {s: sec[s]["rate"] for s in SECTORS if s != "technology"},
        "difference_vs_rest": d, "boot_lo": dlo, "boot_hi": dhi,
        "held": all(sec["technology"]["rate"] > sec[s]["rate"] for s in SECTORS if s != "technology")},
}

json.dump(res, open(os.path.join(OUT, "analysis.json"), "w"), indent=2, default=float)

# ---- print ------------------------------------------------------------------
print(f"extracted {res['n_extracted']}  term false positives {len(fp)}  corpus {N}")
print(f"agreed {len(agree_c)} ({100*len(agree_c)/N:.1f}%)  disputed {len(disp_c)}")
print("\ncomposition, agreed only (n / rate / Wilson / filing bootstrap)")
for c in CLASSES:
    v = comp[c]
    print(f"  {c:11s} {v['n']:4d}  {100*v['rate']:5.1f}%  "
          f"[{100*v['wilson_lo']:4.1f},{100*v['wilson_hi']:5.1f}]  "
          f"boot [{100*v['boot_lo']:4.1f},{100*v['boot_hi']:5.1f}]")
print("\ncomposition, calibrated (share of all 598 corpus sentences)")
for c in CLASSES:
    v = res["composition_calibrated"][c]
    print(f"  {c:11s} {v['count']:7.1f}  {100*v['rate']:5.1f}%  "
          f"boot [{100*v['boot_lo']:4.1f},{100*v['boot_hi']:5.1f}]")
print(f"\ncapability denominator: agreed {len(cap_rids)}, calibrated {cap_cal:.1f}")
v = res["verifiability"]
print(f"  quantified           {v['quantified']['n']}  "
      f"{100*v['quantified']['rate_agreed']:.2f}% of agreed capability")
print(f"  metric_named         {v['metric_named']['n_both']}  "
      f"{100*v['metric_named']['rate_agreed']:.2f}%")
print(f"  evaluation_described {v['evaluation_described']['n']}")
print(f"  baseline_given       0   (Wilson upper {100*v['baseline_given']['wilson_hi']:.2f}%)")
print(f"  uncertainty_given    0   (Wilson upper {100*v['uncertainty_given']['wilson_hi']:.2f}%)")
print(f"  CHECKABLE            {v['checkable']['n']}  "
      f"{100*v['checkable']['rate_agreed']:.2f}% of capability, "
      f"{100*v['checkable']['rate_of_corpus']:.2f}% of corpus")
print("\nverifiability score distribution:", res["verifiability_score_distribution"])
print("\ncapability rate by sector")
for s in SECTORS:
    x = sec[s]
    print(f"  {s:19s} {x['n_capability']:3d}/{x['n_sentences']:3d} = {100*x['rate']:5.1f}%  "
          f"boot [{100*x['boot_lo']:4.1f},{100*x['boot_hi']:5.1f}]")
print(f"  technology minus rest: {100*d:+.1f} pp  boot [{100*dlo:+.1f},{100*dhi:+.1f}]")
print("\npredictions")
for k, p in res["predictions"].items():
    print(f"  {k}: {'HELD' if p['held'] else 'FAILED'}")
