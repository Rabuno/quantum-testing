# Hardware Notes — Simulation Constraints & Optimization

> **Ngay:** 2026-06-12
> **Muc dich:** Gioi han phan cung va cach toi uu simulation

---

## Phan Cung

| Thong so | Chi tiet |
|---|---|
| CPU | Intel Core i5-12450HX (8 cores / 12 threads, 2.4GHz) |
| RAM | 12 GB (kha dung ~4.7 GB) |
| GPU | Intel UHD (integrated, KHONG dung duoc CUDA) |
| OS | Windows 11 Home |
| Python | 3.12+ |

---

## Gioi Han Simulation

### Statevector Simulation
- Memory: 2^n * 16 bytes (complex128)
- 20 qubits: 16 MB
- 25 qubits: 512 MB
- 28 qubits: 4 GB (gan gioi han)
- 30 qubits: 16 GB (VUOT RAM)
- **=> Max: 25-28 qubits cho statevector**

### MPS/Tensor Network Simulation
- Memory: O(n * d * chi^2)
- chi=16: ~50-100 qubits kha thi
- chi=64: ~50-80 qubits
- **=> Max: ~50-100 qubits cho MPS**

### Stabilizer Simulation
- Memory: O(n^2)
- Chi gioi han boi thoi gian, khong phai memory
- **=> Max: 1000+ qubits (Clifford only)**

### QIEA Encoding (Hien tai)
- Memory: O(pop_size * n)
- Pop=24, n=500: ~12K floats = 96 KB
- **=> Max: 500+ tests, rat nhe**

---

## Toi Uu Hoa Tren Laptop

### 1. Su dung numpy efficiently
```python
# Dung float32 thay vi float64 cho statevector (giam 50% memory)
state = np.zeros(2**n, dtype=np.complex64)  # 8 bytes per amplitude

# Dung sparse matrices cho gate operations
from scipy import sparse
gate_sparse = sparse.csr_matrix(gate_dense)
```

### 2. Batch processing
```python
# Xu ly nhieu seeds song song voi multiprocessing
from multiprocessing import Pool
with Pool(processes=8) as pool:  # 8 cores
    results = pool.map(run_experiment, seed_list)
```

### 3. Memory management
```python
# Giai phong memory giua cac runs
import gc
del large_array
gc.collect()

# Dung generators thay vi lists
def generate_solutions():
    for i in range(n):
        yield compute_solution(i)  # Khong luu tat ca vao RAM
```

### 4. Qiskit Aer optimization
```python
# Dung method='automatic' de Aer tu chon phuong phu hop
sim = AerSimulator(method='automatic')

# Dung noise model don gian
noise_model = NoiseModel()
# Chi them noise cho gates thuc su can
```

---

## Kich Thuoc Bai Toan Kha Thi

| Bai toan | Tests | Qubits | Method | Memory | Runtime |
|---|---|---|---|---|---|
| QIEA optimization | 500 | 500 | Encoding | ~100 KB | Seconds |
| Statevector QAOA | 25 | 25 | Exact | ~500 MB | Minutes |
| MPS QAOA | 50 | 50 | Approx | ~2 GB | Minutes-Hours |
| Stabilizer | 1000 | 1000 | Clifford | ~10 MB | Seconds |
| Defects4J benchmark | 24-1000 | - | QIEA | ~MB | Minutes |

---

## Dependencies Can Cai Dat

```bash
# Core (co san)
pip install numpy

# Quantum simulation
pip install qiskit qiskit-aer

# Multi-objective optimization
pip install pymoo

# Tensor network (optional)
pip install quimb

# Statistics
pip install scipy scikit-posthocs

# Visualization
pip install matplotlib seaborn

# Progress tracking
pip install tqdm
```

---

## Chi Luong RAM Cho Moi Component

| Component | RAM Usage |
|---|---|
| Python + numpy | ~200 MB |
| Statevector (25 qubits) | ~500 MB |
| MPS (50 qubits, chi=32) | ~1-2 GB |
| Defects4J matrix (1000x500) | ~4 MB |
| QIEA population (24x500) | ~100 MB |
| OS + other apps | ~3-4 GB |
| **Tong** | **~5-7 GB / 12 GB** |

=> Con ~5-7 GB cho cac tien trinh khac, an toan.
