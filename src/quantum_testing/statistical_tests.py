"""Statistical test suite for algorithm comparison."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np


def wilcoxon_signed_rank(sample_a, sample_b, alternative="two-sided"):
    if len(sample_a) != len(sample_b):
        raise ValueError("Samples must have same length")
    n = len(sample_a)
    if n < 3:
        raise ValueError("Need at least 3 paired observations")
    diffs = [a - b for a, b in zip(sample_a, sample_b)]
    non_zero = [(i, d) for i, d in enumerate(diffs) if abs(d) > 1e-15]
    n_nonzero = len(non_zero)
    if n_nonzero == 0:
        return {"statistic": 0.0, "p_value": 1.0, "alternative": alternative, "significant": False}
    abs_diffs = sorted([(abs(d), i) for i, d in non_zero])
    ranks = _assign_ranks(abs_diffs)
    w_plus = sum(ranks[i] for i, d in non_zero if d > 0)
    w_minus = sum(ranks[i] for i, d in non_zero if d < 0)
    statistic = min(w_plus, w_minus)
    n_eff = n_nonzero
    mean_w = n_eff * (n_eff + 1) / 4.0
    std_w = math.sqrt(n_eff * (n_eff + 1) * (2 * n_eff + 1) / 24.0)
    if std_w < 1e-15:
        p_value = 1.0
    else:
        if statistic < mean_w:
            z = (statistic - mean_w + 0.5) / std_w
        else:
            z = (statistic - mean_w - 0.5) / std_w
        p_value = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
        if alternative == "two-sided":
            p_value = 2.0 * min(p_value, 1.0 - p_value)
        elif alternative == "greater":
            p_value = 1.0 - p_value
    return {"statistic": float(statistic), "p_value": float(p_value), "alternative": alternative, "significant": p_value < 0.05}


def _assign_ranks(sorted_abs_diffs):
    ranks = {}
    i = 0
    while i < len(sorted_abs_diffs):
        j = i
        while j < len(sorted_abs_diffs) and abs(sorted_abs_diffs[j][0] - sorted_abs_diffs[i][0]) < 1e-15:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            _, orig_idx = sorted_abs_diffs[k]
            ranks[orig_idx] = avg_rank
        i = j
    return ranks


def cliffs_delta(sample_a, sample_b):
    if not sample_a or not sample_b:
        raise ValueError("Samples must be non-empty")
    n_a = len(sample_a)
    n_b = len(sample_b)
    wins = 0
    losses = 0
    for a in sample_a:
        for b in sample_b:
            if a > b:
                wins += 1
            elif a < b:
                losses += 1
    delta = (wins - losses) / (n_a * n_b)
    abs_delta = abs(delta)
    if abs_delta < 0.147:
        magnitude = "negligible"
    elif abs_delta < 0.33:
        magnitude = "small"
    elif abs_delta < 0.474:
        magnitude = "medium"
    else:
        magnitude = "large"
    return {"delta": float(delta), "magnitude": magnitude}


def friedman_test(data):
    algorithms = list(data.keys())
    k = len(algorithms)
    if k < 2:
        raise ValueError("Need at least 2 algorithms")
    n = len(data[algorithms[0]])
    if n < 2:
        raise ValueError("Need at least 2 datasets")
    for alg in algorithms:
        if len(data[alg]) != n:
            raise ValueError("All algorithms must have same length")
    rank_sums = {alg: 0.0 for alg in algorithms}
    for dataset_idx in range(n):
        scores = [(data[alg][dataset_idx], alg) for alg in algorithms]
        scores.sort(key=lambda x: x[0])
        i = 0
        while i < len(scores):
            j = i
            while j < len(scores) and abs(scores[j][0] - scores[i][0]) < 1e-15:
                j += 1
            avg_rank = (i + j + 1) / 2.0
            for k_idx in range(i, j):
                rank_sums[scores[k_idx][1]] += avg_rank
            i = j
    sum_sq = sum(r ** 2 for r in rank_sums.values())
    statistic = (12.0 * sum_sq) / (n * k * (k + 1)) - 3.0 * n * (k + 1)
    if k > 2 and n > 2:
        p_value = _chi2_sf(statistic, k - 1)
    else:
        p_value = 1.0
    return {"statistic": float(statistic), "p_value": float(p_value), "significant": p_value < 0.05, "n_datasets": n, "n_algorithms": k, "rank_sums": rank_sums}


def _chi2_sf(x, df):
    if x <= 0:
        return 1.0
    return _gamma_q(df / 2.0, x / 2.0)


def _gamma_q(a, x):
    if x < 0 or a <= 0:
        return 1.0
    if x == 0:
        return 1.0
    if x < a + 1.0:
        p = _gamma_p_series(a, x)
        return 1.0 - p
    else:
        return _gamma_q_cf(a, x)


def _gamma_p_series(a, x, max_iter=300, tol=1e-14):
    if x == 0:
        return 0.0
    ap = a
    s = 1.0 / a
    ds = s
    for _ in range(max_iter):
        ap += 1.0
        ds *= x / ap
        s += ds
        if abs(ds) < abs(s) * tol:
            break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_cf(a, x, max_iter=300, tol=1e-14):
    fpmin = 1e-300
    b_cf = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b_cf
    h = d
    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b_cf += 2.0
        d = an * d + b_cf
        if abs(d) < fpmin:
            d = fpmin
        c = b_cf + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < tol:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def nemenyi_post_hoc(friedman_result, algorithm_names, alpha=0.05):
    k = friedman_result["n_algorithms"]
    n = friedman_result["n_datasets"]
    q_alpha = _nemenyi_critical_value(k, alpha)
    cd = q_alpha * math.sqrt(k * (k + 1) / (6.0 * n))
    rank_sums = friedman_result["rank_sums"]
    avg_ranks = {alg: rank_sums[alg] / n for alg in algorithm_names}
    comparisons = []
    significant_pairs = []
    for i in range(len(algorithm_names)):
        for j in range(i + 1, len(algorithm_names)):
            alg_i = algorithm_names[i]
            alg_j = algorithm_names[j]
            diff = abs(avg_ranks[alg_i] - avg_ranks[alg_j])
            is_sig = diff > cd
            comparisons.append({"algorithm_a": alg_i, "algorithm_b": alg_j, "rank_diff": float(diff), "significant": is_sig})
            if is_sig:
                significant_pairs.append((alg_i, alg_j))
    return {"cd": float(cd), "q_alpha": float(q_alpha), "avg_ranks": avg_ranks, "comparisons": comparisons, "significant_pairs": significant_pairs}


def _nemenyi_critical_value(k, alpha=0.05):
    table = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164}
    if k in table:
        return table[k]
    if k < 2:
        return 1.960
    return table[10] + (k - 10) * 0.05


def compute_cd_diagram_data(data, alpha=0.05):
    friedman = friedman_test(data)
    nemenyi = nemenyi_post_hoc(friedman, list(data.keys()), alpha)
    avg_ranks = nemenyi["avg_ranks"]
    algorithm_order = sorted(avg_ranks.keys(), key=lambda x: avg_ranks[x])
    return {"friedman": friedman, "nemenyi": nemenyi, "avg_ranks": avg_ranks, "cd": nemenyi["cd"], "algorithm_order": algorithm_order}
