"""Shared test fixtures for quantum-testing test suite."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def sample_cd_data():
    """Sample per-algorithm per-dataset scores for CD diagram."""
    return {
        "qiea": [0.95, 0.88, 0.91, 0.87],
        "greedy": [0.92, 0.85, 0.89, 0.83],
        "ga": [0.90, 0.82, 0.87, 0.80],
        "random": [0.70, 0.65, 0.68, 0.60],
        "sa": [0.85, 0.78, 0.82, 0.75],
    }


@pytest.fixture
def sample_histories():
    """Sample convergence histories for 3 algorithms."""
    rng = np.random.RandomState(42)
    histories = {}
    for alg, target in [("qiea", 0.95), ("ga", 0.90), ("random", 0.70)]:
        runs = []
        for _ in range(5):
            gens = 50
            curve = np.linspace(0.3, target, gens) + rng.normal(0, 0.02, gens)
            runs.append(list(np.clip(curve, 0, 1)))
        histories[alg] = runs
    return histories


@pytest.fixture
def sample_summary():
    """Sample summary dict for box plot tests."""
    rng = np.random.RandomState(123)
    return {
        "qiea": {
            "coverage_ratios": list(rng.normal(0.92, 0.03, 15)),
            "reduction_ratios": list(rng.normal(0.75, 0.08, 15)),
            "runtimes": list(rng.normal(2.5, 0.3, 15)),
            "coverage_mean": 0.92,
            "coverage_std": 0.03,
            "reduction_mean": 0.75,
            "reduction_std": 0.08,
            "runtime_mean": 2.5,
            "runtime_std": 0.3,
            "runs": 15,
        },
        "greedy": {
            "coverage_ratios": list(rng.normal(0.89, 0.04, 15)),
            "reduction_ratios": list(rng.normal(0.70, 0.10, 15)),
            "runtimes": list(rng.normal(0.5, 0.1, 15)),
            "coverage_mean": 0.89,
            "coverage_std": 0.04,
            "reduction_mean": 0.70,
            "reduction_std": 0.10,
            "runtime_mean": 0.5,
            "runtime_std": 0.1,
            "runs": 15,
        },
    }


@pytest.fixture
def sample_stat_analysis():
    """Sample statistical analysis dict."""
    return {
        "friedman": {
            "statistic": 12.5,
            "p_value": 0.028,
            "significant": True,
            "n_datasets": 8,
            "n_algorithms": 5,
        },
        "nemenyi": {
            "cd": 1.5,
            "avg_ranks": {"qiea": 1.8, "greedy": 2.5, "ga": 2.7, "sa": 3.2, "random": 4.8},
            "significant_pairs": [("qiea", "random")],
        },
        "wilcoxon": {
            "qiea_vs_greedy": {"statistic": 15.0, "p_value": 0.12, "significant": False},
            "qiea_vs_random": {"statistic": 3.0, "p_value": 0.01, "significant": True},
        },
        "cliffs_delta": {
            "qiea_vs_greedy": {"delta": 0.2, "magnitude": "small"},
            "qiea_vs_random": {"delta": 0.8, "magnitude": "large"},
        },
    }


@pytest.fixture
def sample_coverage_csv(tmp_path):
    """Create a small coverage matrix CSV for heatmap tests."""
    import csv

    csv_path = tmp_path / "coverage.csv"
    n_tests = 10
    n_reqs = 15
    rng = np.random.RandomState(42)

    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        header = ["test_id"] + [f"req_{i}" for i in range(n_reqs)]
        writer.writerow(header)
        for t in range(n_tests):
            row = [f"test_{t}"] + list(rng.randint(0, 2, n_reqs).astype(str))
            writer.writerow(row)

    return csv_path


@pytest.fixture
def sample_pareto_candidates():
    """Sample Pareto candidates for scatter plot."""
    candidates = []
    for seed in range(10):
        candidates.append({
            "seed": seed,
            "algorithm": "qiea" if seed < 5 else "greedy",
            "selected_count": 5 + seed,
            "coverage_ratio": min(0.99, 0.7 + seed * 0.03),
        })
    return candidates


@pytest.fixture
def sample_experiment_dir(tmp_path, sample_cd_data, sample_summary, sample_stat_analysis):
    """Create a minimal experiment directory with all required artifacts."""
    exp_dir = tmp_path / "experiment"
    exp_dir.mkdir()

    # Statistical analysis
    (exp_dir / "statistical_analysis.json").write_text(
        json.dumps(sample_stat_analysis))

    # Per-bug analysis: each bug has all algorithms with a score
    rng = np.random.RandomState(7)
    bugs = ["Lang_1", "Lang_2", "Lang_3", "Lang_4", "Lang_5",
            "Chart_1", "Chart_2", "Math_1"]
    per_bug = {}
    for bug in bugs:
        per_bug[bug] = {}
        for alg in sample_cd_data:
            base = sample_cd_data[alg][0]
            score = float(np.clip(base + rng.normal(0, 0.03), 0, 1))
            per_bug[bug][alg] = {"coverage_mean": score}
    (exp_dir / "per_bug_analysis.json").write_text(json.dumps(per_bug))

    # Summary
    bench_dir = exp_dir / "benchmark"
    bench_dir.mkdir()
    (bench_dir / "summary.json").write_text(json.dumps(sample_summary))

    # Raw runs with history
    import csv as _csv
    rng = np.random.RandomState(42)
    with (bench_dir / "raw_runs.jsonl").open("w") as f:
        for alg in ["qiea", "greedy", "ga"]:
            for seed in [42, 123, 456]:
                hist = list(np.linspace(0.3, 0.9 if alg == "qiea" else 0.7, 30))
                rec = {
                    "algorithm": alg,
                    "seed": seed,
                    "coverage_ratio": rng.uniform(0.8, 1.0),
                    "selected_count": rng.randint(5, 20),
                    "history": hist,
                }
                f.write(json.dumps(rec) + "\n")

    return exp_dir
