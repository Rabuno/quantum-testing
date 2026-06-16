# Contributing Guide

## Development Environment Setup

### Prerequisites

- **Python 3.10+** (3.12 recommended)
- **uv** package manager (recommended)
- **Defects4J** (for benchmarking)
- **Git** for version control

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Rabuno/quantum-testing.git
   cd quantum-testing
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   uv pip install -e '.[dev]'
   ```

3. Verify the installation:
   ```bash
   python -m pytest -q
   python -m quantum_testing.cli --help
   ```

### Available Commands

| Command | Description |
|---------|-------------|
| `quantum-testing demo` | Run QIEA demo with OneMax and coverage problems |
| `quantum-testing minimize` | Minimize test suite using selected algorithm |
| `quantum-testing cit` | Generate constrained t-way combinatorial interaction tests |
| `quantum-testing benchmark` | Run benchmark across multiple algorithms with statistical analysis |
| `quantum-testing pareto` | Sample Pareto frontier across multiple objectives |
| `quantum-testing qubo-export` | Export QUBO formulation for coverage problems |
| `quantum-testing quick-harvest` | Harvest 3 smallest Defects4J bugs for local testing |
| `quantum-testing defects4j-harvest` | Batch-harvest Defects4J matrices for multiple projects |
| `quantum-testing defects4j-matrix` | Harvest single Defects4J coverage matrix |
| `quantum-testing defects4j-benchmark` | Run QIEA on harvested Defects4J bugs |
| `quantum-testing experiment` | Run full multi-algorithm experiment with statistical analysis |
| `quantum-testing plot` | Generate publication-ready figures from experiment results |

### Testing

Run the test suite with coverage:
```bash
# Run all tests with coverage
python -m pytest --cov=quantum_testing --cov-report=html

# Run specific test file
python -m pytest tests/test_cli.py -v

# Run with coverage report
python -m pytest --cov=quantum_testing --cov-report=term-missing
```

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and write tests first (TDD approach recommended)

3. Run tests and linting:
   ```bash
   python -m pytest
   ```

4. Commit with conventional commit messages:
   ```bash
   git commit -m "feat: add new QIEA variant"
   ```

5. Push and create a Pull Request

## Code Style

### Python Style

- Follow **PEP 8** guidelines
- Use **type hints** for all function signatures
- Keep functions under 50 lines
- Document public APIs with docstrings
- Use immutability patterns (return new objects, don't mutate inputs)

### File Structure

```
src/quantum_testing/
├── algorithms/          # QIEA, baselines, quantum-inspired algorithms
├── benchmarks/          # Defects4J runner, metrics, reporting
├── datasets/            # Defects4J data adapter
├── problems/            # Coverage, combinatorial problems
├── multiobjective.py    # NSGA-III many-objective optimization
├── cli.py               # Command-line interface
├── metrics.py           # Metrics computation
└── experiment_runner.py # Experiment orchestration
```

## Project Structure

### Core Modules

- **algorithms/**: All optimization algorithms (QIEA, GA, random, simulated annealing)
- **benchmarks/**: Defects4J integration, benchmark execution, metrics
- **datasets/**: Defects4J data collection and matrix generation
- **problems/**: Coverage minimization, constrained combinatorial testing
- **multiobjective.py**: NSGA-III multi-objective optimization wrapper
- **visualization/**: Publication-ready figure generation

### Key Concepts

1. **QIEA**: Binary quantum-inspired evolutionary algorithm with:
   - Seeded random number generation for reproducibility
   - Population diversity tracking
   - Normalization for numerical stability

2. **Coverage Problem**: Test suite minimization problem:
   - Input: Coverage matrix (tests × requirements)
   - Output: Subset of tests maximizing coverage with minimum size
   - Multi-objective: Coverage ratio, reduction ratio, test count, cost

3. **Constrained CIT**: Combinatorial interaction testing with constraints:
   - t-way interaction strength
   - Forbidden combinations
   - Greedy or QIEA-based generation

4. **Multi-objective Optimization**: NSGA-III for:
   - Coverage ratio (maximize)
   - Reduction ratio (maximize)
   - Selected count (minimize)
   - Total cost (minimize)
   - Uncovered count (minimize)
   - Fitness score (maximize)

## Common Issues

### Import Errors

If you encounter import errors after installing:
```bash
# Deactivate and reactivate virtual environment
deactivate
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Reinstall dependencies
uv pip install -e .
```

### Defects4J Installation

Install Defects4J from [official repo](https://github.com/rjust/defects4j):
```bash
# Clone and setup
git clone https://github.com/rjust/defects4j.git
cd defects4j
git checkout v2.6
./gradlew
```

Then specify the path when using harvest commands:
```bash
quantum-testing quick-harvest --defects4j-home /path/to/defects4j
```

### Memory Issues

Qiskit Aer statevector simulation is limited to ~25-28 qubits on 12GB RAM. For larger problems:
- Use `--qiea-max-qubits` to reduce problem size
- Use simulated annealing or greedy algorithms for larger instances
- Consider QUBO formulation for annealing backends

## Performance Considerations

- **QIEA**: ~160 generations, 24 individuals for synthetic problems
- **Simulated Annealing**: ~3000 steps
- **GA**: ~160 generations, 24 individuals
- **Benchmark**: Default 30 tests × 20 requirements with 10 runs per algorithm

For faster prototyping, reduce complexity:
```bash
quantum-testing benchmark --tests 12 --requirements 8 --runs 5
```

## Code Review Checklist

- [ ] All tests pass
- [ ] Code follows PEP 8 style guidelines
- [ ] Type hints added for new functions
- [ ] Docstrings added for public APIs
- [ ] No mutation of input objects
- [ ] Error handling is explicit (no silent failures)
- [ ] Changes are covered by tests
- [ ] Commit message follows conventional commits format

## Getting Help

- Check existing documentation in `docs/`
- Review research papers referenced in `README.md`
- Run experiments with `quantum-testing experiment --help` for parameter details
- Open an issue on GitHub for bugs or feature requests

## Research Context

This is a research project targeting Q2 journal publication. When adding new features:

1. Ensure reproducibility with seeded RNG
2. Document parameter choices and their rationale
3. Include statistical analysis in benchmarking
4. Compare against classical baselines
5. Consider multi-objective formulation for fairness
