import csv
import json

from quantum_testing.datasets.defects4j import parse_cobertura_xml, safe_filename, write_labeled_matrix
from quantum_testing.problems.coverage import CoverageProblem


def test_parse_cobertura_xml_covered_lines(tmp_path):
    xml = tmp_path / "coverage.xml"
    xml.write_text("""<?xml version="1.0" ?>
<coverage>
  <packages>
    <package name="org.example">
      <classes>
        <class name="Foo" filename="org/example/Foo.java">
          <lines>
            <line number="10" hits="3"/>
            <line number="11" hits="0"/>
          </lines>
        </class>
        <class name="Bar" filename="org/example/Bar.java">
          <lines><line number="7" hits="1"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
""")
    assert parse_cobertura_xml(xml) == {"org/example/Foo.java:10", "org/example/Bar.java:7"}


def test_write_labeled_matrix_is_compatible_with_coverage_problem(tmp_path):
    matrix = tmp_path / "matrix.csv"
    reqs = write_labeled_matrix({
        "A::test_one": {"Foo.java:1", "Foo.java:2"},
        "B::test_two": {"Foo.java:2"},
    }, matrix)
    assert reqs == ["Foo.java:1", "Foo.java:2"]
    problem = CoverageProblem.load_csv(matrix)
    assert problem.n_tests == 2
    assert problem.n_requirements == 2
    assert problem.coverage_sets == [{0, 1}, {1}]


def test_safe_filename_removes_problematic_characters():
    assert safe_filename("org.example.Test::case[1]") == "org.example.Test_case_1"
