# Defects4J Benchmark Integration

Defects4J is the benchmark dataset we should use for real Java regression-testing experiments. The adapter in `quantum_testing.datasets.defects4j` converts Defects4J coverage output into the toolkit's standard test-suite-minimization matrix format:

```text
test_id x covered source-line requirements -> matrix.csv -> CoverageProblem -> QIEA/GA/greedy/random/SA
```

## Why Defects4J matters

Defects4J provides reproducible real bugs across Java projects. Version 3.0.1 contains 854 active bugs from projects such as Lang, Math, Chart, Closure, Mockito, Jsoup, Jackson, Gson, and others.

This lets the paper move beyond synthetic matrices and evaluate against real faulty programs.

## Environment requirements

Defects4J is intentionally optional for this Python package. Real harvesting requires:

- Java 11
- Git
- SVN
- Perl + `cpanm`
- Initialized Defects4J checkout
- Timezone `America/Los_Angeles`

Reference setup:

```bash
git clone https://github.com/rjust/defects4j /opt/data/defects4j
cd /opt/data/defects4j
cpanm --installdeps .
./init.sh
export PATH="$PATH:/opt/data/defects4j/framework/bin"
export TZ=America/Los_Angeles
defects4j info -p Lang
```

The current CI does **not** run Defects4J because Java/Defects4J setup is heavy. CI tests only parser and matrix logic with fixtures.

## Generate a small smoke matrix

Start with a small trigger-test matrix for one bug:

```bash
quantum-testing defects4j-matrix \
  --defects4j-home /opt/data/defects4j \
  --project Lang \
  --bug 1 \
  --version b \
  --test-property tests.trigger \
  --limit-tests 5 \
  --output-dir datasets/defects4j
```

Output layout:

```text
datasets/defects4j/Lang/1b/
├── matrix.csv
├── tests.txt
├── requirements.txt
├── metadata.json
└── raw/coverage/*.xml
```

`matrix.csv` has a `test_id` column followed by source-line requirement columns. It remains compatible with:

```bash
quantum-testing minimize \
  --matrix datasets/defects4j/Lang/1b/matrix.csv \
  --algorithm qiea \
  --seed 42
```

Compare baselines:

```bash
for alg in greedy qiea ga random sa; do
  quantum-testing minimize \
    --matrix datasets/defects4j/Lang/1b/matrix.csv \
    --algorithm "$alg" \
    --seed 42
done
```

## Test scopes

The adapter can export one of:

- `tests.trigger`: failing trigger tests; useful for smoke/fault-revealing experiments, but failures must be interpreted carefully.
- `tests.relevant`: bug-relevant test classes according to Defects4J metadata; useful for focused regression-test selection.
- `tests.all`: all developer-written test classes; broadest and slowest.

Important caveat: Defects4J documents `coverage -t` as a single test method format `<test_class>::<test_method>`. Some exported properties are class-level. For large-scale method-level matrices, generate or provide a method-level test list before harvesting.

## Requirement granularity

Current adapter uses covered source lines from Cobertura XML:

```text
<filename>:<line-number>
```

This is a good first benchmark target because it maps cleanly to test-suite minimization. Future variants should add:

- modified-class-only filtering
- modified-line-only filtering
- branch coverage requirements
- fault-detection/APFD metrics using `tests.trigger`

## Reproducibility metadata

Each matrix includes `metadata.json` with:

- project and bug id
- version (`1b`, `1f`, ...)
- exported Defects4J metadata
- Java/Defects4J environment info
- test property used
- failures from per-test coverage commands
- output paths and created timestamp

## Paper benchmark plan using Defects4J

Recommended first real experiment:

- Projects: Lang, Chart, Math, Cli, Gson
- Bugs: first 10 active bugs per project for initial run
- Test scope: `tests.relevant` or generated method-level list
- Requirement scope: covered lines in modified classes first, all covered lines second
- Algorithms: greedy, QIEA, GA, random, SA
- Seeds: 30 for stochastic algorithms
- Metrics:
  - coverage ratio
  - selected test count
  - reduction ratio
  - runtime
  - fault-revealing trigger-test retention
  - APFD later if ordered execution is added

## Known local blocker

On the current Hermes machine, `java` is not installed:

```text
java: command not found
```

So real Defects4J checkout/coverage execution cannot be verified here yet. The adapter and parser are still unit-tested locally.
