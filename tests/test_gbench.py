from pathlib import Path

import pytest

from algogauge import gbench

FIX = Path(__file__).parent / "fixtures" / "gbench_sample.json"


def test_percentile_nearest_rank():
    v = [10.0, 20.0, 30.0, 40.0]
    assert gbench.percentile(v, 50) == 20.0
    assert gbench.percentile(v, 95) == 40.0
    assert gbench.percentile(v, 0) == 10.0
    assert gbench.percentile([7.0], 99) == 7.0


def test_percentile_empty_raises():
    with pytest.raises(ValueError):
        gbench.percentile([], 50)


def test_parse_groups_repetitions_and_ignores_aggregates():
    stats = {s.name: s for s in gbench.parse(FIX)}
    assert set(stats) == {"OnDataScaling/256", "PauseStrategy"}
    s = stats["OnDataScaling/256"]
    assert (s.family, s.param, s.unit, s.samples, s.iterations) == (
        "OnDataScaling",
        "256",
        "ns",
        3,
        1000,
    )
    assert s.median == 110.0 and s.p95 == 120.0 and s.p99 == 120.0
    assert s.mean == pytest.approx(110.0)
    assert s.stddev == pytest.approx(10.0)  # sample stddev of 100,120,110
    assert s.cv_pct == pytest.approx(100 * 10.0 / 110.0)
    assert s.counters == {"bars": 256.0}
    p = stats["PauseStrategy"]
    assert p.param is None and p.stddev == 0.0 and p.cv_pct == 0.0 and p.counters == {}
