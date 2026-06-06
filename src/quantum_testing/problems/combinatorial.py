"""Constrained combinatorial interaction testing (CIT) utilities."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from quantum_testing.algorithms.qiea import QIEA

Assignment = dict[str, object]
Interaction = tuple[tuple[str, object], ...]
Constraint = Callable[[Assignment], bool]


@dataclass
class CITModel:
    parameters: dict[str, list[object]]
    strength: int = 2
    constraint: Optional[Constraint] = None

    def __post_init__(self) -> None:
        if self.strength < 1:
            raise ValueError("strength must be >= 1")
        if self.strength > len(self.parameters):
            raise ValueError("strength cannot exceed number of parameters")

    @property
    def names(self) -> list[str]:
        return list(self.parameters.keys())

    def valid_assignment(self, assignment: Mapping[str, object]) -> bool:
        return True if self.constraint is None else bool(self.constraint(dict(assignment)))

    def all_assignments(self):
        names = self.names
        for values in itertools.product(*(self.parameters[n] for n in names)):
            row = dict(zip(names, values))
            if self.valid_assignment(row):
                yield row

    def interactions(self) -> set[Interaction]:
        interactions: set[Interaction] = set()
        names = self.names
        for row in self.all_assignments():
            for combo in itertools.combinations(names, self.strength):
                interactions.add(tuple((name, row[name]) for name in combo))
        return interactions

    def row_interactions(self, row: Mapping[str, object]) -> set[Interaction]:
        if not self.valid_assignment(row):
            return set()
        return {tuple((name, row[name]) for name in combo) for combo in itertools.combinations(self.names, self.strength)}

    def covered_interactions(self, rows: Sequence[Mapping[str, object]]) -> set[Interaction]:
        covered: set[Interaction] = set()
        for row in rows:
            covered |= self.row_interactions(row)
        return covered

    def coverage_ratio(self, rows: Sequence[Mapping[str, object]]) -> float:
        all_i = self.interactions()
        if not all_i:
            return 1.0
        return len(self.covered_interactions(rows)) / len(all_i)


def greedy_covering_array(model: CITModel, max_rows: int | None = None, seed: int | None = None) -> tuple[list[Assignment], dict]:
    rng = np.random.default_rng(seed)
    target = model.interactions()
    uncovered = set(target)
    candidates = list(model.all_assignments())
    rng.shuffle(candidates)
    rows: list[Assignment] = []
    while uncovered and candidates and (max_rows is None or len(rows) < max_rows):
        best = max(candidates, key=lambda r: len(model.row_interactions(r) & uncovered))
        gain = model.row_interactions(best) & uncovered
        if not gain:
            break
        rows.append(dict(best))
        uncovered -= gain
        candidates.remove(best)
    report = {"rows": len(rows), "total_interactions": len(target), "covered_interactions": len(target) - len(uncovered), "coverage_ratio": (len(target)-len(uncovered))/len(target) if target else 1.0}
    return rows, report


def _bits_needed(n: int) -> int:
    return max(1, int(np.ceil(np.log2(max(1, n)))))


def _decode(bits: Sequence[int], model: CITModel, n_rows: int) -> list[Assignment]:
    names = model.names
    widths = [_bits_needed(len(model.parameters[name])) for name in names]
    rows: list[Assignment] = []
    pos = 0
    for _ in range(n_rows):
        row: Assignment = {}
        for name, width in zip(names, widths):
            raw = 0
            for b in bits[pos:pos+width]:
                raw = (raw << 1) | int(b)
            pos += width
            vals = model.parameters[name]
            row[name] = vals[raw % len(vals)]
        rows.append(row)
    return rows


def qiea_covering_array(model: CITModel, n_rows: int = 8, generations: int = 120, pop_size: int = 20, seed: int | None = 42) -> tuple[list[Assignment], dict]:
    target = model.interactions()
    widths = [_bits_needed(len(model.parameters[name])) for name in model.names]
    n_bits = n_rows * sum(widths)

    def fitness(bits: Sequence[int]) -> float:
        rows = _decode(bits, model, n_rows)
        valid = [r for r in rows if model.valid_assignment(r)]
        covered = model.covered_interactions(valid)
        cov = len(covered) / len(target) if target else 1.0
        invalid_penalty = (n_rows - len(valid)) / max(1, n_rows)
        unique_penalty = (len(valid) - len({tuple(sorted(r.items())) for r in valid})) / max(1, n_rows)
        return cov - 0.25 * invalid_penalty - 0.05 * unique_penalty

    q = QIEA(n_qubits=n_bits, pop_size=pop_size, max_gen=generations, evaluate_fn=fitness, seed=seed)
    best, fit, history = q.run(verbose=False)
    rows = [r for r in _decode(best, model, n_rows) if model.valid_assignment(r)]
    # Greedy repair: add rows until full coverage if possible; this makes solver useful as a hybrid QIEA+repair algorithm.
    uncovered = target - model.covered_interactions(rows)
    if uncovered:
        candidates = list(model.all_assignments())
        while uncovered:
            best_row = max(candidates, key=lambda r: len(model.row_interactions(r) & uncovered))
            gain = model.row_interactions(best_row) & uncovered
            if not gain:
                break
            rows.append(dict(best_row))
            uncovered -= gain
            candidates.remove(best_row)
    report = {"rows": len(rows), "total_interactions": len(target), "covered_interactions": len(model.covered_interactions(rows)), "coverage_ratio": model.coverage_ratio(rows), "fitness": fit, "history": history}
    return rows, report
