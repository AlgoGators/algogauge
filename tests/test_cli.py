from pathlib import Path

from algogauge import cli, history
from algogauge.gbench import BenchStat

M = {"trade_ngin_sha": "a", "algogauge_sha": "b"}
ROOT = Path(__file__).resolve().parents[1]


def rec(run, name, median, ts, cv=0.0):
    s = BenchStat(
        name=name,
        family=name,
        param=None,
        unit="ns",
        samples=5,
        median=median,
        p95=median + 1,
        p99=median + 2,
        mean=median,
        stddev=0.0,
        cv_pct=cv,
        iterations=1,
        counters={},
    )
    return history.from_stats(run, "s", [s], M, ts, False)[0]


def test_list_prints_suites(capsys):
    assert cli.main(["list", "--manifest", str(ROOT / "algogauge.toml")]) == 0
    out = capsys.readouterr().out
    assert "base_strategy" in out and "trend_following" in out and "gbench" in out


def test_summary_markdown():
    md = cli.summary_markdown([rec("r1", "A", 100.0, "t", cv=20.0)])
    assert md.splitlines()[0].startswith("| benchmark") and "| A |" in md and "no" in md


def test_compare_defaults_and_exit_code(tmp_path, capsys):
    history.append(tmp_path, [rec("r1", "A", 100.0, "2026-01-01T00:00:00Z")])
    history.append(tmp_path, [rec("r2", "A", 150.0, "2026-01-02T00:00:00Z")])
    rc = cli.main(["compare", "s", "--history-dir", str(tmp_path)])
    assert rc == 1 and "[REGRESSION]" in capsys.readouterr().out
    rc = cli.main(["compare", "s", "--history-dir", str(tmp_path), "--threshold", "60"])
    assert rc == 0


def test_compare_needs_two_runs(tmp_path, capsys):
    history.append(tmp_path, [rec("r1", "A", 100.0, "2026-01-01T00:00:00Z")])
    assert cli.main(["compare", "s", "--history-dir", str(tmp_path)]) == 2
    assert "need at least two" in capsys.readouterr().out


def test_run_unknown_suite_returns_1(capsys):
    assert cli.main(["run", "nope", "--manifest", str(ROOT / "algogauge.toml")]) == 1
    assert "unknown suite" in capsys.readouterr().out
