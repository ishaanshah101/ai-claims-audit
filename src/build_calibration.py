"""Build the blinded calibration materials.

Three components.

C1  composition calibration.  A seeded sample stratified over the five agreed
    Part A classes plus the disputed set, presented as text only in a shuffled
    order, with a small number of sentences repeated under two different display
    ids as self-consistency controls.  The reviewer does not see the verdicts
    being checked.

C2  quantification recall audit.  A numeric performance figure is a necessary
    condition for `quantified` = true.  Every sentence in the corpus is screened
    mechanically for a numeral of a kind that could express a performance figure.
    Sentences with no such numeral cannot be quantified, whatever any pass said,
    so the screen yields a hard upper bound on `quantified` that does not depend
    on rater judgement.  Every candidate is then reviewed blind.

C3  the duplicate controls inside C1, plus the fact that C2 includes sentences
    every pass called non-capability, so the reviewer cannot infer the prior
    verdict from the fact that a sentence was selected.

Writes a blind file and a key file.  The key is not read until the reviewer's
judgements are recorded.
"""
import json, os, random, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(BASE, "data", "rating")
OUT = os.path.join(BASE, "data", "calibration")
os.makedirs(OUT, exist_ok=True)
SEED = 20260926
C1_PER_CLASS = {"capability": 30, "risk": 30, "other": 20, "market": 12, "governance": 5}
C1_DISPUTED = 20
N_DUP_CONTROLS = 8

items = {it["rid"]: it for it in json.load(open(os.path.join(R, "items.json")))}
rows = json.load(open(os.path.join(R, "all_ratings.json")))
split = json.load(open(os.path.join(BASE, "results", "partA_split.json")))
agreed = {int(k): v for k, v in split["agreed"].items()}
disputed = {int(k): v for k, v in split["disputed"].items()}

rng = random.Random(SEED)

# ---------------- C1 ----------------
by_class = collections.defaultdict(list)
for rid, c in agreed.items():
    by_class[c].append(rid)
c1 = []
for c, n in C1_PER_CLASS.items():
    pool = sorted(by_class[c])
    take = pool if len(pool) <= n else rng.sample(pool, n)
    c1 += take
dpool = sorted(disputed)
c1 += dpool if len(dpool) <= C1_DISPUTED else rng.sample(dpool, C1_DISPUTED)
c1 = sorted(set(c1))
dups = rng.sample(c1, N_DUP_CONTROLS)

display = [(rid, 0) for rid in c1] + [(rid, 1) for rid in dups]
rng.shuffle(display)
c1_blind, c1_key = [], []
for i, (rid, rep) in enumerate(display, 1):
    did = f"A{i:03d}"
    c1_blind.append({"did": did, "text": items[rid]["text"]})
    c1_key.append({"did": did, "rid": rid, "rep": rep,
                   "prior": agreed.get(rid) or disputed.get(rid)})

# ---------------- C2 ----------------
# numerals that could carry a performance figure: percentages, decimals,
# integers of two digits or more, spelled-out multiples, currency, and
# magnitude words attached to a digit.
NUM = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:percent|percentage points?|bps|basis points?)"
    r"|\b\d+(?:\.\d+)?\s*(?:x|times|fold)\b"
    r"|[$€£]\s?\d|\b\d+(?:\.\d+)?\s*(?:million|billion|thousand|hours?|minutes?|seconds?|days?|weeks?|months?)\b"
    r"|\b\d{2,}(?:,\d{3})*(?:\.\d+)?\b)", re.I)
c2 = []
for rid, it in sorted(items.items()):
    m = NUM.findall(it["text"])
    if m:
        c2.append({"rid": rid, "hits": sorted(set(x.strip() for x in m))[:6]})
c2_rids = [d["rid"] for d in c2]
rng.shuffle(c2)
c2_blind = [{"did": f"B{i:03d}", "text": items[d['rid']]['text'], "numerals": d["hits"]}
            for i, d in enumerate(c2, 1)]
c2_key = [{"did": f"B{i:03d}", "rid": d["rid"]} for i, d in enumerate(c2, 1)]

json.dump(c1_blind, open(os.path.join(OUT, "c1_blind.json"), "w"), indent=1)
json.dump(c1_key, open(os.path.join(OUT, "c1_key.json"), "w"), indent=1)
json.dump(c2_blind, open(os.path.join(OUT, "c2_blind.json"), "w"), indent=1)
json.dump(c2_key, open(os.path.join(OUT, "c2_key.json"), "w"), indent=1)
json.dump({"seed": SEED, "c1_units": len(c1), "c1_displays": len(c1_blind),
           "c1_duplicate_controls": N_DUP_CONTROLS,
           "c1_per_class_requested": C1_PER_CLASS, "c1_disputed_requested": C1_DISPUTED,
           "c2_candidates": len(c2), "corpus": len(items),
           "c2_screen_regex": NUM.pattern},
          open(os.path.join(OUT, "manifest.json"), "w"), indent=2)

print(f"C1: {len(c1)} distinct sentences, {len(c1_blind)} displays "
      f"({N_DUP_CONTROLS} duplicate controls)")
for c in ["capability", "risk", "market", "governance", "other"]:
    print(f"   agreed {c:11s} pool {len(by_class[c]):4d} -> sampled "
          f"{sum(1 for r in c1 if agreed.get(r) == c)}")
print(f"   disputed pool {len(dpool)} -> sampled {sum(1 for r in c1 if r in disputed)}")
print(f"C2: {len(c2)} of {len(items)} sentences carry a candidate numeral "
      f"({100*len(c2)/len(items):.1f}%)")
