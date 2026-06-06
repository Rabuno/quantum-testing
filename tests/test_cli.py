import json
from quantum_testing.cli import main


def test_cli_benchmark_smoke(capsys):
    main(["benchmark", "--tests", "8", "--requirements", "5", "--seed", "4"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "results" in data
    assert "qiea" in data["results"]
