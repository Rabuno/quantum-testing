# Runbook

## Experiment Execution

### Quick Start with Presets

#### 1. Quick Harvest (3 smallest Defects4J bugs)

Harvest Lang/1b, Lang/2b, Chart/1b for local testing:

```bash
quantum-testing quick-harvest \
  --defects4j-home /path/to/defects4j \
  --work-root /tmp/quantum-testing-defects4j \
  --output-dir datasets/defects4j
```

**Expected time**: 30-60 minutes
**Disk usage**: ~600MB-1.5GB (deletable)

#### 2. Single-Algorithm Minimization

Test a coverage matrix with QIEA:

```bash
quantum-testing minimize \
  --matrix datasets/defects4j/Lang/1b/coverage_matrix.csv \
  --algorithm qiea \
  --seed 42
```

#### 3. Benchmark Across Algorithms

Run multiple algorithms on synthetic problems:

```bash
quantum-testing benchmark \
  --tests 30 \
  --requirements 20 \
  --runs 10 \
  --algorithms greedy,qiea,ga,random,sa \
  --seed 42
```

#### 4. Full Multi-Algorithm Experiment

Run comprehensive experiments on harvested bugs:

```bash
quantum-testing experiment \
  --matrix-root datasets/defects4j \
  --projects Lang,Chart \
  --bugs 'Lang:1-2,Chart:1-1' \
  --algorithms greedy,qiea,enhanced_qiea,ga,random,sa \
  --seeds 42,123,456,789,1024 \
  --output-dir artifacts/experiment
```

**Expected time**: 1-4 hours depending on bugs
**Resources**: ~4-8GB RAM

### Defects4J Benchmark Workflow

#### Harvest Coverage Matrices

```bash
quantum-testing defects4j-harvest \
  --defects4j-home /path/to/defects4j \
  --projects Lang,Chart,Cli,Math \
  --bugs 'Lang:1-10,Chart:1-5,Cli:1-3,Math:1-8' \
  --version b \
  --output-dir datasets/defects4j \
  --reuse-workdir \
  --force-coverage
```

#### Run Benchmark on Harvested Data

```bash
quantum-testing defects4j-benchmark \
  --matrix-root datasets/defects4j \
  --projects Lang,Chart \
  --bugs 'Lang:1-2,Chart:1-1' \
  --algorithms greedy,qiea,ga,random,sa \
  --seeds 42,123,456,789,1024 \
  --output-dir artifacts/defects4j-benchmark \
  --run-id exp-001
```

**Note**: Algorithm parameters can be tuned:
```bash
quantum-testing defects4j-benchmark \
  --qiea-pop-size 32 \
  --qiea-generations 200 \
  --ga-pop-size 32 \
  --ga-generations 200 \
  ...
```

### Multi-Objective Pareto Analysis

Sample and filter nondominated solutions:

```bash
quantum-testing pareto \
  --tests 30 \
  --requirements 20 \
  --algorithms greedy,qiea,ga,random,sa \
  --seeds 42,123,456,789,1024
```

Output includes:
- Objective vector names
- Maximization flags per objective
- Candidate solutions count
- Nondominated front size

### QUBO Export for External Solvers

Export QUBO formulation for quantum annealing or classical solvers:

```bash
# Export synthetic problem
quantum-testing qubo-export \
  --tests 12 \
  --requirements 8 \
  --uncovered-weight 2.0 \
  --cost-weight 1.0

# Export from coverage matrix
quantum-testing qubo-export \
  --matrix datasets/defects4j/Lang/1b/coverage_matrix.csv \
  --uncovered-weight 2.0 \
  --cost-weight 1.0
```

Output is JSON-serializable with linear and quadratic terms.

## Visualization and Reporting

### Generate Publication-Ready Figures

```bash
quantum-testing plot \
  --experiment-dir artifacts/experiment \
  --output-dir artifacts/experiment/figures \
  --type all
```

Available figure types:
- `cd`: Coverage diagram (CD diagram)
- `box_coverage`: Box plot of coverage ratios
- `box_reduction`: Box plot of reduction ratios
- `runtime`: Runtime comparison
- `convergence`: Convergence curves
- `stat_summary`: Statistical summary
- `heatmap`: Coverage heatmap
- `all`: All figures (default)

### Custom Figure Generation

```bash
# Generate only box plots
quantum-testing plot \
  --experiment-dir artifacts/experiment \
  --type box_coverage,box_reduction \
  --format pdf

# Generate heatmap from CSV
quantum-testing plot \
  --experiment-dir artifacts/experiment \
  --type heatmap \
  --matrix datasets/defects4j/Lang/1b/coverage_matrix.csv \
  --format png
```

## Statistical Analysis

### Per-Bug Analysis

After running `defects4j-benchmark`, analyze per-bug results:

```bash
python -m json.tool artifacts/defects4j-benchmark/per_bug_analysis.json
```

### Comparative Statistics

Compare algorithms across bugs:

```bash
python -m json.tool artifacts/defects4j-benchmark/comparison.json
```

### Experiment Report

Full experiment report includes:
- Statistical summaries (mean, std, min, max)
- Coverage reduction rates
- Full coverage rates
- Best solution comparisons

## Debugging and Troubleshooting

### Common Issues

#### 1. Memory Exhaustion

**Symptom**: `MemoryError` or kernel crash

**Solutions**:
```bash
# Reduce problem size
quantum-testing benchmark --tests 20 --requirements 15 ...

# Use simulated annealing for large problems
quantum-testing minimize --algorithm sa ...

# Reduce qiea max qubits
quantum-testing experiment --qaoa-max-qubits 20 ...
```

#### 2. Defects4J Installation Issues

**Symptom**: `defects4j-home` path not found

**Solutions**:
```bash
# Verify Defects4J installation
ls /path/to/defects4j/gradlew

# Use full path
quantum-testing quick-harvest --defects4j-home /absolute/path/to/defects4j
```

#### 3. Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'quantum_testing'`

**Solutions**:
```bash
# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Reinstall dependencies
uv pip install -e .
```

#### 4. Test Suite Failures

**Symptom**: pytest reports failures

**Solutions**:
```bash
# Run with verbose output
python -m pytest -v

# Check for specific test file
python -m pytest tests/test_cli.py -v

# Run with coverage
python -m pytest --cov=quantum_testing --cov-report=html
```

### Logging and Debugging

#### Verbose CLI Output

```bash
# Use module form for verbose output
python -m quantum_testing.cli minimize --matrix ... --seed 42

# Add debug flag if available
python -m quantum_testing.cli minimize --matrix ... --seed 42 --debug
```

#### Inspect Raw Results

```bash
# View raw benchmark runs
cat artifacts/experiment/benchmark/raw_runs.jsonl | jq

# View experiment artifacts
ls -lh artifacts/experiment/
```

## Performance Tuning

### Algorithm Parameters

| Parameter | QIEA | GA | Simulated Annealing | Default |
|-----------|------|----|---------------------|---------|
| Population | 24 | 24 | - | 24 |
| Generations | 160 | 160 | 3000 | 160 |
| Max Qubits | 25 | - | - | 25 |
| Rotation Angle | 0.01π | - | - | 0.01π |

**Tuning Guidelines**:
- Larger populations improve diversity but increase runtime
- More generations improve convergence but increase runtime
- Simulated annealing requires more steps for large problems

### Resource Allocation

#### Synthetic Problems

- **Tests**: 12-50
- **Requirements**: 8-30
- **Time**: 1-10 minutes
- **Memory**: < 1GB

#### Defects4J Bugs

- **Small bugs** (Lang/1b, Chart/1b): 1-2 minutes each
- **Medium bugs** (Lang/5b, Math/1b): 5-10 minutes each
- **Large bugs** (Math/7b): 15-30 minutes each

## Maintenance

### Cleaning Up

#### Delete Work Directories

```bash
# Remove Defects4J work directory
rm -rf /tmp/quantum-testing-defects4j

# Remove all artifacts
rm -rf artifacts/
rm -rf datasets/defects4j/*.csv

# Remove virtual environment (if needed)
deactivate
rm -rf .venv
```

#### Update Dependencies

```bash
# Update core dependencies
uv pip install --upgrade -e .

# Update development dependencies
uv pip install --upgrade -e '.[dev]'

# Check for outdated packages
uv pip list --outdated
```

### Backup and Restore

#### Export Results

```bash
# Archive experiment results
tar -czf experiment-backup-$(date +%Y%m%d).tar.gz artifacts/experiment/

# Backup datasets
tar -czf datasets-backup-$(date +%Y%m%d).tar.gz datasets/defects4j/
```

#### Restore Results

```bash
# Extract results
tar -xzf experiment-backup-20260616.tar.gz

# Extract datasets
tar -xzf datasets-backup-20260616.tar.gz
```

## Continuous Integration

### Running Tests in CI

```bash
# Install dependencies
uv pip install -e . -e '.[dev]'

# Run tests with coverage
python -m pytest --cov=quantum_testing --cov-report=xml

# Run specific test file
python -m pytest tests/test_algorithms.py -v
```

### Pre-Commit Checks

```bash
# Linting (if configured)
black --check src/
flake8 src/
mypy src/

# Type checking
mypy src/quantum_testing/
```

## Rollback Procedures

### Reverting a Bad Commit

```bash
# View git log
git log --oneline -10

# Reset to specific commit (keeping changes)
git reset --soft <commit-hash>

# Or hard reset (deleting changes)
git reset --hard <commit-hash>

# Rebase to latest main
git rebase origin/main
```

### Restoring from Backup

See "Backup and Restore" section above.

## Emergency Procedures

### Critical Failure

1. **Stop all running experiments**
2. **Check system resources** (RAM, disk)
3. **Review logs** for error messages
4. **Reduce complexity** and retry
5. **Report issue** with full error output

### Dataset Corruption

```bash
# Verify CSV integrity
head -1 datasets/defects4j/Lang/1b/coverage_matrix.csv
wc -l datasets/defects4j/Lang/1b/coverage_matrix.csv

# Re-harvest specific bug
quantum-testing defects4j-matrix \
  --defects4j-home /path/to/defects4j \
  --project Lang --bug 1 --version b
```

## Monitoring

### Health Checks

```bash
# Check Python installation
python --version

# Check package installation
python -c "import quantum_testing; print(quantum_testing.__version__)"

# Check Qiskit installation
python -c "import qiskit; print(qiskit.__version__)"

# Run quick test
python -m pytest tests/test_cli.py::test_demo -v
```

### Resource Monitoring

```bash
# Monitor memory usage (Linux/macOS)
watch -n 1 'ps aux | grep python'

# Monitor disk usage
du -sh artifacts/ datasets/

# Monitor running processes
ps aux | grep quantum-testing
```

## Contact and Support

- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check `docs/` directory for detailed guides
- **Research Context**: Review `README.md` for project overview
- **Code Review**: Run `python -m pytest -v` before submitting changes
