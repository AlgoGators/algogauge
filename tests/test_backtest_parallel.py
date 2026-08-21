import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python" / "algogauge"))
import backtest_parallel as bp  # noqa: E402


def test_default_binary_path():
    assert bp.default_binary(Path("/repo")) == Path("/repo/build/benchmarks/bt_bench_runner")


def test_verify_checksums_passes_when_matching():
    serial = [{"seed": 1, "checksum": "a"}, {"seed": 2, "checksum": "b"}]
    parallel = [{"seed": 2, "checksum": "b"}, {"seed": 1, "checksum": "a"}]
    bp.verify_checksums(serial, parallel)  # must not raise


def test_verify_checksums_raises_on_mismatch():
    serial = [{"seed": 1, "checksum": "a"}]
    parallel = [{"seed": 1, "checksum": "different"}]
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        bp.verify_checksums(serial, parallel)


def test_verify_checksums_raises_on_unknown_seed():
    with pytest.raises(RuntimeError, match="unknown seed"):
        bp.verify_checksums([{"seed": 1, "checksum": "a"}], [{"seed": 99, "checksum": "a"}])


def test_build_gbench_json_shape():
    worker_results = [
        {"workers": 1, "elapsed_seconds": 10.0, "speedup": 1.0, "efficiency": 1.0, "jobs": 8},
        {"workers": 4, "elapsed_seconds": 3.0, "speedup": 3.33, "efficiency": 0.83, "jobs": 8},
    ]
    doc = bp.build_gbench_json(worker_results)
    assert "benchmarks" in doc and len(doc["benchmarks"]) == 2
    b0 = doc["benchmarks"][0]
    assert b0["name"] == "BacktestSpeedup/1" and b0["run_name"] == "BacktestSpeedup/1"
    assert b0["run_type"] == "iteration" and b0["time_unit"] == "s"
    assert b0["real_time"] == 10.0 and b0["speedup"] == 1.0 and b0["jobs"] == 8
    json.dumps(doc)  # must be JSON-serializable


def test_run_job_parses_last_json_line(monkeypatch):
    class FakeProc:
        stdout = 'some warning line\n{"wall_seconds": 1.5, "seed": 7, "checksum": "x"}\n'

    def fake_run(cmd, **kwargs):
        assert cmd == ["binpath", "--symbols", "10", "--years", "5", "--seed", "7"]
        return FakeProc()

    monkeypatch.setattr(bp.subprocess, "run", fake_run)
    result = bp.run_job("binpath", 10, 5, 7)
    assert result == {"wall_seconds": 1.5, "seed": 7, "checksum": "x"}
