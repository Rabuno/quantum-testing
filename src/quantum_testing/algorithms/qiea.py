"""Quantum-inspired Evolutionary Algorithm (QIEA) implementation.

This module provides a robust binary QIEA class with proper qubit representation,
quantum rotation gates, and population-based updates.
"""

import math
from typing import Callable, List, Optional, Tuple
import numpy as np


class QIEA:
    """Quantum-inspired Evolutionary Algorithm for binary optimization.

    Uses qubit representation (α, β) instead of classical binary strings:
    - |ψ⟩ = α|0⟩ + β|1⟩ with |α|² + |β|² = 1
    - Observation (collapse) → binary solution
    - Quantum rotation gate updates qubits toward better solutions

    Attributes:
        n_qubits: Number of binary variables (qubit count).
        pop_size: Number of quantum individuals in population.
        max_gen: Maximum number of generations.
        rotation_angle: Base rotation angle for quantum gates (radians).
        evaluate_fn: Fitness evaluation function.
        seed: Random seed for reproducibility.
    """

    def __init__(
        self,
        n_qubits: int,
        pop_size: int,
        max_gen: int,
        rotation_angle: float = 0.01 * math.pi,
        evaluate_fn: Optional[Callable[[List[int]], float]] = None,
        seed: Optional[int] = None,
    ):
        """Initialize QIEA.

        Args:
            n_qubits: Number of binary variables (qubit count).
            pop_size: Number of quantum individuals in population.
            max_gen: Maximum number of generations.
            rotation_angle: Base rotation angle for quantum gates (radians).
            evaluate_fn: Fitness evaluation function.
            seed: Random seed for reproducibility.
        """
        self.n_qubits = n_qubits
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.rotation_angle = rotation_angle
        self.evaluate_fn = evaluate_fn
        self.seed = seed

        # Set random seeds for reproducibility
        self._rng = np.random.default_rng(seed)
        self._py_rng = np.random.default_rng(seed)

        # Initialize quantum population: each individual is a list of [alpha, beta] pairs
        # Alpha = 1/sqrt(2) → equal superposition
        self.population: List[List[List[float]]] = self._init_population()

        # Best solution tracking
        self.best_solution: Optional[List[int]] = None
        self.best_fitness = float('-inf')
        self.history: List[float] = []

    def _init_population(self) -> List[List[List[float]]]:
        """Initialize qubits in equal superposition state.

        Returns:
            Population of individuals, each containing qubit pairs [alpha, beta].
        """
        pop = []
        alpha = 1.0 / math.sqrt(2)
        beta = 1.0 / math.sqrt(2)

        for _ in range(self.pop_size):
            individual = [[alpha, beta] for _ in range(self.n_qubits)]
            pop.append(individual)
        return pop

    def observe(self, individual: List[List[float]], rng: Optional[np.random.Generator] = None) -> List[int]:
        """Collapse quantum state to binary string via observation.

        Args:
            individual: Qubit representation [[alpha, beta], ...].
            rng: Optional random generator for reproducibility.

        Returns:
            Binary string [0, 1, ...] where P(1) = |β|².
        """
        if rng is None:
            rng = self._rng

        binary = []
        for alpha, beta in individual:
            # P(1) = |β|²
            prob_1 = beta ** 2
            binary.append(1 if rng.random() < prob_1 else 0)
        return binary

    def _quantum_rotate_single(
        self,
        alpha: float,
        beta: float,
        x_i: int,
        b_i: int,
        fitness_diff: float,
    ) -> Tuple[float, float]:
        """Apply quantum rotation gate to a single qubit.

        Rotation moves the qubit state toward the better solution bit.

        Args:
            alpha: Current alpha amplitude.
            beta: Current beta amplitude.
            x_i: Current solution bit (0 or 1).
            b_i: Best solution bit (0 or 1).
            fitness_diff: Normalized fitness difference for adaptive rotation.

        Returns:
            Tuple of (new_alpha, new_beta) after rotation and normalization.
        """
        # Adaptive rotation angle based on fitness difference
        delta_theta = self.rotation_angle * (1.0 + fitness_diff)

        # Apply rotation gate:
        # R(Δθ) = [[cos(Δθ), -sin(Δθ)], [sin(Δθ), cos(Δθ)]]
        # This rotates the state vector toward |b_i⟩
        if x_i == 0 and b_i == 1:
            # Rotate toward |1⟩
            new_alpha = alpha * math.cos(delta_theta) - beta * math.sin(delta_theta)
            new_beta = alpha * math.sin(delta_theta) + beta * math.cos(delta_theta)
        elif x_i == 1 and b_i == 0:
            # Rotate toward |0⟩
            new_alpha = alpha * math.cos(-delta_theta) - beta * math.sin(-delta_theta)
            new_beta = alpha * math.sin(-delta_theta) + beta * math.cos(-delta_theta)
        else:
            # Same bit as best - no rotation needed, keep current state
            return alpha, beta

        # Normalize to maintain |α|² + |β|² = 1
        norm = math.sqrt(new_alpha ** 2 + new_beta ** 2)
        if norm > 0:
            new_alpha /= norm
            new_beta /= norm

        return new_alpha, new_beta

    def _measure_diversity(self) -> float:
        """Measure population diversity based on alpha variance.

        Returns:
            Standard deviation of alpha values across all qubits in population.
            Higher values indicate more diverse (less converged) population.
        """
        alphas = [ind[q][0] for ind in self.population for q in range(self.n_qubits)]
        return float(np.std(alphas))

    def _normalize_population(self) -> None:
        """Ensure all qubits in population satisfy normalization constraint."""
        for individual in self.population:
            for q in range(self.n_qubits):
                alpha, beta = individual[q]
                norm = math.sqrt(alpha ** 2 + beta ** 2)
                if norm > 0:
                    individual[q] = [alpha / norm, beta / norm]

    def run(
        self,
        verbose: bool = True,
        evaluate_fn: Optional[Callable[[List[int]], float]] = None,
    ) -> Tuple[List[int], float, List[float]]:
        """Run the QIEA algorithm.

        Args:
            verbose: Whether to print progress information.
            evaluate_fn: Optional override for fitness function.

        Returns:
            Tuple of (best_solution, best_fitness, history).
        """
        if evaluate_fn is not None:
            self.evaluate_fn = evaluate_fn

        if self.evaluate_fn is None:
            raise ValueError("evaluate_fn must be provided either in __init__ or run()")

        if verbose:
            print("=" * 60)
            print(f"QIEA: {self.n_qubits} qubits, {self.pop_size} individuals, {self.max_gen} gen")
            print("=" * 60)

        # Reset tracking
        self.best_solution = None
        self.best_fitness = float('-inf')
        self.history = []

        # Re-initialize population to ensure clean start
        self.population = self._init_population()

        for gen in range(self.max_gen):
            # Observation phase: collapse all qubits to binary solutions
            solutions = [self.observe(ind) for ind in self.population]

            # Evaluate fitness for all solutions
            fitnesses = [self.evaluate_fn(sol) for sol in solutions]

            # Track best solution
            gen_best_idx = int(np.argmax(fitnesses))
            gen_best_fitness = fitnesses[gen_best_idx]
            gen_best_solution = solutions[gen_best_idx]

            if gen_best_fitness > self.best_fitness:
                self.best_fitness = gen_best_fitness
                self.best_solution = gen_best_solution.copy()

            self.history.append(self.best_fitness)

            if verbose and gen % 10 == 0:
                avg_fit = float(np.mean(fitnesses))
                diversity = self._measure_diversity()
                print(f"Gen {gen:4d} | Best: {self.best_fitness:.4f} | "
                      f"Avg: {avg_fit:.4f} | Diversity: {diversity:.4f}")

            # Quantum rotation update - FIX: update each individual correctly
            for ind_idx in range(self.pop_size):
                for q in range(self.n_qubits):
                    # Calculate normalized fitness difference
                    fitness_diff = 0.0
                    if self.best_fitness != 0 and fitnesses[ind_idx] != 0:
                        fitness_diff = (self.best_fitness - fitnesses[ind_idx]) / abs(self.best_fitness)

                    # Rotate the current individual's qubit (FIX: use ind_idx not 0)
                    new_alpha, new_beta = self._quantum_rotate_single(
                        self.population[ind_idx][q][0],
                        self.population[ind_idx][q][1],
                        solutions[ind_idx][q],
                        self.best_solution[q],
                        fitness_diff,
                    )
                    self.population[ind_idx][q] = [new_alpha, new_beta]

            # Ensure normalization after all updates
            self._normalize_population()

            # Diversity injection: reset if population converges prematurely
            if gen > 0 and gen % 20 == 0:
                diversity = self._measure_diversity()
                if diversity < 0.1:
                    # Reset random individual to superposition
                    idx = int(self._rng.integers(0, self.pop_size))
                    for q in range(self.n_qubits):
                        self.population[idx][q] = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2)]

        if verbose:
            print(f"\n✅ Done! Best fitness: {self.best_fitness:.4f}")
            if self.best_solution:
                print(f"   Best solution: {''.join(map(str, self.best_solution))}")

        return self.best_solution, self.best_fitness, self.history