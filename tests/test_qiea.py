import math
from quantum_testing.algorithms import QIEA


def test_qiea_onemax_near_optimum():
    q = QIEA(n_qubits=16, pop_size=20, max_gen=120, evaluate_fn=sum, seed=7)
    sol, fit, hist = q.run(verbose=False)
    assert fit >= 15
    assert len(sol) == 16
    assert hist[-1] == fit


def test_qiea_population_normalized():
    q = QIEA(n_qubits=10, pop_size=8, max_gen=20, evaluate_fn=sum, seed=3)
    q.run(verbose=False)
    for ind in q.population:
        for alpha, beta in ind:
            assert math.isclose(alpha * alpha + beta * beta, 1.0, rel_tol=1e-7, abs_tol=1e-7)
