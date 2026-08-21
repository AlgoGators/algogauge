"""Headless tests: build every dashboard page from sample history/ fixtures
and confirm each constructs without raising. No server is started."""

from pathlib import Path

import pytest

dash = pytest.importorskip("dash")

from algogauge import history  # noqa: E402
from algogauge.dashboard import app as dashboard_app  # noqa: E402
from algogauge.gbench import BenchStat  # noqa: E402

M = {"cpu_model": "cpu1", "cores": 8, "trade_ngin_sha": "abc123", "algogauge_sha": "def456"}


def stat(name, median, cv=0.0, counters=None):
    return BenchStat(
        name=name,
        family=name.split("/")[0],
        param=(name.split("/")[1] if "/" in name else None),
        unit="us",
        samples=20,
        median=median,
        p95=median * 1.1,
        p99=median * 1.2,
        mean=median,
        stddev=median * 0.05,
        cv_pct=cv,
        iterations=10,
        counters=counters or {},
    )


@pytest.fixture
def populated_history_dir(tmp_path: Path) -> Path:
    h = tmp_path / "history"
    history.append(
        h,
        history.from_stats(
            "r1",
            "tick_to_trade",
            [stat("ProcessTick/1", 10.0), stat("ProcessTick/8", 15.0)],
            M,
            "2026-01-01T00:00:00Z",
            False,
        ),
    )
    history.append(
        h,
        history.from_stats(
            "r2",
            "tick_to_trade",
            [stat("ProcessTick/1", 11.0), stat("ProcessTick/8", 16.0)],
            M,
            "2026-01-02T00:00:00Z",
            False,
        ),
    )
    history.append(
        h,
        history.from_stats(
            "r1",
            "ingestion_throughput",
            [stat("ArrowToBars/100000", 500.0)],
            M,
            "2026-01-01T00:00:00Z",
            False,
        ),
    )
    history.append(
        h,
        history.from_stats(
            "r1",
            "backtest_speedup",
            [stat("BacktestSpeedup/8", 3.0, counters={"speedup": 3.2, "efficiency": 0.4})],
            M,
            "2026-01-01T00:00:00Z",
            False,
        ),
    )
    history.append(
        h,
        history.from_stats(
            "r_invalid",
            "flaky_suite",
            [stat("Flaky/1", 999.0, cv=99.0)],
            M,
            "2026-01-01T00:00:00Z",
            False,
        ),
    )
    return h


def test_build_overview_layout(populated_history_dir):
    from algogauge.dashboard import data as dd

    all_history = dd.load_history(populated_history_dir)
    layout = dashboard_app.build_overview_layout(all_history)
    assert isinstance(layout, dash.html.Div)


def test_build_suite_layout_with_and_without_data(populated_history_dir):
    from algogauge.dashboard import data as dd

    all_history = dd.load_history(populated_history_dir)
    layout = dashboard_app.build_suite_layout("tick_to_trade", all_history["tick_to_trade"])
    assert isinstance(layout, dash.html.Div)
    empty_layout = dashboard_app.build_suite_layout("nonexistent_suite", [])
    assert isinstance(empty_layout, dash.html.Div)


def test_build_trends_layout(populated_history_dir):
    from algogauge.dashboard import data as dd

    all_history = dd.load_history(populated_history_dir)
    layout = dashboard_app.build_trends_layout(all_history)
    assert isinstance(layout, dash.html.Div)


def test_build_trends_layout_empty():
    layout = dashboard_app.build_trends_layout({})
    assert isinstance(layout, dash.html.Div)


def test_build_compare_layout(populated_history_dir):
    from algogauge.dashboard import data as dd

    all_history = dd.load_history(populated_history_dir)
    layout = dashboard_app.build_compare_layout(all_history)
    assert isinstance(layout, dash.html.Div)


def test_build_runs_layout(populated_history_dir):
    from algogauge.dashboard import data as dd

    all_history = dd.load_history(populated_history_dir)
    layout = dashboard_app.build_runs_layout(all_history)
    assert isinstance(layout, dash.html.Div)


def test_build_app_assembles_all_tabs_without_error(populated_history_dir, tmp_path):
    app = dashboard_app.build_app(populated_history_dir, tmp_path / "results")
    assert app.layout is not None
    tabs = app.layout.children[1]
    tab_values = [t.value for t in tabs.children]
    assert tab_values == ["overview", "suites", "trends", "compare", "runs"]


def test_build_app_with_no_history_at_all(tmp_path):
    app = dashboard_app.build_app(tmp_path / "history", tmp_path / "results")
    assert app.layout is not None
