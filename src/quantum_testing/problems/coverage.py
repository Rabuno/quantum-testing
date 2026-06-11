"""Coverage-matrix test-suite minimization problem.

Research context
-----------------
The single-objective ``fitness`` / ``qubo_energy`` formulation collapses
coverage, cost, and reduction into one scalar, hiding tradeoffs between
objectives. The multi-objective helpers in
:mod:`quantum_testing.multiobjective` and the ``objectives`` / ``qubo_terms``
methods below make those tradeoffs explicit and export a QUBO-like
description usable by annealing / QAOA tooling.

Related work
------------
- Trovato et al., "Reformulating Regression Test Suite Optimization using
  Quantum Annealing -- an Empirical Study", arXiv:2411.15963v2 (2025).
- Bandarupalli, "The Impact of Software Testing with Quantum Optimization
  Meets Machine Learning", arXiv:2506.02090v1 (2025).
- BQTmizer / "Test Case Minimization with Quantum Annealers" (ACM/SSBSE).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

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

    def objectives(self, solution: Sequence[int]) -> Dict[str, float]:
        """Multi-objective summary of ``solution``.

        Returns a dict with the following keys (all JSON-serializable floats
        except ``selected_count`` / ``uncovered_count`` which are integral
        floats for uniform serialization):

        - ``coverage_ratio`` (maximize)
        - ``reduction_ratio`` (maximize)
        - ``selected_count`` (minimize)
        - ``total_cost`` (minimize)
        - ``uncovered_count`` (minimize)
        - ``fitness`` (maximize; scalar from :meth:`fitness`)

        This is the input expected by
        :func:`quantum_testing.multiobjective.objective_vector` and
        :func:`quantum_testing.multiobjective.pareto_front`.
        """
        selected = [i for i, bit in enumerate(solution[: self.n_tests]) if int(bit)]
        covered = self.covered_by(solution)
        cov = metric_coverage_ratio(covered, self.n_requirements)
        red = reduction_ratio(len(selected), self.n_tests)
        cost = sum(self.costs[i] for i in selected)
        uncovered = self.n_requirements - len(covered)
        fit = self.fitness(solution)
        return {
            "coverage_ratio": float(cov),
            "reduction_ratio": float(red),
            "selected_count": float(len(selected)),
            "total_cost": float(cost),
            "uncovered_count": float(uncovered),
            "fitness": float(fit),
        }

    def qubo_terms(
        self,
        uncovered_weight: float = 2.0,
        cost_weight: float | None = None,
    ) -> Dict[str, object]:
        """Export a QUBO-like linear/quadratic description of the problem.

        The exact set-cover problem requires auxiliary variables to express
        the OR of each requirement's covering tests. To keep the export
        compact and usable by annealing / QAOA tooling without introducing
        auxiliaries, this returns a *surrogate* QUBO that:

        - rewards selecting tests that cover many requirements (linear term);
        - penalizes selecting many tests (linear cost term);
        - penalizes redundant overlap between selected tests (quadratic term).

        This is a standard penalty-expansion surrogate used when the true OR
        constraints would blow up the variable count; see e.g. the QUBO
        encodings discussed in Trovato et al., arXiv:2411.15963v2 (2025) and
        the BQTmizer tool line (ACM/SSBSE).

        Parameters
        ----------
        uncovered_weight:
            Weight on the coverage-reward term. Higher values push the
            solver toward full coverage.
        cost_weight:
            Weight on the per-test cost term. Defaults to ``self.alpha``.

        Returns
        -------
        dict
            JSON-serializable dict with keys ``linear``, ``quadratic``,
            ``offset``, ``sense``, ``variables``, and ``metadata``.
        """
        cw = self.alpha if cost_weight is None else float(cost_weight)
        max_cost = sum(self.costs) or 1.0

        linear: Dict[str, float] = {}
        quadratic: Dict[str, float] = {}
        variables: List[str] = [f"x{i}" for i in range(self.n_tests)]

        # Coverage counts per test (how many requirements each test covers).
        cover_counts = [len(s) for s in self.coverage_sets]

        for i in range(self.n_tests):
            # Reward coverage, penalize cost.
            q_ii = -uncovered_weight * cover_counts[i] + cw * (self.costs[i] / max_cost)
            linear[f"x{i}"] = q_ii

        # Quadratic overlap penalty: if two tests share requirements, selecting
        # both is partially redundant, so we add a positive penalty.
        for i in range(self.n_tests):
            for j in range(i + 1, self.n_tests):
                overlap = len(self.coverage_sets[i] & self.coverage_sets[j])
                if overlap:
                    quadratic[f"x{i}*x{j}"] = uncovered_weight * float(overlap)

        return {
            "linear": linear,
            "quadratic": quadratic,
            "offset": 0.0,
            "sense": "minimize",
            "variables": variables,
            "metadata": {
                "n_tests": self.n_tests,
                "n_requirements": self.n_requirements,
                "uncovered_weight": float(uncovered_weight),
                "cost_weight": float(cw),
                "note": (
                    "Surrogate QUBO: rewards coverage, penalizes cost and "
                    "redundant overlap. Not the exact set-cover QUBO with "
                    "auxiliary OR variables."
                ),
            },
        }

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
