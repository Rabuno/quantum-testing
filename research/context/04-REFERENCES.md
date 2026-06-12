# References — Quantum Testing Research

> **Cap nhat:** 2026-06-12

---

## Core Papers (Phai doc het)

### Quantum Optimization for Software Testing

1. **Trovato et al. (2025)** — QAOA-TCS
   - "A Preliminary Investigation on the Usage of Quantum Approximate Optimization Algorithms for Test Case Selection"
   - arXiv:2504.18955
   - Gate-based QAOA cho test case selection, ideal simulation
   - Baselines: Additional Greedy, DIV-GA, SelectQA

2. **Trovato et al. (2025)** — SelectQA
   - Quantum annealing approach for regression test case selection
   - Published in: International Journal on Software Tools for Technology Transfer
   - Outperforms BootQA in effectiveness, matches Greedy in efficiency
   - arXiv:2411.15963

3. **Zhang & Emu (2025)** — Quantum-Guided TCM
   - "Quantum-Guided Test Case Minimization for LLM-Based Code Generation"
   - IEEE CASCON 2025
   - QUBO formulation + quantum annealing, 16x speedup over SA
   - arXiv:2511.15665

4. **Zhang et al. (2025)** — Quantum Optimization for SE Survey
   - "Quantum optimization for software engineering: a survey"
   - ACM Transactions on Software Engineering
   - 77 primary studies from 2083 publications
   - arXiv:2506.16878

5. **Kashfi Haghighi et al. (2025)** — EAQGA
   - "EAQGA: A Quantum-Enhanced Genetic Algorithm with Novel Entanglement-Aware Crossovers"
   - Real IBM 127-qubit Eagle processor
   - 33.6% improvement over GA, 37.2% over QIGA

### Quantum-Inspired Metaheuristics

6. **Gharehchopogh (2023)** — QI Metaheuristic Survey
   - "Quantum-inspired metaheuristic algorithms: comprehensive survey and classification"
   - Artificial Intelligence Review (Springer), 286 citations
   - Classification framework cho quantum-inspired algorithms

7. **Iovane (2025)** — QIEA Perspectives
   - "Quantum-Inspired Algorithms and Perspectives for Optimization"
   - Electronics (MDPI), 30 citations

8. **Priyadarshini (2024)** — Swarm QI Optimization
   - "Swarm-Intelligence-Based Quantum-Inspired Optimization Techniques"
   - Quantum Machine Intelligence (Springer), 21 citations

### Quantum Software Engineering

9. **Murillo et al. (2025)** — Quantum SE Roadmap
   - "Quantum software engineering: Roadmap and challenges ahead"
   - ACM, 120 citations
   - Reviews 102 papers, most focus on test optimization

10. **Wang et al. (2024)** — IGDec-QAOA
    - QAOA for test case optimization with problem decomposition
    - Industrial datasets: ABB, Google, Orona

### Quantum Simulation on Classical Hardware

11. **Kalachev et al. (2025)** — Pilot-Wave Simulator
    - "Pilot-Wave Simulator: Exact Classical Sampling from Ideal and Noisy Quantum Circuits up to Hundreds of Qubits"
    - 476 qubits exact sampling with noise models
    - arXiv:2510.24218

12. **Huang et al. (2025)** — Approximate Noisy Simulation
    - "Approximation Methods for Simulation and Equivalence Checking of Noisy Quantum Circuits"
    - ~200 qubits with 20 noise operators
    - Tensor network + SVD approach
    - arXiv:2503.10340

13. **Codsi & Laakkonen (2026)** — Stabilizer Decomposition
    - "Unifying Graph Measures and Stabilizer Decompositions for Classical Simulation"
    - Linear memory, trivially parallelizable

### Test Suite Minimization

14. **Sharma & Raju (2024)** — Metaheuristic Overview
    - "Metaheuristic optimization algorithms: a comprehensive overview"
    - Soft Computing, 184 citations

15. **Kang et al. (2025)** — Metaheuristic Comparison
    - "A Comparative Study of Four Metaheuristic Algorithms for Test Suite Reduction"
    - 100% requirement coverage comparison

16. **Muazu & Hashim (2025)** — Harmony Search CIT
    - "Enhancing harmony search for coverage efficiency in combinatorial interaction testing"
    - IEEE Access

### Defects4J Benchmark

17. **Just et al. (2014)** — Defects4J
    - "Defects4J: A Database of Existing Faults to Enable Controlled Testing Studies"
    - IST 2014, 1000+ citations

18. **Escher (2025)** — Source Code Embeddings TCP
    - "An Investigation on the Usage of Source Code Embeddings in Test Case Prioritization"
    - Uses Defects4J

### Multi-Objective Optimization

19. **Deb & Jain (2014)** — NSGA-III
    - "An Evolutionary Many-Objective Optimization Algorithm Using Reference-Point-Based Nondominated Sorting Approach"
    - IEEE TEVC

20. **Zhang & Li (2007)** — MOEA/D
    - "MOEA/D: A Multiobjective Evolutionary Algorithm Based on Decomposition"
    - IEEE TEVC

---

## Journals & Venues

### Q2 Targets
- Software Testing, Verification and Reliability (Wiley, IF ~2.5)
- International Journal on Software Tools for Technology Transfer (Springer, IF ~2.0)
- Software Quality Journal (Springer, IF ~2.0)
- Journal of Software: Evolution and Process (Wiley, IF ~2.5)

### Q1 Stretch
- Empirical Software Engineering (Springer, IF ~4.0)
- Information and Software Technology (Elsevier, IF ~4.0)
- Journal of Systems and Software (Elsevier, IF ~3.5)
- IEEE Transactions on Software Engineering (IF ~6.5)

### Conferences
- ICSE, ESEC/FSE, ASE (top SE)
- GECCO, CEC (evolutionary computation)
- QCE, IEEE Quantum Week (quantum computing)
