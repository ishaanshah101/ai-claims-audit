"""Inter-pass agreement on Part A, and the disputed set.

Two passes rated every sentence. This computes observed agreement,
Krippendorff's alpha for nominal data (which is defined for the
two-coders-per-unit design used here), the per-class confusion matrix,
and writes the agreed / disputed split.
"""
import json, collections, itertools, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(BASE, "data", "rating")
OUT = os.path.join(BASE, "results")
os.makedirs(OUT, exist_ok=True)
CLASSES = ["capability", "risk", "market", "governance", "other"]

rows = json.load(open(os.path.join(R, "all_ratings.json")))
by_rid = collections.defaultdict(list)
for d in rows:
    by_rid[d["rid"]].append(d)
assert all(len(v) == 2 for v in by_rid.values())

rids = sorted(by_rid)
pairs = {rid: tuple(sorted(d["class"] for d in by_rid[rid])) for rid in rids}

agree = [rid for rid in rids if pairs[rid][0] == pairs[rid][1]]
disputed = [rid for rid in rids if pairs[rid][0] != pairs[rid][1]]
p_o = len(agree) / len(rids)

# Krippendorff's alpha, nominal, two coders per unit, no missing values.
# With a constant 2 coders per unit the general formula reduces to:
#   D_o = (1/(n_units)) * sum_units [ delta-disagreements / (m-1) ]  with m=2
#   D_e = expected disagreement from the pooled marginal of all judgements
n_units = len(rids)
D_o = sum(0.0 if pairs[r][0] == pairs[r][1] else 1.0 for r in rids) / n_units
marg = collections.Counter(d["class"] for d in rows)
N = sum(marg.values())
D_e = 1.0 - sum(c * (c - 1) for c in marg.values()) / (N * (N - 1))
alpha = 1.0 - D_o / D_e

# Per-class one-vs-rest agreement, and Cohen's kappa treating the two
# judgements per unit as an unordered pair is not well defined, so we
# report per-class positive specific agreement (Cicchetti-Feinstein):
#   PA_k = 2 * (# units where both say k) / (# judgements of k)
spec = {}
for k in CLASSES:
    both = sum(1 for r in rids if pairs[r] == (k, k))
    spec[k] = (2 * both / marg[k]) if marg[k] else float("nan")

confusion = collections.Counter(pairs.values())

# where the disagreements land
dis_pairs = collections.Counter(p for p in pairs.values() if p[0] != p[1])

report = {
    "n_sentences": n_units,
    "n_judgements": N,
    "observed_agreement": p_o,
    "n_agreed": len(agree),
    "n_disputed": len(disputed),
    "krippendorff_alpha_nominal": alpha,
    "expected_disagreement": D_e,
    "marginal_judgements": dict(marg),
    "positive_specific_agreement": spec,
    "disagreement_pairs": {f"{a}|{b}": c for (a, b), c in dis_pairs.most_common()},
}
json.dump(report, open(os.path.join(OUT, "agreement.json"), "w"), indent=2)
json.dump({"agreed": {str(r): pairs[r][0] for r in agree},
           "disputed": {str(r): list(pairs[r]) for r in disputed}},
          open(os.path.join(OUT, "partA_split.json"), "w"), indent=1)

print(f"sentences {n_units}   judgements {N}")
print(f"observed agreement  {p_o:.4f}  ({len(agree)} agreed / {len(disputed)} disputed)")
print(f"Krippendorff alpha (nominal)  {alpha:.4f}   [D_o={D_o:.4f} D_e={D_e:.4f}]")
print("\npositive specific agreement by class")
for k in CLASSES:
    print(f"  {k:11s} {spec[k]:.3f}   ({marg[k]} judgements)")
print("\nagreed class counts")
ac = collections.Counter(pairs[r][0] for r in agree)
for k in CLASSES:
    print(f"  {k:11s} {ac[k]:4d}")
print("\ntop disagreement pairs")
for (a, b), c in dis_pairs.most_common(10):
    print(f"  {a} vs {b}: {c}")

# ---- Part B agreement, on the sentences both passes called capability ----
BOOLS = ["quantified", "metric_named", "evaluation_described",
         "baseline_given", "uncertainty_given"]
capr = [r for r in rids if pairs[r] == ("capability", "capability")]
partb = {}
for b in BOOLS:
    both_t = both_f = disag = 0
    for r in capr:
        vs = [d[b] for d in by_rid[r]]
        if vs[0] and vs[1]: both_t += 1
        elif (not vs[0]) and (not vs[1]): both_f += 1
        else: disag += 1
    n = len(capr)
    po = (both_t + both_f) / n
    # positive specific agreement
    ntrue = sum(1 for r in capr for d in by_rid[r] if d[b])
    psa = (2 * both_t / ntrue) if ntrue else float("nan")
    partb[b] = {"n": n, "both_true": both_t, "both_false": both_f,
                "disagreed": disag, "observed_agreement": po,
                "judgements_true": ntrue, "positive_specific_agreement": psa}
report["part_b_agreement"] = partb
report["n_both_capability"] = len(capr)
json.dump(report, open(os.path.join(OUT, "agreement.json"), "w"), indent=2)
print(f"\nPart B, on the {len(capr)} sentences both passes called capability")
for b in BOOLS:
    d = partb[b]
    psa = d["positive_specific_agreement"]
    psa_s = "n/a" if psa != psa else f"{psa:.3f}"
    print(f"  {b:22s} agree {d['observed_agreement']:.3f}  both-true {d['both_true']:2d}  "
          f"disagreed {d['disagreed']:2d}  PSA {psa_s}")
