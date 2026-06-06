from quantum_testing.algorithms import GreedySetCover
from quantum_testing.problems.coverage import CoverageProblem


def test_coverage_report_and_greedy_full_cover():
    problem = CoverageProblem.from_matrix([[1,0,0], [0,1,0], [0,0,1], [1,1,0]])
    selected, _, covered = GreedySetCover(problem.coverage_sets, seed=1).run(verbose=False)
    sol = [1 if i in selected else 0 for i in range(problem.n_tests)]
    report = problem.report(sol)
    assert covered == {0, 1, 2}
    assert report.coverage_ratio == 1.0
    assert report.selected_count <= 3
    assert report.reduction_ratio >= 0.25
