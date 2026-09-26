"""Statistics used by this audit.

Every function here is small enough to check by hand, and the module runs its own
checks when executed directly, so a change that breaks one of them fails loudly
instead of quietly moving a number in the paper.
"""

from __future__ import annotations

import numpy as np

Z95 = 1.959963984540054


def wilson(successes: int, total: int, z: float = Z95):
    """Wilson score interval for a binomial proportion.

    Chosen over the normal approximation because most of the rates in this study
    sit close to zero, where the normal interval misbehaves and can run negative.
    """
    if total == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = successes / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def cluster_bootstrap_rate(clusters, n_boot: int = 10_000, seed: int = 20260926,
                           alpha: float = 0.05):
    """Percentile bootstrap for a rate, resampling clusters rather than items.

    `clusters` is a list of (numerator, denominator) pairs, one per filing.
    Sentences inside one filing share an author, a house style and a legal
    reviewer, so resampling sentences would treat 623 correlated observations as
    623 independent ones and make every interval too narrow. Filings are the
    unit that was actually sampled, so filings are the unit resampled here.
    """
    num = np.array([c[0] for c in clusters], dtype=float)
    den = np.array([c[1] for c in clusters], dtype=float)
    if num.size == 0 or den.sum() == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, num.size, size=(n_boot, num.size))
    d = den[idx].sum(axis=1)
    boot = np.where(d > 0, num[idx].sum(axis=1) / np.maximum(d, 1e-12), np.nan)
    boot = boot[~np.isnan(boot)]
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(num.sum() / den.sum()), float(lo), float(hi))


def cluster_bootstrap_diff(clusters_a, clusters_b, n_boot: int = 10_000,
                           seed: int = 20260926, alpha: float = 0.05):
    """Bootstrap interval for the difference between two rates, resampling
    clusters independently within each group."""
    na = np.array([c[0] for c in clusters_a], dtype=float)
    da = np.array([c[1] for c in clusters_a], dtype=float)
    nb = np.array([c[0] for c in clusters_b], dtype=float)
    db = np.array([c[1] for c in clusters_b], dtype=float)
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, na.size, size=(n_boot, na.size))
    ib = rng.integers(0, nb.size, size=(n_boot, nb.size))
    ra = na[ia].sum(axis=1) / np.maximum(da[ia].sum(axis=1), 1e-12)
    rb = nb[ib].sum(axis=1) / np.maximum(db[ib].sum(axis=1), 1e-12)
    d = ra - rb
    lo, hi = np.percentile(d, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    point = na.sum() / da.sum() - nb.sum() / db.sum()
    return (float(point), float(lo), float(hi))


def transfer_matrix(prior_labels, review_labels, classes):
    """P(review says j | the passes said i), estimated from the calibration sample.

    Rows are the passes' verdict, columns the reviewer's. A row with no
    calibration units is left as the identity, i.e. no correction is applied to a
    class the calibration pass never saw, which is the conservative choice.
    """
    k = len(classes)
    ix = {c: i for i, c in enumerate(classes)}
    M = np.zeros((k, k))
    for p, r in zip(prior_labels, review_labels):
        M[ix[p], ix[r]] += 1
    for i in range(k):
        if M[i].sum() == 0:
            M[i, i] = 1.0
        else:
            M[i] /= M[i].sum()
    return M


def calibrate_counts(counts, M):
    """Apply the transfer matrix to a vector of pass-assigned counts.

    This is the forward correction: of the sentences the passes put in class i, a
    measured fraction belong in class j, so the corrected count in j is the sum
    over i of counts[i] * M[i, j]. It answers 'what would a careful reader have
    found', not 'invert the confusion matrix', which with cells this small would
    amplify noise rather than remove bias.
    """
    return np.asarray(counts, dtype=float) @ np.asarray(M, dtype=float)


def _selfcheck():
    p, lo, hi = wilson(5, 100)
    assert abs(p - 0.05) < 1e-12 and 0.0 < lo < 0.05 < hi < 0.15, (lo, hi)
    p0, lo0, hi0 = wilson(0, 50)
    assert p0 == 0.0 and lo0 == 0.0 and 0 < hi0 < 0.1
    # published worked value: 2 of 10 gives about (0.0567, 0.5103)
    _, lo2, hi2 = wilson(2, 10)
    assert abs(lo2 - 0.0567) < 0.002 and abs(hi2 - 0.5103) < 0.002, (lo2, hi2)
    # a rate of exactly 1 in 623 should have an upper bound near 0.9 percent
    _, _, hi3 = wilson(1, 623)
    assert 0.005 < hi3 < 0.012, hi3

    r, rlo, rhi = cluster_bootstrap_rate([(1, 10)] * 60)
    assert abs(r - 0.1) < 1e-12 and abs(rlo - 0.1) < 1e-9, (r, rlo)
    r, rlo, rhi = cluster_bootstrap_rate([(2, 10), (0, 10), (1, 10)] * 20)
    assert rlo < r < rhi

    d, dlo, dhi = cluster_bootstrap_diff([(3, 10)] * 15, [(1, 10)] * 15)
    assert abs(d - 0.2) < 1e-12 and abs(dlo - 0.2) < 1e-9

    cl = ["a", "b"]
    M = transfer_matrix(["a", "a", "a", "a", "b"], ["a", "a", "a", "b", "b"], cl)
    assert abs(M[0, 0] - 0.75) < 1e-12 and abs(M[0, 1] - 0.25) < 1e-12
    assert abs(M[1, 1] - 1.0) < 1e-12
    # a class with no calibration units keeps its own count unchanged
    M2 = transfer_matrix(["a"], ["a"], cl)
    assert abs(M2[1, 1] - 1.0) < 1e-12
    out = calibrate_counts([100, 0], M)
    assert abs(out[0] - 75) < 1e-9 and abs(out[1] - 25) < 1e-9
    # calibration conserves total mass
    assert abs(calibrate_counts([37, 11], M).sum() - 48) < 1e-9
    print("stats.py: all self-checks passed")


if __name__ == "__main__":
    _selfcheck()
