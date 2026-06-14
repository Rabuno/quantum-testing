"""Command-line interface for quantum-testing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev

from quantum_testing.algorithms import GreedySetCover, QIEA, RandomSearch, SimpleGA, SimulatedAnnealing
from quantum_testing.benchmarks.defects4j_runner import AlgorithmConfig, discover_defects4j_cases, parse_int_ranges, run_defects4j_benchmark
from quantum_testing.experiment_runner import ExperimentConfig, format_experiment_report, run_experiment
from quantum_testing.batch_harvest import BatchHarvestConfig, batch_harvest_defects4j
from quantum_testing.datasets.defects4j import Defects4JConfig, collect_defects4j_matrix
from quantum_testing.multiobjective import objective_vector, pareto_front
from quantum_testing.problems.coverage import CoverageProblem
from quantum_testing.problems.combinatorial import CITModel, greedy_covering_array, qiea_covering_array
from quantum_testing.visualization import (
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


def cmd_pareto(args):
    """Sample candidate suites and print the nondominated Pareto frontier.

    Objectives (mixed maximize/minimize) are derived from
    :meth:`CoverageProblem.objectives` and filtered with
    :func:`quantum_testing.multiobjective.pareto_front`.
    """
    seed_ranges = parse_int_ranges(args.seeds) if args.seeds else [args.seed]
    algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    candidates: list[dict] = []
    for seed in seed_ranges:
        problem = CoverageProblem.synthetic(
            args.tests, args.requirements, seed=seed
        )
        for alg in algorithms:
            rep = _solve_coverage(problem, alg, seed)
            obj = problem.objectives(
                [1 if i in rep.get("selected_tests", []) else 0 for i in range(problem.n_tests)]
            )
            candidates.append(
                {
                    "seed": seed,
                    "algorithm": alg,
                    "selected_tests": rep.get("selected_tests", []),
                    **obj,
                }
            )

    # Canonical objective vector ordering:
    #   coverage_ratio(max), reduction_ratio(max), selected_count(min),
    #   total_cost(min), uncovered_count(min), fitness(max)
    maximize = [True, True, False, False, False, True]
    nd = pareto_front(candidates, key=objective_vector, maximize=maximize)

    print(
        json.dumps(
            {
                "objectives": {
                    "names": [
                        "coverage_ratio",
                        "reduction_ratio",
                        "selected_count",
                        "total_cost",
                        "uncovered_count",
                        "fitness",
                    ],
                    "maximize": maximize,
                },
                "candidates_sampled": len(candidates),
                "nondominated_count": len(nd),
                "nondominated": nd,
            },
            indent=2,
        )
    )


def cmd_qubo_export(args):
    """Export a QUBO-like description of a coverage problem.

    Accepts either a synthetic problem (``--tests`` / ``--requirements``) or
    a CSV matrix (``--matrix``), and prints the JSON-serializable return of
    :meth:`CoverageProblem.qubo_terms`.
    """
    problem = (
        CoverageProblem.load_csv(args.matrix)
        if args.matrix
        else CoverageProblem.synthetic(
            args.tests, args.requirements, seed=args.seed
        )
    )
    terms = problem.qubo_terms(
        uncovered_weight=args.uncovered_weight,
        cost_weight=args.cost_weight,
    )
    print(json.dumps(terms, indent=2))


def _parse_bug_ranges_arg(raw: str) -> dict[str, str]:
    """Parse a CLI bug-ranges string like ``"Lang:1-10,Chart:1-5"`` into a dict."""
    mapping: dict[str, str] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"expected Project:range, got {token!r}")
        project, range_str = token.split(":", 1)
        mapping[project.strip()] = range_str.strip()
    return mapping


def cmd_quick_harvest(args):
    """Harvest a small, safe preset of Defects4J bugs for local testing.

    Uses 3 bugs (Lang/1b, Lang/2b, Chart/1b) — the smallest bugs in Defects4J.
    Disk: ~600MB-1.5GB work dir (deletable), ~600KB-2.2MB output.
    RAM: ~2-3 GB. Time: ~30-60 minutes.
    """
    projects = ["Lang", "Chart"]
    bug_ranges: dict[str, str] = {"Lang": "1-2", "Chart": "1-1"}
    config = BatchHarvestConfig(
        defects4j_home=Path(args.defects4j_home),
        projects=projects,
        bug_ranges=bug_ranges,
        version="b",
        work_root=Path("/tmp/quantum-testing-defects4j"),
        output_dir=Path("datasets/defects4j"),
        test_property="tests.trigger",
        reuse_workdir=True,
        force_coverage=False,
    )
    print("=" * 60)
    print("QUICK HARVEST — 3 smallest Defects4J bugs")
    print("=" * 60)
    print(f"  Projects : {', '.join(projects)}")
    print(f"  Bugs     : Lang/1b, Lang/2b, Chart/1b")
    print(f"  Work dir : {config.work_root}  (deletable after)")
    print(f"  Output   : {config.output_dir}")
    print()
    result = batch_harvest_defects4j(config)
    print()
    print("=" * 60)
    print(f"Quick harvest complete: {len(result.results)} OK, {len(result.failures)} FAILED")
    print(f"Total tests harvested: {result.total_tests_sum}")
    print(f"Total requirements harvested: {result.total_requirements_sum}")
    if result.failures:
        print()
        print("Failures:")
        for f in result.failures:
            print(f"  {f['project']}/{f['bug_id']}: {f['error']}")
    print()
    print("Next steps:")
    print("  1. Run experiment:")
    print("       uv run python -m quantum_testing.cli experiment \\")
    print("         --projects Lang,Chart --bugs 'Lang:1-2,Chart:1-1' \\")
    print("         --algorithms greedy,qiea,enhanced_qiea,ga,random,sa \\")
    print("         --seeds 42,123,456,789,1024")
    print("  2. Delete work dir when done:")
    print("       rm -rf /tmp/quantum-testing-defects4j")


def cmd_plot(args):
    """Generate publication-ready figures from an experiment directory.

    Reads experiment artifacts (statistical analysis, benchmark results) and
    produces a complete figure set for the paper.
    """
    exp_dir = Path(args.experiment_dir)
    out_dir = args.output_dir or str(exp_dir / "figures")

    if not exp_dir.exists():
        print(f"Error: experiment directory not found: {exp_dir}")
        return

    # Map figure name → function
    FIGURE_MAP = {
        "cd": _plot_cd_from_dir,
        "box_coverage": _plot_box_coverage_from_dir,
        "box_reduction": _plot_box_reduction_from_dir,
        "runtime": _plot_runtime_from_dir,
        "convergence": _plot_convergence_from_dir,
        "stat_summary": _plot_stat_summary_from_dir,
        "heatmap": _plot_heatmap_from_args,
        "all": _plot_all_from_dir,
    }

    fig_type = args.type
    if fig_type not in FIGURE_MAP:
        print(f"Unknown figure type: {fig_type}. Choose from: {', '.join(FIGURE_MAP)}")
        return

    FIGURE_MAP[fig_type](exp_dir, out_dir, args)


def _plot_cd_from_dir(exp_dir, out_dir, args):
    per_bug_path = exp_dir / "per_bug_analysis.json"
    if not per_bug_path.exists():
        print("per_bug_analysis.json not found in experiment directory")
        return
    per_bug = json.loads(per_bug_path.read_text())
    cd_data: dict[str, list[float]] = {}
    for bug_key, bug_data in per_bug.items():
        for alg, scores in bug_data.items():
            if isinstance(scores, dict) and "coverage_mean" in scores:
                cd_data.setdefault(alg, []).append(scores["coverage_mean"])
    if not cd_data:
        print("No coverage data found for CD diagram")
        return
    path = plot_cd_diagram(cd_data, outfile=Path(out_dir) / "cd_diagram.png")
    print(f"CD diagram saved to: {path}")


def _load_summary(exp_dir):
    for candidate in ["benchmark/summary.json", "summary.json"]:
        p = exp_dir / candidate
        if p.exists():
            return json.loads(p.read_text())
    return None


def _plot_box_coverage_from_dir(exp_dir, out_dir, args):
    summary = _load_summary(exp_dir)
    if not summary:
        print("summary.json not found in experiment directory")
        return
    path = plot_box_coverage(summary, Path(out_dir) / "box_coverage.png")
    print(f"Box plot (coverage) saved to: {path}")


def _plot_box_reduction_from_dir(exp_dir, out_dir, args):
    summary = _load_summary(exp_dir)
    if not summary:
        print("summary.json not found in experiment directory")
        return
    path = plot_box_reduction(summary, Path(out_dir) / "box_reduction.png")
    print(f"Box plot (reduction) saved to: {path}")


def _plot_runtime_from_dir(exp_dir, out_dir, args):
    summary = _load_summary(exp_dir)
    if not summary:
        print("summary.json not found in experiment directory")
        return
    path = plot_runtime_comparison(summary, Path(out_dir) / "runtime.png")
    print(f"Runtime comparison saved to: {path}")


def _plot_convergence_from_dir(exp_dir, out_dir, args):
    for candidate in ["benchmark/raw_runs.jsonl", "raw_runs.jsonl"]:
        p = exp_dir / candidate
        if p.exists():
            raw_path = p
            break
    else:
        print("raw_runs.jsonl not found in experiment directory")
        return
    histories: dict[str, list[list[float]]] = {}
    with raw_path.open() as f:
        for line in f:
            rec = json.loads(line)
            alg = rec.get("algorithm", "unknown")
            hist = rec.get("history", rec.get("fitness_history", []))
            if hist:
                histories.setdefault(alg, []).append(hist)
    if not histories:
        print("No convergence history found in raw runs")
        return
    path = plot_convergence(histories, outfile=Path(out_dir) / "convergence.png")
    print(f"Convergence curves saved to: {path}")


def _plot_stat_summary_from_dir(exp_dir, out_dir, args):
    stat_path = exp_dir / "statistical_analysis.json"
    if not stat_path.exists():
        print("statistical_analysis.json not found in experiment directory")
        return
    stat = json.loads(stat_path.read_text())
    path = plot_statistical_summary(stat, Path(out_dir) / "stat_summary.png")
    print(f"Statistical summary saved to: {path}")


def _plot_heatmap_from_args(exp_dir, out_dir, args):
    if not args.matrix:
        print("Heatmap requires --matrix path")
        return
    path = plot_heatmap(args.matrix, outfile=Path(out_dir) / "heatmap.png")
    print(f"Heatmap saved to: {path}")


def _plot_all_from_dir(exp_dir, out_dir, args):
    figures = generate_all_figures(exp_dir, out_dir)
    if figures:
        print(f"Generated {len(figures)} figures:")
        for fig_path in figures:
            print(f"  {fig_path}")
    else:
        print("No figures generated — check experiment directory for required artifacts")


def cmd_batch_harvest(args):
    bug_ranges = _parse_bug_ranges_arg(args.bugs)
    projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    config = BatchHarvestConfig(
        defects4j_home=Path(args.defects4j_home),
        projects=projects,
        bug_ranges=bug_ranges,
        version=args.version,
        work_root=Path(args.work_root),
        output_dir=Path(args.output_dir),
        test_property=args.test_property,
        limit_tests=args.limit_tests,
        reuse_workdir=not args.no_reuse_workdir,
        force_coverage=args.force_coverage,
        test_filter=args.test_filter,
    )
    result = batch_harvest_defects4j(config)
    print()
    print("=" * 60)
    print(f"Batch harvest complete: {len(result.results)} OK, {len(result.failures)} FAILED")
    print(f"Total tests harvested: {result.total_tests_sum}")
    print(f"Total requirements harvested: {result.total_requirements_sum}")
    if result.failures:
        print()
        print("Failures:")
        for f in result.failures:
            print(f"  {f['project']}/{f['bug_id']}: {f['error']}")


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


def cmd_experiment(args):
    """Run a full multi-algorithm, multi-bug experiment with statistical analysis."""
    projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    bug_ranges = _parse_bug_ranges_arg(args.bugs)
    algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    seeds = parse_int_ranges(args.seeds) or [42]

    config = ExperimentConfig(
        matrix_root=Path(args.matrix_root),
        projects=projects,
        bug_ranges=bug_ranges,
        algorithms=algorithms,
        seeds=seeds,
        output_dir=Path(args.output_dir),
        run_id=args.run_id,
        qaoa_p=args.qaoa_p,
        qaoa_max_qubits=args.qaoa_max_qubits,
        nsga3_pop_size=args.nsga3_pop_size,
        nsga3_generations=args.nsga3_generations,
    )

    result = run_experiment(config)

    report = format_experiment_report(result)
    print(report)

    report_format = args.report_format
    out_dir = Path(result.raw_result.get("artifacts", {}).get("raw_runs_jsonl", "")).parent
    if report_format in ("text", "both"):
        text_path = out_dir / "experiment_report.txt"
        text_path.write_text(report)
        print(f"\nText report saved to: {text_path}")
    if report_format in ("json", "both"):
        json_path = out_dir / "experiment_result.json"
        payload = {
            "run_id": result.run_id,
            "statistical_analysis": result.statistical_analysis,
            "per_bug_analysis": result.per_bug_analysis,
        }
        json_path.write_text(json.dumps(payload, indent=2, default=str))
        print(f"JSON result saved to: {json_path}")


def build_parser():
    p = argparse.ArgumentParser(prog="quantum-testing")
    sub = p.add_subparsers(required=True)
    d = sub.add_parser("demo"); d.add_argument("--seed", type=int, default=42); d.set_defaults(func=cmd_demo)
    m = sub.add_parser("minimize"); m.add_argument("--matrix"); m.add_argument("--algorithm", choices=["qiea", "greedy", "ga", "random", "sa"], default="qiea"); m.add_argument("--seed", type=int, default=42); m.add_argument("--history", action="store_true"); m.set_defaults(func=cmd_minimize)
    c = sub.add_parser("cit"); c.add_argument("--model", required=True); c.add_argument("--algorithm", choices=["greedy", "qiea"], default="greedy"); c.add_argument("--strength", type=int); c.add_argument("--rows", type=int, default=8); c.add_argument("--seed", type=int, default=42); c.add_argument("--history", action="store_true"); c.set_defaults(func=cmd_cit)
    b = sub.add_parser("benchmark"); b.add_argument("--tests", type=int, default=30); b.add_argument("--requirements", type=int, default=20); b.add_argument("--seed", type=int, default=42); b.add_argument("--runs", type=int, default=10); b.add_argument("--algorithms", default="greedy,qiea,ga,random,sa"); b.add_argument("--raw", action="store_true"); b.set_defaults(func=cmd_benchmark)
    pareto = sub.add_parser("pareto", help="Sample suites and print nondominated Pareto frontier")
    pareto.add_argument("--tests", type=int, default=20)
    pareto.add_argument("--requirements", type=int, default=15)
    pareto.add_argument("--seed", type=int, default=42)
    pareto.add_argument("--seeds", help="Seed ranges, e.g. 1-5,7")
    pareto.add_argument("--algorithms", default="greedy,qiea,ga,random,sa")
    pareto.set_defaults(func=cmd_pareto)
    qubo = sub.add_parser("qubo-export", help="Export QUBO-like terms for a coverage problem")
    qubo.add_argument("--matrix", help="CSV coverage matrix (omit for synthetic)")
    qubo.add_argument("--tests", type=int, default=12)
    qubo.add_argument("--requirements", type=int, default=8)
    qubo.add_argument("--seed", type=int, default=42)
    qubo.add_argument("--uncovered-weight", type=float, default=2.0)
    qubo.add_argument("--cost-weight", type=float, default=None)
    qubo.set_defaults(func=cmd_qubo_export)
    qh = sub.add_parser("quick-harvest", help="Harvest 3 smallest Defects4J bugs (Lang/1b, Lang/2b, Chart/1b) — safe for local testing")
    qh.add_argument("--defects4j-home", required=True, help="Path to local Defects4J installation")
    qh.set_defaults(func=cmd_quick_harvest)
    bh = sub.add_parser("defects4j-harvest", help="Batch-harvest Defects4J coverage matrices for multiple projects/bugs")
    bh.add_argument("--defects4j-home", required=True)
    bh.add_argument("--projects", required=True, help="Comma-separated project IDs, e.g. Lang,Chart,Cli,Math")
    bh.add_argument("--bugs", required=True, help="Per-project bug ranges, e.g. Lang:1-10,Chart:1-5,Cli:1-3,Math:1-8")
    bh.add_argument("--version", choices=["b", "f"], default="b")
    bh.add_argument("--work-root", default="/tmp/quantum-testing-defects4j")
    bh.add_argument("--output-dir", default="datasets/defects4j")
    bh.add_argument("--test-property", choices=["tests.trigger", "tests.relevant", "tests.all"], default="tests.trigger")
    bh.add_argument("--limit-tests", type=int)
    bh.add_argument("--no-reuse-workdir", action="store_true")
    bh.add_argument("--force-coverage", action="store_true")
    bh.add_argument("--test-filter", help="Regex applied after optional class-to-method expansion")
    bh.set_defaults(func=cmd_batch_harvest)
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
    exp = sub.add_parser("experiment", help="Run full multi-algorithm experiment with statistical analysis")
    exp.add_argument("--matrix-root", default="datasets/defects4j")
    exp.add_argument("--projects", required=True, help="Comma-separated project IDs, e.g. Lang,Chart,Cli")
    exp.add_argument("--bugs", required=True, help="Per-project bug ranges, e.g. Lang:1-10,Chart:1-5")
    exp.add_argument("--algorithms", default="greedy,qiea,enhanced_qiea,ga,random,sa")
    exp.add_argument("--seeds", default="42,123,456,789,1024")
    exp.add_argument("--output-dir", default="artifacts/experiment")
    exp.add_argument("--run-id")
    exp.add_argument("--qaoa-p", type=int, default=1)
    exp.add_argument("--qaoa-max-qubits", type=int, default=25)
    exp.add_argument("--nsga3-pop-size", type=int, default=50)
    exp.add_argument("--nsga3-generations", type=int, default=100)
    exp.add_argument("--report-format", choices=["json", "text", "both"], default="both")
    exp.set_defaults(func=cmd_experiment)
    plot = sub.add_parser("plot", help="Generate publication-ready figures from experiment results")
    plot.add_argument("--experiment-dir", required=True, help="Path to experiment output directory")
    plot.add_argument("--output-dir", help="Figure output directory (default: <experiment-dir>/figures)")
    plot.add_argument(
        "--type",
        choices=["cd", "box_coverage", "box_reduction", "runtime", "convergence", "stat_summary", "heatmap", "all"],
        default="all",
        help="Figure type to generate (default: all)",
    )
    plot.add_argument("--matrix", help="Path to coverage matrix CSV (required for heatmap type)")
    plot.add_argument("--format", choices=["png", "pdf", "svg"], default="png", help="Output format (default: png)")
    plot.set_defaults(func=cmd_plot)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
