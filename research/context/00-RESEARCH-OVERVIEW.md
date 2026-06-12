# Quantum Testing Research — Tong Quan Nghien Cuu

> **Cap nhat:** 2026-06-12
> **Tac gia:** Rabuno
> **Muc tieu:** Bai bao Q2 journal ve Quantum-Inspired Test Suite Minimization

---

## Muc Tieu Nghien Cuu

Xay dung **Entanglement-Enhanced Quantum-Inspired Evolutionary Algorithm (E-QIEA)** cho bai toan **Many-Objective Test Suite Minimization**, chay hoan toan tren laptop ca nhan (khong can quantum hardware that), voi muc do mo phong quantum gan nhat co the.

### Target Journal (Q2)
- **Primary:** Software Testing, Verification and Reliability (Wiley, IF ~2.5)
- **Secondary:** International Journal on Software Tools for Technology Transfer (Springer)
- **Stretch:** Empirical Software Engineering (Springer, Q1)

---

## Phan Cung Hien Tai

| Thong so | Chi tiet |
|---|---|
| CPU | Intel Core i5-12450HX (8 cores / 12 threads, 2.4GHz) |
| RAM | 12 GB (kha dung ~4.7 GB) |
| GPU | Intel UHD (integrated, khong dung duoc CUDA) |
| OS | Windows 11 Home |

### Gioi han Simulation
| Method | Max Qubits | Memory |
|---|---|---|
| Statevector | ~25-28 | O(2^n) |
| MPS/Tensor | ~50-100 | O(n * chi^2) |
| Stabilizer | ~1000+ (Clifford only) | O(n^2) |
| QIEA Encoding | 500+ | O(n) |

---

## Khoang Trong Nghien Cuu (Research Gaps)

1. Chua ai ket hop Entanglement + Many-Objective + QIEA cho test suite minimization
2. Chua ai co benchmark thong nhat tren nhieu Defects4J bugs voi statistical testing
3. Chua ai so sanh truc tiep QIEA vs QAOA vs Quantum Annealing tren cung bai toan testing
4. Chua ai co framework tich hop QUBO export → chay tren real quantum hardware
5. Hau het chi dung single-objective — chua ai dung many-objective (6+ objectives) voi quantum

---

## Kien Truc De Xuat (3 Lop)

```
Layer 1: Enhanced QIEA (CPU, no GPU)
  - Entanglement register
  - Adaptive rotation gate
  - Many-objective (NSGA-III)
  - NISQ noise simulation
  -> Handles 100-500 tests easily

Layer 2: Quantum Circuit Bridge (Qiskit Aer)
  - QUBO export (exact formulation)
  - Statevector simulation (<=25 qubits)
  - MPS simulation (<=50 qubits)
  - Noise models
  -> Validates QIEA on real quantum circuits

Layer 3: Benchmark & Analysis
  - Defects4J (10+ bugs)
  - 9 baselines
  - Wilcoxon + Cliff's delta + CD diagrams
  - Pareto front visualization
```

---

## Research Questions

| RQ | Question |
|---|---|
| RQ1 | E-QIEA co vuot troi QIEA co dien trong test minimization? |
| RQ2 | Many-objective co cung cap Pareto front da dang hon single-objective? |
| RQ3 | QUBO bridge co cho ket qua tuong duong tren quantum simulator? |
| RQ4 | Ket qua co generalize tren nhieu Defects4J bugs? |

---

## Timeline

| Phase | Thoi gian | Cong viec |
|---|---|---|
| Phase 1 | 2 tuan | Implement entanglement register + adaptive rotation |
| Phase 2 | 2 tuan | Implement many-objective + QUBO exact export |
| Phase 3 | 2 tuan | Implement QAOA baseline + Qiskit integration |
| Phase 4 | 3 tuan | Harvest Defects4J (Lang/Chart/Cli/Math bugs 1-10) |
| Phase 5 | 2 tuan | Run all experiments |
| Phase 6 | 2 tuan | Statistical analysis + visualization |
| Phase 7 | 3 tuan | Write paper + submit |

**Tong: ~14 tuan (3.5 thang)**

---

## Top 10 Papers Can Doc

1. Trovato et al. (2025) — QAOA-TCS. arXiv:2504.18955
2. Trovato et al. (2025) — SelectQA. Int J Softw Tools Technol Transfer
3. Zhang & Emu (2025) — Quantum-Guided TCM. IEEE CASCON. arXiv:2511.15665
4. Zhang et al. (2025) — Quantum Optimization for SE Survey. arXiv:2506.16878
5. Kashfi Haghighi et al. (2025) — EAQGA. IBM 127-qubit hardware
6. Gharehchopogh (2023) — QI Metaheuristic Survey. Artif Intell Rev (286 cites)
7. Murillo et al. (2025) — Quantum SE Roadmap. ACM (120 cites)
8. Wang et al. (2024) — IGDec-QAOA. Industrial datasets
9. Kalachev et al. (2025) — Pilot-Wave Simulator. 476 qubits. arXiv:2510.24218
10. Huang et al. (2025) — Approximate Noisy Simulation. 200 qubits. arXiv:2503.10340

---

## Lien Ket Quan Trong

- 01-DEEP-RESEARCH.md — Bao cao nghien cuu sau
- 02-ALGORITHM-DESIGN.md — Thiet ke thuat toan
- 03-PAPER-OUTLINE.md — Outline bai bao
- 04-REFERENCES.md — Tai lieu tham khao
- 05-HARDWARE-NOTES.md — Ghi chu phan cung & simulation
- ../design/ — Chi tiet thiet ke
- ../paper/ — Bai bao
- ../references/ — Tai lieu
