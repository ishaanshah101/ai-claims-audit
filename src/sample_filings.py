"""Draw the filing sample, stratified by broad sector, under a fixed seed.

AI language in 10-K filings is not confined to technology companies, so the sample
is stratified across four broad sectors rather than drawn at random from a frame
that pharmaceutical and financial registrants happen to dominate.
"""
from __future__ import annotations
import json, os
from collections import Counter
import numpy as np

SEED = 20260926
PER_STRATUM = 15
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = os.path.join(BASE, "data", "frame.json")
OUT = os.path.join(BASE, "data", "sample_filings.json")


def sector(sic):
    """Four broad strata from the SEC's own SIC code, documented in the paper."""
    if not sic or not str(sic).isdigit():
        return "other"
    s = int(sic)
    if 7370 <= s <= 7379 or 3570 <= s <= 3579 or 3660 <= s <= 3679:
        return "technology"
    if 2833 <= s <= 2836 or 3826 <= s <= 3851 or 8000 <= s <= 8099 or s == 5912:
        return "healthcare"
    if 6000 <= s <= 6799:
        return "finance_realestate"
    return "other"


def main():
    frame = json.load(open(FRAME))
    rows = frame["rows"]
    for r in rows:
        r["sector"] = sector(r["sic"])

    # one filing per company, so a single registrant cannot dominate the sample
    by_cik = {}
    for r in sorted(rows, key=lambda r: (r["cik"] or "", r["adsh"] or "")):
        by_cik.setdefault(r["cik"], r)
    uniq = list(by_cik.values())
    print(f"frame {len(rows)} filings -> {len(uniq)} distinct registrants")
    print("stratum sizes:", Counter(r["sector"] for r in uniq))

    rng = np.random.default_rng(SEED)
    chosen = []
    for st in ("technology", "healthcare", "finance_realestate", "other"):
        pool = sorted([r for r in uniq if r["sector"] == st], key=lambda r: r["adsh"])
        pick = rng.permutation(len(pool))[:PER_STRATUM]
        for i in pick:
            chosen.append(pool[int(i)])
        print(f"  {st:20s} pool {len(pool):5d} drew {min(PER_STRATUM, len(pool))}")

    json.dump({"seed": SEED, "per_stratum": PER_STRATUM,
               "n": len(chosen), "filings": chosen}, open(OUT, "w"), indent=1)
    print(f"\nsampled {len(chosen)} filings -> {OUT}")


if __name__ == "__main__":
    main()
