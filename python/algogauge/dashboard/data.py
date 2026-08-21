"""Data loading and shaping for the dashboard. Pure functions -- no Dash/Plotly
imports here, so this module is trivial to unit test without a running app.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from .. import history as history_mod
from ..history import Record


def load_history(history_dir: Path) -> dict[str, list[Record]]:
    """suite name -> all its records, across all runs."""
    return history_mod.load_all(history_dir)


def runs_for_suite(records: list[Record]) -> list[dict]:
    """One row per distinct run_id, sorted oldest to newest."""
    by_run: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        by_run[r.run_id].append(r)
    rows = []
    for run_id, recs in by_run.items():
        rows.append(
            {
                "run_id": run_id,
                "ts": recs[0].ts,
                "valid": all(r.valid for r in recs),
                "machine": recs[0].machine,
                "trade_ngin_sha": recs[0].trade_ngin_sha,
                "algogauge_sha": recs[0].algogauge_sha,
                "n_benchmarks": len(recs),
            }
        )
    return sorted(rows, key=lambda r: r["ts"])


def latest_run_records(records: list[Record], valid_only: bool = True) -> list[Record]:
    run_id = history_mod.latest_run(records, valid_only=valid_only)
    if run_id is None:
        return []
    return [r for r in records if r.run_id == run_id]


def previous_run_records(
    records: list[Record], before_run_id: str, valid_only: bool = True
) -> list[Record]:
    """Records of the latest valid run strictly before `before_run_id` (by timestamp)."""
    target_ts = next((r.ts for r in records if r.run_id == before_run_id), None)
    if target_ts is None:
        return []
    pool = [r for r in records if (r.valid or not valid_only) and r.ts < target_ts]
    if not pool:
        return []
    run_id = max(pool, key=lambda r: (r.ts, r.run_id)).run_id
    return [r for r in pool if r.run_id == run_id]


def _param_sort_key(param: str | None) -> float:
    try:
        return float(param)
    except (TypeError, ValueError):
        return float("inf")


def group_by_family(records: list[Record]) -> dict[str, list[Record]]:
    """Group records (already scoped to one run) by benchmark family, each
    group sorted by numeric param so scaling plots come out in order."""
    out: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        out[r.family].append(r)
    for fam in out:
        out[fam].sort(key=lambda r: _param_sort_key(r.param))
    return dict(out)


def headline_metric(
    records_for_benchmark: list[Record],
    extractor: Callable[[Record], float] = lambda r: r.median,
) -> dict | None:
    """Latest valid value for one (suite, benchmark) plus delta vs. the
    previous valid run. `records_for_benchmark` must already be filtered to
    a single benchmark name (e.g. "ProcessTick/8")."""
    latest = latest_run_records(records_for_benchmark)
    if not latest:
        return None
    latest_val = extractor(latest[0])
    prev = previous_run_records(records_for_benchmark, latest[0].run_id)
    prev_val = extractor(prev[0]) if prev else None
    delta_pct = ((latest_val - prev_val) / prev_val * 100.0) if prev_val else None
    return {
        "value": latest_val,
        "unit": latest[0].unit,
        "delta_pct": delta_pct,
        "run_id": latest[0].run_id,
        "ts": latest[0].ts,
    }


def benchmark_records(records: list[Record], benchmark: str) -> list[Record]:
    return [r for r in records if r.benchmark == benchmark]
