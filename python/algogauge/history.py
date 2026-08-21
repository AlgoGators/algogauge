"""Compact, committed run history: one JSONL file per suite, one line per benchmark per run."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .gbench import BenchStat

CV_INVALID_PCT = 15.0


@dataclass
class Record:
    run_id: str
    suite: str
    benchmark: str
    family: str
    param: str | None
    unit: str
    median: float
    p95: float
    p99: float
    mean: float
    stddev: float
    cv_pct: float
    samples: int
    iterations: int
    counters: dict[str, float]
    valid: bool
    invalid_reason: str | None
    machine: dict
    trade_ngin_sha: str
    algogauge_sha: str
    ts: str
    perf: bool = field(default=False)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, line: str) -> "Record":
        return cls(**json.loads(line))


def from_stats(
    run_id: str, suite: str, stats: list[BenchStat], machine: dict, ts: str, perf: bool
) -> list[Record]:
    out = []
    for s in stats:
        valid = s.cv_pct <= CV_INVALID_PCT
        out.append(
            Record(
                run_id=run_id,
                suite=suite,
                benchmark=s.name,
                family=s.family,
                param=s.param,
                unit=s.unit,
                median=s.median,
                p95=s.p95,
                p99=s.p99,
                mean=s.mean,
                stddev=s.stddev,
                cv_pct=s.cv_pct,
                samples=s.samples,
                iterations=s.iterations,
                counters=dict(s.counters),
                valid=valid,
                invalid_reason=None if valid else f"cv_pct > {CV_INVALID_PCT:g}",
                machine=dict(machine),
                trade_ngin_sha=str(machine.get("trade_ngin_sha", "unknown")),
                algogauge_sha=str(machine.get("algogauge_sha", "unknown")),
                ts=ts,
                perf=perf,
            )
        )
    return out


def history_path(history_dir: Path, suite: str) -> Path:
    return Path(history_dir) / f"{suite}.jsonl"


def append(history_dir: Path, records: list[Record]) -> Path:
    if not records:
        raise ValueError("no records to append")
    suites = {r.suite for r in records}
    if len(suites) != 1:
        raise ValueError(f"records span multiple suites: {sorted(suites)}")
    p = history_path(history_dir, records[0].suite)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_json() + "\n")
    return p


def load(history_dir: Path, suite: str) -> list[Record]:
    p = history_path(history_dir, suite)
    if not p.exists():
        return []
    return [Record.from_json(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_all(history_dir: Path) -> dict[str, list[Record]]:
    d = Path(history_dir)
    return {p.stem: load(d, p.stem) for p in sorted(d.glob("*.jsonl"))}


def latest_run(records: list[Record], valid_only: bool = True) -> str | None:
    pool = [r for r in records if r.valid] if valid_only else list(records)
    if not pool:
        return None
    return max(pool, key=lambda r: (r.ts, r.run_id)).run_id
