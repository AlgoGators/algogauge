from algogauge import history
from algogauge.dashboard import data as dd
from algogauge.gbench import BenchStat

M1 = {"cpu_model": "cpu1", "cores": 4, "trade_ngin_sha": "aaa", "algogauge_sha": "bbb"}
M2 = {"cpu_model": "cpu1", "cores": 4, "trade_ngin_sha": "ccc", "algogauge_sha": "bbb"}


def stat(name, median, cv=0.0, counters=None):
    return BenchStat(
        name=name,
        family=name.split("/")[0],
        param=(name.split("/")[1] if "/" in name else None),
        unit="ns",
        samples=5,
        median=median,
        p95=median + 1,
        p99=median + 2,
        mean=median,
        stddev=0.0,
        cv_pct=cv,
        iterations=1,
        counters=counters or {},
    )


def recs(run_id, ts, suite, stats, machine=M1, cv=0.0):
    return history.from_stats(run_id, suite, stats, machine, ts, False)


def test_runs_for_suite_groups_and_sorts():
    records = recs("r1", "2026-01-01T00:00:00Z", "s", [stat("A", 1), stat("B", 2)])
    records += recs("r2", "2026-01-02T00:00:00Z", "s", [stat("A", 1)])
    rows = dd.runs_for_suite(records)
    assert [r["run_id"] for r in rows] == ["r1", "r2"]
    assert rows[0]["n_benchmarks"] == 2 and rows[0]["valid"] is True


def test_latest_and_previous_run_records():
    records = recs("r1", "2026-01-01T00:00:00Z", "s", [stat("A", 1)])
    records += recs("r2", "2026-01-02T00:00:00Z", "s", [stat("A", 2)])
    assert [r.run_id for r in dd.latest_run_records(records)] == ["r2"]
    assert [r.run_id for r in dd.previous_run_records(records, "r2")] == ["r1"]
    assert dd.previous_run_records(records, "r1") == []
    assert dd.previous_run_records(records, "nope") == []


def test_group_by_family_sorts_by_numeric_param():
    records = recs(
        "r1", "t", "s", [stat("F/32", 1), stat("F/8", 1), stat("F/128", 1), stat("Other", 1)]
    )
    groups = dd.group_by_family(records)
    assert [r.param for r in groups["F"]] == ["8", "32", "128"]
    assert groups["Other"][0].param is None


def test_headline_metric_computes_delta():
    records = recs("r1", "2026-01-01T00:00:00Z", "s", [stat("A", 100.0)])
    records += recs("r2", "2026-01-02T00:00:00Z", "s", [stat("A", 120.0)])
    m = dd.headline_metric(dd.benchmark_records(records, "A"))
    assert m["value"] == 120.0 and m["delta_pct"] == 20.0 and m["run_id"] == "r2"


def test_headline_metric_none_when_no_data():
    assert dd.headline_metric([]) is None


def test_headline_metric_custom_extractor_for_counters():
    records = recs("r1", "t", "s", [stat("BacktestSpeedup/8", 1.0, counters={"speedup": 3.2})])
    m = dd.headline_metric(
        dd.benchmark_records(records, "BacktestSpeedup/8"),
        extractor=lambda r: r.counters["speedup"],
    )
    assert m["value"] == 3.2
