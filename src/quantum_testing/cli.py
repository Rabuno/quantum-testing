"""Command-line interface for quantum-testing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

from quantum_testing.algorithms import GreedySetCover, QIEA, RandomSearch, SimpleGA, SimulatedAnnealing
from quantum_testing.benchmarks.defects4j_runner import AlgorithmConfig, discover_defects4j_cases, parse_int_ranges, run_defects4j_benchmark
from quantum_testing.datasets.defects4j import Defects4JConfig, collect_defects4j_matrix
from quantum_testing.problems.coverage import CoverageProblem
from quantum_testing.problems.combinatorial import CITModel, greedy_covering_array, qiea_covering_array


def onemax(bits):
    return sum(bits)


def _solve_coverage(problem: CoverageProblem, algorithm: str, seed: int, include_history: bool = False) -> dict:
    if algorithm == "greedy":
        selected, _, _ = GreedySetCover(problem.coverage_sets, seed=seed).run(verbose=False)
        sol = [1 if i in selected else 0 for i in range(problem.n_tests)]
        return problem.report(sol).to_dict()
    if algorithm == "qiea":
        sol, _, hist = QIEA(problem.n_tests, pop_size=24, max_gen=160, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        if include_history:
            rep["history"] = hist
        return rep
    if algorithm == "ga":
        sol, _, hist = SimpleGA(problem.n_tests, pop_size=24, max_gen=160, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        if include_history:
            rep["history"] = hist
        return rep
    if algorithm == "random":
        sol, _, hist = RandomSearch(problem.n_tests, max_evals=24 * 160, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        if include_history:
            rep["history"] = hist
        return rep
    if algorithm == "sa":
        sol, energy, hist = SimulatedAnnealing(problem.n_tests, energy_fn=problem.qubo_energy, max_steps=3000, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["qubo_energy"] = energy
        if include_history:
            rep["energy_history"] = hist
        return rep
    raise ValueError(f"unknown algorithm: {algorithm}")


def _summarize_runs(runs: list[dict]) -> dict:
    def vals(key: str) -> list[float]:
        return [float(r[key]) for r in runs]
    return {
        "runs": len(runs),
        "coverage_mean": mean(vals("coverage_ratio")),
        "coverage_std": pstdev(vals("coverage_ratio")) if len(runs) > 1 else 0.0,
        "selected_mean": mean(vals("selected_count")),
        "selected_std": pstdev(vals("selected_count")) if len(runs) > 1 else 0.0,
        "reduction_mean": mean(vals("reduction_ratio")),
        "full_coverage_rate": sum(1 for r in runs if r["coverage_ratio"] >= 1.0) / len(runs),
        "best_selected_full_coverage": min((r["selected_count"] for r in runs if r["coverage_ratio"] >= 1.0), default=None),
    }


def cmd_demo(args):
    q = QIEA(20, 12, 100, evaluate_fn=onemax, seed=args.seed)
    sol, fit, _ = q.run(verbose=False)
    problem = CoverageProblem.synthetic(20, 15, seed=args.seed)
    cov = _solve_coverage(problem, "qiea", args.seed)
    print(json.dumps({"onemax": {"fitness": fit, "solution": sol}, "coverage": cov}, indent=2))


def cmd_minimize(args):
    problem = CoverageProblem.load_csv(args.matrix) if args.matrix else CoverageProblem.synthetic(seed=args.seed)
    print(json.dumps(_solve_coverage(problem, args.algorithm, args.seed, include_history=args.history), indent=2))


def _constraint_from_model(data):
    forbidden = data.get("forbidden", [])
    def constraint(row):
        for partial in forbidden:
            if all(row.get(k) == v for k, v in partial.items()):
                return False
        return True
    return constraint if forbidden else None


def cmd_cit(args):
    data = json.loads(Path(args.model).read_text())
    strength = args.strength or data.get("strength", 2)
    model = CITModel(data["parameters"], strength=strength, constraint=_constraint_from_model(data))
    if args.algorithm == "greedy":
        rows, report = greedy_covering_array(model, max_rows=args.rows, seed=args.seed)
    else:
        rows, report = qiea_covering_array(model, n_rows=args.rows, seed=args.seed)
    if not args.history and "history" in report:
        report = {k: v for k, v in report.items() if k != "history"}
    print(json.dumps({"rows": rows, "report": report}, indent=2))


def cmd_benchmark(args):
    algorithms = args.algorithms.split(",")
    by_alg = {alg: [] for alg in algorithms}
    for offset in range(args.runs):
        seed = args.seed + offset
        problem = CoverageProblem.synthetic(args.tests, args.requirements, seed=seed)
        for alg in algorithms:
            by_alg[alg].append(_solve_coverage(problem, alg, seed))
    payload = {
        "dataset": {"tests": args.tests, "requirements": args.requirements, "seed": args.seed, "runs": args.runs},
        "algorithms": algorithms,
        "summary": {alg: _summarize_runs(runs) for alg, runs in by_alg.items()},
    }
    if args.raw:
        payload["runs"] = by_alg
    print(json.dumps(payload, indent=2))


def cmd_defects4j_matrix(args):
    cfg = Defects4JConfig(
        defects4j_home=Path(args.defects4j_home),
        project=args.project,
        bug_id=args.bug,
        version=args.version,
        work_root=Path(args.work_root),
        output_dir=Path(args.output_dir),
        test_property=args.test_property,
        limit_tests=args.limit_tests,
        reuse_workdir=not args.no_reuse_workdir,
        force_coverage=args.force_coverage,
        test_filter=args.test_filter,
    )
    result = collect_defects4j_matrix(cfg)
    print(json.dumps(result.__dict__ | {
        "matrix_csv": str(result.matrix_csv),
        "tests_txt": str(result.tests_txt),
        "requirements_txt": str(result.requirements_txt),
        "metadata_json": str(result.metadata_json),
    }, indent=2, default=str))


def cmd_defects4j_benchmark(args):
    projects = args.projects.split(",") if args.projects else None
    bugs = parse_int_ranges(args.bugs)
    seeds = parse_int_ranges(args.seeds) or [42]
    algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    cases = discover_defects4j_cases(args.matrix_root, projects=projects, bugs=bugs, version=args.version)
    config = AlgorithmConfig(
        qiea_pop_size=args.qiea_pop_size,
        qiea_generations=args.qiea_generations,
        qiea_rotation_angle=args.qiea_rotation_angle,
        ga_pop_size=args.ga_pop_size,
        ga_generations=args.ga_generations,
        random_evals=args.random_evals,
        sa_steps=args.sa_steps,
    )
    result = run_defects4j_benchmark(
        cases=cases,
        algorithms=algorithms,
        seeds=seeds,
        output_dir=args.output_dir,
        run_id=args.run_id,
        config=config,
        paper_metrics_path=args.paper_metrics,
    )
    print(json.dumps({
        "run_id": result["run_id"],
        "cases": len(cases),
        "records": result["summary"]["total_records"],
        "summary": result["summary"],
        "comparison": result["comparison"],
        "artifacts": result["artifacts"],
    }, indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="quantum-testing")
    sub = p.add_subparsers(required=True)
    d = sub.add_parser("demo"); d.add_argument("--seed", type=int, default=42); d.set_defaults(func=cmd_demo)
    m = sub.add_parser("minimize"); m.add_argument("--matrix"); m.add_argument("--algorithm", choices=["qiea", "greedy", "ga", "random", "sa"], default="qiea"); m.add_argument("--seed", type=int, default=42); m.add_argument("--history", action="store_true"); m.set_defaults(func=cmd_minimize)
    c = sub.add_parser("cit"); c.add_argument("--model", required=True); c.add_argument("--algorithm", choices=["greedy", "qiea"], default="greedy"); c.add_argument("--strength", type=int); c.add_argument("--rows", type=int, default=8); c.add_argument("--seed", type=int, default=42); c.add_argument("--history", action="store_true"); c.set_defaults(func=cmd_cit)
    b = sub.add_parser("benchmark"); b.add_argument("--tests", type=int, default=30); b.add_argument("--requirements", type=int, default=20); b.add_argument("--seed", type=int, default=42); b.add_argument("--runs", type=int, default=10); b.add_argument("--algorithms", default="greedy,qiea,ga,random,sa"); b.add_argument("--raw", action="store_true"); b.set_defaults(func=cmd_benchmark)
    d4j = sub.add_parser("defects4j-matrix", help="Harvest a Defects4J test x covered-line matrix")
    d4j.add_argument("--defects4j-home", required=True)
    d4j.add_argument("--project", required=True)
    d4j.add_argument("--bug", type=int, required=True)
    d4j.add_argument("--version", choices=["b", "f"], default="b")
    d4j.add_argument("--work-root", default="/tmp/quantum-testing-defects4j")
    d4j.add_argument("--output-dir", default="datasets/defects4j")
    d4j.add_argument("--test-property", choices=["tests.trigger", "tests.relevant", "tests.all"], default="tests.trigger")
    d4j.add_argument("--limit-tests", type=int)
    d4j.add_argument("--no-reuse-workdir", action="store_true")
    d4j.add_argument("--force-coverage", action="store_true")
    d4j.add_argument("--test-filter", help="Regex applied after optional class-to-method expansion")
    d4j.set_defaults(func=cmd_defects4j_matrix)
    d4jb = sub.add_parser("defects4j-benchmark", help="Run QIEA and baselines on harvested Defects4J matrices")
    d4jb.add_argument("--matrix-root", default="datasets/defects4j")
    d4jb.add_argument("--projects", help="Comma-separated project IDs, e.g. Lang,Chart")
    d4jb.add_argument("--bugs", help="Bug ids/ranges, e.g. 1,2,5-10")
    d4jb.add_argument("--version", choices=["b", "f"], default="b")
    d4jb.add_argument("--algorithms", default="greedy,qiea,ga,random,sa")
    d4jb.add_argument("--seeds", default="42")
    d4jb.add_argument("--output-dir", default="artifacts/defects4j-benchmark")
    d4jb.add_argument("--run-id")
    d4jb.add_argument("--paper-metrics")
    d4jb.add_argument("--qiea-pop-size", type=int, default=24)
    d4jb.add_argument("--qiea-generations", type=int, default=160)
    d4jb.add_argument("--qiea-rotation-angle", type=float, default=0.01 * 3.141592653589793)
    d4jb.add_argument("--ga-pop-size", type=int, default=24)
    d4jb.add_argument("--ga-generations", type=int, default=160)
    d4jb.add_argument("--random-evals", type=int)
    d4jb.add_argument("--sa-steps", type=int, default=3000)
    d4jb.set_defaults(func=cmd_defects4j_benchmark)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
