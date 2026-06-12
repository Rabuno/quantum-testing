"""Tests for entanglement register, NISQ noise model, and enhanced QIEA."""

import math

import numpy as np
import pytest

from quantum_testing.algorithms.entanglement import EntanglementRegister, NISQNoiseModel
from quantum_testing.algorithms.enhanced_qiea import EnhancedQIEA, adaptive_rotation_angle


# ============================================================
# EntanglementRegister tests
# ============================================================


class TestEntanglementRegister:
    def test_init(self):
        reg = EntanglementRegister(10)
        assert reg.n == 10
        assert reg.matrix.shape == (10, 10)
        assert np.all(reg.matrix == 0.0)

    def test_init_validation(self):
        with pytest.raises(ValueError, match="n_qubits"):
            EntanglementRegister(0)
        with pytest.raises(ValueError, match="decay_rate"):
            EntanglementRegister(5, decay_rate=1.5)

    def test_update_symmetry(self):
        reg = EntanglementRegister(5, decay_rate=0.5)
        reg.update(0, 1, 0.8)
        assert reg.matrix[0, 1] == pytest.approx(0.4)
        assert reg.matrix[1, 0] == pytest.approx(0.4)

    def test_update_ema(self):
        reg = EntanglementRegister(3, decay_rate=0.1)
        reg.update(0, 1, 1.0)
        assert reg.matrix[0, 1] == pytest.approx(0.1)
        reg.update(0, 1, 1.0)
        assert reg.matrix[0, 1] == pytest.approx(0.19)

    def test_self_update_noop(self):
        reg = EntanglementRegister(3)
        reg.update(1, 1, 0.9)
        assert reg.matrix[1, 1] == 0.0

    def test_update_from_population(self):
        reg = EntanglementRegister(4, decay_rate=0.5)
        solutions = [[1, 0, 1, 0], [1, 0, 1, 1], [0, 1, 0, 1]]
        fitnesses = [0.9, 0.7, 0.3]
        reg.update_from_population(solutions, fitnesses, top_fraction=0.5)
        # Top 2 solutions: [1,0,1,0] and [1,0,1,1]
        # Qubits 0 and 2 always agree -> high correlation
        assert reg.matrix[0, 2] > reg.matrix[0, 1]

    def test_get_entangled_pairs(self):
        reg = EntanglementRegister(4, decay_rate=1.0)
        reg.update(0, 1, 0.8)
        reg.update(2, 3, 0.3)
        pairs = reg.get_entangled_pairs(threshold=0.5)
        assert len(pairs) == 1
        assert pairs[0][0] == 0
        assert pairs[0][1] == 1

    def test_get_correlated_group(self):
        reg = EntanglementRegister(5, decay_rate=1.0)
        reg.update(0, 1, 0.9)
        reg.update(0, 2, 0.7)
        reg.update(0, 3, 0.2)
        group = reg.get_correlated_group(0, threshold=0.5)
        assert group == [1, 2]

    def test_merge(self):
        reg1 = EntanglementRegister(3, decay_rate=1.0)
        reg2 = EntanglementRegister(3, decay_rate=1.0)
        reg1.update(0, 1, 0.8)
        reg2.update(0, 1, 0.4)
        merged = reg1.merge(reg2)
        assert merged.matrix[0, 1] == pytest.approx(0.6)

    def test_merge_size_mismatch(self):
        reg1 = EntanglementRegister(3)
        reg2 = EntanglementRegister(5)
        with pytest.raises(ValueError, match="different sizes"):
            reg1.merge(reg2)

    def test_copy(self):
        reg = EntanglementRegister(3, decay_rate=0.5)
        reg.update(0, 1, 0.7)
        cp = reg.copy()
        assert cp.matrix[0, 1] == pytest.approx(0.35)
        cp.update(0, 1, 1.0)
        assert reg.matrix[0, 1] != cp.matrix[0, 1]

    def test_reset(self):
        reg = EntanglementRegister(3, decay_rate=1.0)
        reg.update(0, 1, 0.9)
        reg.reset()
        assert np.all(reg.matrix == 0.0)

    def test_entropy(self):
        reg = EntanglementRegister(3, decay_rate=1.0)
        assert reg.entropy() == 0.0
        reg.update(0, 1, 1.0)
        assert reg.entropy() > 0.0


# ============================================================
# NISQNoiseModel tests
# ============================================================


class TestNISQNoiseModel:
    def test_init(self):
        noise = NISQNoiseModel(0.01, 0.005, 0.005)
        assert noise.p_dep == 0.01
        assert noise.p_ad == 0.005
        assert noise.p_meas == 0.005

    def test_no_noise(self):
        noise = NISQNoiseModel(0.0, 0.0, 0.0, seed=42)
        # |1> state: alpha=0, beta=1
        assert noise.noisy_observation(0.0, 1.0) == 1
        # |0> state: alpha=1, beta=0
        assert noise.noisy_observation(1.0, 0.0) == 0

    def test_full_depolarizing(self):
        noise = NISQNoiseModel(1.0, 0.0, 0.0, seed=42)
        # With p_dep=1, p1 = 0.5 regardless of state
        results = [noise.noisy_observation(1.0, 0.0) for _ in range(100)]
        assert 0 in results and 1 in results  # roughly 50/50

    def test_effective_error_rate(self):
        noise = NISQNoiseModel(0.01, 0.005, 0.005)
        expected = 1.0 - 0.99 * 0.995 * 0.995
        assert noise.effective_error_rate() == pytest.approx(expected)

    def test_batch_observation(self):
        noise = NISQNoiseModel(0.0, 0.0, 0.0, seed=42)
        alphas = np.array([0.0, 1.0, 0.0])
        betas = np.array([1.0, 0.0, 1.0])
        bits = noise.noisy_observation_batch(alphas, betas)
        np.testing.assert_array_equal(bits, [1, 0, 1])

    def test_repr(self):
        noise = NISQNoiseModel(0.01, 0.005, 0.005)
        r = repr(noise)
        assert "NISQNoiseModel" in r


# ============================================================
# Adaptive rotation angle tests
# ============================================================


class TestAdaptiveRotationAngle:
    def test_direction_toward_1(self):
        # p1 = 0.25 < 0.5, best_bit=1 -> positive rotation
        angle = adaptive_rotation_angle(0, 100, 0.5, 0.5, (0.866, 0.5), 1)
        assert angle > 0

    def test_direction_toward_0(self):
        # p1 = 0.75 > 0.5, best_bit=0 -> negative rotation
        angle = adaptive_rotation_angle(0, 100, 0.5, 0.5, (0.5, 0.866), 0)
        assert angle < 0

    def test_no_direction_when_aligned(self):
        # p1 = 0.75 > 0.5, best_bit=1 -> already aligned
        angle = adaptive_rotation_angle(0, 100, 0.5, 0.5, (0.5, 0.866), 1)
        assert angle == 0.0

    def test_low_diversity_boost(self):
        angle_normal = adaptive_rotation_angle(0, 100, 0.5, 0.5, (0.866, 0.5), 1)
        angle_low = adaptive_rotation_angle(0, 100, 0.05, 0.5, (0.866, 0.5), 1)
        assert abs(angle_low) > abs(angle_normal)

    def test_generation_decay(self):
        angle_early = adaptive_rotation_angle(0, 100, 0.5, 0.5, (0.866, 0.5), 1)
        angle_late = adaptive_rotation_angle(99, 100, 0.5, 0.5, (0.866, 0.5), 1)
        assert abs(angle_early) > abs(angle_late)


# ============================================================
# EnhancedQIEA tests
# ============================================================


class TestEnhancedQIEA:
    def _make_fitness_fn(self):
        """Simple onemax fitness for testing."""
        return lambda sol: float(sum(sol))

    def test_basic_run(self):
        eqiea = EnhancedQIEA(
            n_qubits=10, pop_size=20, max_gen=50,
            evaluate_fn=self._make_fitness_fn(), seed=42,
        )
        sol, fit, hist = eqiea.run(verbose=False)
        assert len(sol) == 10
        assert fit > 0
        assert len(hist) == 50

    def test_with_all_enhancements(self):
        eqiea = EnhancedQIEA(
            n_qubits=10, pop_size=20, max_gen=30,
            evaluate_fn=self._make_fitness_fn(), seed=42,
            use_entanglement=True,
            use_adaptive_rotation=True,
            use_entanglement_crossover=True,
        )
        sol, fit, hist = eqiea.run(verbose=False)
        assert len(sol) == 10
        assert fit > 0
        assert len(eqiea.diversity_history) == 30

    def test_without_enhancements(self):
        eqiea = EnhancedQIEA(
            n_qubits=10, pop_size=20, max_gen=30,
            evaluate_fn=self._make_fitness_fn(), seed=42,
            use_entanglement=False,
            use_adaptive_rotation=False,
            use_entanglement_crossover=False,
        )
        sol, fit, hist = eqiea.run(verbose=False)
        assert len(sol) == 10
        assert fit > 0

    def test_with_noise(self):
        noise = NISQNoiseModel(0.01, 0.005, 0.005, seed=42)
        eqiea = EnhancedQIEA(
            n_qubits=10, pop_size=20, max_gen=30,
            evaluate_fn=self._make_fitness_fn(), seed=42,
            noise_model=noise,
        )
        sol, fit, hist = eqiea.run(verbose=False)
        assert len(sol) == 10

    def test_coverage_problem(self):
        from quantum_testing.problems.coverage import CoverageProblem
        problem = CoverageProblem.synthetic(n_tests=20, n_requirements=15, seed=42)
        eqiea = EnhancedQIEA(
            n_qubits=20, pop_size=30, max_gen=50,
            evaluate_fn=problem.fitness, seed=42,
        )
        sol, fit, hist = eqiea.run(verbose=False)
        assert len(sol) == 20
        report = problem.report(sol)
        assert report.coverage_ratio >= 0.0

    def test_reproducibility(self):
        fn = self._make_fitness_fn()
        eqiea1 = EnhancedQIEA(n_qubits=10, pop_size=20, max_gen=20, evaluate_fn=fn, seed=123)
        sol1, fit1, _ = eqiea1.run(verbose=False)
        eqiea2 = EnhancedQIEA(n_qubits=10, pop_size=20, max_gen=20, evaluate_fn=fn, seed=123)
        sol2, fit2, _ = eqiea2.run(verbose=False)
        assert sol1 == sol2
        assert fit1 == fit2

    def test_entanglement_entropy_tracked(self):
        eqiea = EnhancedQIEA(
            n_qubits=10, pop_size=20, max_gen=10,
            evaluate_fn=self._make_fitness_fn(), seed=42,
            use_entanglement=True,
        )
        eqiea.run(verbose=False)
        assert len(eqiea.entanglement_entropy_history) == 10
