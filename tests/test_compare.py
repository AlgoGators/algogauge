from algogauge import compare, history
from algogauge.gbench import BenchStat

M = {"trade_ngin_sha": "a", "algogauge_sha": "b"}


def rec(run, name, median, ts):
    s = BenchStat(
        name=name,
        family=name,
        param=None,
        unit="ns",
        samples=5,
        median=median,
        p95=median,
        p99=median,
        mean=median,
        stddev=0.0,
        cv_pct=0.0,
        iterations=1,
        counters={},
    )
    return history.from_stats(run, "s", [s], M, ts, False)[0]


def test_compare_flags_regressions_only_above_threshold():
    base = [
        rec("r1", "A", 100.0, "t1"),
        rec("r1", "B", 100.0, "t1"),
        rec("r1", "OnlyBase", 1.0, "t1"),
    ]
    cur = [
        rec("r2", "A", 115.0, "t2"),
        rec("r2", "B", 105.0, "t2"),
        rec("r2", "OnlyCur", 1.0, "t2"),
    ]
    d = compare.compare(base, cur, threshold_pct=10.0)
    assert [x.benchmark for x in d] == ["A", "B"]
    assert d[0].delta_pct == 15.0 and d[0].regressed is True
    assert d[1].delta_pct == 5.0 and d[1].regressed is False
    assert compare.has_regression(d) is True
    assert compare.has_regression(d[1:]) is False


def test_select_run_latest_and_explicit():
    recs = [rec("r1", "A", 1, "t1"), rec("r2", "A", 2, "t2")]
    assert [r.run_id for r in compare.select_run(recs, "latest")] == ["r2"]
    assert [r.median for r in compare.select_run(recs, "r1")] == [1]
    assert compare.select_run(recs, "nope") == []


def test_render_table_is_ascii_and_marks_regressions():
    d = compare.compare([rec("r1", "A", 100.0, "t1")], [rec("r2", "A", 130.0, "t2")], 10.0)
    out = compare.render_table(d, 10.0)
    assert out.isascii() and "A" in out and "+30.0%" in out and "[REGRESSION]" in out
