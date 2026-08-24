import json
import shutil
from datetime import datetime
from pathlib import Path

from algogauge import runner
from algogauge.manifest import Defaults, Suite

FIX = Path(__file__).parent / "fixtures" / "gbench_sample.json"

# Real sample of /usr/bin/time -v stderr output
TIME_V_STDERR = """\tCommand being timed: "python3 -c x=[i*i for i in range(2000000)]"
\tUser time (seconds): 0.04
\tSystem time (seconds): 0.00
\tPercent of CPU this job got: 98%
\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.05
\tAverage shared text size (kbytes): 0
\tAverage unshared data size (kbytes): 0
\tAverage stack size (kbytes): 0
\tAverage total size (kbytes): 0
\tMaximum resident set size (kbytes): 87772
\tAverage resident set size (kbytes): 0
\tMajor (requiring I/O) page faults: 0
\tMinor (reclaiming a frame) page faults: 20516
\tVoluntary context switches: 1
\tInvoluntary context switches: 5
\tSwaps: 0
\tFile system inputs: 0
\tFile system outputs: 0
\tSocket messages sent: 0
\tSocket messages received: 0
\tSignals delivered: 0
\tPage size (bytes): 4096
\tExit status: 0"""


def suite(kind="gbench", perf=True):
    return Suite(
        name="demo",
        kind=kind,
        binary="build/demo" if kind == "gbench" else None,
        script="python/demo.py" if kind == "script" else None,
        args=("--n", "2"),
        repetitions=3,
        min_time="1s",
        perf=perf,
    )


def test_new_run_id_format():
    assert runner.new_run_id(datetime(2026, 8, 21, 13, 5, 9)) == "20260821_130509"


def test_gbench_command_uses_display_aggregates_only():
    cmd = runner.gbench_command(Path("build/demo"), suite(), Path("out/benchmark.json"))
    assert cmd[0] == str(Path("build/demo"))
    assert "--benchmark_display_aggregates_only=true" in cmd
    assert "--benchmark_report_aggregates_only=true" not in cmd
    assert "--benchmark_repetitions=3" in cmd and "--benchmark_min_time=1s" in cmd


def fake_executor(calls):
    """Records commands; fakes the benchmark binary by copying the fixture JSON to --benchmark_out."""

    def run(cmd, **kw):
        calls.append(list(cmd))
        for a in cmd:
            if isinstance(a, str) and a.startswith("--benchmark_out="):
                shutil.copy(FIX, a.split("=", 1)[1])
            if isinstance(a, str) and a == "--out":
                shutil.copy(FIX, cmd[cmd.index(a) + 1])

        class R:
            returncode = 0
            stdout = ""
            stderr = TIME_V_STDERR

        return R()

    return run


def test_run_suite_gbench_skip_perf_writes_results_and_history(tmp_path):
    calls = []
    res = runner.run_suite(
        suite(),
        Defaults(),
        tmp_path,
        skip_perf=True,
        results_dir=tmp_path / "results",
        history_dir=tmp_path / "history",
        run_id="r1",
        executor=fake_executor(calls),
    )
    assert res.run_id == "r1" and res.perf_ran is False
    assert (res.result_dir / "benchmark.json").exists()
    assert res.result_dir == tmp_path / "results" / "demo" / "r1"
    assert len(calls) == 2  # gbench run + time -v for peak RSS
    assert not any("perf" in c[0] for c in calls)
    lines = (tmp_path / "history" / "demo.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["suite"] == "demo"
    assert {r.benchmark for r in res.records} == {"OnDataScaling/256", "PauseStrategy"}
    # Verify peak_rss_kb was captured and written
    assert (res.result_dir / "peak_rss_kb.txt").read_text() == "87772"
    assert json.loads(lines[0])["peak_rss_kb"] == 87772


def test_run_suite_runs_perf_stages_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "check_perf_permissions", lambda: None)
    calls = []
    res = runner.run_suite(
        suite(),
        Defaults(),
        tmp_path,
        results_dir=tmp_path / "r",
        history_dir=tmp_path / "h",
        run_id="r1",
        executor=fake_executor(calls),
    )
    assert res.perf_ran is True
    heads = [c[0] for c in calls]
    # First call: gbench, next 4: perf record, perf script, stackcollapse, flamegraph, then time -v for peak RSS
    assert (
        heads[1:3] == ["perf", "perf"]
        and heads[3].endswith("stackcollapse-perf.pl")
        and heads[4].endswith("flamegraph.pl")
        and "/usr/bin/time" in heads[5]
    )


def test_run_suite_skips_perf_when_permissions_fail(tmp_path, monkeypatch, capsys):
    def boom():
        raise RuntimeError("perf_event_paranoid must be 0")

    monkeypatch.setattr(runner, "check_perf_permissions", boom)
    calls = []
    res = runner.run_suite(
        suite(),
        Defaults(),
        tmp_path,
        results_dir=tmp_path / "r",
        history_dir=tmp_path / "h",
        run_id="r1",
        executor=fake_executor(calls),
    )
    assert res.perf_ran is False and len(calls) == 2  # gbench + time -v
    assert "skipping perf" in capsys.readouterr().out


def test_run_suite_script_kind(tmp_path):
    calls = []
    res = runner.run_suite(
        suite(kind="script", perf=False),
        Defaults(),
        tmp_path,
        results_dir=tmp_path / "r",
        history_dir=tmp_path / "h",
        run_id="r1",
        executor=fake_executor(calls),
    )
    cmd = calls[0]
    assert cmd[1].endswith("demo.py") and cmd[2:4] == ["--n", "2"] and "--out" in cmd
    assert len(res.records) == 2
    # Script suites don't capture peak RSS, so peak_rss_kb should be None
    assert json.loads((tmp_path / "h" / "demo.jsonl").read_text().splitlines()[0])["peak_rss_kb"] is None
