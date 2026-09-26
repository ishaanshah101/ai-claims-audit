"""Download each sampled 10-K and extract every sentence that mentions AI.

Two things matter here. The AI term list is fixed in advance and applied
identically to every filing, and the sentence splitter is deterministic, so the
set of candidate sentences a rerun produces is byte-identical to this one.
"""
from __future__ import annotations
import html, json, os, re, time, urllib.request
from collections import Counter

# The SEC requires a descriptive User-Agent with a contact address on every
# automated request. Replicators should set SEC_USER_AGENT to their own.
UA = os.environ.get("SEC_USER_AGENT",
                    "Ishaan Shah academic research ishaanshah101@gmail.com")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(BASE, "data", "sample_filings.json")
RAW = os.path.join(BASE, "data", "filings")
OUT = os.path.join(BASE, "data", "sentences.json")

# Fixed before any filing was read.
AI_PATTERNS = [
    r"artificial intelligence", r"machine learning", r"generative ai",
    r"large language model", r"deep learning", r"neural network",
    r"\bai\b", r"\bai-", r"\bgenai\b", r"\bml\b", r"foundation model",
]
AI_RE = re.compile("|".join(AI_PATTERNS), re.I)


def url_for(adsh, cik, doc):
    a = adsh.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{a}/{doc}"


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return open(path, "rb").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=90).read()
            open(path, "wb").write(data)
            return data
        except Exception:
            if attempt == 3:
                return None
            time.sleep(2 + 3 * attempt)


def to_text(raw: bytes) -> str:
    s = raw.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style|ix:header)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace(" ", " ").replace("’", "'").replace("“", '"') \
         .replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


ABBREV = r"(?<!\bNo)(?<!\bInc)(?<!\bLtd)(?<!\bCorp)(?<!\bCo)(?<!\bU\.S)(?<!\bU\.K)" \
         r"(?<!\bMr)(?<!\bMs)(?<!\bDr)(?<!\bSt)(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)(?<!\bApprox)"
SPLIT_RE = re.compile(ABBREV + r"(?<=[.!?])\s+(?=[A-Z(\"'])")


def sentences(text):
    return [p.strip() for p in SPLIT_RE.split(text) if p.strip()]


def main():
    os.makedirs(RAW, exist_ok=True)
    sample = json.load(open(SAMPLE))
    out, failures = [], []
    for i, f in enumerate(sample["filings"], 1):
        url = url_for(f["adsh"], f["cik"], f["doc"])
        path = os.path.join(RAW, f"{f['adsh']}_{f['doc']}"[:180])
        raw = fetch(url, path)
        if not raw:
            failures.append((f["adsh"], url))
            continue
        text = to_text(raw)
        sents = sentences(text)
        hits = []
        for j, s in enumerate(sents):
            if not AI_RE.search(s):
                continue
            if not (60 <= len(s) <= 1200):     # drop fragments and run-on tables
                continue
            if sum(c.isdigit() for c in s) > len(s) * 0.25:   # drop numeric tables
                continue
            hits.append({"idx": j, "text": s})
        out.append({**f, "url": url, "chars": len(text),
                    "n_sentences": len(sents), "ai_sentences": hits,
                    "n_ai": len(hits)})
        print(f"  [{i:2d}/60] {f['name'][:42]:42s} {len(text):>9,} chars  {len(hits):>4} AI sentences")
        time.sleep(0.2)

    json.dump({"ai_patterns": AI_PATTERNS, "filings": out, "failures": failures},
              open(OUT, "w"), indent=1)
    tot = sum(f["n_ai"] for f in out)
    print(f"\nfilings fetched     : {len(out)} of 60   failures: {len(failures)}")
    print(f"AI sentences total  : {tot}")
    print(f"median per filing   : {sorted(f['n_ai'] for f in out)[len(out)//2]}")
    print("by sector:", Counter(f["sector"] for f in out))


if __name__ == "__main__":
    main()
