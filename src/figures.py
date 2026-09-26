"""Figures.

Palette #2a78d6, #eb6834, #8a6fbf, carried over from the companion audit where
it was checked for lightness spread, chroma, deuteranopia and protanopia
separation, normal-vision separation, and contrast against a light surface.
"""
from __future__ import annotations
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS, FIGS = os.path.join(BASE, "results"), os.path.join(BASE, "figures")
os.makedirs(FIGS, exist_ok=True)
C1, C2, C3 = "#2a78d6", "#eb6834", "#8a6fbf"
INK, MUTED, GRID, SURF = "#1c1c1c", "#5a5a5a", "#dcdcd8", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.dpi": 200, "savefig.bbox": "tight",
})
CLASSES = ["risk", "other", "capability", "market", "governance"]
LABELS = {"risk": "risk factor", "other": "other", "capability": "own capability",
          "market": "market or industry", "governance": "governance"}


def fig1(res):
    """What AI language in an annual report is actually about."""
    comp = res["composition_calibrated"]
    vals = [comp[c]["rate"] for c in CLASSES]
    cols = [C2, MUTED, C1, C3, "#8a8a84"]
    fig, ax = plt.subplots(figsize=(7.2, 1.55))
    left = 0.0
    for v, c, col in zip(vals, CLASSES, cols):
        ax.barh([0], [v], left=left, color=col, height=0.52,
                edgecolor=SURF, linewidth=2)
        if v > 0.055:
            ax.text(left + v / 2, 0, f"{v:.0%}", ha="center", va="center",
                    color="white", fontweight="bold", fontsize=10)
        left += v
    ax.set_yticks([]); ax.set_xlim(0, 1); ax.set_ylim(-0.42, 0.42)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_xlabel(f"share of the {res['n_corpus']} AI sentences in 59 annual reports")
    ax.grid(axis="y", visible=False)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
    ax.legend(h, [LABELS[c] for c in CLASSES], loc="upper center",
              bbox_to_anchor=(0.5, -0.62), ncol=5, frameon=False, fontsize=8.5,
              handlelength=1.1, columnspacing=1.4)
    ax.set_title("What AI language in a 10-K is about, after calibration",
                 loc="left", fontweight="bold", pad=10)
    fig.savefig(os.path.join(FIGS, "fig1_composition.png")); plt.close(fig)


def fig2(res):
    """The funnel from AI sentence to a claim anyone could check."""
    v = res["verifiability"]
    n = res["n_corpus"]
    stages = [
        ("mentions AI", n),
        ("claims the company's\nown AI does something", v["denominator_agreed"]),
        ("names the quantity\nbeing claimed", v["metric_named"]["n_both"]),
        ("gives a number", v["quantified"]["n"]),
        ("says what the number\nwas measured over", v["evaluation_described"]["n"]),
        ("states a baseline", v["baseline_given"]["n"]),
        ("states an uncertainty", v["uncertainty_given"]["n"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ys = np.arange(len(stages))[::-1]
    cols = [MUTED, C1] + [C3] * 3 + [C2] * 2
    for y, (lab, c), col in zip(ys, stages, cols):
        if c > 0:
            ax.barh([y], [c], color=col, height=0.62)
            ax.text(c * 1.35, y, f"{c}", va="center",
                    fontsize=9, fontweight="bold", color=INK)
        else:
            # a count of zero gets no bar, only the number, so the eye is not
            # told there is something there
            ax.text(0.28, y, "0", va="center", fontsize=9,
                    fontweight="bold", color=C2)
    ax.set_yticks(ys); ax.set_yticklabels([s[0] for s in stages], fontsize=8.5)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(0, n * 2.6)
    ax.set_xticks([1, 10, 100, n]); ax.set_xticklabels(["1", "10", "100", str(n)])
    ax.set_xlabel("number of sentences (log scale)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Every filter an AI claim has to pass to be checkable",
                 loc="left", fontweight="bold", pad=10)
    fig.savefig(os.path.join(FIGS, "fig2_funnel.png")); plt.close(fig)


def fig3(res):
    """Capability-claim rate by sector, with filing-level bootstrap intervals."""
    order = ["technology", "healthcare", "other", "finance_realestate"]
    names = {"technology": "technology", "healthcare": "healthcare",
             "finance_realestate": "finance and\nreal estate", "other": "everything else"}
    s = res["sector_capability"]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    xs = np.arange(len(order))
    for i, k in enumerate(order):
        v = s[k]
        ax.plot([i, i], [v["boot_lo"], v["boot_hi"]], color=MUTED, lw=1.4,
                solid_capstyle="round", zorder=1)
        ax.scatter([i], [v["rate"]], s=62, color=C1, zorder=3,
                   edgecolor=SURF, linewidth=1.2)
        ax.text(i + 0.14, v["rate"], f"{v['rate']:.0%}", va="center",
                fontsize=9, fontweight="bold", color=INK)
    ov = res["composition_agreed"]["capability"]["rate"]
    ax.axhline(ov, color=C2, lw=1.2, ls=(0, (4, 3)), zorder=0)
    ax.text(-0.4, ov + 0.008, f"all sectors, {ov:.0%}",
            color=C2, fontsize=8.5, ha="left")
    ax.set_xticks(xs); ax.set_xticklabels([names[k] for k in order], fontsize=8.5)
    ax.set_xlim(-0.45, len(order) - 0.25)
    ax.set_ylim(0, max(s[k]["boot_hi"] for k in order) * 1.12)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_ylabel("share of AI sentences that are\nown-capability claims")
    ax.grid(axis="x", visible=False)
    ax.set_title("Capability-claim rate by sector, 95% bootstrap over filings",
                 loc="left", fontweight="bold", pad=10)
    fig.savefig(os.path.join(FIGS, "fig3_sector.png")); plt.close(fig)


def fig4(res, cal):
    """How far each pass verdict survived blinded review."""
    M = res["transfer_matrix"]
    order = ["capability", "risk", "market", "governance", "other"]
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    arr = np.array([[M[i][j] for j in order] for i in order])
    im = ax.imshow(arr, cmap="Blues", vmin=0, vmax=1)
    for i in range(5):
        for j in range(5):
            v = arr[i, j]
            if v > 0.001:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                        color="white" if v > 0.55 else INK,
                        fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(5)); ax.set_yticks(range(5))
    ax.set_xticklabels([LABELS[c] for c in order], rotation=30, ha="right", fontsize=8.5)
    ax.set_yticklabels([LABELS[c] for c in order], fontsize=8.5)
    ax.set_xlabel("blinded reviewer said"); ax.set_ylabel("both automated passes said")
    ax.grid(False)
    ax.set_title("Where the automated verdicts went under review",
                 loc="left", fontweight="bold", pad=10, fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03).outline.set_visible(False)
    fig.savefig(os.path.join(FIGS, "fig4_calibration.png")); plt.close(fig)


if __name__ == "__main__":
    res = json.load(open(os.path.join(RESULTS, "analysis.json")))
    cal = json.load(open(os.path.join(RESULTS, "calibration.json")))
    fig1(res); fig2(res); fig3(res); fig4(res, cal)
    for f in sorted(os.listdir(FIGS)):
        print(f, os.path.getsize(os.path.join(FIGS, f)), "bytes")
