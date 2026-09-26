"""Unblind the calibration pass and measure the passes' bias.

C1 gives, for each class the two automated passes agreed on, the rate at which
that verdict survives blinded review, and where it goes when it does not. Those
survival rates are the correction applied to every composition rate in the paper.

C2 gives a hard result rather than an estimate: a numeric performance figure is
necessary for `quantified`, the numeral screen enumerates every sentence in the
corpus that could carry one, and the blinded review of that candidate set fixes
the true count of quantified claims exactly.
"""
import json, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL = os.path.join(BASE, "data", "calibration")
OUT = os.path.join(BASE, "results")
CLASSES = ["capability", "risk", "market", "governance", "other"]

key1 = {d["did"]: d for d in json.load(open(os.path.join(CAL, "c1_key.json")))}
rev1 = {json.loads(l)["did"]: json.loads(l)["class"]
        for l in open(os.path.join(CAL, "c1_reviewer.jsonl"))}
key2 = {d["did"]: d["rid"] for d in json.load(open(os.path.join(CAL, "c2_key.json")))}
rev2 = {json.loads(l)["did"]: json.loads(l) for l in open(os.path.join(CAL, "c2_reviewer.jsonl"))}
terms = {d["rid"]: d for d in json.load(open(os.path.join(CAL, "term_hits.json")))}
ratings = json.load(open(os.path.join(BASE, "data", "rating", "all_ratings.json")))
by_rid = collections.defaultdict(list)
for d in ratings:
    by_rid[d["rid"]].append(d)

# ---- self-consistency of the reviewer, from the duplicate controls ----
dups = collections.defaultdict(list)
for did, k in key1.items():
    dups[k["rid"]].append(did)
pairs = {rid: dd for rid, dd in dups.items() if len(dd) == 2}
same = sum(1 for rid, dd in pairs.items() if rev1[dd[0]] == rev1[dd[1]])
print(f"reviewer self-consistency on duplicate controls: {same}/{len(pairs)}")
selfcons = {"n_pairs": len(pairs), "n_consistent": same,
            "disagreed": [{"rid": rid, "calls": [rev1[d] for d in dd]}
                          for rid, dd in pairs.items() if rev1[dd[0]] != rev1[dd[1]]]}

# one judgement per rid: on a duplicate pair that agreed, either; if they
# disagreed the unit is dropped from the survival estimate and reported.
rev_by_rid, dropped = {}, []
for rid, dd in dups.items():
    cs = {rev1[d] for d in dd}
    if len(cs) == 1:
        rev_by_rid[rid] = cs.pop()
    else:
        dropped.append(rid)

# ---- C1 survival rates, agreed units only ----
surv, flow = {}, {}
for c in CLASSES:
    rids = sorted({k["rid"] for k in key1.values()
                   if k["prior"] == c and k["rid"] in rev_by_rid})
    if not rids:
        continue
    kept = sum(1 for r in rids if rev_by_rid[r] == c)
    surv[c] = {"n_reviewed": len(rids), "n_survived": kept,
               "survival_rate": kept / len(rids)}
    f = collections.Counter(rev_by_rid[r] for r in rids if rev_by_rid[r] != c)
    flow[c] = dict(f)

# ---- C1 on the disputed set: where does review land? ----
disp = sorted({k["rid"] for k in key1.values()
               if isinstance(k["prior"], list) and k["rid"] in rev_by_rid})
disp_res = collections.Counter(rev_by_rid[r] for r in disp)
prior_by_rid = {k["rid"]: k["prior"] for k in key1.values()}
disp_in_pair = sum(1 for r in disp if rev_by_rid[r] in prior_by_rid[r])

print("\nC1 survival of the agreed verdict under blinded review")
for c in CLASSES:
    if c in surv:
        s = surv[c]
        print(f"  {c:11s} {s['n_survived']:2d}/{s['n_reviewed']:2d} = {s['survival_rate']:.3f}"
              + (f"   -> {flow[c]}" if flow[c] else ""))
print(f"\nC1 disputed sentences reviewed: {len(disp)}")
print(f"  reviewer landed on: {dict(disp_res)}")
print(f"  landed inside the disputing pair: {disp_in_pair}/{len(disp)}")

# ---- C2: the true quantified count ----
screened = set(key2.values())
true_q = sorted(key2[d] for d, v in rev2.items() if v["quantified"])
pass_q = sorted({d["rid"] for d in ratings if d.get("quantified")})
pass_q_both = sorted(r for r in pass_q
                     if all(x.get("quantified") for x in by_rid[r]))
not_ai = sorted(key2[d] for d, v in rev2.items() if not v["ai_reference"])
print(f"\nC2 numeral screen: {len(screened)} of 623 sentences could carry a figure")
print(f"  reviewer: quantified = true on {len(true_q)} -> rids {true_q}")
print(f"  passes:   quantified = true on rids {pass_q} (both passes: {pass_q_both})")
missed = [r for r in true_q if r not in pass_q]
false_pos = [r for r in pass_q if r not in true_q]
print(f"  claims the passes missed: {missed}")
print(f"  claims the passes over-called: {false_pos}")

# term-list false positives, mechanically enumerated over the whole corpus
only_ml = sorted(r for r, d in terms.items() if d["only_ml"])
fp_name = [35, 246, 313, 381, 545]
fp_all = sorted(set(only_ml) | set(fp_name))
print(f"\nterm-list false positives, whole corpus: {len(fp_all)} of 623 "
      f"({100*len(fp_all)/623:.1f}%)  [{len(only_ml)} on 'ml', {len(fp_name)} on 'ai']")
print(f"  C2 reviewer independently called {len(not_ai)} of its {len(screened)} "
      f"candidates non-AI; all inside that set: {set(not_ai) <= set(fp_all)}")

json.dump({"reviewer_self_consistency": selfcons,
           "dropped_units": dropped,
           "c1_survival": surv, "c1_reclassification_flow": flow,
           "c1_disputed_n": len(disp), "c1_disputed_resolution": dict(disp_res),
           "c1_disputed_inside_pair": disp_in_pair,
           "c2_screened": len(screened),
           "c2_true_quantified_rids": true_q,
           "passes_quantified_rids": pass_q,
           "passes_quantified_both_rids": pass_q_both,
           "quantified_missed_by_passes": missed,
           "quantified_overcalled_by_passes": false_pos,
           "term_false_positive_rids": fp_all,
           "term_false_positive_only_ml": only_ml,
           "term_false_positive_name_or_stray": fp_name,
           "c2_reviewer_non_ai_rids": not_ai},
          open(os.path.join(OUT, "calibration.json"), "w"), indent=2)
