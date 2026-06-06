"""Defects4J-focused benchmark runner.

The runner consumes harvested ``datasets/defects4j/<Project>/<BugVersion>/matrix.csv``
artifacts and evaluates QIEA against classical baselines. It does not require a
live Defects4J installation unless the caller separately harvests matrices.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from quantum_testing.algorithms import GreedySetCover, QIEA, RandomSearch, SimpleGA, SimulatedAnnealing
from quantum_testing.benchmarks.paper_metrics import compare_to_paper_metrics, load_paper_metrics
from quantum_testing.benchmarks.reporting import compare_primary_to_baselines, summarize_records
from quantum_testing.problems.coverage import CoverageProblem


@dataclass
class Defects4JBenchmarkCase:
    project: str
    bug_id: int
    version: str
    matrix_csv: Path
    metadata_json: Path | None = None


@dataclass
class AlgorithmConfig:
    qiea_pop_size: int = 24
    qiea_generations: int = 160
    qiea_rotation_angle: float = 0.031415926535897934
    ga_pop_size: int = 24
    ga_generations: int = 160
    random_evals: int | None = None
    sa_steps: int = 3000


@dataclass
class BenchmarkRunRecord:
    project: str
    bug_id: int
    version: str
    algorithm: str
    seed: int
    runtime_seconds: float
    selected_count: int
    total_tests: int
    total_requirements: int
    coverage_ratio: float
    reduction_ratio: float
    total_cost: float
    fitness: float
    full_coverage: bool
    selected_tests: list[int]
    matrix_csv: str

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_csv_arg(value: str | None) -> list[str] | None:
    if value is None or value == "":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_int_ranges(value: str | None) -> list[int] | None:
    """Parse ``1,2,5-7`` into integers."""
    if value is None or value == "":
        return None
    out: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return out


def discover_defects4j_cases(
    matrix_root: str | Path,
    projects: Iterable[str] | None = None,
    bugs: Iterable[int] | None = None,
    version: str = "b",
) -> list[Defects4JBenchmarkCase]:
    root = Path(matrix_root)
    project_filter = set(projects or [])
    bug_filter = set(int(b) for b in (bugs or []))
    cases: list[Defects4JBenchmarkCase] = []
    if not root.exists():
        return cases
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        project = project_dir.name
        if project_filter and project not in project_filter:
            continue
        for version_dir in sorted(p for p in project_dir.iterdir() if p.is_dir()):
            name = version_dir.name
            if not name.endswith(version):
                continue
            try:
                bug_id = int(name[: -len(version)])
            except ValueError:
                continue
            if bug_filter and bug_id not in bug_filter:
                continue
            matrix = version_dir / "matrix.csv"
            if matrix.exists():
                meta = version_dir / "metadata.json"
                cases.append(Defects4JBenchmarkCase(project, bug_id, version, matrix, meta if meta.exists() else None))
    return cases


def solve_coverage_algorithm(problem: CoverageProblem, algorithm: str, seed: int, config: AlgorithmConfig) -> dict:
    """Run one optimization algorithm and return a coverage report dict."""
    if algorithm == "greedy":
        selected, _, _ = GreedySetCover(problem.coverage_sets, seed=seed).run(verbose=False)
        sol = [1 if i in selected else 0 for i in range(problem.n_tests)]
        return problem.report(sol).to_dict()
    if algorithm == "qiea":
        sol, fit, hist = QIEA(
            problem.n_tests,
            pop_size=config.qiea_pop_size,
            max_gen=config.qiea_generations,
            rotation_angle=config.qiea_rotation_angle,
            evaluate_fn=problem.fitness,
            seed=seed,
        ).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = fit
        rep["history_length"] = len(hist)
        # Explicitly record quantum simulation scale for paper artifact claims.
        rep["simulated_qubits"] = problem.n_tests
        return rep
    if algorithm == "ga":
        sol, fit, hist = SimpleGA(problem.n_tests, config.ga_pop_size, config.ga_generations, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = fit
        rep["history_length"] = len(hist)
        return rep
    if algorithm == "random":
        max_evals = config.random_evals or (config.qiea_pop_size * config.qiea_generations)
        sol, fit, hist = RandomSearch(problem.n_tests, max_evals=max_evals, evaluate_fn=problem.fitness, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["final_fitness"] = fit
        rep["history_length"] = len(hist)
        return rep
    if algorithm == "sa":
        sol, energy, hist = SimulatedAnnealing(problem.n_tests, energy_fn=problem.qubo_energy, max_steps=config.sa_steps, seed=seed).run(verbose=False)
        rep = problem.report(sol).to_dict()
        rep["qubo_energy"] = energy
        rep["history_length"] = len(hist)
        return rep
    raise ValueError(f"unknown algorithm: {algorithm}")


def run_defects4j_benchmark(
    cases: list[Defects4JBenchmarkCase],
    algorithms: list[str],
    seeds: list[int],
    output_dir: str | Path,
    run_id: str | None = None,
    config: AlgorithmConfig | None = None,
    paper_metrics_path: str | Path | None = None,
) -> dict:
    config = config or AlgorithmConfig()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(output_dir) / run_id
    out.mkdir(parents=True, exist_ok=True)
    raw_jsonl = out / "raw_runs.jsonl"
    records: list[dict] = []
    skipped: list[dict] = []

    with raw_jsonl.open("w") as jf:
        for case in cases:
            try:
                problem = CoverageProblem.load_csv(case.matrix_csv)
                if problem.n_tests == 0 or problem.n_requirements == 0:
                    raise ValueError("empty matrix")
            except Exception as exc:
                skipped.append({"case": asdict(case) | {"matrix_csv": str(case.matrix_csv), "metadata_json": str(case.metadata_json) if case.metadata_json else None}, "error": str(exc)})
                continue
            for algorithm in algorithms:
                alg_seeds = seeds if algorithm != "greedy" else [seeds[0] if seeds else 0]
                for seed in alg_seeds:
                    start = time.perf_counter()
                    report = solve_coverage_algorithm(problem, algorithm, seed, config)
                    runtime = time.perf_counter() - start
                    record = BenchmarkRunRecord(
                        project=case.project,
                        bug_id=case.bug_id,
                        version=case.version,
                        algorithm=algorithm,
                        seed=seed,
                        runtime_seconds=runtime,
                        selected_count=int(report["selected_count"]),
                        total_tests=int(report["total_tests"]),
                        total_requirements=int(report["total_requirements"]),
                        coverage_ratio=float(report["coverage_ratio"]),
                        reduction_ratio=float(report["reduction_ratio"]),
                        total_cost=float(report["total_cost"]),
                        fitness=float(report["fitness"]),
                        full_coverage=float(report["coverage_ratio"]) >= 1.0,
                        selected_tests=list(report["selected_tests"]),
                        matrix_csv=str(case.matrix_csv),
                    ).to_dict()
                    records.append(record)
                    jf.write(json.dumps(record) + "\n")
                    jf.flush()

    _write_csv(out / "raw_runs.csv", records)
    summary = summarize_records(records)
    comparison = compare_primary_to_baselines(summary, primary="qiea")
    payload = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cases": [asdict(c) | {"matrix_csv": str(c.matrix_csv), "metadata_json": str(c.metadata_json) if c.metadata_json else None} for c in cases],
        "algorithms": algorithms,
        "seeds": seeds,
        "algorithm_config": asdict(config),
        "summary": summary,
        "comparison": comparison,
        "skipped_cases": skipped,
        "artifacts": {
            "raw_runs_jsonl": str(raw_jsonl),
            "raw_runs_csv": str(out / "raw_runs.csv"),
            "summary_json": str(out / "summary.json"),
            "comparison_json": str(out / "comparison.json"),
        },
    }
    if paper_metrics_path:
        paper_metrics = load_paper_metrics(paper_metrics_path)
        payload["paper_comparison"] = compare_to_paper_metrics(records, paper_metrics, primary="qiea")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2))
    (out / "skipped_cases.json").write_text(json.dumps(skipped, indent=2))
    (out / "config.json").write_text(json.dumps({"algorithms": algorithms, "seeds": seeds, "algorithm_config": asdict(config)}, indent=2))
    (out / "result.json").write_text(json.dumps(payload, indent=2))
    return payload


def _write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        path.write_text("")
        return
    fields = [k for k in records[0].keys() if k != "selected_tests"] + ["selected_tests"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["selected_tests"] = " ".join(map(str, row.get("selected_tests", [])))
            writer.writerow(row)
