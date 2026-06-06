from quantum_testing.benchmarks.defects4j_runner import (
    AlgorithmConfig,
    discover_defects4j_cases,
    parse_int_ranges,
    run_defects4j_benchmark,
)


def test_parse_int_ranges():
    assert parse_int_ranges("1,3-5") == [1, 3, 4, 5]


def test_discover_defects4j_cases_fixture():
    cases = discover_defects4j_cases("tests/fixtures/defects4j", projects=["Lang"], bugs=[1])
    assert len(cases) == 1
    assert cases[0].project == "Lang"
    assert cases[0].bug_id == 1


def test_run_defects4j_benchmark_fixture(tmp_path):
    cases = discover_defects4j_cases("tests/fixtures/defects4j")
    result = run_defects4j_benchmark(
        cases,
        algorithms=["greedy", "qiea", "ga", "random", "sa"],
        seeds=[1, 2],
        output_dir=tmp_path,
        run_id="fixture",
        config=AlgorithmConfig(
            qiea_pop_size=8,
            qiea_generations=20,
            ga_pop_size=8,
            ga_generations=20,
            sa_steps=100,
        ),
        paper_metrics_path="docs/paper_metrics/example_2604_26674.json",
    )
    assert result["summary"]["total_records"] == 9  # greedy once, four stochastic algs x two seeds
    assert "qiea" in result["summary"]["algorithms"]
    assert result["summary"]["algorithms"]["qiea"]["coverage"]["mean"] >= 0.0
    assert (tmp_path / "fixture" / "raw_runs.jsonl").exists()
    assert (tmp_path / "fixture" / "summary.json").exists()
    assert "paper_comparison" in result
