"""Entanglement register and NISQ noise model for Enhanced QIEA."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np


class EntanglementRegister:
    """Pairwise entanglement correlation matrix between qubits."""

    def __init__(self, n_qubits: int, decay_rate: float = 0.1, seed: Optional[int] = None):
        if n_qubits < 1:
            raise ValueError(f"n_qubits must be >= 1, got {n_qubits}")
        if not 0.0 <= decay_rate <= 1.0:
            raise ValueError(f"decay_rate must be in [0, 1], got {decay_rate}")
        self.n = n_qubits
        self.decay_rate = decay_rate
        self.matrix = np.zeros((n_qubits, n_qubits), dtype=np.float64)
        self._rng = np.random.default_rng(seed)

    def update(self, qubit_i: int, qubit_j: int, correlation: float) -> None:
        if qubit_i == qubit_j:
            return
        old = self.matrix[qubit_i, qubit_j]
        new = (1.0 - self.decay_rate) * old + self.decay_rate * float(correlation)
        self.matrix[qubit_i, qubit_j] = new
        self.matrix[qubit_j, qubit_i] = new

    def update_from_population(self, solutions, fitnesses, top_fraction=0.3):
        if not solutions or not fitnesses:
            return
        n_top = max(2, int(len(solutions) * top_fraction))
        idx = np.argsort(fitnesses)[::-1][:n_top]
        top = np.array([solutions[i] for i in idx], dtype=np.float64)
        for i in range(self.n):
            for j in range(i + 1, self.n):
                agreement = np.mean(top[:, i] == top[:, j])
                self.update(i, j, float(agreement))

    def get_entangled_pairs(self, threshold=0.5):
        pairs = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if self.matrix[i, j] > threshold:
                    pairs.append((i, j, float(self.matrix[i, j])))
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def get_correlated_group(self, qubit, threshold=0.5):
        correlated = []
        for j in range(self.n):
            if j != qubit and self.matrix[qubit, j] > threshold:
                correlated.append((j, float(self.matrix[qubit, j])))
        correlated.sort(key=lambda x: x[1], reverse=True)
        return [j for j, _ in correlated]

    def merge(self, other):
        if self.n != other.n:
            raise ValueError(f"Cannot merge: different sizes {self.n} vs {other.n}")
        merged = EntanglementRegister(self.n, self.decay_rate)
        merged.matrix = (self.matrix + other.matrix) / 2.0
        return merged

    def copy(self):
        reg = EntanglementRegister(self.n, self.decay_rate)
        reg.matrix = self.matrix.copy()
        return reg

    def reset(self):
        self.matrix.fill(0.0)

    def entropy(self):
        total = float(np.sum(np.abs(self.matrix))) / 2.0
        max_possible = self.n * (self.n - 1) / 2.0
        return total / max_possible if max_possible > 0 else 0.0


class NISQNoiseModel:
    """NISQ (Noisy Intermediate-Scale Quantum) noise simulation."""

    def __init__(self, depolarizing_prob=0.01, amplitude_damping_prob=0.005,
                 measurement_error_prob=0.005, seed=None):
        self.p_dep = depolarizing_prob
        self.p_ad = amplitude_damping_prob
        self.p_meas = measurement_error_prob
        self._rng = np.random.default_rng(seed)

    def noisy_observation(self, alpha: float, beta: float) -> int:
        p1 = beta ** 2
        p1 = (1.0 - self.p_dep) * p1 + self.p_dep * 0.5
        p1 = p1 * (1.0 - self.p_ad)
        bit = 1 if self._rng.random() < p1 else 0
        if self._rng.random() < self.p_meas:
            bit = 1 - bit
        return bit

    def noisy_observation_batch(self, alphas: np.ndarray, betas: np.ndarray) -> np.ndarray:
        p1 = betas ** 2
        p1 = (1.0 - self.p_dep) * p1 + self.p_dep * 0.5
        p1 = p1 * (1.0 - self.p_ad)
        rand = self._rng.random(len(p1))
        bits = (rand < p1).astype(int)
        flip_mask = self._rng.random(len(bits)) < self.p_meas
        bits[flip_mask] = 1 - bits[flip_mask]
        return bits

    def effective_error_rate(self) -> float:
        p_no_error = (1.0 - self.p_dep) * (1.0 - self.p_ad) * (1.0 - self.p_meas)
        return 1.0 - p_no_error

    def __repr__(self) -> str:
        return (f"NISQNoiseModel(depolarizing={self.p_dep}, "
                f"amplitude_damping={self.p_ad}, measurement_error={self.p_meas})")
