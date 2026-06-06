# 🧪 Quantum-inspired Testing

Quantum-inspired Evolutionary Algorithm (QIEA) applied to software testing optimization.

## Overview

This project demonstrates how **quantum computing concepts** (superposition, quantum rotation gates, observation/collapse) can be used to build evolutionary algorithms that outperform classical approaches for software testing problems like:

- **Test Suite Minimization** — Select minimum tests to maximize requirement coverage
- **Test Case Generation** — Optimize input combinations for maximum fault detection
- **OneMax Benchmark** — Comparison baseline

## How QIEA Works

| Classical GA | QIEA |
|---|---|
| Binary string `0/1` | Qubit `α\|0⟩ + β\|1⟩` |
| Mutation (flip bit) | Quantum rotation gate |
| Crossover | Observation (collapse to binary) |
| Fixed throughout evolution | Adaptive via superposition |

The key advantage: qubits in **superposition** explore the search space more efficiently before collapsing to classical solutions.

## Demos

### Demo 1: OneMax
Maximize the number of 1-bits in a binary string.
```bash
python qiea_demo.py
# QIEA result: 20/20 bits optimal
```

### Demo 2: Test Suite Optimization (Maximum Coverage)
20 test cases, 15 requirements → find minimum tests to cover all requirements.
```
Selected tests: [10, 11, 14]
Tests count: 3/20
Requirements covered: 15/15 = 100%
```

### Demo 3: QIEA vs Classical GA
Head-to-head comparison on OneMax (30 bits, 200 generations, 3 runs each).

## Requirements

- Python 3.8+
- NumPy

```bash
pip install numpy
```

## Usage

```bash
python qiea_demo.py
```

## Project Structure

```
quantum-testing/
├── qiea_demo.py    # QIEA implementation + 3 demos
└── README.md
```

## Roadmap

- [ ] Qiskit/PennyLane integration for real quantum circuits
- [ ] QAOA for test suite minimization
- [ ] Multi-objective optimization benchmarks
- [ ] Web visualization of qubit convergence

## References

- Quantum-inspired Evolutionary Algorithm (QIEA) — research papers
- Maximum Coverage Problem — NP-hard optimization
- Genetic Algorithms vs Quantum-inspired approaches

## License

MIT
