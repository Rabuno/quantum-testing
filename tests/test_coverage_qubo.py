"""Tests for CoverageProblem.objectives() and CoverageProblem.qubo_terms()."""
from __future__ import annotations

import json

from quantum_testing.problems.coverage import CoverageProblem


def _problem():
    return CoverageProblem.synthetic(15, 10, seed=1)


def test_objectives_returns_expected_keys():
    problem = _problem()
    sol = [1] * problem.n_tests
    obj = problem.objectives(sol)
    expected_keys = {
        "coverage_ratio",
        "reduction_ratio",
        "selected_count",
        "total_cost",
        "uncovered_count",
        "fitness",
    }
    assert set(obj.keys()) == expected_keys


def test_objectives_values_are_json_serializable():
    problem = _problem()
    sol = [0] * problem.n_tests
    obj = problem.objectives(sol)
    payload = json.dumps(obj)
    restored = json.loads(payload)
    assert set(restored.keys()) == set(obj.keys())


def test_objectives_consistent_with_report():
    problem = _problem()
    sol = [1 if i % 2 == 0 else 0 for i in range(problem.n_tests)]
    obj = problem.objectives(sol)
    rep = problem.report(sol)
    assert obj["coverage_ratio"] == rep.coverage_ratio
    assert obj["reduction_ratio"] == rep.reduction_ratio
    assert obj["selected_count"] == float(rep.selected_count)
    assert obj["total_cost"] == rep.total_cost
    assert obj["fitness"] == rep.fitness


def test_objectives_uncovered_count_non_negative():
    problem = _problem()
    obj = problem.objectives([0] * problem.n_tests)
    assert obj["uncovered_count"] == float(problem.n_requirements)
    full = problem.objectives([1] * problem.n_tests)
    assert full["uncovered_count"] >= 0.0


def test_qubo_terms_structure():
    problem = _problem()
    terms = problem.qubo_terms()
    assert set(terms.keys()) == {
        "linear",
        "quadratic",
        "offset",
        "sense",
        "variables",
        "metadata",
    }
    assert terms["sense"] == "minimize"
    assert terms["offset"] == 0.0
    assert terms["variables"] == [f"x{i}" for i in range(problem.n_tests)]
    assert set(terms["linear"].keys()) == {f"x{i}" for i in range(problem.n_tests)}


def test_qubo_terms_json_serializable():
    problem = _problem()
    terms = problem.qubo_terms()
    # Must round-trip through JSON.
    restored = json.loads(json.dumps(terms))
    assert restored["sense"] == "minimize"
    assert restored["variables"] == terms["variables"]


def test_quadratic_keys_use_overlap_representation():
    problem = _problem()
    terms = problem.qubo_terms()
    # Every quadratic key should be of the form "xI*xJ" with I < J.
    for key in terms["quadratic"]:
        assert "*" in key
        left, right = key.split("*", 1)
        assert left.startswith("x") and right.startswith("x")
        i = int(left[1:])
        j = int(right[1:])
        assert 0 <= i < j < problem.n_tests
        # And the coefficient must be positive (overlap penalty).
        assert terms["quadratic"][key] >= 0.0


def test_qubo_terms_metadata_contains_weights():
    problem = _problem()
    terms = problem.qubo_terms(uncovered_weight=3.5, cost_weight=0.25)
    md = terms["metadata"]
    assert md["uncovered_weight"] == 3.5
    assert md["cost_weight"] == 0.25
    assert "note" in md


def test_report_to_dict_unchanged_shape():
    """Ensure report().to_dict() still exposes the original fields."""
    problem = _problem()
    sol = [0, 1] + [0] * (problem.n_tests - 2)
    d = problem.report(sol).to_dict()
    for key in (
        "selected_tests",
        "selected_count",
        "total_tests",
        "covered_requirements",
        "total_requirements",
        "coverage_ratio",
        "reduction_ratio",
        "total_cost",
        "fitness",
    ):
        assert key in d
