"""Validate the six rater output files against the preregistered schema.

Part B is recorded only when Part A is `capability` (PREREGISTRATION.md §4),
so non-capability rows must carry null on all five dimensions.
Exits non-zero if anything is wrong.
"""
import json, collections, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(BASE, "data", "rating")
CLASSES = {"capability", "risk", "market", "governance", "other"}
BOOLS = ["quantified", "metric_named", "evaluation_described",
         "baseline_given", "uncertainty_given"]

items = json.load(open(os.path.join(R, "items.json")))
problems, rows = [], []

for r in range(6):
    exp = {it["rid"] for it in json.load(open(os.path.join(R, f"rater_{r}_items.json")))}
    seen = set()
    n = 0
    for ln, line in enumerate(open(os.path.join(R, f"rater_{r}.jsonl")), 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            d = json.loads(line)
        except Exception as e:
            problems.append(f"rater {r} line {ln}: bad JSON {e}")
            continue
        if d.get("rater") != r:
            problems.append(f"rater {r} line {ln}: rater field is {d.get('rater')}")
        rid = d.get("rid")
        if rid not in exp:
            problems.append(f"rater {r} line {ln}: rid {rid} was not assigned to this rater")
        if rid in seen:
            problems.append(f"rater {r}: duplicate rid {rid}")
        seen.add(rid)
        cls = d.get("class")
        if cls not in CLASSES:
            problems.append(f"rater {r} rid {rid}: bad class {cls!r}")
        for b in BOOLS:
            v = d.get(b)
            if cls == "capability":
                if not isinstance(v, bool):
                    problems.append(f"rater {r} rid {rid}: capability but {b}={v!r}")
            else:
                if v is not None:
                    problems.append(f"rater {r} rid {rid}: class {cls} but {b}={v!r}")
        rows.append(d)
    miss = exp - seen
    if miss:
        problems.append(f"rater {r}: missing {len(miss)} rids, e.g. {sorted(miss)[:10]}")
    print(f"rater {r}: {n} rows, {len(exp)} assigned, {len(miss)} missing")

cov = collections.Counter(d["rid"] for d in rows)
bad = {rid: c for rid, c in cov.items() if c != 2}
print(f"\nrows {len(rows)}  distinct rids {len(cov)}  corpus items {len(items)}")
print(f"rids not rated exactly twice: {len(bad)}")
if bad:
    problems.append(f"coverage: {list(bad.items())[:10]}")
if len(cov) != len(items):
    problems.append(f"coverage: {len(cov)} rids rated but {len(items)} in corpus")

print("\nclass counts by rater")
for r in range(6):
    c = collections.Counter(d["class"] for d in rows if d["rater"] == r)
    print(f"  r{r}: " + "  ".join(f"{k}={c[k]}" for k in
          ["capability", "risk", "market", "governance", "other"]))

caps = [d for d in rows if d["class"] == "capability"]
print(f"\ncapability judgements: {len(caps)}")
for b in BOOLS:
    print(f"  {b}: {sum(1 for d in caps if d[b])} true")

json.dump(rows, open(os.path.join(R, "all_ratings.json"), "w"), indent=0)
print(f"\nPROBLEMS: {len(problems)}")
for p in problems[:40]:
    print(" -", p)
sys.exit(1 if problems else 0)
