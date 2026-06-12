"""Tests for exact set-cover QUBO formulation."""
from __future__ import annotations

import pytest

from quantum_testing.problems.qubo_exact import (
    ExactQUBOFormulation,
    compute_qubo_density,
)
from quantum_testing.problems.coverage import CoverageProblem


def _small_problem():
    return CoverageProblem.synthetic(n_tests=10, n_requirements=6, seed=42)


def _medium_problem():
    return CoverageProblem.synthetic(n_tests=20, n_requirements=12, seed=7)


class TestExactQUBOFormulation:
    def test_init_default(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        assert qubo.problem is cp
        assert qubo.n_x == 10
        assert qubo.n_y == 6
        assert qubo.n_vars == 16

    def test_init_custom_weights(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp, coverage_weight=5.0, cost_weight=2.0, coupling_weight=3.0)
        assert qubo.A == 5.0
        assert qubo.B == 2.0
        assert qubo.C == 3.0

    def test_variable_name(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        assert qubo.variable_name(0) == "x0"
        assert qubo.variable_name(9) == "x9"
        assert qubo.variable_name(10) == "y0"
        assert qubo.variable_name(15) == "y5"

    def test_variable_index(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        assert qubo.variable_index("x0") == 0
        assert qubo.variable_index("x9") == 9
        assert qubo.variable_index("y0") == 10
        assert qubo.variable_index("y5") == 15

    def test_qubo_terms_structure(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        assert set(terms.keys()) == {
            "linear", "quadratic", "offset", "sense", "variables", "metadata",
        }
        assert terms["sense"] == "minimize"
        assert len(terms["variables"]) == qubo.n_vars

    def test_qubo_terms_all_variables_in_linear(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        for v in terms["variables"]:
            assert v in terms["linear"], f"{v} missing from linear terms"

    def test_qubo_terms_quadratic_keys_valid(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        for key in terms["quadratic"]:
            assert "*" in key
            v1, v2 = key.split("*", 1)
            assert v1 in terms["variables"]
            assert v2 in terms["variables"]

    def test_qubo_terms_metadata(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        md = terms["metadata"]
        assert md["formulation"] == "exact_set_cover_with_or_auxiliaries"
        assert md["n_tests"] == 10
        assert md["n_requirements"] == 6
        assert md["n_total_vars"] == 16

    def test_decode_solution(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        sol = {f"x{i}": 0 for i in range(10)}
        sol.update({f"y{j}": 0 for j in range(6)})
        sol["x0"] = 1
        sol["x3"] = 1
        decoded = qubo.decode_solution(sol)
        assert len(decoded) == 10
        assert decoded[0] == 1
        assert decoded[3] == 1
        assert sum(decoded) == 2

    def test_brute_force_solve_small(self):
        cp = CoverageProblem.synthetic(n_tests=6, n_requirements=4, seed=1)
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        result = ExactQUBOFormulation.brute_force_solve(terms, max_vars=25)
        assert result is not None
        assert "assignment" in result
        assert "energy" in result
        assert result["n_variables"] == 10

    def test_brute_force_returns_none_too_large(self):
        cp = _medium_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        result = ExactQUBOFormulation.brute_force_solve(terms, max_vars=20)
        assert result is None

    def test_brute_force_matches_greedy(self):
        cp = CoverageProblem.synthetic(n_tests=8, n_requirements=5, seed=3)
        qubo = ExactQUBOFormulation(cp, coverage_weight=10.0, cost_weight=1.0, coupling_weight=5.0)
        terms = qubo.qubo_terms()
        bf = ExactQUBOFormulation.brute_force_solve(terms, max_vars=25)
        assert bf is not None
        greedy_bits = [1] * 8
        greedy_energy = 0.0
        for var_name, coeff in terms["linear"].items():
            idx = qubo.variable_index(var_name)
            if idx < 8:
                val = greedy_bits[idx]
            else:
                val = 1
            greedy_energy += coeff * val
        for pair_str, coeff in terms["quadratic"].items():
            v1, v2 = pair_str.split("*")
            i1 = qubo.variable_index(v1)
            i2 = qubo.variable_index(v2)
            val1 = greedy_bits[i1] if i1 < 8 else 1
            val2 = greedy_bits[i2] if i2 < 8 else 1
            greedy_energy += coeff * val1 * val2
        greedy_energy += terms["offset"]
        assert bf["energy"] <= greedy_energy + 1e-6


class TestComputeQuboDensity:
    def test_density_zero_for_no_quadratic(self):
        terms = {
            "variables": ["x0", "x1"],
            "linear": {"x0": 1.0, "x1": -1.0},
            "quadratic": {},
        }
        assert compute_qubo_density(terms) == 0.0

    def test_density_full(self):
        terms = {
            "variables": ["x0", "x1", "x2"],
            "linear": {},
            "quadratic": {"x0*x1": 1.0, "x0*x2": 1.0, "x1*x2": 1.0},
        }
        assert compute_qubo_density(terms) == 1.0

    def test_density_partial(self):
        cp = _small_problem()
        qubo = ExactQUBOFormulation(cp)
        terms = qubo.qubo_terms()
        density = compute_qubo_density(terms)
        assert 0.0 < density < 1.0
