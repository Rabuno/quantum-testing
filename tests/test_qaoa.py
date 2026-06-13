"""Tests for QAOA baseline (qaoa_baseline.py)."""

import math

import pytest

from quantum_testing.problems.coverage import CoverageProblem

try:
    from quantum_testing.algorithms.qaoa_baseline import (
        QAOABaseline,
        estimate_qaoa_resources,
    )
    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False


@pytest.fixture
def small_problem():
    """Small coverage problem (10 tests, 8 requirements)."""
    return CoverageProblem.synthetic(
        n_tests=10, n_requirements=8, min_cover=2, max_cover=5, seed=42
    )


@pytest.fixture
def tiny_problem():
    """Tiny coverage problem (5 tests, 4 requirements) for exact QUBO."""
    return CoverageProblem.synthetic(
        n_tests=5, n_requirements=4, min_cover=1, max_cover=3, seed=7
    )


@pytest.mark.skipif(not HAS_QISKIT, reason="qiskit/qiskit-aer not installed")
class TestQAOABaseline:
    """Tests for QAOABaseline class."""

    def test_init_default(self, small_problem):
        solver = QAOABaseline(small_problem)
        assert solver.p == 3
        assert solver.n_vars == 10
        assert solver.backend_method == "statevector"

    def test_init_exact_qubo(self, tiny_problem):
        solver = QAOABaseline(tiny_problem, use_exact_qubo=True)
        assert solver.n_vars == 9  # 5 tests + 4 requirements
        assert solver.qubo is not None

    def test_init_custom_p(self, small_problem):
        solver = QAOABaseline(small_problem, p=5)
        assert solver.p == 5

    def test_get_qubo_dict_surrogate(self, small_problem):
        solver = QAOABaseline(small_problem, use_exact_qubo=False)
        qubo_dict, offset = solver._get_qubo_dict()
        assert isinstance(qubo_dict, dict)
        assert isinstance(offset, float)
        # Should have linear terms for each test.
        for i in range(10):
            assert (i, i) in qubo_dict

    def test_get_qubo_dict_exact(self, tiny_problem):
        solver = QAOABaseline(tiny_problem, use_exact_qubo=True)
        qubo_dict, offset = solver._get_qubo_dict()
        assert isinstance(qubo_dict, dict)
        # 9 variables: x0..x4, y0..y3
        assert (0, 0) in qubo_dict  # x0 linear

    def test_qubo_to_ising(self, small_problem):
        solver = QAOABaseline(small_problem)
        qubo_dict, offset = solver._get_qubo_dict()
        h, J, ising_offset = solver._qubo_to_ising(qubo_dict)
        assert isinstance(h, dict)
        assert isinstance(J, dict)
        assert isinstance(ising_offset, float)
        # h should have entries for all qubits.
        for i in range(10):
            assert i in h

    def test_qubo_to_ising_conversion_correctness(self):
        """Test QUBO -> Ising on a simple 1-variable case."""
        solver = QAOABaseline.__new__(QAOABaseline)
        solver.n_vars = 1
        # QUBO: H = -x_0 (minimize => want x_0=1)
        qubo_dict = {(0, 0): -1.0}
        h, J, offset = solver._qubo_to_ising(qubo_dict)
        # x = (1-Z)/2, so -x = -(1-Z)/2 = -0.5 + 0.5*Z
        # h[0] = 0.5, offset = -0.5
        assert abs(h[0] - 0.5) < 1e-10
        assert abs(offset - (-0.5)) < 1e-10

    def test_build_qaoa_circuit(self, small_problem):
        solver = QAOABaseline(small_problem, p=2)
        h = {i: 0.1 for i in range(10)}
        J = {}
        gammas = [0.5, 0.3]
        betas = [0.2, 0.4]
        qc = solver._build_qaoa_circuit(h, J, gammas, betas)
        assert qc.num_qubits == 10
        # Should have measurements.
        assert qc.num_clbits == 10

    def test_build_qaoa_circuit_p1(self, small_problem):
        solver = QAOABaseline(small_problem, p=1)
        h = {0: 0.5}
        J = {}
        qc = solver._build_qaoa_circuit(h, J, [0.3], [0.7])
        assert qc.num_qubits == 10

    def test_evaluate_energy(self, small_problem):
        solver = QAOABaseline(small_problem)
        h = {0: 1.0}
        J = {}
        offset = 0.0
        e0 = solver._evaluate_energy("0" * 10, h, J, offset)
        e1 = solver._evaluate_energy("1" + "0" * 9, h, J, offset)
        # Z=+1 for bit=0, Z=-1 for bit=1
        # E = h_0 * Z_0 = 1.0 * 1 = 1 for bit=0, 1.0 * (-1) = -1 for bit=1
        assert abs(e0 - 1.0) < 1e-10
        assert abs(e1 - (-1.0)) < 1e-10

    def test_run_returns_dict(self, small_problem):
        solver = QAOABaseline(small_problem, p=1, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=5)
        assert isinstance(result, dict)
        assert "solution" in result
        assert "energy" in result
        assert "objectives" in result
        assert "n_vars" in result
        assert "p" in result
        assert "params" in result

    def test_run_solution_length(self, small_problem):
        solver = QAOABaseline(small_problem, p=1, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=5)
        assert len(result["solution"]) == 10

    def test_run_solution_binary(self, small_problem):
        solver = QAOABaseline(small_problem, p=1, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=5)
        for bit in result["solution"]:
            assert bit in (0, 1)

    def test_run_objectives_keys(self, small_problem):
        solver = QAOABaseline(small_problem, p=1, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=5)
        obj = result["objectives"]
        assert "coverage_ratio" in obj
        assert "reduction_ratio" in obj
        assert "selected_count" in obj
        assert "total_cost" in obj
        assert "uncovered_count" in obj
        assert "fitness" in obj

    def test_run_with_exact_qubo(self, tiny_problem):
        solver = QAOABaseline(tiny_problem, p=1, use_exact_qubo=True, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=3)
        assert isinstance(result, dict)
        assert len(result["solution"]) == 5

    def test_params_length(self, small_problem):
        solver = QAOABaseline(small_problem, p=3, seed=42)
        result = solver.run(n_shots=256, optimizer_steps=5)
        assert len(result["params"]) == 6  # 2 * p


class TestEstimateQaoaResources:
    """Tests for estimate_qaoa_resources function."""

    def test_surrogate_qubo(self):
        res = estimate_qaoa_resources(10, 8, p=3, use_exact=False)
        assert res["n_qubits"] == 10
        assert res["n_params"] == 6
        assert res["feasible"] is True
        assert res["backend"] == "statevector"

    def test_exact_qubo(self):
        res = estimate_qaoa_resources(5, 4, p=2, use_exact=True)
        assert res["n_qubits"] == 9
        assert res["n_params"] == 4
        assert res["feasible"] is True

    def test_infeasible(self):
        res = estimate_qaoa_resources(100, 50, p=3, use_exact=False)
        assert res["feasible"] is False
        assert res["backend"] == "infeasible"

    def test_mps_backend(self):
        res = estimate_qaoa_resources(40, 0, p=3, use_exact=False)
        assert res["backend"] == "mps"

    def test_memory_calculation(self):
        res = estimate_qaoa_resources(10, 0, p=1, use_exact=False)
        expected_mb = (2 ** 10) * 16 / (1024 * 1024)
        assert abs(res["memory_mb"] - expected_mb) < 1e-10
