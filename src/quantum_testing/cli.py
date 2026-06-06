"""Command-line interface for quantum-testing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from quantum_testing.algorithms import GreedySetCover, QIEA, RandomSearch, SimpleGA
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
        if include_history:
            rep["history"] = hist
        else:
            rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        return rep
    if algorithm == "ga":
        sol, _, hist = SimpleGA(problem.n_tests, pop_size=24, max_gen=160, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        if include_history:
            rep["history"] = hist
        else:
            rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        return rep
    if algorithm == "random":
        sol, _, hist = RandomSearch(problem.n_tests, max_evals=24*160, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        if include_history:
            rep["history"] = hist
        else:
            rep["final_fitness"] = hist[-1] if hist else rep["fitness"]
        return rep
    raise ValueError(f"unknown algorithm: {algorithm}")


def cmd_demo(args):
    q = QIEA(20, 12, 100, evaluate_fn=onemax, seed=args.seed)
    sol, fit, _ = q.run(verbose=False)
    problem = CoverageProblem.synthetic(20, 15, seed=args.seed)
    cov = _solve_coverage(problem, "qiea", args.seed)
    print(json.dumps({"onemax": {"fitness": fit, "solution": sol}, "coverage": cov}, indent=2))


def cmd_minimize(args):
    problem = CoverageProblem.load_csv(args.matrix) if args.matrix else CoverageProblem.synthetic(seed=args.seed)
    print(json.dumps(_solve_coverage(problem, args.algorithm, args.seed), indent=2))


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
    print(json.dumps({"rows": rows, "report": report}, indent=2))


def cmd_benchmark(args):
    problem = CoverageProblem.synthetic(args.tests, args.requirements, seed=args.seed)
    results = {alg: _solve_coverage(problem, alg, args.seed) for alg in ["greedy", "qiea", "ga", "random"]}
    print(json.dumps({"dataset": {"tests": args.tests, "requirements": args.requirements, "seed": args.seed}, "results": results}, indent=2))


def build_parser():
    p = argparse.ArgumentParser(prog="quantum-testing")
    sub = p.add_subparsers(required=True)
    d = sub.add_parser("demo"); d.add_argument("--seed", type=int, default=42); d.set_defaults(func=cmd_demo)
    m = sub.add_parser("minimize"); m.add_argument("--matrix"); m.add_argument("--algorithm", choices=["qiea","greedy","ga","random"], default="qiea"); m.add_argument("--seed", type=int, default=42); m.set_defaults(func=cmd_minimize)
    c = sub.add_parser("cit"); c.add_argument("--model", required=True); c.add_argument("--algorithm", choices=["greedy","qiea"], default="greedy"); c.add_argument("--strength", type=int); c.add_argument("--rows", type=int, default=8); c.add_argument("--seed", type=int, default=42); c.set_defaults(func=cmd_cit)
    b = sub.add_parser("benchmark"); b.add_argument("--tests", type=int, default=30); b.add_argument("--requirements", type=int, default=20); b.add_argument("--seed", type=int, default=42); b.set_defaults(func=cmd_benchmark)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
