"""Multi-objective helpers for test-suite optimization.

Research context
-----------------
Classical test-suite minimization collapses coverage, cost/time, and fault
detection into a single scalar fitness too early, hiding tradeoffs between
objectives. Multi-objective / Pareto formulations keep these tradeoffs
explicit and let practitioners choose a preferred compromise *after* seeing
the nondominated frontier.

This module provides small, stdlib-only helpers used by the coverage problem
and CLI to report and filter candidate suites along several objectives:

- maximize ``coverage_ratio`` (fault-detection potential)
- maximize ``reduction_ratio`` (suite-size reduction)
- minimize ``total_cost`` / ``selected_count`` (execution cost)

Related work
------------
- Trovato et al., "Reformulating Regression Test Suite Optimization using
  Quantum Annealing -- an Empirical Study", arXiv:2411.15963v2 (2025).
  Frames regression test selection as quantum annealing and proposes
  SelectQA, emphasizing QUBO/annealing formulations and empirical comparison
  against prior quantum approaches on test-suite optimization.
- Bandarupalli, "The Impact of Software Testing with Quantum Optimization
  Meets Machine Learning", arXiv:2506.02090v1 (2025). Emphasizes hybrid
  quantum-optimization + ML for test case prioritization in CI/CD, with
  Defects4J validation, defect detection efficiency, execution-time reduction,
  and interpretability.
- BQTmizer / "Test Case Minimization with Quantum Annealers" (ACM/SSBSE
  tool line). Reinforces QUBO exports and minimization with quantum annealers.
- Multi-objective / Pareto optimization is a standard way to avoid collapsing
  coverage, cost/time, and fault-detection into one opaque scalar too early.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Sequence, Tuple


# ---------------------------------------------------------------------------
# Objective vector
# ---------------------------------------------------------------------------

def objective_vector(
    values: dict | None = None,
    *,
    coverage_ratio: float | None = None,
    reduction_ratio: float | None = None,
    selected_count: int | None = None,
    total_cost: float | None = None,
    uncovered_count: int | None = None,
    fitness: float | None = None,
) -> Tuple[float, float, float, float, float, float]:
    """Return a 6-dimensional objective vector for a candidate suite.

    The canonical ordering is::

        (coverage_ratio, reduction_ratio, selected_count,
         total_cost, uncovered_count, fitness)

    Callers may pass a mapping with those keys (for reports/CLI records) or
    explicit keyword arguments. The ordering is chosen so that callers can mix
    maximize/minimize objectives uniformly via the ``maximize`` list passed to
    :func:`dominates` / :func:`pareto_front`.

    Parameters
    ----------
    coverage_ratio:
        Fraction of requirements covered by the selected tests. Higher is
        better (maximize).
    reduction_ratio:
        Fraction of tests removed from the full suite. Higher is better
        (maximize).
    selected_count:
        Number of selected tests. Lower is better (minimize).
    total_cost:
        Sum of per-test costs for the selected tests. Lower is better
        (minimize).
    uncovered_count:
        Number of requirements not covered. Lower is better (minimize).
    fitness:
        Scalar fitness from :meth:`CoverageProblem.fitness`. Higher is
        better (maximize).
    """
    if values is not None:
        coverage_ratio = values["coverage_ratio"] if coverage_ratio is None else coverage_ratio
        reduction_ratio = values["reduction_ratio"] if reduction_ratio is None else reduction_ratio
        selected_count = values["selected_count"] if selected_count is None else selected_count
        total_cost = values["total_cost"] if total_cost is None else total_cost
        uncovered_count = values["uncovered_count"] if uncovered_count is None else uncovered_count
        fitness = values["fitness"] if fitness is None else fitness

    required = {
        "coverage_ratio": coverage_ratio,
        "reduction_ratio": reduction_ratio,
        "selected_count": selected_count,
        "total_cost": total_cost,
        "uncovered_count": uncovered_count,
        "fitness": fitness,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(f"missing objective values: {', '.join(missing)}")

    return (
        float(coverage_ratio),
        float(reduction_ratio),
        float(selected_count),
        float(total_cost),
        float(uncovered_count),
        float(fitness),
    )


# ---------------------------------------------------------------------------
# Pareto dominance
# ---------------------------------------------------------------------------

def dominates(
    a: Sequence[float],
    b: Sequence[float],
    maximize: Sequence[bool],
) -> bool:
    """Return True iff solution ``a`` Pareto-dominates solution ``b``.

    ``a`` dominates ``b`` when it is no worse than ``b`` on every objective
    and strictly better on at least one. Objectives listed in ``maximize``
    are treated as "higher is better"; the rest are treated as "lower is
    better".

    Parameters
    ----------
    a, b:
        Objective vectors of equal length.
    maximize:
        Boolean mask of the same length; ``True`` means the corresponding
        objective is maximized.

    Notes
    -----
    This is the standard weak Pareto-dominance relation used in
    multi-objective evolutionary optimization (see e.g. Deb, *Multi-Objective
    Optimization using Evolutionary Algorithms*, 2001).
    """
    if len(a) != len(b) or len(a) != len(maximize):
        raise ValueError("a, b, and maximize must have the same length")

    at_least_one_strict = False
    for ai, bi, mx in zip(a, b, maximize):
        if mx:
            if ai < bi:
                return False
            if ai > bi:
                at_least_one_strict = True
        else:
            if ai > bi:
                return False
            if ai < bi:
                at_least_one_strict = True
    return at_least_one_strict


# ---------------------------------------------------------------------------
# Pareto front
# ---------------------------------------------------------------------------

def pareto_front(
    items: Iterable[dict],
    key: Callable[[dict], Sequence[float]],
    maximize: Sequence[bool],
) -> List[dict]:
    """Return the nondominated subset of ``items``, preserving input order.

    Each item is a dict (e.g. a coverage report). ``key`` extracts the
    objective vector from the dict. The returned list contains only items
    that are not dominated by any other item in the input, in the same
    relative order they appeared.

    This is a simple O(n^2) filter suitable for the small candidate sets
    produced by the CLI sampling commands. For large populations a
    fast non-dominated sort (NSGA-II style) would be preferable.
    """
    collected: List[Tuple[dict, Sequence[float]]] = []
    for item in items:
        vec = key(item)
        if len(vec) != len(maximize):
            raise ValueError(
                f"objective vector length {len(vec)} != maximize length {len(maximize)}"
            )
        collected.append((item, vec))

    nondominated: List[dict] = []
    for i, (item_i, vec_i) in enumerate(collected):
        dominated = False
        for j, (_, vec_j) in enumerate(collected):
            if i == j:
                continue
            if dominates(vec_j, vec_i, maximize):
                dominated = True
                break
        if not dominated:
            nondominated.append(item_i)
    return nondominated


# ---------------------------------------------------------------------------
# Scalarization helper
# ---------------------------------------------------------------------------

def weighted_tchebycheff(
    vector: Sequence[float],
    weights: Sequence[float],
    ideal: Sequence[float],
    maximize: Sequence[bool],
) -> float:
    """Weighted Tchebycheff scalarization of a multi-objective vector.

    Returns a scalar "distance" from the ``ideal`` point; lower is better.
    ``weights`` must be non-negative and sum to a positive value. Objectives
    marked in ``maximize`` are negated internally so that the function
    always measures distance in "lower is better" space.

    The Tchebycheff scalarization is standard in multi-objective optimization
    because it can reach every point on a convex Pareto front (Miettinen,
    *Nonlinear Multiobjective Optimization*, 1998).
    """
    if not (len(vector) == len(weights) == len(ideal) == len(maximize)):
        raise ValueError("vector, weights, ideal, maximize must have the same length")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    total_w = sum(weights)
    if total_w <= 0:
        raise ValueError("weights must sum to a positive value")

    worst = 0.0
    for vi, wi, ii, mx in zip(vector, weights, ideal, maximize):
        # Normalize to "lower is better" space.
        delta = (vi - ii) if not mx else (ii - vi)
        worst = max(worst, wi * delta)
    return worst
