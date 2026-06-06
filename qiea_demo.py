"""
QIEA — Quantum-inspired Evolutionary Algorithm Demo
====================================================
Áp dụng QIEA để tối ưu hóa bài toán test case generation.

QIEA dùng qubit representation (α, β) thay vì binary truyền thống:
- |ψ⟩ = α|0⟩ + β|1⟩  với |α|² + |B|² = 1
- Observation (collapse) → binary solution
- Quantum rotation gate để update qubit theo fitness

Ứng dụng demo: Tìm optimal test input set cho bài toán
"Maximum Coverage" — chọn subset test cases maximize coverage.
"""

import numpy as np
import random
import math
from typing import List, Tuple, Callable

class QIEA:
    """Quantum-inspired Evolutionary Algorithm"""
    
    def __init__(
        self,
        n_qubits: int,         # Số qubits = số binary variables
        pop_size: int,         # Số quantum individuals
        max_gen: int,          # Số generations
        rotation_angle: float = 0.01 * math.pi,  # Góc rotation
        evaluate_fn=None       # Hàm đánh giá fitness
    ):
        self.n_qubits = n_qubits
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.rotation_angle = rotation_angle
        self.evaluate_fn = evaluate_fn
        
        # Initialize quantum population: mỗi qubit = (alpha, beta)
        # Alpha = 1/sqrt(2) → equal superposition
        self.population = self._init_population()
        
        # Best solution tracking
        self.best_solution = None
        self.best_fitness = float('-inf')
        self.history = []
    
    def _init_population(self):
        """Initialize qubits trong equal superposition"""
        pop = []
        for _ in range(self.pop_size):
            individual = []
            for _ in range(self.n_qubits):
                # |ψ⟩ = (1/√2)|0⟩ + (1/√2)|1⟩  → max superposition
                alpha = 1.0 / math.sqrt(2)
                beta = 1.0 / math.sqrt(2)
                individual.append([alpha, beta])
            pop.append(individual)
        return pop
    
    def observe(self, individual) -> List[int]:
        """Collapse quantum state → binary string"""
        binary = []
        for alpha, beta in individual:
            # P(1) = |β|²
            prob_1 = beta ** 2
            if random.random() < prob_1:
                binary.append(1)
            else:
                binary.append(0)
        return binary
    
    def quantum_rotate(self, qubit_idx, solution_binary, best_binary, fitness_diff):
        """Quantum Rotation Gate: update qubit theo hướng tốt hơn"""
        alpha, beta = self.population[0][qubit_idx]  # Reference from first individual
        
        # Determine rotation direction
        # Nếu solution[i] tốt hơn best[i] → rotate về phía đó
        x_i = solution_binary[qubit_idx]
        b_i = best_binary[qubit_idx]
        
        # Rotation angle (adaptive)
        delta_theta = self.rotation_angle * (1 + fitness_diff)
        
        # Apply rotation gate
        # R(Δθ) = [[cos(Δθ), -sin(Δθ)], [sin(Δθ), cos(Δθ)]]
        if x_i == 0 and b_i == 1:
            # Rotate toward |1⟩
            new_alpha = alpha * math.cos(delta_theta) - beta * math.sin(delta_theta)
            new_beta = alpha * math.sin(delta_theta) + beta * math.cos(delta_theta)
        elif x_i == 1 and b_i == 0:
            # Rotate toward |0⟩
            new_alpha = alpha * math.cos(-delta_theta) - beta * math.sin(-delta_theta)
            new_beta = alpha * math.sin(-delta_theta) + beta * math.cos(-delta_theta)
        else:
            new_alpha, new_beta = alpha, beta
        
        # Normalize
        norm = math.sqrt(new_alpha**2 + new_beta**2)
        if norm > 0:
            new_alpha /= norm
            new_beta /= norm
        
        return new_alpha, new_beta
    
    def run(self, verbose=True):
        """Chạy QIEA"""
        if verbose:
            print("=" * 60)
            print(f"QIEA: {self.n_qubits} qubits, {self.pop_size} individuals, {self.max_gen} gen")
            print("=" * 60)
        
        for gen in range(self.max_gen):
            # Observation phase: collapse → binary solutions
            solutions = [self.observe(ind) for ind in self.population]
            
            # Evaluate fitness
            fitnesses = [self.evaluate_fn(sol) for sol in solutions]
            
            # Track best
            gen_best_idx = np.argmax(fitnesses)
            gen_best_fitness = fitnesses[gen_best_idx]
            gen_best_solution = solutions[gen_best_idx]
            
            if gen_best_fitness > self.best_fitness:
                self.best_fitness = gen_best_fitness
                self.best_solution = gen_best_solution.copy()
            
            self.history.append(self.best_fitness)
            
            if verbose and gen % 10 == 0:
                print(f"Gen {gen:4d} | Best fitness: {self.best_fitness:.4f} | "
                      f"Gen best: {gen_best_fitness:.4f}")
            
            # Quantum rotation update
            for ind_idx in range(self.pop_size):
                for q in range(self.n_qubits):
                    fitness_diff = 0
                    if fitnesses[ind_idx] != 0:
                        try:
                            fitness_diff = (self.best_fitness - fitnesses[ind_idx]) / abs(self.best_fitness)
                        except (ZeroDivisionError, ValueError):
                            fitness_diff = 0
                    
                    new_alpha, new_beta = self.quantum_rotate(
                        q, solutions[ind_idx], self.best_solution, fitness_diff
                    )
                    self.population[ind_idx][q] = [new_alpha, new_beta]
            
            # Diversity injection: nếu quá convergent, reset một số qubits
            if gen > 0 and gen % 20 == 0:
                diversity = self._measure_diversity()
                if diversity < 0.1:
                    # Reset random individual to superposition
                    idx = random.randint(0, self.pop_size - 1)
                    for q in range(self.n_qubits):
                        self.population[idx][q] = [1/math.sqrt(2), 1/math.sqrt(2)]
        
        if verbose:
            print(f"\n✅ Done! Best fitness: {self.best_fitness:.4f}")
            print(f"   Best solution: {self.best_solution}")
        
        return self.best_solution, self.best_fitness, self.history
    
    def _measure_diversity(self) -> float:
        """Độ đa dạng của population"""
        alphas = [ind[0][0] for ind in self.population]
        return np.std(alphas)


# =====================================================================
# DEMO 1: OneMax Problem (đơn giản — tối ưu số bit 1)
# =====================================================================
def onemax(solution: List[int]) -> float:
    """Fitness = số bit 1"""
    return sum(solution)


# =====================================================================
# DEMO 2: Test Suite Optimization (Maximum Coverage)
# =====================================================================
def create_test_coverage_problem(n_tests=20, n_requirements=15, seed=42):
    """
    Giả lập bài toán test suite optimization.
    Mỗi test case cover một subset requirements.
    Mục tiêu: chọn minimum tests để cover maximum requirements.
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # coverage[i] = set of requirements covered by test i
    coverage = []
    for i in range(n_tests):
        # Mỗi test cover 2-8 requirements randomly
        n_cover = random.randint(2, 8)
        covered = set(random.sample(range(n_requirements), min(n_cover, n_requirements)))
        coverage.append(covered)
    
    def fitness(solution: List[int]) -> float:
        """Fitness = coverage - penalty for too many tests"""
        selected = [i for i, s in enumerate(solution) if s == 1]
        total_cover = set()
        for idx in selected:
            total_cover |= coverage[idx]
        
        coverage_score = len(total_cover) / n_requirements  # 0..1
        cost_penalty = 0.1 * (len(selected) / n_tests)  # penalty test count
        
        return coverage_score - cost_penalty
    
    return fitness, coverage


# =====================================================================
# DEMO 3: QIEA vs Classical GA So sánh
# =====================================================================
def classical_ga(n_bits, max_gen, evaluate_fn, pop_size=20):
    """Classical Genetic Algorithm để so sánh"""
    # Init random binary population
    pop = [[random.randint(0, 1) for _ in range(n_bits)] for _ in range(pop_size)]
    
    best_sol = None
    best_fit = float('-inf')
    history = []
    
    for gen in range(max_gen):
        fits = [evaluate_fn(ind) for ind in pop]
        gen_best_idx = np.argmax(fits)
        
        if fits[gen_best_idx] > best_fit:
            best_fit = fits[gen_best_idx]
            best_sol = pop[gen_best_idx].copy()
        
        history.append(best_fit)
        
        # Selection (tournament)
        new_pop = []
        for _ in range(pop_size):
            candidates = random.sample(list(zip(pop, fits)), 3)
            winner = max(candidates, key=lambda x: x[1])[0]
            new_pop.append(winner.copy())
        
        # Crossover
        pop = []
        for i in range(0, len(new_pop), 2):
            p1 = new_pop[i]
            p2 = new_pop[(i+1) % len(new_pop)]
            point = random.randint(1, n_bits - 1)
            c1 = p1[:point] + p2[point:]
            c2 = p2[:point] + p1[point:]
            pop.extend([c1, c2])
        
        # Mutation
        for ind in pop:
            for j in range(n_bits):
                if random.random() < 0.05:
                    ind[j] = 1 - ind[j]
    
    return best_sol, best_fit, history


# =====================================================================
# MAIN — Run all demos
# =====================================================================
if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("  QUANTUM-INSPIRED EVOLUTIONARY ALGORITHM DEMO")
    print("🧪" * 30 + "\n")
    
    # ---- DEMO 1: OneMax ----
    print("\n" + "=" * 60)
    print("DEMO 1: OneMax Problem (20 bits)")
    print("=" * 60)
    
    qiea = QIEA(
        n_qubits=20,
        pop_size=10,
        max_gen=100,
        evaluate_fn=onemax
    )
    sol, fit, hist = qiea.run(verbose=True)
    print(f"QIEA result: {sum(sol)}/20 bits = 1")
    
    # ---- DEMO 2: Test Coverage Optimization ----
    print("\n" + "=" * 60)
    print("DEMO 2: Test Suite Optimization (20 tests, 15 requirements)")
    print("=" * 60)
    
    fitness_fn, coverage = create_test_coverage_problem(
        n_tests=20, n_requirements=15, seed=42
    )
    
    # Print problem
    print("\nCoverage matrix:")
    for i, cov in enumerate(coverage):
        print(f"  Test {i:2d}: covers requirements {sorted(cov)}")
    
    # Run QIEA
    print("\n--- QIEA ---")
    qiea2 = QIEA(
        n_qubits=20,
        pop_size=15,
        max_gen=200,
        evaluate_fn=fitness_fn
    )
    qiea2.run(verbose=True)
    
    selected_tests = [i for i, s in enumerate(qiea2.best_solution) if s == 1]
    covered_reqs = set()
    for idx in selected_tests:
        covered_reqs |= coverage[idx]
    print(f"\n  Selected tests: {selected_tests}")
    print(f"  Tests count: {len(selected_tests)}/{20}")
    print(f"  Requirements covered: {len(covered_reqs)}/15 = {sorted(covered_reqs)}")
    
    # ---- DEMO 3: QIEA vs GA Comparison ----
    print("\n" + "=" * 60)
    print("DEMO 3: QIEA vs Classical GA Comparison")
    print("=" * 60)
    
    N_BITS = 30
    MAX_GEN = 200
    
    # Run QIEA 3 times
    qiea_results = []
    for run_i in range(3):
        q = QIEA(n_qubits=N_BITS, pop_size=15, max_gen=MAX_GEN, evaluate_fn=onemax)
        q.population = q._init_population()  # Reset
        _, fit_q, hist_q = q.run(verbose=False)
        qiea_results.append((fit_q, hist_q))
        print(f"  QIEA run {run_i+1}: best = {fit_q}")
    
    # Run GA 3 times
    ga_results = []
    for run_i in range(3):
        _, fit_g, hist_g = classical_ga(N_BITS, MAX_GEN, onemax)
        ga_results.append((fit_g, hist_g))
        print(f"  GA   run {run_i+1}: best = {fit_g}")
    
    # Summary
    avg_qiea = np.mean([r[0] for r in qiea_results])
    avg_ga = np.mean([r[0] for r in ga_results])
    
    print(f"\n📊 Average best fitness over 3 runs (OneMax, {N_BITS} bits, {MAX_GEN} gen):")
    print(f"  QIEA: {avg_qiea:.2f}")
    print(f"  GA:   {avg_ga:.2f}")
    
    if avg_qiea >= avg_ga:
        print(f"  ✅ QIEA matches or beats GA! (Δ = {avg_qiea - avg_ga:+.2f})")
    else:
        print(f"  📌 GA wins this round. QIEA có thể cần tune parameters.")
    
    print("\n🎉 All demos complete!")
