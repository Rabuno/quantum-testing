# Harvest Presets

## Quick Start (Recommended)

Harvest 3 smallest bugs — safe for any machine with 4GB+ RAM:

```bash
uv run python -m quantum_testing.cli quick-harvest \
  --defects4j-home /path/to/defects4j
```

This harvests: **Lang/1b, Lang/2b, Chart/1b**

| Resource | Estimate |
|----------|----------|
| Work dir | ~600MB–1.5GB (deletable) |
| Output | ~600KB–2.2MB (kept) |
| RAM | ~2–3 GB |
| Time | ~30–60 min |

## Medium Batch (10 bugs)

For stronger statistical analysis:

```bash
uv run python -m quantum_testing.cli batch-harvest \
  --defects4j-home /path/to/defects4j \
  --projects Lang,Chart,Math \
  --bugs "Lang:1-5,Chart:1-3,Math:1-2"
```

| Resource | Estimate |
|----------|----------|
| Work dir | ~2–5 GB (deletable) |
| Output | ~2–8 MB (kept) |
| RAM | ~3–4 GB |
| Time | ~1.5–3 hours |

## After Harvest

```bash
# Run experiment on harvested data
uv run python -m quantum_testing.cli experiment \
  --projects Lang,Chart --bugs "Lang:1-2,Chart:1-1" \
  --algorithms greedy,qiea,enhanced_qiea,ga,random,sa \
  --seeds 42,123,456,789,1024

# Delete work dir to reclaim disk (data is safe in datasets/defects4j/)
rm -rf /tmp/quantum-testing-defects4j
```

## Safety Notes

- **Work dir** (`/tmp/quantum-testing-defects4j`) is fully deletable after harvest
- **Output dir** (`datasets/defects4j`) contains the actual coverage matrices — keep this
- If harvest fails midway, re-run with same command — it resumes from cached workdir
- Each bug runs tests individually; some trigger tests may fail by design (recorded, not fatal)
