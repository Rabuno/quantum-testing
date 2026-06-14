"""Tests for the visualization module.

All plot functions are tested by verifying they return valid Path objects
pointing to existing files with non-zero size. No pixel-level assertions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantum_testing.visualization import (
    ALG_NAMES,
    PALETTE,
    _alg_label,
    _save,
    _setup_style,
    generate_all_figures,
    plot_box_coverage,
    plot_box_reduction,
    plot_cd_diagram,
    plot_convergence,
    plot_heatmap,
    plot_pareto_front,
    plot_runtime_comparison,
    plot_statistical_summary,
)


class TestHelpers:
    def test_alg_label_known(self):
        assert _alg_label("qiea") == "QIEA"
        assert _alg_label("enhanced_qiea") == "E-QIEA"
        assert _alg_label("greedy") == "Greedy"

    def test_alg_label_unknown(self):
        assert _alg_label("custom_algo") == "custom_algo"

    def test_palette_has_colors(self):
        assert len(PALETTE) >= 6
        for color in PALETTE:
            assert color.startswith("#")

    def test_alg_names_complete(self):
        for key in ["qiea", "enhanced_qiea", "greedy", "ga", "random", "sa"]:
            assert key in ALG_NAMES

    def test_setup_style(self):
        _setup_style()  # Should not raise

    def test_save(self, tmp_path):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        path = _save(fig, tmp_path / "test.png")
        assert path.exists()
        assert path.stat().st_size > 0


class TestCDDiagram:
    def test_returns_path(self, sample_cd_data, tmp_path):
        out = tmp_path / "cd.png"
        result = plot_cd_diagram(sample_cd_data, outfile=out)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_custom_title(self, sample_cd_data, tmp_path):
        out = tmp_path / "cd_title.pdf"
        result = plot_cd_diagram(sample_cd_data, title="Custom", outfile=out)
        assert result.exists()

    def test_two_algorithms(self, tmp_path):
        data = {"qiea": [0.9, 0.8], "greedy": [0.85, 0.75]}
        result = plot_cd_diagram(data, outfile=tmp_path / "cd2.png")
        assert result.exists()


class TestBoxPlots:
    def test_coverage(self, sample_summary, tmp_path):
        result = plot_box_coverage(sample_summary, tmp_path / "box_cov.png")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_reduction(self, sample_summary, tmp_path):
        result = plot_box_reduction(sample_summary, tmp_path / "box_red.png")
        assert result.exists()

    def test_runtime(self, sample_summary, tmp_path):
        result = plot_runtime_comparison(sample_summary, tmp_path / "runtime.png")
        assert result.exists()

    def test_empty_data(self, tmp_path):
        with pytest.raises(ValueError):
            plot_box_coverage({}, tmp_path / "empty.png")

    def test_missing_key(self, tmp_path):
        with pytest.raises(ValueError):
            plot_box_coverage({"qiea": {"no_data": 1}}, tmp_path / "bad.png")


class TestConvergence:
    def test_basic(self, sample_histories, tmp_path):
        result = plot_convergence(sample_histories, outfile=tmp_path / "conv.png")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_smoothing(self, sample_histories, tmp_path):
        result = plot_convergence(
            sample_histories, outfile=tmp_path / "conv_smooth.png",
            smooth_window=3)
        assert result.exists()

    def test_empty_histories(self, tmp_path):
        result = plot_convergence({}, outfile=tmp_path / "conv_empty.png")
        assert result.exists()

    def test_single_run(self, tmp_path):
        histories = {"qiea": [[0.1, 0.3, 0.5, 0.7, 0.9]]}
        result = plot_convergence(histories, outfile=tmp_path / "conv_single.png")
        assert result.exists()


class TestHeatmap:
    def test_basic(self, sample_coverage_csv, tmp_path):
        result = plot_heatmap(sample_coverage_csv, outfile=tmp_path / "heat.png")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_with_limits(self, sample_coverage_csv, tmp_path):
        result = plot_heatmap(
            sample_coverage_csv, outfile=tmp_path / "heat_small.png",
            max_tests=5, max_reqs=8)
        assert result.exists()


class TestParetoFront:
    def test_basic(self, sample_pareto_candidates, tmp_path):
        result = plot_pareto_front(
            sample_pareto_candidates, outfile=tmp_path / "pareto.png")
        assert result.exists()
        assert result.stat().st_size > 0


class TestStatSummary:
    def test_basic(self, sample_stat_analysis, tmp_path):
        result = plot_statistical_summary(
            sample_stat_analysis, tmp_path / "stat.png")
        assert result.exists()
        assert result.stat().st_size > 0

    def test_empty(self, tmp_path):
        result = plot_statistical_summary({}, tmp_path / "stat_empty.png")
        assert result.exists()


class TestGenerateAllFigures:
    def test_full_generation(self, sample_experiment_dir, tmp_path):
        out_dir = tmp_path / "all_figs"
        figures = generate_all_figures(sample_experiment_dir, out_dir)
        assert len(figures) > 0
        for fig_path in figures:
            assert fig_path.exists()
            assert fig_path.stat().st_size > 0

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_dir = tmp_path / "empty_exp"
        empty_dir.mkdir()
        figures = generate_all_figures(empty_dir, tmp_path / "empty_figs")
        assert figures == []
