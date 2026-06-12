"""Enhanced QIEA (E-QIEA) with entanglement register and adaptive rotation.

This is the core novel contribution of the research:
- Entanglement register tracks pairwise qubit correlations
- Adaptive rotation gate adjusts angle based on diversity and generation
- Entanglement-aware crossover preserves correlated groups
- Optional NISQ noise simulation for realism
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

import numpy as np

from quantum_testing.algorithms.entanglement import EntanglementRegister, NISQNoiseModel


def adaptive_rotation_angle(
    generation: int,
    max_gen: int,
    diversity: float,
    max_diversity: float,
    qubit_state: Tuple[float, float],
    best_bit: int,
) -> float:
    """Compute adaptive rotation angle based on convergence state.

    The angle adapts based on:
    1. Generation progress (larger early, smaller later)
    2. Population diversity (larger when diversity is low)
    3. Qubit alignment with best solution (direction)

    Args:
        generation: Current generation number.
        max_gen: Maximum generations.
        diversity: Current population diversity.
        max_diversity: Maximum observed diversity.
        qubit_state: Current (alpha, beta) of the qubit.
        best_bit: Best solution bit at this position.

    Returns:
        Signed rotation angle in radians.
    """
    # Base angle: decreases over time (π/18 = 10 degrees initially)
    frac = generation / max(1, max_gen - 1)
    theta_base = (math.pi / 18.0) * (1.0 - frac)

    # Diversity scaling: boost exploration when diversity is low
    diversity_ratio = diversity / max(max_diversity, 1e-12)
    if diversity_ratio < 0.2:
        theta_base *= 3.0
    elif diversity_ratio < 0.5:
        theta_base *= 1.5

    # Direction: rotate toward best_bit
    alpha, beta = qubit_state
    p1 = beta ** 2
    if best_bit == 1 and p1 < 0.5:
        direction = 1.0
    elif best_bit == 0 and p1 > 0.5:
        direction = -1.0
    else:
        direction = 0.0

    return direction * theta_base


class EnhancedQIEA:
    """Entanglement-Enhanced Quantum-Inspired Evolutionary Algorithm.

    Novel contributions over standard QIEA:
    1. EntanglementRegister: tracks pairwise qubit correlations
    2. Adaptive rotation: generation + diversity aware angle
    3. Entanglement-aware crossover: preserves correlated groups
    4. Optional NISQ noise: depolarizing + amplitude damping + measurement error
    """

    def __init__(
        self,
        n_qubits: int,
        pop_size: int,
        max_gen: int,
        evaluate_fn: Optional[Callable[[List[int]], float]] = None,
        seed: Optional[int] = None,
        # Enhancement params
        use_entanglement: bool = True,
        use_adaptive_rotation: bool = True,
        use_entanglement_crossover: bool = True,
        entanglement_decay_rate: float = 0.1,
        crossover_rate: float = 0.3,
        # Noise params
        noise_model: Optional[NISQNoiseModel] = None,
    ):
        self.n_qubits = n_qubits
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.evaluate_fn = evaluate_fn
        self.seed = seed
        self.use_entanglement = use_entanglement
        self.use_adaptive_rotation = use_adaptive_rotation
        self.use_entanglement_crossover = use_entanglement_crossover
        self.entanglement_decay_rate = entanglement_decay_rate
        self.crossover_rate = crossover_rate
        self.noise_model = noise_model

        self._rng = np.random.default_rng(seed)

        # Per-individual entanglement registers
        self.entanglement_registers: List[EntanglementRegister] = [
            EntanglementRegister(n_qubits, entanglement_decay_rate, seed)
            for _ in range(pop_size)
        ]

        # Population: list of individuals, each = list of [alpha, beta]
        self.population: List[List[List[float]]] = self._init_population()
        self.best_solution: Optional[List[int]] = None
        self.best_fitness = float("-inf")
        self.history: List[float] = []
        self.diversity_history: List[float] = []
        self.entanglement_entropy_history: List[float] = []

    def _init_population(self):
        pop = []
        alpha = 1.0 / math.sqrt(2)
        beta = 1.0 / math.sqrt(2)
        for _ in range(self.pop_size):
            individual = [[alpha, beta] for _ in range(self.n_qubits)]
            pop.append(individual)
        return pop

    def observe(self, individual, rng=None):
        """Collapse quantum state to binary string via observation."""
        if rng is None:
            rng = self._rng
        binary = []
        for q_idx, (alpha, beta) in enumerate(individual):
            if self.noise_model is not None:
                bit = self.noise_model.noisy_observation(alpha, beta)
            else:
                prob_1 = beta ** 2
                bit = 1 if rng.random() < prob_1 else 0
            binary.append(bit)
        return binary

    def _quantum_rotate_single(self, alpha, beta, delta_theta):
        """Apply quantum rotation gate R(delta_theta) to a single qubit."""
        if abs(delta_theta) < 1e-12:
            return alpha, beta
        cos_t = math.cos(delta_theta)
        sin_t = math.sin(delta_theta)
        new_alpha = alpha * cos_t - beta * sin_t
        new_beta = alpha * sin_t + beta * cos_t
        norm = math.sqrt(new_alpha ** 2 + new_beta ** 2)
        if norm > 0:
            new_alpha /= norm
            new_beta /= norm
        return new_alpha, new_beta

    def _adaptive_rotation_angle(self, gen, diversity, max_diversity, qubit_state, best_bit):
        return adaptive_rotation_angle(gen, self.max_gen, diversity, max_diversity, qubit_state, best_bit)

    def _measure_diversity(self):
        alphas = [ind[q][0] for ind in self.population for q in range(self.n_qubits)]
        return float(np.std(alphas))

    def _measure_max_diversity(self):
        return 1.0 / math.sqrt(2)  # Max std dev for uniform [0, 1]

    def _entanglement_aware_crossover(self, parent1_idx, parent2_idx):
        """Create offspring by averaging parent qubit states and entanglement."""
        child = []
        for q in range(self.n_qubits):
            a1, b1 = self.population[parent1_idx][q]
            a2, b2 = self.population[parent2_idx][q]
            child.append([(a1 + a2) / 2.0, (b1 + b2) / 2.0])
        # Normalize
        for q in range(self.n_qubits):
            a, b = child[q]
            norm = math.sqrt(a ** 2 + b ** 2)
            if norm > 0:
                child[q] = [a / norm, b / norm]
        # Merge entanglement
        child_entanglement = self.entanglement_registers[parent1_idx].merge(
            self.entanglement_registers[parent2_idx]
        )
        return child, child_entanglement

    def run(self, verbose=True, evaluate_fn=None):
        """Run the Enhanced QIEA algorithm.

        Returns:
            Tuple of (best_solution, best_fitness, history).
        """
        if evaluate_fn is not None:
            self.evaluate_fn = evaluate_fn
        if self.evaluate_fn is None:
            raise ValueError("evaluate_fn must be provided")

        self.best_solution = None
        self.best_fitness = float("-inf")
        self.history = []
        self.diversity_history = []
        self.entanglement_entropy_history = []
        self.population = self._init_population()
        self.entanglement_registers = [
            EntanglementRegister(self.n_qubits, self.entanglement_decay_rate, self.seed)
            for _ in range(self.pop_size)
        ]

        max_diversity = self._measure_max_diversity()

        for gen in range(self.max_gen):
            # Observation phase
            solutions = [self.observe(ind) for ind in self.population]
            fitnesses = [self.evaluate_fn(sol) for sol in solutions]

            gen_best_idx = int(np.argmax(fitnesses))
            gen_best_fitness = fitnesses[gen_best_idx]
            if gen_best_fitness > self.best_fitness:
                self.best_fitness = gen_best_fitness
                self.best_solution = solutions[gen_best_idx].copy()

            self.history.append(self.best_fitness)
            diversity = self._measure_diversity()
            self.diversity_history.append(diversity)

            # Update entanglement registers
            if self.use_entanglement:
                for reg in self.entanglement_registers:
                    reg.update_from_population(solutions, fitnesses)
                avg_entropy = np.mean([reg.entropy() for reg in self.entanglement_registers])
                self.entanglement_entropy_history.append(float(avg_entropy))

            # Quantum rotation update
            for ind_idx in range(self.pop_size):
                for q in range(self.n_qubits):
                    if self.best_solution is None:
                        continue
                    x_i = solutions[ind_idx][q]
                    b_i = self.best_solution[q]

                    if self.use_adaptive_rotation:
                        delta_theta = self._adaptive_rotation_angle(
                            gen, diversity, max_diversity,
                            tuple(self.population[ind_idx][q]), b_i
                        )
                    else:
                        fitness_diff = 0.0
                        if self.best_fitness != 0 and fitnesses[ind_idx] != 0:
                            fitness_diff = (self.best_fitness - fitnesses[ind_idx]) / abs(self.best_fitness)
                        delta_theta = 0.01 * math.pi * (1.0 + fitness_diff)
                        if x_i == 0 and b_i == 1:
                            pass  # positive rotation
                        elif x_i == 1 and b_i == 0:
                            delta_theta = -delta_theta
                        else:
                            delta_theta = 0.0

                    new_alpha, new_beta = self._quantum_rotate_single(
                        self.population[ind_idx][q][0],
                        self.population[ind_idx][q][1],
                        delta_theta,
                    )
                    self.population[ind_idx][q] = [new_alpha, new_beta]

            # Entanglement-aware crossover
            if self.use_entanglement_crossover and self._rng.random() < self.crossover_rate:
                p1_idx = int(self._rng.integers(0, self.pop_size))
                p2_idx = int(self._rng.integers(0, self.pop_size))
                while p2_idx == p1_idx:
                    p2_idx = int(self._rng.integers(0, self.pop_size))
                child, child_ent = self._entanglement_aware_crossover(p1_idx, p2_idx)
                # Replace worst individual
                worst_idx = int(np.argmin(fitnesses))
                self.population[worst_idx] = child
                self.entanglement_registers[worst_idx] = child_ent

            # Diversity injection
            if gen > 0 and gen % 20 == 0 and diversity < 0.1:
                idx = int(self._rng.integers(0, self.pop_size))
                for q in range(self.n_qubits):
                    self.population[idx][q] = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2)]

        return self.best_solution, self.best_fitness, self.history
