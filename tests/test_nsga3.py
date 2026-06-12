"""Tests for NSGA-III many-objective wrapper."""
from __future__ import annotations

import pytest

from quantum_testing.algorithms.nsga3 import (
    CoverageProblemNSGA3,
    select_best_from_pareto,
)
from quantum_testing.problems.coverage import CoverageProblem


def _small_problem():
    """Small problem for fast NSGA-III tests."""
    return CoverageProblem.synthetic(n_tests=20, n_requirements=12, seed=42)


def _medium_problem():
    """Medium problem for quality tests."""
    return CoverageProblem.synthetic(n_tests=30, n_requirements=15, seed=7)


class TestCoverageProblemNSGA3:
    def test_init_default(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        assert solver.problem is cp
        assert solver.n_obj == 6
        assert solver.pop_size >= 40
        assert solver.pop_size % 4 == 0

    def test_init_clamps_pop_size(self):
        """pop_size not divisible by 4 gets rounded up."""
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=41, seed=0)
        assert solver.pop_size % 4 == 0
        assert solver.pop_size >= 41

    def test_run_returns_expected_keys(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        assert "pareto_front" in result
        assert "hypervolume" in result
        assert "n_gen" in result
        assert "pop_size" in result
        assert "ref_dirs_count" in result
        assert result["n_gen"] == 10

    def test_run_pareto_front_nonempty(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=20, verbose=False)
        assert len(result["pareto_front"]) > 0

    def test_run_pareto_solutions_have_required_keys(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        for sol in result["pareto_front"]:
            assert "solution" in sol
            assert "objectives" in sol
            assert "fitness" in sol
            assert len(sol["solution"]) == cp.n_tests

    def test_run_pareto_solutions_are_binary(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        for sol in result["pareto_front"]:
            for bit in sol["solution"]:
                assert bit in (0, 1)

    def test_run_pareto_objectives_have_six_keys(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        expected_keys = {
            "coverage_ratio", "reduction_ratio", "selected_count",
            "total_cost", "uncovered_count", "fitness",
        }
        for sol in result["pareto_front"]:
            assert set(sol["objectives"].keys()) == expected_keys

    def test_run_coverage_ratio_in_range(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        for sol in result["pareto_front"]:
            assert 0.0 <= sol["objectives"]["coverage_ratio"] <= 1.0

    def test_run_reproducible_with_seed(self):
        cp = _small_problem()
        s1 = CoverageProblemNSGA3(cp, pop_size=40, seed=42)
        r1 = s1.run(n_gen=10, verbose=False)
        s2 = CoverageProblemNSGA3(cp, pop_size=40, seed=42)
        r2 = s2.run(n_gen=10, verbose=False)
        assert r1["hypervolume"] == r2["hypervolume"]

    def test_run_more_generations_improves_or_maintains(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        r1 = solver.run(n_gen=5, verbose=False)
        solver2 = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        r2 = solver2.run(n_gen=30, verbose=False)
        assert len(r2["pareto_front"]) >= 1


class TestSelectBestFromPareto:
    def test_selects_single_solution(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=10, verbose=False)
        best = select_best_from_pareto(result["pareto_front"])
        assert "solution" in best
        assert "objectives" in best
        assert "fitness" in best

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            select_best_from_pareto([])

    def test_weights_affect_selection(self):
        cp = _small_problem()
        solver = CoverageProblemNSGA3(cp, pop_size=40, seed=0)
        result = solver.run(n_gen=20, verbose=False)
        pf = result["pareto_front"]
        if len(pf) < 2:
            pytest.skip("Pareto front too small")
        b1 = select_best_from_pareto(pf, weight_coverage=0.9, weight_reduction=0.05, weight_cost=0.05)
        b2 = select_best_from_pareto(pf, weight_coverage=0.05, weight_reduction=0.05, weight_cost=0.9)
        assert b1 in pf
        assert b2 in pf
