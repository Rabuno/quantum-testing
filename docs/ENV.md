# Environment Configuration

## Python Environment

### Python Version

- **Minimum**: Python 3.10
- **Recommended**: Python 3.12
- **Tested**: Python 3.10, 3.11, 3.12

### Virtual Environment

Project uses `uv` for dependency management. Create a virtual environment:

```bash
# Using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Dependencies

#### Core Dependencies (required)

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | >=1.20.0 | Numerical operations |
| `matplotlib` | >=3.7.0 | Visualization |
| `pymoo` | >=0.6.1.6 | Multi-objective optimization (NSGA-III) |
| `qiskit` | >=2.4.1 | Quantum circuit simulation |
| `qiskit-aer` | >=0.17.2 | Quantum statevector simulation |

#### Development Dependencies (optional)

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=7.0 | Testing framework |
| `pytest-cov` | >=4.0 | Coverage reporting |
| `pytest>=9.0.3` | - | Latest pytest for dev group |

### Installation

```bash
# Install core dependencies
uv pip install -e .

# Install development dependencies
uv pip install -e '.[dev]'
```

## Environment Variables

This project does not use `.env` files for runtime configuration. All configuration is specified via:

1. **Command-line arguments** (primary method)
2. **Configuration files** (for experiments and benchmarks)
3. **Code constants** (algorithm parameters)

### No Required Environment Variables

There are no mandatory environment variables. All critical paths and settings are:

- **CLI arguments**: Specified at runtime (e.g., `--matrix`, `--algorithm`)
- **Configuration files**: JSON/YAML files for experiments
- **Hard-coded defaults**: Meaningful defaults for algorithm parameters

### Optional Environment Variables (not currently used)

These variables are reserved for future use and should not be set:

```bash
# Reserved for future use
# QISKIT_BACKEND=...      # Qiskit backend selection
# LOG_LEVEL=...           # Logging verbosity
# RANDOM_SEED=...         # Global random seed
# CACHE_DIR=...           # Cache directory for results
```

## Configuration Files

### pyproject.toml

Main project configuration:

```toml
[project]
name = "quantum-testing"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "matplotlib>=3.7.0",
    "numpy>=1.20.0",
    "pymoo>=0.6.1.6",
    "qiskit>=2.4.1",
    "qiskit-aer>=0.17.2",
]
```

### Experiment Configuration

Experiments use JSON/YAML files for detailed configuration:

```bash
quantum-testing experiment \
  --projects Lang,Chart \
  --bugs 'Lang:1-2,Chart:1-1' \
  --algorithms greedy,qiea,enhanced_qiea,ga,random,sa \
  --seeds 42,123,456,789,1024 \
  --output-dir artifacts/experiment
```

## System Requirements

### Minimum (for synthetic problems)

- **CPU**: 4 cores
- **RAM**: 4 GB
- **Disk**: 100 MB

### Recommended (for Defects4J benchmarks)

- **CPU**: 8 cores
- **RAM**: 8-12 GB
- **Disk**: 2-3 GB (for work directories and harvested data)

### Quantum Simulation Limits

- **Qiskit Aer statevector**: ~25-28 qubits on 12GB RAM
- **Larger problems**: Use simulated annealing or greedy algorithms
- **Quantum backends**: Can be added after classical baselines are stable

## Platform-Specific Notes

### Windows

- Use Git Bash or WSL for Unix-like command experience
- Paths with backslashes may need escaping in some shells
- Path length limits are less restrictive on Windows (260 char limit can be raised)

### Linux/macOS

- Bash is the primary shell
- Path separators are forward slashes
- File permissions are enforced

## Storage Locations

### Output Directories

- **Datasets**: `datasets/defects4j/` (harvested coverage matrices)
- **Artifacts**: `artifacts/defects4j-benchmark/`, `artifacts/experiment/`
- **Temporary work**: `/tmp/quantum-testing-defects4j/` (deletable)

### Generated Files

- **Coverage matrices**: CSV files in `datasets/defects4j/`
- **Experiment results**: JSON, JSONL, text reports
- **Figures**: PNG, PDF, SVG plots in `artifacts/*/figures/`

## Defects4J Configuration

### Installation

Download from [Defects4J GitHub](https://github.com/rjust/defects4j):

```bash
git clone https://github.com/rjust/defects4j.git
cd defects4j
git checkout v2.6
./gradlew
```

### Environment Variables (reserved)

```bash
# Specify Defects4J installation path when needed
export DEFECTS4J_HOME=/path/to/defects4j
```

### Usage

```bash
quantum-testing quick-harvest --defects4j-home /path/to/defects4j
```

## Debug Mode

Enable verbose logging by adding Python flags:

```bash
# Verbose pytest
python -m pytest -v

# Verbose CLI output
python -m quantum_testing.cli --help

# Debug mode (development)
export PYTHONDEBUG=1
python -m quantum_testing.cli minimize ...
```

## Troubleshooting

### Import Errors

If `quantum-testing` command is not found:

```bash
# Ensure virtual environment is activated
which quantum-testing  # or where quantum-testing on Windows

# Or use module form
python -m quantum_testing.cli
```

### Qiskit Backend Issues

```bash
# Use statevector simulator by default
export QISKIT_BACKEND='statevector_simulator'

# Or use MPS backend for larger problems
export QISKIT_BACKEND='mps'
```

### Memory Issues

Reduce problem size or switch to classical algorithms:

```bash
# Reduce QIEA max qubits
quantum-testing experiment --qaoa-max-qubits 20 ...

# Use simulated annealing for large problems
quantum-testing minimize --algorithm sa ...
```
