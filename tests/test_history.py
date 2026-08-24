from pathlib import Path

from algogauge import history
from algogauge.gbench import BenchStat

MACHINE = {"cpu_model": "x", "cores": 4, "trade_ngin_sha": "abc", "algogauge_sha": "def"}


def stat(name="A/1", cv=1.0):
    return BenchStat(
        name=name,
        family=name.split("/")[0],
        param="1" if "/" in name else None,
        unit="ns",
        samples=20,
        median=100.0,
        p95=110.0,
        p99=115.0,
        mean=101.0,
        stddev=1.0,
        cv_pct=cv,
        iterations=10,
        counters={"k": 2.0},
    )


def test_from_stats_marks_validity():
    recs = history.from_stats(
        "r1", "s", [stat(cv=1.0), stat("B", cv=20.0)], MACHINE, "2026-08-21T00:00:00Z", True
    )
    assert [r.valid for r in recs] == [True, False]
    assert recs[1].invalid_reason == "cv_pct > 15"
    assert recs[0].trade_ngin_sha == "abc" and recs[0].suite == "s" and recs[0].run_id == "r1"


def test_from_stats_with_peak_rss_kb():
    recs = history.from_stats(
        "r1", "s", [stat()], MACHINE, "2026-08-21T00:00:00Z", True, peak_rss_kb=87772
    )
    assert len(recs) == 1
    assert recs[0].peak_rss_kb == 87772


def test_from_stats_without_peak_rss_kb():
    recs = history.from_stats(
        "r1", "s", [stat()], MACHINE, "2026-08-21T00:00:00Z", True
    )
    assert len(recs) == 1
    assert recs[0].peak_rss_kb is None


def test_from_stats_peak_rss_same_for_all_records():
    """Verify peak_rss_kb is stamped onto all records in a run."""
    recs = history.from_stats(
        "r1", "s", [stat(), stat("B"), stat("C")], MACHINE, "2026-08-21T00:00:00Z", True, peak_rss_kb=65536
    )
    assert len(recs) == 3
    assert all(r.peak_rss_kb == 65536 for r in recs)


def test_round_trip_json():
    r = history.from_stats("r1", "s", [stat()], MACHINE, "t", False)[0]
    assert history.Record.from_json(r.to_json()) == r


def test_round_trip_json_with_peak_rss_kb():
    r = history.from_stats("r1", "s", [stat()], MACHINE, "t", False, peak_rss_kb=87772)[0]
    assert history.Record.from_json(r.to_json()) == r


def test_round_trip_json_old_format_without_peak_rss_kb():
    """Test that old JSON records without peak_rss_kb field still parse correctly."""
    r = history.from_stats("r1", "s", [stat()], MACHINE, "t", False)[0]
    json_str = r.to_json()
    # Remove peak_rss_kb from JSON to simulate old format
    import json
    data = json.loads(json_str)
    del data["peak_rss_kb"]
    old_format_json = json.dumps(data)
    
    # Should still parse correctly with peak_rss_kb defaulting to None
    loaded = history.Record.from_json(old_format_json)
    assert loaded.peak_rss_kb is None


def test_append_and_load(tmp_path: Path):
    recs = history.from_stats("r1", "s", [stat(), stat("B")], MACHINE, "2026-01-01T00:00:00Z", True)
    p = history.append(tmp_path, recs)
    assert p == tmp_path / "s.jsonl" and p.read_text().count("\n") == 2
    history.append(
        tmp_path, history.from_stats("r2", "s", [stat()], MACHINE, "2026-01-02T00:00:00Z", True)
    )
    loaded = history.load(tmp_path, "s")
    assert [r.run_id for r in loaded] == ["r1", "r1", "r2"]
    assert history.load(tmp_path, "missing") == []
    assert set(history.load_all(tmp_path)) == {"s"}


def test_append_and_load_with_peak_rss_kb(tmp_path: Path):
    """Test append and load with peak_rss_kb field."""
    recs = history.from_stats(
        "r1", "s", [stat(), stat("B")], MACHINE, "2026-01-01T00:00:00Z", True, peak_rss_kb=87772
    )
    p = history.append(tmp_path, recs)
    assert p == tmp_path / "s.jsonl" and p.read_text().count("\n") == 2
    loaded = history.load(tmp_path, "s")
    assert [r.peak_rss_kb for r in loaded] == [87772, 87772]


def test_latest_run_prefers_valid():
    recs = history.from_stats(
        "r1", "s", [stat()], MACHINE, "2026-01-01T00:00:00Z", True
    ) + history.from_stats("r2", "s", [stat(cv=50)], MACHINE, "2026-01-02T00:00:00Z", True)
    assert history.latest_run(recs) == "r1"
    assert history.latest_run(recs, valid_only=False) == "r2"
    assert history.latest_run([]) is None
