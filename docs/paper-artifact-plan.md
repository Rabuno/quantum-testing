# Paper Artifact Plan

## Working title

Hybrid Quantum-Inspired Evolutionary Optimization for Cost-Aware Test-Suite Minimization and Constrained Combinatorial Interaction Testing

## Hypothesis

A lightweight hybrid QIEA + repair strategy can match or outperform simple evolutionary/random baselines for coverage-constrained testing tasks while remaining easier to run than QAOA/annealing stacks. The strongest novelty target is constrained t-way CIT, where recent software-testing literature is less saturated than generic test-case selection.

## Research questions

- RQ1: For test-suite minimization, how does QIEA compare with greedy set cover, GA, random search, and QUBO-style simulated annealing across synthetic coverage matrices?
- RQ2: For constrained CIT, can hybrid QIEA + greedy repair generate full t-way coverage with competitive row counts?
- RQ3: How sensitive are QIEA outcomes to seed, population size, rotation angle, and repair strategy?
- RQ4: What is the trade-off between selected-test reduction, retained coverage, and runtime?

## Baselines currently implemented

- Greedy set cover
- Random search
- Classical GA
- QUBO-style simulated annealing
- QIEA
- Greedy CIT generator
- Hybrid QIEA CIT generator with greedy repair

## Minimum experiment matrix for a workshop paper

Coverage minimization:

- synthetic tests: 30, 60, 120
- requirements: 20, 40, 80
- seeds: 30 per setting
- algorithms: greedy, qiea, ga, random, sa
- metrics: coverage ratio, selected count, reduction ratio, full-coverage rate, runtime

CIT:

- strengths: 2 and 3
- parameter models: uniform 2-level, mixed-level, constrained mixed-level
- algorithms: greedy vs qiea+repair
- metrics: covered interactions, row count, invalid assignment rate, runtime

## Next implementation milestones

1. Runtime timing and CSV export for `benchmark`.
2. Parameter sweep CLI for QIEA hyperparameters.
3. Real Python project adapter using coverage.py XML/JSON.
4. Statistical analysis script: mean/std, Wilcoxon or bootstrap confidence intervals.
5. Plots: coverage/reduction/runtime and convergence curves.
