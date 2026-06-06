"""Defects4J dataset harvesting utilities.

This module intentionally keeps Defects4J as an optional external dependency.
Unit tests exercise XML parsing and matrix generation with fixtures; real dataset
collection requires a local Defects4J installation, Java 11, Perl dependencies,
and initialized project repositories.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence
from xml.etree import ElementTree as ET


@dataclass
class Defects4JConfig:
    """Configuration for harvesting one Defects4J bug-version matrix."""

    defects4j_home: Path
    project: str
    bug_id: int
    version: str = "b"
    work_root: Path = Path("/tmp/quantum-testing-defects4j")
    output_dir: Path = Path("datasets/defects4j")
    test_property: str = "tests.trigger"
    limit_tests: int | None = None
    reuse_workdir: bool = True
    force_coverage: bool = False
    requirement_scope: str = "covered-lines"
    expand_class_tests: bool = True
    test_filter: str | None = None


@dataclass
class Defects4JResult:
    """Paths and counts produced by a Defects4J harvest."""

    matrix_csv: Path
    tests_txt: Path
    requirements_txt: Path
    metadata_json: Path
    total_tests: int
    total_requirements: int
    failures: list[dict]


def safe_filename(test_id: str) -> str:
    """Convert a Java test id into a filesystem-safe, mostly readable name."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", test_id).strip("._")
    return safe[:180] or "test"


def parse_cobertura_xml(path: str | Path) -> set[str]:
    """Parse covered line requirements from a Cobertura ``coverage.xml`` file.

    Requirement IDs use ``<filename>:<line-number>``. Only lines with ``hits > 0``
    are included. The parser is namespace-tolerant and works with the XML emitted
    by Defects4J/Cobertura as well as small test fixtures.
    """
    root = ET.parse(path).getroot()
    requirements: set[str] = set()
    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename") or cls.attrib.get("name") or "unknown"
        for line in cls.findall(".//line"):
            number = line.attrib.get("number")
            hits_raw = line.attrib.get("hits", "0")
            try:
                hits = int(float(hits_raw))
            except ValueError:
                hits = 0
            if number is not None and hits > 0:
                requirements.add(f"{filename}:{number}")
    return requirements


def write_labeled_matrix(
    test_coverages: Mapping[str, set[str]],
    out_csv: str | Path,
    requirements: Sequence[str] | None = None,
) -> list[str]:
    """Write a dense labeled binary coverage matrix.

    The first column is ``test_id`` and remaining columns are requirement labels.
    This format remains compatible with ``CoverageProblem.load_csv`` because that
    loader skips a non-binary first column and ignores the header.
    """
    out = Path(out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    reqs = list(requirements) if requirements is not None else sorted(set().union(*test_coverages.values()) if test_coverages else set())
    req_index = {r: i for i, r in enumerate(reqs)}
    with out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["test_id", *reqs])
        for test_id, covered in test_coverages.items():
            row = [0] * len(reqs)
            for req in covered:
                idx = req_index.get(req)
                if idx is not None:
                    row[idx] = 1
            writer.writerow([test_id, *row])
    return reqs


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def _defects4j_bin(home: Path) -> Path:
    return home / "framework" / "bin" / "defects4j"


def _base_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["TZ"] = "America/Los_Angeles"
    env["PATH"] = f"{home / 'framework' / 'bin'}:{env.get('PATH', '')}"
    return env


def validate_prerequisites(defects4j_home: str | Path) -> dict:
    """Validate local Defects4J prerequisites and return environment metadata."""
    home = Path(defects4j_home).expanduser().resolve()
    d4j = _defects4j_bin(home)
    if not d4j.exists():
        raise FileNotFoundError(f"Defects4J executable not found: {d4j}")
    java = shutil.which("java")
    if java is None:
        raise RuntimeError("Java is required for Defects4J; install Java 11 and ensure java is on PATH")
    java_version = subprocess.run([java, "-version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    version_text = (java_version.stderr or java_version.stdout).strip()
    if "11" not in version_text.splitlines()[0]:
        raise RuntimeError(f"Defects4J 3.x expects Java 11; detected: {version_text.splitlines()[0] if version_text else 'unknown'}")
    return {"defects4j_home": str(home), "defects4j_bin": str(d4j), "java": java, "java_version": version_text}


def _export_property(d4j: Path, workdir: Path, prop: str, env: dict[str, str]) -> list[str]:
    result = _run([str(d4j), "export", "-w", str(workdir), "-p", prop], env=env)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _java_source_for_class(workdir: Path, test_src_dir: str | None, class_name: str) -> Path | None:
    if not test_src_dir:
        return None
    candidate = workdir / test_src_dir / Path(*class_name.split(".")).with_suffix(".java")
    return candidate if candidate.exists() else None


def _extract_test_methods(java_file: Path) -> list[str]:
    """Extract likely JUnit test methods from a Java test source file."""
    text = java_file.read_text(errors="ignore")
    methods: list[str] = []
    # JUnit 4/5 style: @Test ... public void methodName(...)
    for match in re.finditer(r"@Test(?:\s*\([^)]*\))?\s+(?:public\s+)?(?:void|[A-Za-z0-9_<>, ?]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text, re.MULTILINE):
        methods.append(match.group(1))
    # JUnit 3 style: public void testSomething(...)
    for match in re.finditer(r"public\s+void\s+(test[A-Za-z0-9_]*)\s*\(", text):
        if match.group(1) not in methods:
            methods.append(match.group(1))
    return methods


def _expand_class_level_tests(tests: list[str], workdir: Path, test_src_dir: str | None) -> tuple[list[str], dict[str, list[str]]]:
    """Expand class-level Defects4J exports into method-level coverage targets."""
    expanded: list[str] = []
    mapping: dict[str, list[str]] = {}
    for test_id in tests:
        if "::" in test_id:
            expanded.append(test_id)
            mapping[test_id] = [test_id]
            continue
        java_file = _java_source_for_class(workdir, test_src_dir, test_id)
        methods = _extract_test_methods(java_file) if java_file else []
        method_ids = [f"{test_id}::{m}" for m in methods]
        if method_ids:
            expanded.extend(method_ids)
            mapping[test_id] = method_ids
        else:
            expanded.append(test_id)
            mapping[test_id] = [test_id]
    return expanded, mapping


def collect_defects4j_matrix(config: Defects4JConfig) -> Defects4JResult:
    """Harvest a labeled test × covered-line matrix for one Defects4J bug version.

    This function runs Defects4J commands and can be slow. It is resumable: cached
    ``raw/coverage/*.xml`` files are reused unless ``force_coverage`` is true.
    """
    metadata = validate_prerequisites(config.defects4j_home)
    home = Path(config.defects4j_home).expanduser().resolve()
    d4j = _defects4j_bin(home)
    env = _base_env(home)
    version_id = f"{config.bug_id}{config.version}"
    workdir = config.work_root / f"{config.project}_{version_id}"
    outdir = config.output_dir / config.project / version_id
    raw_dir = outdir / "raw" / "coverage"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not (config.reuse_workdir and (workdir / ".defects4j.config").exists()):
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.parent.mkdir(parents=True, exist_ok=True)
        _run([str(d4j), "checkout", "-p", config.project, "-v", version_id, "-w", str(workdir)], env=env, timeout=1800)
    _run([str(d4j), "compile", "-w", str(workdir)], env=env, timeout=1800)

    exported = {}
    for prop in ["tests.all", "tests.relevant", "tests.trigger", "classes.modified", "dir.src.tests"]:
        try:
            exported[prop] = _export_property(d4j, workdir, prop, env)
        except subprocess.CalledProcessError as exc:
            exported[prop] = []
            exported[f"{prop}.error"] = exc.stderr

    original_tests = list(exported.get(config.test_property, []))
    class_expansion: dict[str, list[str]] = {}
    if config.expand_class_tests:
        tests, class_expansion = _expand_class_level_tests(original_tests, workdir, (exported.get("dir.src.tests") or [None])[0])
    else:
        tests = original_tests
    if config.test_filter:
        pattern = re.compile(config.test_filter)
        tests = [test for test in tests if pattern.search(test)]
    if config.limit_tests is not None:
        tests = tests[: config.limit_tests]

    coverages: dict[str, set[str]] = {}
    failures: list[dict] = []
    for test_id in tests:
        xml_cache = raw_dir / f"{safe_filename(test_id)}.xml"
        if not xml_cache.exists() or config.force_coverage:
            try:
                _run([str(d4j), "coverage", "-w", str(workdir), "-t", test_id], env=env, timeout=1800)
                shutil.copy2(workdir / "coverage.xml", xml_cache)
            except Exception as exc:  # record and continue; some trigger tests fail by design
                failures.append({"test_id": test_id, "error": str(exc)})
                continue
        coverages[test_id] = parse_cobertura_xml(xml_cache)

    matrix_csv = outdir / "matrix.csv"
    requirements = write_labeled_matrix(coverages, matrix_csv)
    tests_txt = outdir / "tests.txt"
    requirements_txt = outdir / "requirements.txt"
    metadata_json = outdir / "metadata.json"
    tests_txt.write_text("\n".join(coverages.keys()) + ("\n" if coverages else ""))
    requirements_txt.write_text("\n".join(requirements) + ("\n" if requirements else ""))
    payload = {
        "source": "defects4j",
        "project": config.project,
        "bug_id": config.bug_id,
        "version": version_id,
        "test_property": config.test_property,
        "requirement_scope": config.requirement_scope,
        "timezone": "America/Los_Angeles",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workdir": str(workdir),
        "output_dir": str(outdir),
        "total_tests": len(coverages),
        "total_requirements": len(requirements),
        "original_tests_count": len(original_tests),
        "expanded_tests_count": len(tests),
        "test_filter": config.test_filter,
        "class_expansion": class_expansion,
        "failures": failures,
        "exports": exported,
        "environment": metadata,
    }
    metadata_json.write_text(json.dumps(payload, indent=2))
    return Defects4JResult(matrix_csv, tests_txt, requirements_txt, metadata_json, len(coverages), len(requirements), failures)
