"""Exact set-cover QUBO formulation with auxiliary OR variables.

Research context
-----------------
The exact set-cover QUBO uses auxiliary variables y_j for each requirement j
to encode the OR constraint: y_j = OR_{i covers j} x_i.

The formulation is:
    H = A * sum_j (1 - y_j)^2 + B * sum_i cost_i * x_i
        + C * sum_{(i,j) in covers} (x_i - y_j)^2

Expanding:
    H = A * sum_j (1 - 2*y_j + y_j^2)
        + B * sum_i cost_i * x_i
        + C * sum_{(i,j)} (x_i^2 - 2*x_i*y_j + y_j^2)

Since x_i, y_j are binary: x_i^2 = x_i, y_j^2 = y_j.

This is the EXACT formulation (not the surrogate overlap penalty), suitable
for QAOA, quantum annealing, or exact brute-force on small instances.

Related work
------------
- Trovato et al., "Reformulating Regression Test Suite Optimization using
  Quantum Annealing -- an Empirical Study", arXiv:2411.15963v2 (2025).
- Lucas, "Ising formulations of many NP problems", Frontiers in Physics, 2014.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from quantum_testing.problems.coverage import CoverageProblem


class ExactQUBOFormulation:
    """Exact set-cover QUBO with auxiliary OR variables.

    Variables:
        x_0 ... x_{n_tests-1}  (test selection)
        y_0 ... y_{n_req-1}    (requirement covered indicator)

    Objective (minimize):
        H = A * sum_j (1 - y_j)^2
            + B * sum_i (cost_i / max_cost) * x_i
            + C * sum_{(i,j) in covers} (x_i - y_j)^2

    Parameters
    ----------
    problem : CoverageProblem
        The coverage problem to encode.
    coverage_weight : float
        Penalty for uncovered requirements (default 10.0).
    cost_weight : float
        Weight on test cost (default 1.0).
    coupling_weight : float
        Weight on x_i <-> y_j coupling (default 5.0).
    """

    def __init__(
        self,
        problem: CoverageProblem,
        coverage_weight: float = 10.0,
        cost_weight: float = 1.0,
        coupling_weight: float = 5.0,
    ):
        self.problem = problem
        self.A = coverage_weight
        self.B = cost_weight
        self.C = coupling_weight
        self.n_x = problem.n_tests
        self.n_y = problem.n_requirements
        self.n_vars = self.n_x + self.n_y

    def variable_name(self, idx: int) -> str:
        """Return variable name for index idx."""
        if idx < self.n_x:
            return f"x{idx}"
        return f"y{idx - self.n_x}"

    def variable_index(self, name: str) -> int:
        """Return variable index for variable name."""
        if name.startswith("x"):
            return int(name[1:])
        elif name.startswith("y"):
            return self.n_x + int(name[1:])
        raise ValueError(f"Unknown variable: {name}")

    def _build_terms(self) -> Tuple[Dict[str, float], Dict[str, float], float]:
        """Build linear, quadratic, and offset terms."""
        linear: Dict[str, float] = {}
        quadratic: Dict[Tuple[str, str], float] = {}
        offset = 0.0

        # Term 1: A * sum_j (1 - y_j)^2
        # Since y_j in {0,1}, y_j^2 = y_j, so (1-y_j)^2 = 1 - 2*y_j + y_j = 1 - y_j
        # Linear: y_j -> -A, offset: +A per requirement
        for j in range(self.n_y):
            y_name = f"y{j}"
            linear[y_name] = linear.get(y_name, 0.0) - self.A
        offset += self.A * self.n_y

        # Term 2: B * sum_i (cost_i / max_cost) * x_i
        max_cost = sum(self.problem.costs) or 1.0
        for i in range(self.n_x):
            x_name = f"x{i}"
            linear[x_name] = linear.get(x_name, 0.0) + self.B * (
                self.problem.costs[i] / max_cost
            )

        # Term 3: C * sum_{(i,j) in covers} (x_i - y_j)^2
        # = C * sum (x_i - 2*x_i*y_j + y_j)  [binary: x^2=x, y^2=y]
        for i in range(self.n_x):
            for j in self.problem.coverage_sets[i]:
                if j >= self.n_y:
                    continue
                x_name = f"x{i}"
                y_name = f"y{j}"
                linear[x_name] = linear.get(x_name, 0.0) + self.C
                linear[y_name] = linear.get(y_name, 0.0) + self.C
                key = tuple(sorted([x_name, y_name]))
                quadratic[key] = quadratic.get(key, 0.0) - 2.0 * self.C

        return linear, quadratic, offset

    def qubo_terms(self) -> Dict:
        """Export exact set-cover QUBO.

        Returns
        -------
        dict with keys: linear, quadratic, offset, sense, variables, metadata.
        """
        linear, quadratic, offset = self._build_terms()
        variables = [self.variable_name(i) for i in range(self.n_vars)]

        quad_str = {}
        for (v1, v2), val in quadratic.items():
            key = f"{v1}*{v2}"
            quad_str[key] = quad_str.get(key, 0.0) + val

        return {
            "linear": linear,
            "quadratic": quad_str,
            "offset": offset,
            "sense": "minimize",
            "variables": variables,
            "metadata": {
                "n_tests": self.n_x,
                "n_requirements": self.n_y,
                "n_total_vars": self.n_vars,
                "coverage_weight": self.A,
                "cost_weight": self.B,
                "coupling_weight": self.C,
                "formulation": "exact_set_cover_with_or_auxiliaries",
                "note": "y_j = OR_{i covers j} x_i via penalty",
            },
        }

    def decode_solution(self, qubo_solution: Dict[str, int]) -> List[int]:
        """Extract test selection from QUBO solution (drop y variables)."""
        return [qubo_solution.get(f"x{i}", 0) for i in range(self.n_x)]

    @staticmethod
    def brute_force_solve(
        qubo_terms: Dict,
        max_vars: int = 25,
    ) -> Optional[Dict]:
        """Brute-force solve a QUBO by enumerating all 2^n assignments.

        Only feasible for small instances (n <= ~25).

        Parameters
        ----------
        qubo_terms : dict
            Output from qubo_terms().
        max_vars : int
            Maximum variables for brute-force.

        Returns
        -------
        dict or None
            Best assignment and energy, or None if too large.
        """
        variables = qubo_terms["variables"]
        n = len(variables)
        if n > max_vars:
            return None

        var_idx = {v: i for i, v in enumerate(variables)}
        linear = qubo_terms["linear"]
        quadratic = qubo_terms["quadratic"]
        offset = qubo_terms["offset"]

        best_energy = float("inf")
        best_bits = None

        for assignment in range(2 ** n):
            bits = [(assignment >> i) & 1 for i in range(n)]
            energy = offset
            for var_name, coeff in linear.items():
                energy += coeff * bits[var_idx[var_name]]
            for pair_str, coeff in quadratic.items():
                v1, v2 = pair_str.split("*")
                energy += coeff * bits[var_idx[v1]] * bits[var_idx[v2]]
            if energy < best_energy:
                best_energy = energy
                best_bits = bits

        best_assignment = {variables[i]: best_bits[i] for i in range(n)}
        return {
            "assignment": best_assignment,
            "energy": best_energy,
            "n_variables": n,
        }


def compute_qubo_density(terms: Dict) -> float:
    """Compute density of non-zero quadratic terms in a QUBO."""
    variables = terms["variables"]
    n = len(variables)
    max_pairs = n * (n - 1) // 2
    if max_pairs == 0:
        return 0.0
    n_nonzero = len(terms["quadratic"])
    return n_nonzero / max_pairs
