# Comparison plan: arXiv:2604.26674 + Defects4J

Baseline paper:

- Adam Krafczyk, Klaus Schmid, **"Reproducible Automated Program Repair Is Hard -- Experiences With the Defects4J Dataset"**, arXiv:2604.26674v1, submitted 2026-04-29, EASE 2026.
- Scope: Defects4J reproducibility/workability for APR, not quantum optimization.
- Dataset facts from the abstract/API metadata:
  - Defects4J 2.0 has 835 defects from 17 Java projects.
  - 180 / 835 defects (21.6%) are unsuitable for strict APR evaluation.
  - Additional 59 / 835 defects (7.1%) are likely under-specified/trivial-to-game.

## Why this paper is still the right comparison anchor

The paper is recent and Defects4J-centered, but it does not propose a competing quantum test-suite optimizer. Therefore, the defensible comparison is not "our quantum beats their quantum". The defensible comparison is:

> Use their stricter Defects4J workability framing as the dataset-validity baseline, then show that QIEA reduces validation/test-selection cost on a workable Defects4J subset while preserving full coverage/fault-trigger evidence.

This avoids an invalid apples-to-oranges claim.

## Claim target

Minimum publishable claim for the first paper iteration:

> On a real Defects4J subset, QIEA reaches full covered-line requirement coverage with fewer selected tests than at least one stochastic baseline, while using a simulated-qubit representation and rotation-gate update instead of classical fixed-bit mutation only.

For the current real smoke subsets:

- Project: `Lang`
- Bug: `1b`
- Test source: `tests.relevant`
- Filter: `NumberUtilsTest::test`
- Requirement scope: covered source lines from Defects4J/Cobertura `coverage.xml`

Observed benchmark A (`artifacts/defects4j-benchmark/lang1-numberutils-12-30seeds`):

- Candidate tests: 12 method-level tests.
- Requirements: 97 covered source lines.
- Seeds: 30.
- QIEA: full coverage rate = 1.00, mean selected tests = 7.00 / 12, reduction = 41.67%.
- Random search: full coverage rate = 1.00, mean selected tests = 7.37 / 12, reduction = 38.61%.
- Improvement over random on selected count: about 4.98% fewer selected tests.
- QIEA tied greedy, GA, and SA on selected count in this small subset.

Observed benchmark B (`artifacts/defects4j-benchmark/lang1-numberutils-24-30seeds`):

- Candidate tests: 24 method-level tests.
- Requirements: 181 covered source lines.
- Seeds: 30.
- QIEA: full coverage rate = 1.00, mean selected tests = 17.00 / 24, reduction = 29.17%.
- Random search: full coverage rate = 0.00, mean coverage = 97.88%, mean selected tests = 15.87 / 24.
- Stronger smoke claim: under the same benchmark budget, QIEA consistently reaches full requirement coverage, while random search never reaches full coverage on this 24-test subset.
- QIEA tied greedy, GA, and SA on selected count/full coverage in this subset.

Interpretation:

- These are real Defects4J smoke results, not synthetic-only results.
- The strongest current claim is coverage reliability vs random under a fixed budget, not superiority over greedy/GA/SA yet.
- The next stronger target is to find cases where QIEA beats GA or SA on selected-count, full-coverage rate, or stability under equal evaluation budget.

## Next benchmark expansion

Prioritize cases aligned with the 2026 paper's workability framing:

1. Generate matrices for workable-looking small subsets first:
   - `Lang`: bugs 1-10
   - `Chart`: bugs 1-10
   - `Cli`: bugs 1-10
2. Use method-level expansion from `tests.relevant`.
3. Filter to modified-class-related tests when necessary to avoid zero-coverage class-level exports.
4. Run 30 seeds:
   - `greedy,qiea,ga,random,sa`
5. Primary metrics:
   - full coverage rate
   - selected test count
   - reduction ratio
   - runtime
   - simulated qubits = number of candidate tests
6. Strongest claim condition:
   - QIEA full coverage rate >= baseline full coverage rate
   - QIEA selected-count mean < at least one non-trivial baseline, ideally GA or SA

## Current limitation

The current benchmark does not yet reproduce the full workability classification from arXiv:2604.26674. It uses the paper as a dataset-validity anchor and Defects4J workability motivation. Direct quantitative comparison to the paper requires either:

- importing their published/reproduced per-bug workability data if available, or
- reproducing their framework and tagging benchmark cases as workable/non-workable before optimization.
