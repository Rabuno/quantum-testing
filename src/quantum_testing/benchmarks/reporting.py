"""Reporting helpers for benchmark artifacts."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Iterable


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "std": None, "median": None, "min": None, "max": None}
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def summarize_records(records: Iterable[dict]) -> dict:
    """Summarize raw benchmark records by algorithm and aggregate."""
    by_alg: dict[str, list[dict]] = defaultdict(list)
    by_case_alg: dict[tuple[str, int, str, str], list[dict]] = defaultdict(list)
    records = list(records)
    for record in records:
        by_alg[record["algorithm"]].append(record)
        by_case_alg[(record["project"], int(record["bug_id"]), record["version"], record["algorithm"])].append(record)

    def summarize_group(group: list[dict]) -> dict:
        full = [r for r in group if r["full_coverage"]]
        return {
            "runs": len(group),
            "cases": len({(r["project"], r["bug_id"], r["version"]) for r in group}),
            "coverage": _stats([float(r["coverage_ratio"]) for r in group]),
            "selected_count": _stats([float(r["selected_count"]) for r in group]),
            "reduction_ratio": _stats([float(r["reduction_ratio"]) for r in group]),
            "runtime_seconds": _stats([float(r["runtime_seconds"]) for r in group]),
            "full_coverage_rate": len(full) / len(group) if group else 0.0,
            "best_selected_full_coverage": min((int(r["selected_count"]) for r in full), default=None),
        }

    return {
        "total_records": len(records),
        "algorithms": {alg: summarize_group(group) for alg, group in sorted(by_alg.items())},
        "cases": {
            f"{project}-{bug_id}{version}-{alg}": summarize_group(group)
            for (project, bug_id, version, alg), group in sorted(by_case_alg.items())
        },
    }


def compare_primary_to_baselines(summary: dict, primary: str = "qiea") -> dict:
    """Compare a primary algorithm against baselines using full-coverage-safe metrics."""
    algs = summary.get("algorithms", {})
    if primary not in algs:
        return {"primary": primary, "error": "primary algorithm missing"}
    primary_stats = algs[primary]
    comparisons = {}
    p_selected = primary_stats["selected_count"]["mean"]
    p_runtime = primary_stats["runtime_seconds"]["mean"]
    p_full = primary_stats["full_coverage_rate"]
    for alg, stats in algs.items():
        if alg == primary:
            continue
        b_selected = stats["selected_count"]["mean"]
        b_runtime = stats["runtime_seconds"]["mean"]
        selected_improvement = None
        runtime_improvement = None
        if b_selected and p_selected is not None:
            selected_improvement = (b_selected - p_selected) / b_selected
        if b_runtime and p_runtime is not None:
            runtime_improvement = (b_runtime - p_runtime) / b_runtime
        comparisons[alg] = {
            "primary_full_coverage_rate": p_full,
            "baseline_full_coverage_rate": stats["full_coverage_rate"],
            "selected_count_delta": None if p_selected is None or b_selected is None else p_selected - b_selected,
            "selected_count_relative_improvement": selected_improvement,
            "runtime_delta_seconds": None if p_runtime is None or b_runtime is None else p_runtime - b_runtime,
            "runtime_relative_improvement": runtime_improvement,
            "claim_safe": p_full >= stats["full_coverage_rate"] and selected_improvement is not None and selected_improvement > 0,
        }
    return {"primary": primary, "comparisons": comparisons}
