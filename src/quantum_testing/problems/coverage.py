"""Coverage-matrix test-suite minimization problem."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

import numpy as np

from quantum_testing.metrics import coverage_ratio as metric_coverage_ratio, reduction_ratio


@dataclass
class CoverageReport:
    selected_tests: list[int]
    selected_count: int
    total_tests: int
    covered_requirements: list[int]
    total_requirements: int
    coverage_ratio: float
    reduction_ratio: float
    total_cost: float
    fitness: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class CoverageProblem:
    """Test-suite minimization over a tests x requirements coverage matrix."""

    def __init__(self, coverage_sets: Sequence[Iterable[int]], n_requirements: Optional[int] = None, costs: Optional[Sequence[float]] = None, alpha: float = 0.1):
        self.coverage_sets: list[set[int]] = [set(s) for s in coverage_sets]
        inferred = max((max(s) for s in self.coverage_sets if s), default=-1) + 1
        self.n_requirements = int(n_requirements if n_requirements is not None else inferred)
        self.n_tests = len(self.coverage_sets)
        self.costs = list(costs) if costs is not None else [1.0] * self.n_tests
        if len(self.costs) != self.n_tests:
            raise ValueError("costs length must equal number of tests")
        self.alpha = alpha

    @classmethod
    def from_matrix(cls, matrix: Sequence[Sequence[int | bool]], costs: Optional[Sequence[float]] = None, alpha: float = 0.1) -> "CoverageProblem":
        rows = [list(row) for row in matrix]
        coverage_sets = [{j for j, val in enumerate(row) if int(val) != 0} for row in rows]
        n_req = len(rows[0]) if rows else 0
        return cls(coverage_sets, n_req, costs, alpha)

    @classmethod
    def load_csv(cls, path: str | Path, alpha: float = 0.1) -> "CoverageProblem":
        rows: list[list[int]] = []
        with open(path, newline="") as f:
            sample = f.read(2048)
            f.seek(0)
            has_header = csv.Sniffer().has_header(sample)
            reader = csv.reader(f)
            if has_header:
                next(reader, None)
            for row in reader:
                if not row:
                    continue
                # Permit an initial test-id column if the first cell is non-binary.
                cells = row
                if cells and cells[0].strip() not in {"0", "1"}:
                    cells = cells[1:]
                rows.append([int(x) for x in cells])
        return cls.from_matrix(rows, alpha=alpha)

    @classmethod
    def synthetic(cls, n_tests: int = 30, n_requirements: int = 20, min_cover: int = 2, max_cover: int = 8, seed: int | None = 42, alpha: float = 0.1) -> "CoverageProblem":
        rng = np.random.default_rng(seed)
        sets: list[set[int]] = []
        for _ in range(n_tests):
            k = int(rng.integers(min_cover, min(max_cover, n_requirements) + 1))
            sets.append(set(map(int, rng.choice(n_requirements, size=k, replace=False))))
        # Ensure every requirement is coverable.
        for req in range(n_requirements):
            if not any(req in s for s in sets):
                sets[int(rng.integers(0, n_tests))].add(req)
        return cls(sets, n_requirements, alpha=alpha)

    def covered_by(self, solution: Sequence[int]) -> set[int]:
        covered: set[int] = set()
        for i, bit in enumerate(solution[: self.n_tests]):
            if int(bit):
                covered |= self.coverage_sets[i]
        return covered

    def fitness(self, solution: Sequence[int]) -> float:
        selected = [i for i, bit in enumerate(solution[: self.n_tests]) if int(bit)]
        covered = self.covered_by(solution)
        cov = metric_coverage_ratio(covered, self.n_requirements)
        max_cost = sum(self.costs) or 1.0
        cost_ratio = sum(self.costs[i] for i in selected) / max_cost
        return cov - self.alpha * cost_ratio

    def qubo_energy(
        self,
        solution: Sequence[int],
        uncovered_weight: float = 2.0,
        cost_weight: float | None = None,
    ) -> float:
        """QUBO-style energy for test-suite minimization.

        Lower is better. The formulation penalizes uncovered requirements
        strongly and selected-test cost weakly, mirroring quantum annealing / QAOA
        set-cover encodings while remaining executable without quantum SDKs.
        """
        selected = [i for i, bit in enumerate(solution[: self.n_tests]) if int(bit)]
        covered = self.covered_by(solution)
        uncovered = self.n_requirements - len(covered)
        max_cost = sum(self.costs) or 1.0
        cw = self.alpha if cost_weight is None else cost_weight
        selected_cost_ratio = sum(self.costs[i] for i in selected) / max_cost
        return uncovered_weight * uncovered + cw * selected_cost_ratio

    def report(self, solution: Sequence[int]) -> CoverageReport:
        selected = [i for i, bit in enumerate(solution[: self.n_tests]) if int(bit)]
        covered = sorted(self.covered_by(solution))
        return CoverageReport(
            selected_tests=selected,
            selected_count=len(selected),
            total_tests=self.n_tests,
            covered_requirements=covered,
            total_requirements=self.n_requirements,
            coverage_ratio=metric_coverage_ratio(covered, self.n_requirements),
            reduction_ratio=reduction_ratio(len(selected), self.n_tests),
            total_cost=sum(self.costs[i] for i in selected),
            fitness=self.fitness(solution),
        )
