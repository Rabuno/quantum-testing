"""Unified experiment runner for Phase 5 — full algorithm comparison on Defects4J.

This module orchestrates running ALL algorithms on ALL harvested Defects4J bugs,
performs statistical analysis (Friedman, Nemenyi, Wilcoxon, Cliff's delta), and
produces publication-ready results for the target journal paper.

Usage
-----
>>> from quantum_testing.experiment_runner import ExperimentConfig, run_experiment
>>> config = ExperimentConfig(
...     matrix_root="datasets/defects4j",
...     projects=["Lang", "Chart"],
...     bug_ranges={"Lang": "1-10", "Chart": "1-5"},
...     algorithms=["greedy", "qiea", "enhanced_qiea", "ga", "random", "sa"],
...     seeds=[42, 123, 456, 789, 1024],
...     output_dir="artifacts/experiment",
... )
>>> result = run_experiment(config)
>>> report = format_experiment_report(result)
>>> print(report)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Optional

from quantum_testing.benchmarks.defects4j_runner import (
    AlgorithmConfig,
    discover_defects4j_cases,
    run_defects4j_benchmark,
)
from quantum_testing.statistical_tests import (
    cliffs_delta,
    compute_cd_diagram_data,
    friedman_test,
    nemenyi_post_hoc,
    wilcoxon_signed_rank,
)


@dataclass
class ExperimentConfig:
    """Configuration for a full experiment run.

    Attributes
    ----------
    matrix_root : Path
        Root directory containing harvested Defects4J coverage matrices.
    projects : list[str]
        Defects4J project IDs to include, e.g. ``["Lang", "Chart"]``.
    bug_ranges : dict[str, str]
        Per-project bug ranges, e.g. ``{"Lang": "1-10", "Chart": "1-5"}``.
    algorithms : list[str]
        Algorithm identifiers to evaluate. Defaults to the core 6.
    seeds : list[int]
        Random seeds for stochastic algorithms. 5 seeds recommended for
        statistical power in the paper.
    output_dir : Path
        Directory for experiment artifacts and reports.
    run_id : str | None
        Explicit run identifier. Auto-generated from timestamp when *None*.
    qaoa_p : int
        Number of QAOA layers. Keep small (1-2) for simulation feasibility.
    qaoa_max_qubits : int
        Maximum qubit count for QAOA — problems larger than this skip QAOA.
    nsga3_pop_size : int
        NSGA-III population size.
    nsga3_generations : int
        NSGA-III generation count.
    algorithm_config : AlgorithmConfig | None
        Fine-grained algorithm hyper-parameters forwarded to the benchmark
        runner. When *None* the runner uses its built-in defaults.
    """

    matrix_root: Path
    projects: list[str]
    bug_ranges: dict[str, str]
    algorithms: list[str] = field(
        default_factory=lambda: [
            "greedy",
            "qiea",
            "enhanced_qiea",
            "ga",
            "random",
            "sa",
        ]
    )
    seeds: list[int] = field(
        default_factory=lambda: [42, 123, 456, 789, 1024]
    )
    output_dir: Path = field(default_factory=lambda: Path("artifacts/experiment"))
    run_id: str | None = None
    qaoa_p: int = 1
    qaoa_max_qubits: int = 25
    nsga3_pop_size: int = 50
    nsga3_generations: int = 100
    algorithm_config: AlgorithmConfig | None = None


@dataclass
class ExperimentResult:
    """Container for all experiment outputs.

    Attributes
    ----------
    run_id : str
        Unique identifier for this experiment run.
    raw_result : dict
        The full payload returned by :func:`run_defects4j_benchmark`.
    statistical_analysis : dict | None
        Nested dict with Friedman, Nemenyi, Wilcoxon, and Cliff's delta
        results. *None* when fewer than 2 algorithms or fewer than 3 bugs
        are present (insufficient data for non-parametric tests).
    per_bug_analysis : dict | None
        Per-bug breakdown: best algorithm per bug, win counts, and raw
        metric values. *None* when no bugs were evaluated.
    """

    run_id: str
    raw_result: dict
    statistical_analysis: dict | None = None
    per_bug_analysis: dict | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_metric_by_algorithm(
    records: list[dict],
    metric: str,
) -> dict[str, list[float]]:
    """Group a single metric value per algorithm across all records.

    For deterministic algorithms (greedy) only one seed is present; for
    stochastic algorithms the list contains one entry per seed per bug.
    """
    result: dict[str, list[float]] = {}
    for rec in records:
        alg = rec["algorithm"]
        result.setdefault(alg, []).append(float(rec[metric]))
    return result


def _collect_metric_per_bug_by_algorithm(
    records: list[dict],
    metric: str,
) -> dict[str, dict[str, list[float]]]:
    """Group metric values by ``bug_key -> algorithm -> [values]``."""
    result: dict[str, dict[str, list[float]]] = {}
    for rec in records:
        bug_key = f"{rec['project']}-{rec['bug_id']}{rec['version']}"
        alg = rec["algorithm"]
        result.setdefault(bug_key, {}).setdefault(alg, []).append(
            float(rec[metric])
        )
    return result


def _mean_per_bug(
    per_bug: dict[str, dict[str, list[float]]],
) -> dict[str, dict[str, float]]:
    """Average per-seed values so each bug/algorithm pair has one number."""
    return {
        bug: {alg: mean(vals) for alg, vals in algs.items()}
        for bug, algs in per_bug.items()
    }


def _run_statistical_analysis(records: list[dict], algorithms: list[str]) -> dict | None:
    """Run the full statistical test battery on benchmark records.

    Returns a dict with keys ``friedman``, ``nemenyi``, ``wilcoxon``, and
    ``cliffs_delta``, or *None* when there is insufficient data.
    """
    if len(algorithms) < 2:
        return None

    metrics = ["coverage_ratio", "reduction_ratio", "selected_count"]
    per_bug_means: dict[str, dict[str, dict[str, float]]] = {}
    for metric in metrics:
        per_bug = _collect_metric_per_bug_by_algorithm(records, metric)
        per_bug_means[metric] = _mean_per_bug(per_bug)

    n_bugs = len(next(iter(per_bug_means.values()), {}))
    if n_bugs < 3:
        return None

    friedman_results = {}
    nemenyi_results = {}
    for metric in metrics:
        data = per_bug_means[metric]
        bug_keys = sorted(data.keys())
        friedman_data: dict[str, list[float]] = {}
        for alg in algorithms:
            vals = [data[bug].get(alg, 0.0) for bug in bug_keys]
            if any(v is not None for v in vals):
                friedman_data[alg] = vals
        if len(friedman_data) < 2:
            continue
        try:
            fr = friedman_test(friedman_data)
        except (ValueError, ZeroDivisionError):
            continue
        friedman_results[metric] = fr
        if fr.get("significant") and len(friedman_data) >= 3:
            try:
                nemenyi_results[metric] = nemenyi_post_hoc(
                    fr, list(friedman_data.keys())
                )
            except (ValueError, ZeroDivisionError):
                nemenyi_results[metric] = None
        else:
            nemenyi_results[metric] = None

    wilcoxon_results = {}
    cliffs_results = {}
    primary = "enhanced_qiea"
    if primary in algorithms:
        primary_records = _collect_metric_by_algorithm(records, "reduction_ratio")
        primary_vals = primary_records.get(primary, [])
        for alg in algorithms:
            if alg == primary:
                continue
            alg_vals = primary_records.get(alg, [])
            if len(primary_vals) < 3 or len(alg_vals) < 3:
                wilcoxon_results[alg] = None
                cliffs_results[alg] = None
                continue
            min_len = min(len(primary_vals), len(alg_vals))
            p_slice = primary_vals[:min_len]
            a_slice = alg_vals[:min_len]
            try:
                wilcoxon_results[alg] = wilcoxon_signed_rank(p_slice, a_slice)
            except (ValueError, ZeroDivisionError):
                wilcoxon_results[alg] = None
            try:
                cliffs_results[alg] = cliffs_delta(p_slice, a_slice)
            except (ValueError, ZeroDivisionError):
                cliffs_results[alg] = None

    cd_diagram = None
    try:
        reduction_per_bug = per_bug_means.get("reduction_ratio", {})
        bug_keys = sorted(reduction_per_bug.keys())
        cd_data: dict[str, list[float]] = {}
        for alg in algorithms:
            vals = [reduction_per_bug[bug].get(alg, 0.0) for bug in bug_keys]
            if any(v is not None for v in vals):
                cd_data[alg] = vals
        if len(cd_data) >= 2 and len(bug_keys) >= 3:
            cd_diagram = compute_cd_diagram_data(cd_data)
    except (ValueError, ZeroDivisionError):
        cd_diagram = None

    return {
        "friedman": friedman_results,
        "nemenyi": nemenyi_results,
        "wilcoxon": wilcoxon_results,
        "cliffs_delta": cliffs_results,
        "cd_diagram": cd_diagram,
        "n_bugs": n_bugs,
        "n_algorithms": len(algorithms),
        "metrics_analyzed": metrics,
    }


def _run_per_bug_analysis(
    records: list[dict],
    algorithms: list[str],
) -> dict | None:
    """Produce per-bug breakdown: best algorithm, win counts, raw metrics."""
    if not records:
        return None

    per_bug = _collect_metric_per_bug_by_algorithm(records, "reduction_ratio")
    per_bug_means = _mean_per_bug(per_bug)

    bug_details: dict[str, dict] = {}
    win_counts: dict[str, int] = {alg: 0 for alg in algorithms}

    for bug_key, alg_means in sorted(per_bug_means.items()):
        best_alg = max(alg_means, key=lambda a: alg_means.get(a, 0.0))
        win_counts[best_alg] = win_counts.get(best_alg, 0) + 1
        bug_details[bug_key] = {
            "best_algorithm": best_alg,
            "best_reduction_ratio": alg_means[best_alg],
            "algorithm_means": dict(alg_means),
        }

    coverage_per_bug = _collect_metric_per_bug_by_algorithm(records, "coverage_ratio")
    coverage_means = _mean_per_bug(coverage_per_bug)
    for bug_key in bug_details:
        if bug_key in coverage_means:
            bug_details[bug_key]["coverage_means"] = coverage_means[bug_key]

    selected_per_bug = _collect_metric_per_bug_by_algorithm(records, "selected_count")
    selected_means = _mean_per_bug(selected_per_bug)
    for bug_key in bug_details:
        if bug_key in selected_means:
            bug_details[bug_key]["selected_means"] = selected_means[bug_key]

    return {
        "bug_details": bug_details,
        "win_counts": win_counts,
        "n_bugs": len(per_bug_means),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_experiment(config: ExperimentConfig) -> ExperimentResult:
    """Execute a full experiment: benchmark + statistics + per-bug analysis.

    Parameters
    ----------
    config : ExperimentConfig
        Complete experiment configuration.

    Returns
    -------
    ExperimentResult
        Container with raw benchmark output, statistical analysis, and
        per-bug breakdown.
    """
    run_id = config.run_id or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    experiment_dir = Path(config.output_dir) / run_id
    experiment_dir.mkdir(parents=True, exist_ok=True)

    cases = discover_defects4j_cases(
        matrix_root=config.matrix_root,
        projects=config.projects,
        bugs=None,
        version="b",
    )

    filtered_cases = []
    version_suffix = "b"
    for case in cases:
        project = case.project
        bug_id = case.bug_id
        if project not in config.bug_ranges:
            filtered_cases.append(case)
            continue
        range_str = config.bug_ranges[project]
        parts = range_str.split("-", 1)
        if len(parts) == 2:
            lo, hi = int(parts[0]), int(parts[1])
            if lo <= bug_id <= hi:
                filtered_cases.append(case)
        else:
            if bug_id == int(parts[0]):
                filtered_cases.append(case)
    cases = filtered_cases

    raw_result = run_defects4j_benchmark(
        cases=cases,
        algorithms=config.algorithms,
        seeds=config.seeds,
        output_dir=experiment_dir,
        run_id="benchmark",
        config=config.algorithm_config,
    )

    records = []
    raw_jsonl = experiment_dir / "benchmark" / "raw_runs.jsonl"
    if raw_jsonl.exists():
        with raw_jsonl.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    statistical_analysis = _run_statistical_analysis(records, config.algorithms)
    per_bug_analysis = _run_per_bug_analysis(records, config.algorithms)

    result = ExperimentResult(
        run_id=run_id,
        raw_result=raw_result,
        statistical_analysis=statistical_analysis,
        per_bug_analysis=per_bug_analysis,
    )

    _save_experiment_artifacts(result, experiment_dir)

    return result


def _save_experiment_artifacts(
    result: ExperimentResult, experiment_dir: Path
) -> None:
    """Persist statistical and per-bug analysis to the experiment directory."""
    if result.statistical_analysis is not None:
        stat_path = experiment_dir / "statistical_analysis.json"
        stat_path.write_text(
            json.dumps(result.statistical_analysis, indent=2, default=str)
        )
    if result.per_bug_analysis is not None:
        bug_path = experiment_dir / "per_bug_analysis.json"
        bug_path.write_text(
            json.dumps(result.per_bug_analysis, indent=2, default=str)
        )
    report = format_experiment_report(result)
    report_path = experiment_dir / "experiment_report.txt"
    report_path.write_text(report)


def format_experiment_report(result: ExperimentResult) -> str:
    """Format an :class:`ExperimentResult` as a publication-ready text report.

    The report includes:
    - Experiment summary (run ID, cases, algorithms, seeds)
    - Aggregate metric table (coverage, reduction, selected count, runtime)
    - Statistical test results (Friedman, Nemenyi, Wilcoxon, Cliff's delta)
    - Per-bug breakdown with win counts
    """
    lines: list[str] = []
    sep = "=" * 72
    subsep = "-" * 72

    lines.append(sep)
    lines.append("EXPERIMENT REPORT")
    lines.append(sep)
    lines.append(f"Run ID: {result.run_id}")
    lines.append(
        f"Generated: {datetime.now(timezone.utc).isoformat()}"
    )
    lines.append("")

    raw = result.raw_result
    summary = raw.get("summary", {})
    algorithms = summary.get("algorithms", {})
    n_cases = len(raw.get("cases", []))
    n_records = summary.get("total_records", 0)
    algo_names = sorted(algorithms.keys())

    lines.append("1. EXPERIMENT SUMMARY")
    lines.append(subsep)
    lines.append(f"  Cases evaluated   : {n_cases}")
    lines.append(f"  Total records     : {n_records}")
    lines.append(f"  Algorithms        : {', '.join(algo_names)}")
    lines.append(f"  Seeds             : {raw.get('seeds', [])}")
    lines.append("")

    lines.append("2. AGGREGATE METRICS")
    lines.append(subsep)
    header = f"  {'Algorithm':<18} {'Cov(mean)':>10} {'Red(mean)':>10} {'Sel(mean)':>10} {'FullCov%':>9} {'Time(s)':>10}"
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for algo in algo_names:
        stats = algorithms[algo]
        cov = stats.get("coverage", {}).get("mean", 0.0) or 0.0
        red = stats.get("reduction_ratio", {}).get("mean", 0.0) or 0.0
        sel = stats.get("selected_count", {}).get("mean", 0.0) or 0.0
        full = stats.get("full_coverage_rate", 0.0) or 0.0
        tim = stats.get("runtime_seconds", {}).get("mean", 0.0) or 0.0
        lines.append(
            f"  {algo:<18} {cov:>10.4f} {red:>10.4f} {sel:>10.1f} {full:>8.1%} {tim:>10.3f}"
        )
    lines.append("")

    stat = result.statistical_analysis
    lines.append("3. STATISTICAL ANALYSIS")
    lines.append(subsep)
    if stat is None:
        lines.append("  Insufficient data for statistical tests")
        lines.append("  (need >= 2 algorithms and >= 3 bugs)")
    else:
        lines.append(f"  Bugs analyzed : {stat.get('n_bugs', '?')}")
        lines.append(f"  Algorithms    : {stat.get('n_algorithms', '?')}")
        lines.append("")

        friedman = stat.get("friedman", {})
        if friedman:
            lines.append("  3a. Friedman Test (per metric)")
            for metric, fr in sorted(friedman.items()):
                sig = "***" if fr.get("significant") else "n.s."
                lines.append(
                    f"      {metric:<25} "
                    f"stat={fr.get('statistic', 0):.3f}  "
                    f"p={fr.get('p_value', 1):.4f}  {sig}"
                )
            lines.append("")

        nemenyi = stat.get("nemenyi", {})
        if nemenyi:
            lines.append("  3b. Nemenyi Post-Hoc (where Friedman significant)")
            for metric, nem in sorted(nemenyi.items()):
                if nem is None:
                    lines.append(f"      {metric}: not significant or insufficient data")
                    continue
                cd_val = nem.get("cd", 0.0)
                lines.append(f"      {metric}  (CD = {cd_val:.4f})")
                for comp in nem.get("comparisons", []):
                    sig_mark = "*" if comp.get("significant") else "="
                    lines.append(
                        f"        {comp['algorithm_a']:<18} vs {comp['algorithm_b']:<18}  "
                        f"diff={comp['rank_diff']:.3f}  {sig_mark}"
                    )
            lines.append("")

        wilcoxon = stat.get("wilcoxon", {})
        cliffs = stat.get("cliffs_delta", {})
        if wilcoxon or cliffs:
            lines.append("  3c. Wilcoxon & Cliff's Delta (enhanced_qiea vs baselines)")
            lines.append(f"      {'Baseline':<18} {'Wilcoxon p':>12} {'Signif.':>9} {'Cliff d':>10} {'Magnitude':>12}")
            for alg in algo_names:
                if alg == "enhanced_qiea":
                    continue
                w = wilcoxon.get(alg)
                c = cliffs.get(alg)
                if w is None and c is None:
                    continue
                w_p = f"{w['p_value']:.4f}" if w else "N/A"
                w_sig = "yes" if w and w.get("significant") else "no"
                c_d = f"{c['delta']:+.3f}" if c else "N/A"
                c_mag = c.get("magnitude", "N/A") if c else "N/A"
                lines.append(
                    f"      {alg:<18} {w_p:>12} {w_sig:>9} {c_d:>10} {c_mag:>12}"
                )
            lines.append("")

        cd = stat.get("cd_diagram")
        if cd is not None:
            lines.append("  3d. CD Diagram Ranking (reduction_ratio)")
            avg_ranks = cd.get("avg_ranks", {})
            cd_val = cd.get("cd", 0.0)
            ranked = sorted(avg_ranks.items(), key=lambda x: x[1])
            lines.append(f"      CD = {cd_val:.4f}")
            for alg, rank in ranked:
                lines.append(f"        {rank:.2f}  {alg}")
            lines.append("")

    lines.append("")

    per_bug = result.per_bug_analysis
    lines.append("4. PER-BUG ANALYSIS")
    lines.append(subsep)
    if per_bug is None:
        lines.append("  No per-bug data available.")
    else:
        win_counts = per_bug.get("win_counts", {})
        n_bugs = per_bug.get("n_bugs", 0)
        lines.append(f"  Total bugs : {n_bugs}")
        lines.append("")
        lines.append("  Win counts (best reduction_ratio per bug):")
        for alg, count in sorted(win_counts.items(), key=lambda x: -x[1]):
            pct = count / n_bugs if n_bugs > 0 else 0
            lines.append(f"    {alg:<18} {count:>4}  ({pct:.1%})")
        lines.append("")

        bug_details = per_bug.get("bug_details", {})
        lines.append("  Per-bug best algorithm:")
        lines.append(f"    {'Bug':<20} {'Best Alg':<18} {'Red. Ratio':>11} {'Coverage':>10} {'Selected':>10}")
        for bug_key, detail in sorted(bug_details.items()):
            best = detail.get("best_algorithm", "?")
            red = detail.get("best_reduction_ratio", 0.0)
            cov_vals = detail.get("coverage_means", {})
            sel_vals = detail.get("selected_means", {})
            cov_str = f"{cov_vals.get(best, 0):.4f}" if cov_vals else "N/A"
            sel_str = f"{sel_vals.get(best, 0):.1f}" if sel_vals else "N/A"
            lines.append(
                f"    {bug_key:<20} {best:<18} {red:>11.4f} {cov_str:>10} {sel_str:>10}"
            )

    lines.append("")
    lines.append(sep)
    lines.append("END OF REPORT")
    lines.append(sep)

    return "\n".join(lines)
