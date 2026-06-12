"""NSGA-III many-objective wrapper for test suite minimization.

Research context
-----------------
NSGA-III (Deb & Jain, 2014) extends NSGA-II to many-objective optimization
(4+ objectives) using reference-point-based selection instead of crowding
distance. This module provides a lightweight wrapper around pymoo NSGA-III
that integrates with CoverageProblem.objectives() via a pymoo Problem
formulation with 6 objectives:

  (minimize) -coverage_ratio     -> maximize coverage
  (minimize) -reduction_ratio    -> maximize reduction
  (minimize)  selected_count     -> minimize count
  (minimize)  total_cost         -> minimize cost
  (minimize)  uncovered_count    -> minimize uncovered
  (minimize) -fitness            -> maximize fitness

Related work
------------
- Deb, K. & Jain, H. "An Evolutionary Many-Objective Optimization Algorithm
  Using Reference-Point-Based Nondominated Sorting Approach, Part I: Solving
  Problems With Box Constraints", IEEE TEVC 18(4), 2014.
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Optional

import numpy as np

try:
    from pymoo.core.problem import Problem
    from pymoo.algorithms.moo.nsga3 import NSGA3
    from pymoo.optimize import minimize as pymoo_minimize
    from pymoo.util.ref_dirs import get_reference_directions
    HAS_PYMOO = True
except ImportError:
    HAS_PYMOO = False

from quantum_testing.problems.coverage import CoverageProblem


class CoverageProblemNSGA3:
    """Wrap pymoo NSGA-III for many-objective test suite minimization.

    Solves the 6-objective formulation derived from CoverageProblem.objectives()
    using reference-point-based many-objective selection (NSGA-III).

    Parameters
    ----------
    problem : CoverageProblem
        The coverage problem to optimize.
    n_partitions : int, optional
        Number of Das-Dennis reference-direction partitions.
        Automatically clamped to a feasible value for 6 objectives.
    pop_size : int, optional
        Population size (default 100, divisible by 4 per pymoo).
    seed : int, optional
        Random seed for reproducibility.

    Example
    -------
    >>> cp = CoverageProblem.synthetic(n_tests=30, n_requirements=20, seed=0)
    >>> solver = CoverageProblemNSGA3(cp, pop_size=80, seed=42)
    >>> result = solver.run(n_gen=50)
    >>> result["pareto_front"]
    """

    def __init__(
        self,
        problem: CoverageProblem,
        n_partitions: int = 8,
        pop_size: int = 100,
        seed: Optional[int] = None,
    ):
        if not HAS_PYMOO:
            raise ImportError(
                "pymoo is required for NSGA-III. Install with:\n"
                "  uv add pymoo"
            )
        self.problem = problem
        self.n_obj = 6
        self.pop_size = self._round_up_div4(pop_size)
        self.seed = seed
        self.n_gen = 0
        self._last_result = None
        max_partitions = min(n_partitions, 12)
        self.ref_dirs = get_reference_directions(
            "das-dennis", self.n_obj, n_partitions=max_partitions
        )
        if self.pop_size < len(self.ref_dirs):
            self.pop_size = self._round_up_div4(len(self.ref_dirs) + 4)

    @staticmethod
    def _round_up_div4(n: int) -> int:
        return n + (4 - n % 4) if n % 4 != 0 else n

    def run(
        self,
        n_gen: int = 100,
        verbose: bool = False,
    ) -> Dict:
        """Run NSGA-III on the coverage problem.

        Parameters
        ----------
        n_gen : int
            Number of generations.
        verbose : bool
            If True, print generation progress.

        Returns
        -------
        dict with keys:
            pareto_front : list[dict]
                Non-dominated solutions, each with solution/objectives/fitness.
            hypervolume : float or None
                Approximate hypervolume indicator.
            n_gen : int
                Generations executed.
            pop_size : int
                Population size used.
            ref_dirs_count : int
                Number of reference directions.
        """
        n_tests = self.problem.n_tests

        class _PymooProblem(Problem):
            def __init__(inner_self, rng=None):
                super().__init__(
                    n_var=n_tests,
                    n_obj=6,
                    n_constr=0,
                    xl=0.0,
                    xu=1.0,
                    type_var=np.float64,
                )

            def _evaluate(inner_self, X, out, *args, **kwargs):
                n_samp = X.shape[0]
                F = np.zeros((n_samp, 6))
                for idx in range(n_samp):
                    binary = (X[idx] > 0.5).astype(int).tolist()
                    obj = self.problem.objectives(binary)
                    F[idx, 0] = -obj["coverage_ratio"]
                    F[idx, 1] = -obj["reduction_ratio"]
                    F[idx, 2] = obj["selected_count"]
                    F[idx, 3] = obj["total_cost"]
                    F[idx, 4] = obj["uncovered_count"]
                    F[idx, 5] = -obj["fitness"]
                out["F"] = F

        problem = _PymooProblem()
        algorithm = NSGA3(
            pop_size=self.pop_size,
            ref_dirs=self.ref_dirs,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = pymoo_minimize(
                problem,
                algorithm,
                termination=("n_gen", n_gen),
                seed=self.seed,
                verbose=verbose,
                save_history=False,
            )

        self.n_gen = n_gen
        self._last_result = res

        pareto_solutions = []
        if res.X is not None and res.F is not None:
            for i in range(res.X.shape[0]):
                binary = (res.X[i] > 0.5).astype(int).tolist()
                obj = self.problem.objectives(binary)
                pareto_solutions.append({
                    "solution": binary,
                    "objectives": obj,
                    "fitness": obj["fitness"],
                })

        hypervolume = None
        if res.F is not None and res.F.shape[0] > 0:
            try:
                from pymoo.indicators.hv import Hypervolume
                ref_point = np.max(res.F, axis=0) * 1.1 + 1e-6
                hv = Hypervolume(ref_point=ref_point)
                hypervolume = float(hv.do(res.F))
            except Exception:
                hypervolume = None

        return {
            "pareto_front": pareto_solutions,
            "hypervolume": hypervolume,
            "n_gen": n_gen,
            "pop_size": self.pop_size,
            "ref_dirs_count": len(self.ref_dirs),
        }


def select_best_from_pareto(
    pareto_solutions: List[Dict],
    weight_coverage: float = 0.4,
    weight_reduction: float = 0.3,
    weight_cost: float = 0.3,
) -> Dict:
    """Select a single best solution from the Pareto front using weighted scalarization.

    Parameters
    ----------
    pareto_solutions : list[dict]
        Output from CoverageProblemNSGA3.run()["pareto_front"].
    weight_coverage : float
        Weight on coverage_ratio.
    weight_reduction : float
        Weight on reduction_ratio.
    weight_cost : float
        Weight on cost efficiency.

    Returns
    -------
    dict
        The selected solution with keys solution/objectives/fitness.
    """
    if not pareto_solutions:
        raise ValueError("pareto_solutions is empty")

    covs = [s["objectives"]["coverage_ratio"] for s in pareto_solutions]
    reds = [s["objectives"]["reduction_ratio"] for s in pareto_solutions]
    counts = [s["objectives"]["selected_count"] for s in pareto_solutions]
    costs = [s["objectives"]["total_cost"] for s in pareto_solutions]

    def norm(vals):
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-12:
            return [0.5] * len(vals)
        return [(v - lo) / (hi - lo) for v in vals]

    n_cov = norm(covs)
    n_red = norm(reds)
    n_cnt = [1.0 - v for v in norm(counts)]
    n_cst = [1.0 - v for v in norm(costs)]

    best_score = -1.0
    best_idx = 0
    for i in range(len(pareto_solutions)):
        score = (
            weight_coverage * n_cov[i]
            + weight_reduction * n_red[i]
            + weight_cost * (n_cnt[i] + n_cst[i]) / 2.0
        )
        if score > best_score:
            best_score = score
            best_idx = i

    return pareto_solutions[best_idx]
