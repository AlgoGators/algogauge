"""Parse Google Benchmark JSON output into per-benchmark statistics."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_STANDARD_KEYS = {
    "name",
    "run_name",
    "run_type",
    "repetitions",
    "repetition_index",
    "threads",
    "iterations",
    "real_time",
    "cpu_time",
    "time_unit",
    "aggregate_name",
    "aggregate_unit",
    "family_index",
    "per_family_instance_index",
    "label",
    "error_occurred",
    "error_message",
}


@dataclass(frozen=True)
class BenchStat:
    name: str
    family: str
    param: str | None
    unit: str
    samples: int
    median: float
    p95: float
    p99: float
    mean: float
    stddev: float
    cv_pct: float
    iterations: int
    counters: dict[str, float] = field(default_factory=dict)


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile; q in [0, 100]."""
    if not values:
        raise ValueError("percentile of empty list")
    s = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(s)))
    return s[rank - 1]


def _split(name: str) -> tuple[str, str | None]:
    fam, sep, param = name.partition("/")
    return (fam, param if sep else None)


def parse(path: Path) -> list[BenchStat]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = defaultdict(list)
    for b in data.get("benchmarks", []):
        if b.get("run_type", "iteration") != "iteration" or b.get("error_occurred"):
            continue
        rows[b.get("run_name", b["name"])].append(b)

    out: list[BenchStat] = []
    for name, reps in rows.items():
        times = [float(r["real_time"]) for r in reps]
        mean = statistics.fmean(times)
        sd = statistics.stdev(times) if len(times) > 1 else 0.0
        fam, param = _split(name)
        last = reps[-1]
        counters = {
            k: float(v)
            for k, v in last.items()
            if k not in _STANDARD_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        out.append(
            BenchStat(
                name=name,
                family=fam,
                param=param,
                unit=last.get("time_unit", "ns"),
                samples=len(times),
                median=percentile(times, 50),
                p95=percentile(times, 95),
                p99=percentile(times, 99),
                mean=mean,
                stddev=sd,
                cv_pct=(100.0 * sd / mean) if mean else 0.0,
                iterations=int(last.get("iterations", 0)),
                counters=counters,
            )
        )
    return out
