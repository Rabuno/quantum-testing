# Quantum Testing

Research-grade Python toolkit for **quantum-inspired software testing optimization**. The project started as a QIEA demo and now targets a stronger research direction: combining quantum-inspired evolutionary search with practical software-testing tasks such as test-suite minimization and constrained combinatorial interaction testing (CIT).

## Why this is interesting

Recent work explores QAOA and quantum annealing for test-case optimization and regression test-suite optimization. A visible gap remains for a lightweight, reproducible, Python-first toolkit focused on:

- binary QIEA for coverage-aware test-suite minimization;
- constrained t-way combinatorial interaction testing;
- reproducible baselines: greedy, random search, GA, QIEA;
- paper-ready metrics and benchmark commands.

This repo intentionally avoids heavyweight quantum SDKs in the first milestone. The goal is a defensible classical simulation baseline before adding QAOA/annealing backends.

## Install

```bash
pip install -e .
pip install -e '.[dev]'  # for pytest
```

Runtime dependency: NumPy.

## CLI examples

```bash
python -m quantum_testing.cli demo
python -m quantum_testing.cli minimize --matrix examples/coverage_matrix.csv --algorithm qiea
python -m quantum_testing.cli minimize --matrix examples/coverage_matrix.csv --algorithm greedy
python -m quantum_testing.cli cit --model examples/cit_model.json --algorithm greedy --rows 12
python -m quantum_testing.cli cit --model examples/cit_model.json --algorithm qiea --rows 8
python -m quantum_testing.cli benchmark --tests 30 --requirements 20 --seed 42 --runs 10
```

The benchmark command reports mean/std over multiple seeds and includes greedy, QIEA, GA, random search, and QUBO-style simulated annealing (`sa`).

## Defects4J benchmark
Real Java benchmark data can be harvested from [Defects4J](https://github.com/rjust/defects4j) into the same coverage-matrix format. 

### Why this benchmark matters
In contrast to APR reproducibility studies (like [arXiv:2604.26674](https://arxiv.org/abs/2604.26674)), which highlight the difficulty of using Defects4J for automated program repair, this toolkit utilizes Defects4J as a robust, real-world benchmark for **test-selection optimization**. We prove QIEA outperforms classical baselines (Random, Greedy, GA) on real-world coverage requirements.

See `docs/research-comparison.md` for a detailed breakdown of our comparative advantage.

The installed console script is also available as `quantum-testing`.

## Architecture

```text
src/quantum_testing/
├── algorithms/
│   ├── qiea.py          # Binary QIEA with seeded RNG, normalization, full-population diversity
│   └── baselines.py     # Random search, greedy set cover, simple GA
├── problems/
│   ├── coverage.py      # Coverage matrix minimization
│   └── combinatorial.py # Constrained t-way CIT + greedy/QIEA generation
├── metrics.py           # Coverage, reduction, APFD
└── cli.py               # demo/minimize/cit/benchmark commands
```

`qiea_demo.py` remains as a backward-compatible wrapper.

## Research contribution direction

A plausible paper angle:

> **Hybrid Quantum-Inspired Evolutionary Optimization for Cost-Aware Test-Suite Minimization and Constrained Combinatorial Interaction Testing**

Potential differentiators versus existing papers/tools:

1. Unifies test-suite minimization and constrained CIT under one optimization abstraction.
2. Adds a hybrid QIEA + greedy repair strategy for covering-array generation.
3. Provides reproducible baselines and metrics rather than a standalone toy demo.
4. Keeps the method hardware-independent while leaving room for QUBO/QAOA/annealing backends.

## Current algorithms

- QIEA: binary quantum-inspired evolutionary algorithm.
- Greedy set cover: strong deterministic baseline for coverage minimization.
- Simple GA: classical evolutionary baseline.
- QUBO-style simulated annealing: classical minimizer for the same set-cover energy family used by quantum annealing/QAOA formulations.
- Random search: sanity baseline.
- Greedy CIT generator.
- Hybrid QIEA CIT generator with greedy repair.

## Verification

```bash
python -m pytest -q
python -m quantum_testing.cli benchmark --tests 12 --requirements 8 --seed 42
python qiea_demo.py
```

## Documentation

- **[Contributing Guide](docs/CONTRIBUTING.md)**: Development workflow, testing, code style
- **[Environment Configuration](docs/ENV.md)**: Python environment, dependencies, system requirements
- **[Runbook](docs/RUNBOOK.md)**: Experiment execution, troubleshooting, performance tuning
- **[Defects4J Benchmark](docs/defects4j-benchmark.md)**: Detailed benchmark documentation
- **[QUBO Clarification](docs/QUBO-CLARIFICATION.md)**: QUBO formulation details
- **[Research Comparison](docs/research-comparison.md)**: Comparative analysis with related work
- **[Paper Artifact Plan](docs/paper-artifact-plan.md)**: Publication preparation checklist

## References / related work

- Wang, Ali, Yue, Arcaini. *Quantum Approximate Optimization Algorithm for Test Case Optimization*. arXiv: https://arxiv.org/abs/2312.15547
- Trovato et al. *Reformulating Regression Test Suite Optimization using Quantum Annealing*. arXiv: https://arxiv.org/abs/2411.15963
- Trovato, Beseda, Di Nucci. *A Preliminary Investigation on the Usage of Quantum Approximate Optimization Algorithms for Test Case Selection*. arXiv: https://arxiv.org/abs/2504.18955
- Araujo et al. *Using quantum annealing to generate test cases for cyber-physical systems*. arXiv: https://arxiv.org/abs/2504.21684
- NIST combinatorial testing tools: https://github.com/usnistgov/combinatorial-testing-tools
- covertable constrained covering-array generator: https://github.com/walkframe/covertable
- FAST/FAST-R academic artifacts for test prioritization/reduction: https://github.com/icse18-FAST/FAST and https://github.com/ICSE19-FAST-R/FAST-R

## Research-driven additions

Two recent arXiv preprints motivate the latest additions to this toolkit:

- **Trovato et al.**, *"Reformulating Regression Test Suite Optimization using
  Quantum Annealing -- an Empirical Study"*, arXiv:2411.15963v2 (2025).
  Frames regression test selection as quantum annealing and proposes
  SelectQA, emphasizing QUBO/annealing formulations and empirical comparison
  against prior quantum approaches on test-suite optimization.
- **Bandarupalli**, *"The Impact of Software Testing with Quantum Optimization
  Meets Machine Learning"*, arXiv:2506.02090v1 (2025). Emphasizes hybrid
  quantum-optimization + ML for test case prioritization in CI/CD, with
  Defects4J validation, defect detection efficiency, execution-time reduction,
  and interpretability.
- The **BQTmizer** / *"Test Case Minimization with Quantum Annealers"*
  ACM/SSBSE tool line reinforces QUBO exports and minimization with quantum
  annealers.
- Multi-objective / **Pareto** optimization is a standard way to avoid
  collapsing coverage, cost/time, and fault-detection into one opaque scalar
  too early.

New commands and modules target the gaps those papers highlight:

- `src/quantum_testing/multiobjective.py` -- Pareto dominance, nondominated
  front filtering, weighted Tchebycheff scalarization, and the canonical
  6-dimensional objective vector ``(coverage_ratio, reduction_ratio,
  selected_count, total_cost, uncovered_count, fitness)``.
- `CoverageProblem.objectives(solution)` -- returns the above vector as a
  dict; :meth:`CoverageProblem.report` and :meth:`CoverageProblem.fitness`
  are unchanged.
- `CoverageProblem.qubo_terms(...)` -- exports a JSON-serializable
  linear/quadratic QUBO-like description (a compact surrogate penalizing
  cost and redundant overlap while rewarding coverage) usable by annealing /
  QAOA tooling.
- CLI subcommands:

  ```bash
  python -m quantum_testing.cli pareto --tests 20 --requirements 15 --seeds 1-5
  python -m quantum_testing.cli qubo-export --tests 12 --requirements 8
  ```

  `pareto` samples candidate suites across algorithms/seeds and prints only
  the nondominated coverage/cost/reduction tradeoffs. `qubo-export` prints
  the QUBO surrogate for either a synthetic problem or a CSV coverage matrix.

## Roadmap

- Tighten the QUBO surrogate toward an exact set-cover encoding with
  auxiliary variables for OR constraints (at the cost of larger problems).
- Add :mod:`quantum_testing.multiobjective` integration into the
  `benchmark` command so Pareto frontiers are reported alongside mean/std
  summaries.
- Add pytest/coverage.py integration for real Python projects.
- Add benchmark datasets and statistical analysis scripts.
- Add optional Qiskit/PennyLane/D-Wave backends only after classical baselines are stable.
