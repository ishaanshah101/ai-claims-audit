"""Audit the extractor's AI term list for false positives.

The term list was fixed before any filing was downloaded, which is the right
order but means its failure modes can only be measured after the fact. This
records which pattern matched each sentence and isolates the sentences whose
only match is a short initialism, which is where a false positive is possible:
`ml` also spells millilitre, and `ai` occurs inside entity names and as a
stray token in extracted text.
"""
import json, os, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATS = {
    "artificial intelligence": r"artificial intelligence",
    "machine learning": r"machine learning",
    "generative ai": r"generative ai",
    "large language model": r"large language model",
    "deep learning": r"deep learning",
    "neural network": r"neural network",
    "ai": r"\bai\b",
    "ai-": r"\bai-",
    "genai": r"\bgenai\b",
    "ml": r"\bml\b",
    "foundation model": r"foundation model",
}
C = {k: re.compile(v, re.I) for k, v in PATS.items()}
items = json.load(open(os.path.join(BASE, "data", "rating", "items.json")))
short = {"ai", "ai-", "ml"}
rows = []
for it in items:
    hit = [k for k, r in C.items() if r.search(it["text"])]
    rows.append({"rid": it["rid"], "patterns": hit,
                 "only_short": bool(hit) and set(hit) <= short,
                 "only_ml": hit == ["ml"]})
cnt = collections.Counter(p for r in rows for p in r["patterns"])
print("pattern hit counts (a sentence can hit several)")
for k in PATS:
    print(f"  {k:26s} {cnt[k]:4d}")
onlyshort = [r for r in rows if r["only_short"]]
onlyml = [r for r in rows if r["only_ml"]]
print(f"\nsentences whose only match is a short initialism: {len(onlyshort)}")
print(f"sentences whose only match is 'ml': {len(onlyml)}")
json.dump(rows, open(os.path.join(BASE, "data", "calibration", "term_hits.json"), "w"), indent=0)
by_rid = {it["rid"]: it["text"] for it in items}
print("\n--- only-ml sentences ---")
for r in onlyml:
    print(f"[{r['rid']}] {by_rid[r['rid']][:260]}\n")

# ---- second screen: sentences whose only match is `ai`/`ai-`, where the
# token may be an entity name or a stray artefact of text extraction rather
# than a reference to artificial intelligence.
SUFFIX = re.compile(r"\b(Inc|LLC|L\.L\.C|Corp|Corporation|Ltd|plc|N\.A|Holdings?)\b")
onlyai = [r for r in rows if r["only_short"] and "ml" not in r["patterns"]]
cands = []
for r in onlyai:
    t = by_rid[r["rid"]]
    wins = []
    for m in re.finditer(r"\bai\b|\bai-", t, re.I):
        a, b = max(0, m.start() - 40), min(len(t), m.end() + 40)
        wins.append((m.group(0), t[a:b]))
    # flag when every occurrence sits next to a corporate suffix, or is a
    # lowercase standalone token, i.e. never used as the term "AI"
    def suspicious(g, w):
        if g.islower() and g == "ai":
            return True
        return bool(SUFFIX.search(w))
    if wins and all(suspicious(g, w) for g, w in wins):
        cands.append((r["rid"], wins))
print(f"\nonly-'ai' sentences: {len(onlyai)}")
print(f"of those, flagged as possible entity-name or stray-token matches: {len(cands)}")
for rid, wins in cands:
    print(f"\n[{rid}] {by_rid[rid][:240]}")
    for g, w in wins[:3]:
        print(f"      match {g!r} in ...{w.strip()}...")
