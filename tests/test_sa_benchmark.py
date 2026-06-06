import json
from quantum_testing.algorithms import SimulatedAnnealing
from quantum_testing.problems.coverage import CoverageProblem
from quantum_testing.cli import main


def test_simulated_annealing_qubo_energy_finds_full_coverage():
    problem = CoverageProblem.from_matrix([[1,0,0], [0,1,0], [0,0,1], [1,1,1]])
    sol, energy, history = SimulatedAnnealing(problem.n_tests, problem.qubo_energy, max_steps=500, seed=5).run(verbose=False)
    report = problem.report(sol)
    assert report.coverage_ratio == 1.0
    assert energy <= problem.qubo_energy([1, 1, 1, 1])
    assert history


def test_cli_multirun_benchmark_summary(capsys):
    main(["benchmark", "--tests", "8", "--requirements", "5", "--runs", "3", "--seed", "10"])
    data = json.loads(capsys.readouterr().out)
    assert data["dataset"]["runs"] == 3
    assert "summary" in data
    assert "sa" in data["summary"]
    assert data["summary"]["qiea"]["runs"] == 3
