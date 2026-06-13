"""Tests for statistical_tests.py."""

import math

import pytest

from quantum_testing.statistical_tests import (
    wilcoxon_signed_rank,
    cliffs_delta,
    friedman_test,
    nemenyi_post_hoc,
    compute_cd_diagram_data,
    _nemenyi_critical_value,
)


class TestWilcoxonSignedRank:
    def test_clear_difference(self):
        a = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        b = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = wilcoxon_signed_rank(a, b)
        assert result["significant"] is True
        assert result["p_value"] < 0.05

    def test_no_difference(self):
        a = [5, 5, 5, 5, 5]
        b = [5, 5, 5, 5, 5]
        result = wilcoxon_signed_rank(a, b)
        assert result["significant"] is False
        assert result["p_value"] == 1.0

    def test_small_difference(self):
        a = [1.0, 1.1, 1.2, 1.3, 1.4]
        b = [1.0, 1.0, 1.0, 1.0, 1.0]
        result = wilcoxon_signed_rank(a, b)
        assert isinstance(result["statistic"], float)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_alternative_greater(self):
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        result = wilcoxon_signed_rank(a, b, alternative="greater")
        assert isinstance(result["p_value"], float)

    def test_alternative_less(self):
        a = [1, 2, 3, 4, 5]
        b = [10, 11, 12, 13, 14]
        result = wilcoxon_signed_rank(a, b, alternative="less")
        assert isinstance(result["p_value"], float)

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            wilcoxon_signed_rank([1, 2], [1, 2, 3])

    def test_too_few(self):
        with pytest.raises(ValueError):
            wilcoxon_signed_rank([1], [2])

    def test_returns_dict_keys(self):
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        result = wilcoxon_signed_rank(a, b)
        assert "statistic" in result
        assert "p_value" in result
        assert "alternative" in result
        assert "significant" in result


class TestCliffsDelta:
    def test_large_separation(self):
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        result = cliffs_delta(a, b)
        assert result["delta"] > 0.9
        assert result["magnitude"] == "large"

    def test_no_separation(self):
        a = [1, 2, 3]
        b = [1, 2, 3]
        result = cliffs_delta(a, b)
        assert abs(result["delta"]) < 0.01

    def test_negative_delta(self):
        a = [1, 2, 3]
        b = [10, 11, 12]
        result = cliffs_delta(a, b)
        assert result["delta"] < -0.9

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            cliffs_delta([], [1, 2])

    def test_magnitude_categories(self):
        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        b = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        result = cliffs_delta(a, b)
        assert result["magnitude"] in ("negligible", "small", "medium", "large")


class TestFriedmanTest:
    def test_clear_difference(self):
        data = {
            "A": [0.9, 0.8, 0.85, 0.95, 0.88],
            "B": [0.5, 0.6, 0.55, 0.45, 0.52],
            "C": [0.7, 0.65, 0.72, 0.68, 0.71],
        }
        result = friedman_test(data)
        assert result["significant"] is True
        assert result["n_datasets"] == 5
        assert result["n_algorithms"] == 3

    def test_no_difference(self):
        data = {
            "A": [0.5, 0.5, 0.5],
            "B": [0.5, 0.5, 0.5],
        }
        result = friedman_test(data)
        assert result["significant"] is False

    def test_two_algorithms(self):
        data = {
            "A": [0.9, 0.8, 0.7],
            "B": [0.5, 0.6, 0.4],
        }
        result = friedman_test(data)
        assert isinstance(result["statistic"], float)

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            friedman_test({"A": [1, 2], "B": [1, 2, 3]})

    def test_single_algorithm_raises(self):
        with pytest.raises(ValueError):
            friedman_test({"A": [1, 2, 3]})

    def test_single_dataset_raises(self):
        with pytest.raises(ValueError):
            friedman_test({"A": [1], "B": [2]})


class TestNemenyiPostHoc:
    def test_basic(self):
        data = {
            "A": [0.9, 0.8, 0.85, 0.95],
            "B": [0.5, 0.6, 0.55, 0.45],
            "C": [0.7, 0.65, 0.72, 0.68],
        }
        friedman = friedman_test(data)
        result = nemenyi_post_hoc(friedman, ["A", "B", "C"])
        assert "cd" in result
        assert "comparisons" in result
        assert "avg_ranks" in result
        assert len(result["comparisons"]) == 3

    def test_significant_pair_detected(self):
        data = {
            "A": [0.95, 0.92, 0.98, 0.96],
            "B": [0.30, 0.35, 0.28, 0.32],
        }
        friedman = friedman_test(data)
        result = nemenyi_post_hoc(friedman, ["A", "B"])
        assert len(result["significant_pairs"]) >= 1


class TestCriticalValue:
    def test_k2(self):
        assert abs(_nemenyi_critical_value(2) - 1.960) < 0.001

    def test_k5(self):
        assert abs(_nemenyi_critical_value(5) - 2.728) < 0.001

    def test_k10(self):
        assert abs(_nemenyi_critical_value(10) - 3.164) < 0.001


class TestCdDiagramData:
    def test_full_pipeline(self):
        data = {
            "E-QIEA": [0.92, 0.88, 0.95, 0.90, 0.87],
            "GA": [0.75, 0.78, 0.72, 0.80, 0.76],
            "Greedy": [0.65, 0.70, 0.68, 0.62, 0.66],
            "Random": [0.40, 0.35, 0.45, 0.38, 0.42],
        }
        result = compute_cd_diagram_data(data)
        assert "friedman" in result
        assert "nemenyi" in result
        assert "avg_ranks" in result
        assert "cd" in result
        assert "algorithm_order" in result
        assert len(result["algorithm_order"]) == 4
