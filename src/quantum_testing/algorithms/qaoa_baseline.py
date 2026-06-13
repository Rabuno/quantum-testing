"""QAOA baseline for test suite minimization via Qiskit Aer."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False

from quantum_testing.problems.coverage import CoverageProblem
from quantum_testing.problems.qubo_exact import ExactQUBOFormulation


class QAOABaseline:
    """QAOA solver for test suite minimization."""

    def __init__(
        self,
        problem: CoverageProblem,
        p: int = 3,
        backend: str = "statevector",
        max_qubits: int = 25,
        use_exact_qubo: bool = False,
        seed: Optional[int] = None,
    ):
        if not HAS_QISKIT:
            raise ImportError(
                "qiskit and qiskit-aer are required. Install with: "
                "uv add qiskit qiskit-aer"
            )
        self.problem = problem
        self.p = p
        self.backend_method = backend
        self.max_qubits = max_qubits
        self.use_exact_qubo = use_exact_qubo
        self.seed = seed
        self._rng = np.random.default_rng(seed)
        self.qubo = ExactQUBOFormulation(problem) if use_exact_qubo else None
        self.n_vars = self._get_n_vars()
        self._simulator = None

    def _get_n_vars(self) -> int:
        if self.use_exact_qubo and self.qubo is not None:
            return self.qubo.n_vars
        return self.problem.n_tests

    def _get_qubo_dict(self) -> Tuple[Dict, float]:
        if self.use_exact_qubo and self.qubo is not None:
            terms = self.qubo.qubo_terms()
        else:
            terms = self.problem.qubo_terms()
        qubo_dict: Dict[Tuple[int, int], float] = {}
        for var_name, coeff in terms["linear"].items():
            if self.use_exact_qubo and self.qubo is not None:
                idx = self.qubo.variable_index(var_name)
            else:
                idx = int(var_name[1:])
            qubo_dict[(idx, idx)] = qubo_dict.get((idx, idx), 0.0) + coeff
        for pair_str, coeff in terms["quadratic"].items():
            parts = pair_str.split("*")
            v1_name, v2_name = parts[0], parts[1]
            if self.use_exact_qubo and self.qubo is not None:
                i = self.qubo.variable_index(v1_name)
                j = self.qubo.variable_index(v2_name)
            else:
                i = int(v1_name[1:])
                j = int(v2_name[1:])
            key = (min(i, j), max(i, j))
            qubo_dict[key] = qubo_dict.get(key, 0.0) + coeff
        return qubo_dict, terms["offset"]

    def _qubo_to_ising(self, qubo_dict):
        """Convert QUBO to Ising: x_i = (1 - Z_i) / 2."""
        n = self.n_vars
        h = {i: 0.0 for i in range(n)}
        J = {}
        offset = 0.0
        for (i, j), coeff in qubo_dict.items():
            if i == j:
                h[i] += -coeff / 2.0
                offset += coeff / 2.0
            else:
                q = coeff / 4.0
                offset += q
                h[i] += -q
                h[j] += -q
                key = (min(i, j), max(i, j))
                J[key] = J.get(key, 0.0) + q
        h = {k: v for k, v in h.items() if abs(v) > 1e-12}
        J = {k: v for k, v in J.items() if abs(v) > 1e-12}
        return h, J, offset

    def _build_qaoa_circuit(self, h, J, gammas, betas):
        """Build p-layer QAOA circuit."""
        n = self.n_vars
        p = self.p
        qc = QuantumCircuit(n)
        for i in range(n):
            qc.h(i)
        for layer in range(p):
            gamma = gammas[layer]
            beta = betas[layer]
            for i, hi in h.items():
                if abs(hi) > 1e-12:
                    qc.rz(2.0 * gamma * hi, i)
            for (i, j), jij in J.items():
                if abs(jij) > 1e-12:
                    qc.cx(i, j)
                    qc.rz(2.0 * gamma * jij, j)
                    qc.cx(i, j)
            for i in range(n):
                qc.rx(2.0 * beta, i)
        qc.measure_all()
        return qc

    def _evaluate_energy(self, bitstring, h, J, offset):
        """Evaluate Ising energy of a bitstring."""
        bits = [int(b) for b in bitstring]
        energy = offset
        for i, hi in h.items():
            z = 1.0 - 2.0 * bits[i]
            energy += hi * z
        for (i, j), jij in J.items():
            zi = 1.0 - 2.0 * bits[i]
            zj = 1.0 - 2.0 * bits[j]
            energy += jij * zi * zj
        return energy

    def _objective(self, params, h, J, offset, n_shots=1024):
        """Expected energy for given QAOA parameters."""
        gammas = params[:self.p].tolist()
        betas = params[self.p:].tolist()
        qc = self._build_qaoa_circuit(h, J, gammas, betas)
        if self._simulator is None:
            self._simulator = AerSimulator(
                method=self.backend_method,
                seed_simulator=self.seed,
            )
        job = self._simulator.run(qc, shots=n_shots)
        result = job.result()
        counts = result.get_counts()
        total_energy = 0.0
        total_shots = 0
        for bitstring, count in counts.items():
            energy = self._evaluate_energy(bitstring[::-1], h, J, offset)
            total_energy += energy * count
            total_shots += count
        return total_energy / total_shots if total_shots > 0 else 0.0

    def run(self, n_shots=1024, optimizer_steps=50, initial_params=None):
        """Run QAOA optimization."""
        qubo_dict, offset = self._get_qubo_dict()
        h, J, ising_offset = self._qubo_to_ising(qubo_dict)
        total_offset = offset + ising_offset
        n_params = 2 * self.p
        if initial_params is None:
            params = self._rng.uniform(0, 2 * math.pi, n_params)
        else:
            params = initial_params.copy()
        best_energy = float("inf")
        best_params = params.copy()
        for step in range(optimizer_steps):
            if step == 0:
                current_params = params
            else:
                current_params = best_params + self._rng.normal(0, 0.3, n_params)
            try:
                energy = self._objective(current_params, h, J, total_offset, n_shots)
                if energy < best_energy:
                    best_energy = energy
                    best_params = current_params.copy()
            except Exception:
                continue
        gammas = best_params[:self.p].tolist()
        betas = best_params[self.p:].tolist()
        qc = self._build_qaoa_circuit(h, J, gammas, betas)
        if self._simulator is None:
            self._simulator = AerSimulator(
                method=self.backend_method,
                seed_simulator=self.seed,
            )
        job = self._simulator.run(qc, shots=n_shots * 4)
        result = job.result()
        counts = result.get_counts()
        best_bitstring = None
        best_sample_energy = float("inf")
        for bitstring, count in counts.items():
            energy = self._evaluate_energy(bitstring[::-1], h, J, total_offset)
            if energy < best_sample_energy:
                best_sample_energy = energy
                best_bitstring = bitstring[::-1]
        bits = [int(b) for b in best_bitstring] if best_bitstring else [0] * self.n_vars
        if self.use_exact_qubo and self.qubo is not None:
            solution = self.qubo.decode_solution(
                {"x" + str(i): bits[i] for i in range(self.qubo.n_x)}
            )
        else:
            solution = bits[:self.problem.n_tests]
        if len(solution) < self.problem.n_tests:
            solution = solution + [0] * (self.problem.n_tests - len(solution))
        solution = solution[:self.problem.n_tests]
        objectives = self.problem.objectives(solution)
        return {
            "solution": solution,
            "energy": best_sample_energy,
            "objectives": objectives,
            "n_vars": self.n_vars,
            "p": self.p,
            "params": best_params.tolist(),
        }


def estimate_qaoa_resources(n_tests, n_requirements, p, use_exact=False):
    """Estimate QAOA resource requirements."""
    n_qubits = n_tests + n_requirements if use_exact else n_tests
    n_params = 2 * p
    memory_mb = (2 ** n_qubits) * 16 / (1024 * 1024)
    feasible = n_qubits <= 28
    if n_qubits <= 28:
        backend = "statevector"
    elif n_qubits <= 50:
        backend = "mps"
    else:
        backend = "infeasible"
    return {
        "n_qubits": n_qubits,
        "n_params": n_params,
        "memory_mb": memory_mb,
        "feasible": feasible,
        "backend": backend,
    }
