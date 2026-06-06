"""Baseline algorithms for comparison with QIEA.

Provides simple optimization baselines: random search, greedy set-cover, and classical GA.
"""

import math
from typing import Callable, List, Optional, Set, Tuple
import numpy as np


class RandomSearch:
    """Random search baseline for binary optimization.

    Randomly samples binary strings repeatedly and returns the best found.
    """

    def __init__(
        self,
        n_bits: int,
        max_evals: int,
        evaluate_fn: Callable[[List[int]], float],
        seed: Optional[int] = None,
    ):
        """Initialize random search.

        Args:
            n_bits: Number of binary variables.
            max_evals: Maximum number of evaluations.
            evaluate_fn: Fitness evaluation function.
            seed: Random seed for reproducibility.
        """
        self.n_bits = n_bits
        self.max_evals = max_evals
        self.evaluate_fn = evaluate_fn
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def run(self, verbose: bool = True) -> Tuple[List[int], float, List[float]]:
        """Run random search.

        Returns:
            Tuple of (best_solution, best_fitness, history).
        """
        best_solution: Optional[List[int]] = None
        best_fitness = float('-inf')
        history: List[float] = []

        if verbose:
            print(f"RandomSearch: {self.n_bits} bits, {self.max_evals} evaluations")

        for i in range(self.max_evals):
            # Random binary solution
            solution = [int(self._rng.random() < 0.5) for _ in range(self.n_bits)]
            fitness = self.evaluate_fn(solution)

            if fitness > best_fitness:
                best_fitness = fitness
                best_solution = solution.copy()

            history.append(best_fitness)

            if verbose and i % max(1, self.max_evals // 10) == 0:
                print(f"  Eval {i:5d} | Best fitness: {best_fitness:.4f}")

        if verbose:
            print(f"Done! Best fitness: {best_fitness:.4f}")

        return best_solution, best_fitness, history


class GreedySetCover:
    """Greedy set-cover baseline for test suite minimization.

    Iteratively selects the test case that covers the most uncovered requirements.
    """

    def __init__(
        self,
        coverage_matrix: List[Set[int]],
        seed: Optional[int] = None,
    ):
        """Initialize greedy set-cover.

        Args:
            coverage_matrix: List where coverage_matrix[i] is set of requirements covered by test i.
            seed: Random seed (used for deterministic tie-breaking).
        """
        self.coverage_matrix = coverage_matrix
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def run(self, verbose: bool = True) -> Tuple[List[int], int, Set[int]]:
        """Run greedy set-cover to find minimum test subset covering all requirements.

        Returns:
            Tuple of (selected_indices, num_selected, covered_requirements).
        """
        n_tests = len(self.coverage_matrix)
        all_requirements: Set[int] = set()
        for cov in self.coverage_matrix:
            all_requirements |= cov

        if not all_requirements:
            return [], 0, set()

        selected: List[int] = []
        covered: Set[int] = set()
        remaining = set(range(n_tests))

        if verbose:
            print(f"GreedySetCover: {n_tests} tests, {len(all_requirements)} requirements")

        while covered != all_requirements and remaining:
            # Find test covering most uncovered requirements
            best_test = None
            best_gain = -1

            # Sort for deterministic tie-breaking
            candidates = list(remaining)
            # Use deterministic shuffle if seed provided
            if self.seed is not None:
                self._rng.shuffle(candidates)

            for test_idx in candidates:
                gain = len(self.coverage_matrix[test_idx] - covered)
                if gain > best_gain:
                    best_gain = gain
                    best_test = test_idx

            if best_test is not None:
                selected.append(best_test)
                covered |= self.coverage_matrix[best_test]
                remaining.remove(best_test)

                if verbose:
                    print(f"  Selected test {best_test}, covered {len(covered)}/{len(all_requirements)}")

        return selected, len(selected), covered


class SimpleGA:
    """Simple Genetic Algorithm baseline for binary optimization.

    Tournament selection, single-point crossover, bit-flip mutation.
    """

    def __init__(
        self,
        n_bits: int,
        pop_size: int,
        max_gen: int,
        evaluate_fn: Callable[[List[int]], float],
        mutation_rate: float = 0.05,
        seed: Optional[int] = None,
    ):
        """Initialize Simple GA.

        Args:
            n_bits: Number of binary variables.
            pop_size: Population size.
            max_gen: Maximum generations.
            evaluate_fn: Fitness evaluation function.
            mutation_rate: Per-bit mutation probability.
            seed: Random seed for reproducibility.
        """
        self.n_bits = n_bits
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.evaluate_fn = evaluate_fn
        self.mutation_rate = mutation_rate
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def run(self, verbose: bool = True) -> Tuple[List[int], float, List[float]]:
        """Run simple GA.

        Returns:
            Tuple of (best_solution, best_fitness, history).
        """
        # Initialize random binary population
        pop = [[int(self._rng.random() < 0.5) for _ in range(self.n_bits)]
               for _ in range(self.pop_size)]

        best_sol: Optional[List[int]] = None
        best_fit = float('-inf')
        history: List[float] = []

        if verbose:
            print(f"SimpleGA: {self.n_bits} bits, {self.pop_size} pop, {self.max_gen} gen")

        for gen in range(self.max_gen):
            # Evaluate population
            fits = [self.evaluate_fn(ind) for ind in pop]

            # Track best
            gen_best_idx = int(np.argmax(fits))
            if fits[gen_best_idx] > best_fit:
                best_fit = fits[gen_best_idx]
                best_sol = pop[gen_best_idx].copy()

            history.append(best_fit)

            if verbose and gen % 10 == 0:
                avg_fit = float(np.mean(fits))
                print(f"Gen {gen:4d} | Best: {best_fit:.4f} | Avg: {avg_fit:.4f}")

            # Tournament selection
            new_pop: List[List[int]] = []
            for _ in range(self.pop_size):
                # Tournament of 3
                indices = list(self._rng.choice(self.pop_size, size=3, replace=False))
                winner_idx = max(indices, key=lambda i: fits[i])
                new_pop.append(pop[winner_idx].copy())

            # Crossover (single-point)
            pop = []
            for i in range(0, self.pop_size, 2):
                p1 = new_pop[i]
                p2 = new_pop[(i + 1) % self.pop_size]
                point = int(self._rng.integers(1, self.n_bits))
                c1 = p1[:point] + p2[point:]
                c2 = p2[:point] + p1[point:]
                pop.extend([c1, c2])

            # Mutation
            for ind in pop:
                for j in range(self.n_bits):
                    if self._rng.random() < self.mutation_rate:
                        ind[j] = 1 - ind[j]

        if verbose:
            print(f"Done! Best fitness: {best_fit:.4f}")

        return best_sol, best_fit, history


class SimulatedAnnealing:
    """Binary simulated annealing baseline for QUBO-style minimization.

    The optimizer minimizes an energy function. It is useful as a classical
    counterpart to QUBO/QAOA/quantum-annealing formulations without requiring
    quantum SDKs or hardware.
    """

    def __init__(
        self,
        n_bits: int,
        energy_fn: Callable[[List[int]], float],
        max_steps: int = 2000,
        start_temp: float = 2.0,
        end_temp: float = 0.01,
        seed: Optional[int] = None,
    ):
        self.n_bits = n_bits
        self.energy_fn = energy_fn
        self.max_steps = max_steps
        self.start_temp = start_temp
        self.end_temp = end_temp
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def run(self, verbose: bool = True) -> Tuple[List[int], float, List[float]]:
        current = [int(self._rng.random() < 0.5) for _ in range(self.n_bits)]
        current_energy = self.energy_fn(current)
        best = current.copy()
        best_energy = current_energy
        history: List[float] = []

        for step in range(self.max_steps):
            frac = step / max(1, self.max_steps - 1)
            temp = self.start_temp * ((self.end_temp / self.start_temp) ** frac)
            candidate = current.copy()
            bit = int(self._rng.integers(0, self.n_bits))
            candidate[bit] = 1 - candidate[bit]
            candidate_energy = self.energy_fn(candidate)
            delta = candidate_energy - current_energy
            if delta <= 0 or self._rng.random() < math.exp(-delta / max(temp, 1e-12)):
                current = candidate
                current_energy = candidate_energy
                if current_energy < best_energy:
                    best = current.copy()
                    best_energy = current_energy
            history.append(best_energy)
            if verbose and step % max(1, self.max_steps // 10) == 0:
                print(f"Step {step:5d} | Best energy: {best_energy:.4f} | Temp: {temp:.4f}")

        return best, best_energy, history