"""Batch harvesting utilities for Defects4J coverage matrices.

Provides a high-level entry point to harvest coverage matrices for multiple
bugs across multiple Defects4J projects in a single call, with progress
reporting and graceful per-bug error handling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quantum_testing.datasets.defects4j import Defects4JConfig, Defects4JResult, collect_defects4j_matrix


@dataclass
class BatchHarvestConfig:
    """Configuration for a batch Defects4J harvest run.

    Each project listed in *projects* is combined with every bug id parsed from
    the corresponding entry in *bug_ranges* to produce the full cartesian
    product of harvest tasks.
    """

    defects4j_home: Path
    projects: list[str]
    bug_ranges: dict[str, str]
    version: str = "b"
    work_root: Path = Path("/tmp/quantum-testing-defects4j")
    output_dir: Path = Path("datasets/defects4j")
    test_property: str = "tests.trigger"
    limit_tests: int | None = None
    reuse_workdir: bool = True
    force_coverage: bool = False
    test_filter: str | None = None
    max_parallel: int = 1


@dataclass
class BatchHarvestResult:
    """Aggregated results from a batch Defects4J harvest run."""

    results: list[Defects4JResult] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    total_tests_sum: int = 0
    total_requirements_sum: int = 0


def _parse_bug_range(range_str: str) -> list[int]:
    """Parse a bug-range string such as ``"1-10"`` or ``"1,3,5-7"`` into a sorted list of ints."""
    bug_ids: list[int] = []
    for token in range_str.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            start = int(parts[0])
            end = int(parts[1])
            bug_ids.extend(range(start, end + 1))
        else:
            bug_ids.append(int(token))
    return sorted(set(bug_ids))


def _build_tasks(config: BatchHarvestConfig) -> list[tuple[str, int]]:
    """Expand *config* into a flat ``(project, bug_id)`` task list."""
    tasks: list[tuple[str, int]] = []
    for project in config.projects:
        range_str = config.bug_ranges.get(project, "")
        if not range_str:
            continue
        for bug_id in _parse_bug_range(range_str):
            tasks.append((project, bug_id))
    return tasks


def batch_harvest_defects4j(config: BatchHarvestConfig) -> BatchHarvestResult:
    """Harvest Defects4J coverage matrices for multiple projects and bugs.

    Iterates over every ``(project, bug_id)`` pair derived from *config*,
    calls :func:`collect_defects4j_matrix` for each, and collects results.
    Individual failures are recorded but do not stop the batch.

    Args:
        config: Batch harvest configuration.

    Returns:
        A :class:`BatchHarvestResult` with per-bug results, failure records,
        and aggregated test/requirement counts.
    """
    tasks = _build_tasks(config)
    result = BatchHarvestResult()

    for project, bug_id in tasks:
        label = f"{project}/{bug_id}{config.version}"
        try:
            single_config = Defects4JConfig(
                defects4j_home=config.defects4j_home,
                project=project,
                bug_id=bug_id,
                version=config.version,
                work_root=config.work_root,
                output_dir=config.output_dir,
                test_property=config.test_property,
                limit_tests=config.limit_tests,
                reuse_workdir=config.reuse_workdir,
                force_coverage=config.force_coverage,
                test_filter=config.test_filter,
            )
            single_result = collect_defects4j_matrix(single_config)
            result.results = [*result.results, single_result]
            result.total_tests_sum = result.total_tests_sum + single_result.total_tests
            result.total_requirements_sum = result.total_requirements_sum + single_result.total_requirements
            print(f"Harvesting {label}... OK ({single_result.total_tests} tests, {single_result.total_requirements} requirements)")
        except Exception as exc:
            error_msg = str(exc)
            result.failures = [*result.failures, {"project": project, "bug_id": bug_id, "error": error_msg}]
            print(f"Harvesting {label}... FAILED: {error_msg}")

    return result
