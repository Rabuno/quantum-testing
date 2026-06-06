from quantum_testing.problems.combinatorial import CITModel, greedy_covering_array, qiea_covering_array


def small_model():
    return CITModel({"a": [0, 1], "b": [0, 1], "c": [0, 1]}, strength=2)


def test_greedy_cit_full_pairwise_coverage():
    model = small_model()
    rows, report = greedy_covering_array(model, seed=1)
    assert rows
    assert report["coverage_ratio"] == 1.0
    assert model.coverage_ratio(rows) == 1.0


def test_qiea_cit_positive_coverage():
    model = small_model()
    rows, report = qiea_covering_array(model, n_rows=4, generations=30, pop_size=8, seed=2)
    assert rows
    assert report["coverage_ratio"] >= 0.75
