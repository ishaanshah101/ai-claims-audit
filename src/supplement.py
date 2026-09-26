"""Filing-level summaries and an audit of how well the blinding actually held."""
import json, os, re, collections
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
items = {i["rid"]: i for i in json.load(open(os.path.join(BASE, "data/rating/items.json")))}
cal = json.load(open(os.path.join(BASE, "results/calibration.json")))
split = json.load(open(os.path.join(BASE, "results/partA_split.json")))
agree = {int(k): v for k, v in split["agreed"].items()}
fp = set(cal["term_false_positive_rids"])
corpus = [r for r in sorted(items) if r not in fp]

byf = collections.defaultdict(list)
for r in corpus:
    byf[items[r]["adsh"]].append(r)
n_f = len(byf)
cap_f = [f for f, ids in byf.items() if any(agree.get(r) == "capability" for r in ids)]
q_f = [items[r]["adsh"] for r in cal["c2_true_quantified_rids"]]
sents = sorted(len(v) for v in byf.values())
res = {
    "n_filings_in_corpus": n_f,
    "n_filings_with_a_capability_claim": len(cap_f),
    "n_filings_with_a_quantified_claim": len(set(q_f)),
    "n_filings_with_a_checkable_claim": len({items[48]["adsh"]}),
    "sentences_per_filing": {"min": sents[0], "median": sents[len(sents)//2],
                             "max": sents[-1], "mean": sum(sents)/len(sents)},
    "n_filings_sampled": 60,
    "n_filings_yielding_no_ai_sentence": 60 - len({i["adsh"] for i in items.values()}),
    "n_filings_dropped_entirely_by_term_correction":
        len({i["adsh"] for i in items.values()} - set(byf)),
}

# blinding audit: does the presented text still name the registrant?
STOP = {"inc", "corp", "corporation", "company", "co", "ltd", "llc", "holdings",
        "holding", "group", "plc", "the", "and", "of", "technologies", "systems",
        "international", "trust", "new", "class", "common", "stock"}
leak = []
for r in corpus:
    name = items[r]["name"]
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", name) if len(t) > 3 and t.lower() not in STOP]
    hit = [t for t in toks if re.search(r"\b" + re.escape(t) + r"\b", items[r]["text"], re.I)]
    if hit:
        leak.append({"rid": r, "name": name, "tokens_present": hit})
# a generic token like "Health" or "Technology" does not identify a registrant,
# so the broad screen is split into a narrow one that keeps only tokens which are
# distinctive to the filer
GENERIC = {"health", "technology", "solutions", "hotels", "financial", "business",
           "medical", "private", "protection", "structure", "services", "capital",
           "energy", "american", "national", "general", "first", "global"}
narrow = [x for x in leak
          if any(t.lower() not in GENERIC for t in x["tokens_present"])]
res["blinding_leak_narrow_n"] = len(narrow)
res["blinding_leak_narrow_rate"] = len(narrow) / len(corpus)
res["blinding_leak_narrow"] = [{"rid": x["rid"], "name": x["name"].split("  ")[0],
                                "tokens": x["tokens_present"]} for x in narrow]
res["blinding_leak_n"] = len(leak)
res["blinding_leak_rate"] = len(leak) / len(corpus)
res["blinding_leak_examples"] = leak[:8]
res["blinding_leak_rids"] = [x["rid"] for x in leak]
# did leakage change the verdict? compare agreement rate on leaked vs clean
lk = {x["rid"] for x in leak}
res["agreement_on_leaked"] = (sum(1 for r in corpus if r in lk and r in agree) /
                              max(len(lk & set(corpus)), 1))
res["agreement_on_clean"] = (sum(1 for r in corpus if r not in lk and r in agree) /
                             max(len([r for r in corpus if r not in lk]), 1))
json.dump(res, open(os.path.join(BASE, "results/supplement.json"), "w"), indent=2)
for k, v in res.items():
    if k not in ("blinding_leak_examples", "blinding_leak_rids", "blinding_leak_narrow"):
        print(f"{k}: {v}")
print("\nnarrow leaks, one line each:")
for x in res["blinding_leak_narrow"]:
    print("  rid", x["rid"], x["name"], "->", x["tokens"])
