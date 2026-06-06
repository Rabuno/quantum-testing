"""External paper metric ingestion for benchmark comparisons."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable


def load_paper_metrics(path: str | Path) -> list[dict]:
    """Load external paper metrics from JSON or CSV.

    JSON supports either a top-level list or an object with a ``metrics`` list.
    CSV rows are returned as dictionaries with numeric fields converted where
    possible. This keeps published/reproduced paper numbers out of source code.
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, dict):
            return list(data.get("metrics", []))
        return list(data)
    if p.suffix.lower() == ".csv":
        with p.open(newline="") as f:
            return [_coerce_row(row) for row in csv.DictReader(f)]
    raise ValueError(f"unsupported paper metrics format: {p}")


def _coerce_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if v is None or v == "":
            out[k] = None
            continue
        try:
            out[k] = int(v)
            continue
        except ValueError:
            pass
        try:
            out[k] = float(v)
            continue
        except ValueError:
            pass
        out[k] = v
    return out


def compare_to_paper_metrics(records: Iterable[dict], paper_metrics: list[dict], primary: str = "qiea") -> dict:
    """Compare primary benchmark records against externally supplied metrics.

    Matching uses project + bug_id + version when available. The function is
    intentionally conservative: it reports deltas but does not infer a claim when
    external metrics omit coverage or selected-count fields.
    """
    records = [r for r in records if r.get("algorithm") == primary]
    by_case: dict[tuple[str, int, str], list[dict]] = {}
    for r in records:
        by_case.setdefault((r["project"], int(r["bug_id"]), r["version"]), []).append(r)

    comparisons = []
    for m in paper_metrics:
        project = m.get("project")
        bug_id = m.get("bug_id")
        version = m.get("version", "b")
        if project is None or bug_id is None:
            continue
        group = by_case.get((str(project), int(bug_id), str(version)), [])
        if not group:
            continue
        q_selected = sum(float(r["selected_count"]) for r in group) / len(group)
        q_cov = sum(float(r["coverage_ratio"]) for r in group) / len(group)
        p_selected = m.get("selected_count")
        p_cov = m.get("coverage_ratio")
        selected_delta = None if p_selected is None else q_selected - float(p_selected)
        coverage_delta = None if p_cov is None else q_cov - float(p_cov)
        comparisons.append({
            "project": project,
            "bug_id": int(bug_id),
            "version": version,
            "paper_algorithm": m.get("algorithm", m.get("source", "paper")),
            "primary_algorithm": primary,
            "primary_selected_mean": q_selected,
            "paper_selected_count": p_selected,
            "selected_count_delta": selected_delta,
            "primary_coverage_mean": q_cov,
            "paper_coverage_ratio": p_cov,
            "coverage_delta": coverage_delta,
            "claim_safe": (coverage_delta is None or coverage_delta >= 0) and (selected_delta is not None and selected_delta < 0),
        })
    return {"primary": primary, "comparisons": comparisons}
