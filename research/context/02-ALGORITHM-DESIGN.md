# Algorithm Design — Entanglement-Enhanced QIEA

> **Ngay:** 2026-06-12
> **Trang thai:** Design phase (chua implement)

---

## 1. Kien Truc Thuat Toan

### 1.1. QIEA Co Dien (Hien tai)

Moi ca the = n qubits, moi qubit = (alpha, beta) voi |alpha|^2 + |beta|^2 = 1

Quantum Rotation Gate:
    [alpha']   [cos(theta)  -sin(theta)] [alpha]
    [beta'] =  [sin(theta)   cos(theta)] [beta]

Observation: P(1) = |beta|^2 -> collapse to binary string
Fitness: coverage_ratio - alpha * cost_ratio

### 1.2. Enhanced QIEA (De xuat)

ENTANGLEMENT REGISTER:
    Ma tran n x n, E[i][j] = correlation giua qubit i va qubit j
    E[i][j] = 0: khong co entanglement
    E[i][j] = 1: hoan toan entangled
    Cap nhat: E[i][j] = (1 - gamma) * E[i][j] + gamma * corr(i, j)

ADAPTIVE ROTATION GATE:
    theta = f(convergence_state, generation)
    theta_base = pi/18 (10 do)
    theta_adaptive = theta_base * (1 - diversity / max_diversity)
    Neu diversity < threshold -> theta = theta_base * 2

ENTANGLEMENT-AWARE CROSSOVER:
    1. Chon 2 parents P1, P2
    2. Tao offspring O voi qubit amplitudes trung binh
    3. Cap nhat E_O = (E_P1 + E_P2) / 2
    4. Neu E_O[i][j] > threshold -> giu qubit i va j cung trang thai

QUANTUM MUTATION:
    Xoay qubit truoc khi observe: theta_mut = random(-pi/8, pi/8)

NISQ NOISE SIMULATION:
    Depolarizing: P(noise) = p_dep
    Amplitude damping: |1> -> |0> voi xac suat p_ad
    Measurement error: flip bit voi xac suat p_meas

---

## 2. Entanglement Register — Data Structure

```python
class EntanglementRegister:
    """Ma tran entanglement giua cac qubit"""
    
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.matrix = np.zeros((n_qubits, n_qubits))
        self.decay_rate = 0.1
    
    def update(self, qubit_i, qubit_j, correlation):
        self.matrix[qubit_i][qubit_j] = (
            (1 - self.decay_rate) * self.matrix[qubit_i][qubit_j] 
            + self.decay_rate * correlation
        )
        self.matrix[qubit_j][qubit_i] = self.matrix[qubit_i][qubit_j]
    
    def get_entangled_pairs(self, threshold=0.5):
        pairs = []
        for i in range(self.n):
            for j in range(i+1, self.n):
                if self.matrix[i][j] > threshold:
                    pairs.append((i, j, self.matrix[i][j]))
        return pairs
    
    def merge(self, other):
        merged = EntanglementRegister(self.n)
        merged.matrix = (self.matrix + other.matrix) / 2
        return merged
```

---

## 3. Adaptive Rotation Gate

```python
def adaptive_rotation_angle(generation, max_gen, diversity, max_diversity, 
                             qubit_state, best_bit):
    # Goc co ban giam dan theo thoi gian
    theta_base = (np.pi / 18) * (1 - generation / max_gen)
    
    # Neu diversity thap -> tang exploration
    if diversity < 0.2 * max_diversity:
        theta_base *= 3.0
    elif diversity < 0.5 * max_diversity:
        theta_base *= 1.5
    
    # Huong xoay: huong ve best_bit
    p1 = abs(qubit_state[1])**2
    if best_bit == 1 and p1 < 0.5:
        direction = 1
    elif best_bit == 0 and p1 > 0.5:
        direction = -1
    else:
        direction = 0
    
    return direction * theta_base
```

---

## 4. Many-Objective Optimization (6 Objectives)

| Objective | Mo ta | Huong |
|---|---|---|
| coverage_ratio | Ty le requirement duoc cover | Maximize |
| reduction_ratio | Ty le giam so luong test | Maximize |
| selected_count | So luong test duoc chon | Minimize |
| total_cost | Tong chi phi chay test | Minimize |
| uncovered_count | So requirement chua cover | Minimize |
| fitness | Gia tri fitness tong hop | Maximize |

Su dung NSGA-III (pymoo) cho Pareto front.

---

## 5. QUBO Exact Formulation

Minimize: H = A * (1 - coverage)^2 + B * sum(x_i)

QUBO terms:
- Linear: Q[i][i] = -2*A*req_count_i + B - 2*A*penalty
- Quadratic: Q[i][j] = A * overlap(i,j)

Compatible voi IBM Qiskit Aer va D-Wave.

---

## 6. NISQ Noise Model

```python
class NISQNoiseModel:
    def __init__(self, depolarizing_prob=0.01, 
                 amplitude_damping_prob=0.005,
                 measurement_error_prob=0.005):
        self.p_dep = depolarizing_prob
        self.p_ad = amplitude_damping_prob
        self.p_meas = measurement_error_prob
    
    def noisy_observation(self, alpha, beta):
        # 1. Depolarizing
        p1 = abs(beta)**2
        p1_noisy = (1 - self.p_dep) * p1 + self.p_dep * 0.5
        # 2. Observation
        bit = 1 if np.random.random() < p1_noisy else 0
        # 3. Measurement error
        if np.random.random() < self.p_meas:
            bit = 1 - bit
        return bit
```

---

## 7. Implementation Roadmap

| Phase | Thoi gian | Cong viec |
|---|---|---|
| Phase 1 | 2 tuan | Entanglement register + adaptive rotation |
| Phase 2 | 2 tuan | Many-objective + QUBO exact export |
| Phase 3 | 2 tuan | QAOA baseline + Qiskit integration |
| Phase 4 | 3 tuan | Harvest Defects4J bugs |
| Phase 5 | 2 tuan | Run experiments |
| Phase 6 | 2 tuan | Statistical analysis |
| Phase 7 | 3 tuan | Write paper |
