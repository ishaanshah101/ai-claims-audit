"""Blind the sentences and split them across raters.

Blinding here means three things: the registrant's own name and ticker are removed
from the sentence text, no metadata travels with the sentence, and the running order
is a seeded shuffle across filings so a rater cannot reconstruct a company from a run
of consecutive sentences.
"""
from __future__ import annotations
import json, os, re
import numpy as np

SEED = 20260926
N_RATERS = 6
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENT = os.path.join(BASE, "data", "sentences.json")
OUT = os.path.join(BASE, "data", "rating")


def name_tokens(display_name):
    """Tokens worth redacting from a sentence: the registrant name and its ticker."""
    if not display_name:
        return []
    toks = []
    m = re.match(r"^(.*?)\s*\(", display_name)
    base = (m.group(1) if m else display_name).strip()
    base = re.sub(r"\s*\(CIK[^)]*\)", "", base).strip()
    if len(base) > 3:
        toks.append(base)
        stripped = re.sub(r"[.,]", "", base)
        stripped = re.sub(r"\b(Inc|Corp|Corporation|Co|Company|Ltd|LLC|plc|Holdings|Group|Trust|Incorporated)\b",
                          "", stripped, flags=re.I).strip()
        if len(stripped) > 3 and stripped.lower() != base.lower():
            toks.append(stripped)
    for t in re.findall(r"\(([A-Z][A-Z0-9.\-]{1,6})\)", display_name):
        if t != "CIK":
            toks.append(t)
    return sorted(set(toks), key=len, reverse=True)


def redact(text, toks):
    out = text
    for t in toks:
        out = re.sub(r"\b" + re.escape(t) + r"\b", "the Company", out, flags=re.I)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    data = json.load(open(SENT))
    items = []
    for f in data["filings"]:
        toks = name_tokens(f["name"])
        for s in f["ai_sentences"]:
            items.append({
                "sid": f"{f['adsh']}#{s['idx']}",
                "adsh": f["adsh"], "sector": f["sector"], "cik": f["cik"],
                "name": f["name"], "raw": s["text"],
                "text": redact(s["text"], toks),
            })
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(items))
    items = [items[int(i)] for i in order]
    for n, it in enumerate(items, 1):
        it["rid"] = n

    json.dump(items, open(os.path.join(OUT, "items.json"), "w"), indent=1)

    # each item to exactly two raters, fixed before rating
    assign = {k: [] for k in range(N_RATERS)}
    for i, it in enumerate(items):
        for k in (i % N_RATERS, (i - 1) % N_RATERS):
            assign[k].append(it)
    for k, v in assign.items():
        blind = [{"rid": x["rid"], "text": x["text"]} for x in v]
        json.dump(blind, open(os.path.join(OUT, f"rater_{k}_items.json"), "w"), indent=1)
        print(f"rater {k}: {len(blind)} sentences")

    redacted = sum(1 for it in items if it["text"] != it["raw"])
    print(f"\ntotal sentences : {len(items)}")
    print(f"name redacted in: {redacted}")
    cov = {}
    for k, v in assign.items():
        for x in v:
            cov[x["rid"]] = cov.get(x["rid"], 0) + 1
    print("coverage per sentence:", sorted(set(cov.values())))


if __name__ == "__main__":
    main()
