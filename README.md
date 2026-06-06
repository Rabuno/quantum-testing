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

### Defects4J benchmark matrices

Real Java benchmark data can be harvested from [Defects4J](https://github.com/rjust/defects4j) into the same coverage-matrix format:

```bash
quantum-testing defects4j-matrix \
  --defects4j-home /path/to/defects4j \
  --project Lang \
  --bug 1 \
  --version b \
  --test-property tests.trigger \
  --limit-tests 5

quantum-testing minimize \
  --matrix datasets/defects4j/Lang/1b/matrix.csv \
  --algorithm qiea
```

Run a multi-case Defects4J benchmark once matrices are harvested:

```bash
quantum-testing defects4j-benchmark \
  --matrix-root datasets/defects4j \
  --projects Lang,Chart,Cli \
  --bugs 1-10 \
  --algorithms greedy,qiea,ga,random,sa \
  --seeds 1-30
```

QIEA uses simulated qubits represented by amplitudes `(α, β)`, measurement/collapse, and rotation-gate updates; this is not a plain bit-string optimizer.

See `docs/defects4j-benchmark.md`. Defects4J harvesting requires Java 11 and an initialized Defects4J checkout; the Python CI only tests adapter parsing and matrix generation.

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

## References / related work

- Wang, Ali, Yue, Arcaini. *Quantum Approximate Optimization Algorithm for Test Case Optimization*. arXiv: https://arxiv.org/abs/2312.15547
- Trovato et al. *Reformulating Regression Test Suite Optimization using Quantum Annealing*. arXiv: https://arxiv.org/abs/2411.15963
- Trovato, Beseda, Di Nucci. *A Preliminary Investigation on the Usage of Quantum Approximate Optimization Algorithms for Test Case Selection*. arXiv: https://arxiv.org/abs/2504.18955
- Araujo et al. *Using quantum annealing to generate test cases for cyber-physical systems*. arXiv: https://arxiv.org/abs/2504.21684
- NIST combinatorial testing tools: https://github.com/usnistgov/combinatorial-testing-tools
- covertable constrained covering-array generator: https://github.com/walkframe/covertable
- FAST/FAST-R academic artifacts for test prioritization/reduction: https://github.com/icse18-FAST/FAST and https://github.com/ICSE19-FAST-R/FAST-R

## Roadmap

- Add QUBO formulation for coverage minimization.
- Add multi-objective Pareto reporting for coverage, cost, runtime, and fault history.
- Add pytest/coverage.py integration for real Python projects.
- Add benchmark datasets and statistical analysis scripts.
- Add optional Qiskit/PennyLane/D-Wave backends only after classical baselines are stable.
