import json
from quantum_testing.cli import main


def test_cli_benchmark_smoke(capsys):
    main(["benchmark", "--tests", "8", "--requirements", "5", "--seed", "4"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "summary" in data
    assert "qiea" in data["summary"]


def test_cli_pareto_smoke(capsys):
    main(
        [
            "pareto",
            "--tests",
            "10",
            "--requirements",
            "8",
            "--seed",
            "1",
            "--algorithms",
            "greedy,qiea",
        ]
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "objectives" in data
    assert data["objectives"]["names"] == [
        "coverage_ratio",
        "reduction_ratio",
        "selected_count",
        "total_cost",
        "uncovered_count",
        "fitness",
    ]
    assert data["candidates_sampled"] >= 2
    # Nondominated list is non-empty and a subset of candidates.
    assert 0 < data["nondominated_count"] <= data["candidates_sampled"]
    # Every nondominated entry carries the objective keys.
    for entry in data["nondominated"]:
        assert "coverage_ratio" in entry
        assert "algorithm" in entry


def test_cli_pareto_with_seed_ranges(capsys):
    main(
        [
            "pareto",
            "--tests",
            "8",
            "--requirements",
            "6",
            "--seeds",
            "1-2",
            "--algorithms",
            "greedy",
        ]
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["candidates_sampled"] == 2


def test_cli_qubo_export_smoke(capsys):
    main(["qubo-export", "--tests", "6", "--requirements", "4", "--seed", "3"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["sense"] == "minimize"
    assert data["offset"] == 0.0
    assert len(data["variables"]) == 6
    assert set(data["linear"].keys()) == {f"x{i}" for i in range(6)}
    assert "metadata" in data


def test_cli_qubo_export_custom_weights(capsys):
    main(
        [
            "qubo-export",
            "--tests",
            "5",
            "--requirements",
            "4",
            "--uncovered-weight",
            "3.0",
            "--cost-weight",
            "0.25",
        ]
    )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["metadata"]["uncovered_weight"] == 3.0
    assert data["metadata"]["cost_weight"] == 0.25
