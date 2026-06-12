# CLAUDE.md — Quantum Testing Research Project

> Project-level context for Claude Code. Loaded in every session started from this directory.

---

## Muc tieu du an

Xay dung **Entanglement-Enhanced Quantum-Inspired Evolutionary Algorithm (E-QIEA)** cho bai toan **Many-Objective Test Suite Minimization**, chay hoan toan tren laptop ca nhan (khong can quantum hardware that), voi muc do mo phong quantum gan nhat co the.

**Target Journal (Q2):** Software Testing, Verification and Reliability (Wiley, IF ~2.5)

---

## Cau truc du an

```
quantum-testing/
├── src/quantum_testing/          — Source code chinh
│   ├── algorithms/               — QIEA, baselines
│   ├── benchmarks/               — Defects4J runner, metrics, reporting
│   ├── datasets/                 — Defects4J data adapter
│   ├── problems/                 — Combinatorial, coverage problems
│   ├── cli.py                    — Command-line interface
│   ├── metrics.py                — Metrics computation
│   └── multiobjective.py         — Many-objective optimization
├── tests/                        — Unit + integration tests
├── research/                     — Research context (de tiep tuc tren may khac)
│   ├── context/                  — Tong quan, nghien cuu, thiet ke
│   ├── design/                   — Chi tiet thiet ke
│   ├── paper/                    — Bai bao nhap
│   └── references/               — PDF papers
├── datasets/                     — Defects4J coverage matrices
├── artifacts/                    — Ket qua benchmark
├── docs/                         — Tai lieu bo sung
└── examples/                     — Vi du input
```

---

## Tech Stack

- **Language:** Python 3.12+
- **Package manager:** uv
- **Quantum simulation:** Qiskit Aer (statevector, MPS)
- **Optimization:** NSGA-III (many-objective)
- **Benchmark:** Defects4J
- **Testing:** pytest

---

## Quy uoc code

- Duong dan file: dung dau gach cheo (src/quantum_testing/...)
- Git commit: dung tien to quy uoc (feat:, fix:, docs:, refactor:)
- Functions: < 50 dong, Files: < 800 dong
- Immutability: khong mutate objects, luon return new copies
- Error handling: handle explicitly, khong swallow errors

---

## Research Context

Khi can tiep tuc nghien cuu tren session/may khac:

1. Doc research/context/00-RESEARCH-OVERVIEW.md (30 giay)
2. Doc research/context/02-ALGORITHM-DESIGN.md (1 phut)
3. Doc research/context/03-PAPER-OUTLINE.md (1 phut)
4. Bat dau code tiep tuc

---

## Ghi chu

- Du an KHONG can GPU — chay hoan toan tren CPU
- Qiskit Aer statevector gioi han ~25-28 qubits tren RAM 12GB
- QIEA encoding co the handle 500+ qubits (O(n) memory)
- Defects4J bugs dang dung: Lang/1b, Lang/24b
