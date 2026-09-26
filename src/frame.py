"""Enumerate the sampling frame: every 10-K filed in 2025 whose full text
mentions artificial intelligence, according to EDGAR full-text search.

EDGAR's full-text search is the registrar's own index of filing documents, so the
frame is exactly reproducible by anyone who reruns this file. The API is public,
documented and free, and SEC's access policy asks for a descriptive User-Agent,
which is set below.
"""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request

# The SEC requires a descriptive User-Agent with a contact address on every
# automated request. Replicators should set SEC_USER_AGENT to their own.
UA = os.environ.get("SEC_USER_AGENT",
                    "Ishaan Shah academic research ishaanshah101@gmail.com")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "frame.json")
QUERY = '"artificial intelligence"'
FORMS = "10-K"
START, END = "2025-01-01", "2025-12-31"
PAGE = 10


def fts(frm=0):
    q = urllib.parse.urlencode({"q": QUERY, "forms": FORMS,
                                "startdt": START, "enddt": END, "from": frm})
    req = urllib.request.Request("https://efts.sec.gov/LATEST/search-index?" + q,
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(5):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2 + 2 * attempt)


def main():
    first = fts(0)
    total = first["hits"]["total"]["value"]
    print(f"frame size reported by EDGAR: {total}")
    rows, seen = [], set()
    frm = 0
    while frm < min(total, 9990):
        d = first if frm == 0 else fts(frm)
        hits = d["hits"]["hits"]
        if not hits:
            break
        for h in hits:
            s = h["_source"]
            key = h["_id"]
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "id": key,
                "adsh": s.get("adsh"),
                "cik": (s.get("ciks") or [None])[0],
                "name": (s.get("display_names") or [None])[0],
                "sic": (s.get("sics") or [None])[0],
                "file_date": s.get("file_date"),
                "period_ending": s.get("period_ending"),
                "state": (s.get("biz_states") or [None])[0],
                "doc": key.split(":")[-1],
            })
        frm += PAGE
        if frm % 500 == 0:
            print(f"  {len(rows)} collected")
        time.sleep(0.16)
    json.dump({"query": QUERY, "forms": FORMS, "start": START, "end": END,
               "reported_total": total, "collected": len(rows), "rows": rows},
              open(OUT, "w"), indent=1)
    print(f"collected {len(rows)} filings -> {OUT}")
    from collections import Counter
    print("distinct CIKs:", len({r['cik'] for r in rows}))
    print("top SIC codes:", Counter(r["sic"] for r in rows).most_common(8))


if __name__ == "__main__":
    main()
