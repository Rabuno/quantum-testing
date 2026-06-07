"""Tests for quantum_testing.multiobjective."""
from __future__ import annotations

import json

import pytest

from quantum_testing.multiobjective import (
    dominates,
    objective_vector,
    pareto_front,
    weighted_tchebycheff,
)


def test_objective_vector_returns_six_tuple():
    v = objective_vector(
        coverage_ratio=0.9,
        reduction_ratio=0.5,
        selected_count=4,
        total_cost=7.5,
        uncovered_count=2,
        fitness=0.7,
    )
    assert len(v) == 6
    assert v == (0.9, 0.5, 4.0, 7.5, 2.0, 0.7)
    # All elements are JSON-serializable floats.
    json.dumps(list(v))


def test_dominates_basic_maximize():
    maximize = [True, True]
    # a is better on both objectives -> dominates b.
    assert dominates([0.9, 0.8], [0.5, 0.5], maximize) is True
    # a worse on first, better on second -> no domination.
    assert dominates([0.4, 0.9], [0.5, 0.5], maximize) is False
    # equal on both -> no domination (not strictly better anywhere).
    assert dominates([0.5, 0.5], [0.5, 0.5], maximize) is False


def test_dominates_mixed_maximize_minimize():
    # objectives: coverage(max), selected_count(min)
    maximize = [True, False]
    a = [1.0, 2.0]  # full coverage, cheap
    b = [0.5, 5.0]  # partial coverage, expensive
    c = [1.0, 5.0]  # full coverage, expensive

    assert dominates(a, b, maximize) is True
    assert dominates(b, a, maximize) is False
    # a and c tie on coverage but a is cheaper -> a dominates c.
    assert dominates(a, c, maximize) is True
    # c does not dominate a because it's more expensive.
    assert dominates(c, a, maximize) is False


def test_dominates_length_mismatch_raises():
    with pytest.raises(ValueError):
        dominates([1.0, 2.0], [1.0], [True, False])


def test_pareto_front_filters_dominated():
    items = [
        {"id": "a", "v": [1.0, 1.0]},
        {"id": "b", "v": [0.5, 0.5]},
        {"id": "c", "v": [0.9, 0.9]},
    ]
    maximize = [True, True]
    front = pareto_front(items, key=lambda d: d["v"], maximize=maximize)
    ids = [d["id"] for d in front]
    assert ids == ["a"]


def test_pareto_front_preserves_input_order():
    items = [
        {"id": "x", "v": [0.8, 0.8]},
        {"id": "y", "v": [0.9, 0.5]},
        {"id": "z", "v": [0.5, 0.9]},
    ]
    maximize = [True, True]
    front = pareto_front(items, key=lambda d: d["v"], maximize=maximize)
    ids = [d["id"] for d in front]
    # y and z are nondominated wrt each other; x is dominated by neither but
    # also does not dominate the others (it's worse on both axes than neither
    # y nor z individually, but not strictly worse than *every* other point on
    # *every* axis). x is nondominated because no single item beats it on all.
    assert set(ids) == {"x", "y", "z"}
    # Relative order matches input.
    assert ids == ["x", "y", "z"]


def test_pareto_front_mixed_max_min():
    # coverage(max), cost(min)
    items = [
        {"id": "a", "v": [1.0, 5.0]},
        {"id": "b", "v": [0.5, 2.0]},
        {"id": "c", "v": [0.9, 2.0]},
    ]
    maximize = [True, False]
    front = pareto_front(items, key=lambda d: d["v"], maximize=maximize)
    ids = [d["id"] for d in front]
    # b is dominated by c (same cost, higher coverage). a and c trade coverage
    # against cost, so both remain nondominated.
    assert ids == ["a", "c"]


def test_weighted_tchebycheff_scalarizes():
    maximize = [True, False]
    ideal = [1.0, 0.0]
    weights = [0.5, 0.5]

    # At the ideal -> 0 distance.
    assert weighted_tchebycheff([1.0, 0.0], weights, ideal, maximize) == 0.0

    # Worse on both.
    s = weighted_tchebycheff([0.5, 3.0], weights, ideal, maximize)
    assert s > 0.0

    # Equal weights, so worst-axis distance is max(0.5*0.5, 0.5*3.0) = 1.5.
    assert s == pytest.approx(1.5)


def test_weighted_tchebycheff_rejects_bad_weights():
    with pytest.raises(ValueError):
        weighted_tchebycheff([1.0], [-1.0], [0.0], [True])
    with pytest.raises(ValueError):
        weighted_tchebycheff([1.0], [0.0], [0.0], [True])
