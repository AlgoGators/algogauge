"""Compare two runs and flag median regressions beyond a threshold."""

from __future__ import annotations

from dataclasses import dataclass

from .history import Record, latest_run


@dataclass(frozen=True)
class Delta:
    benchmark: str
    unit: str
    baseline_median: float
    current_median: float
    delta_pct: float
    regressed: bool


def select_run(records: list[Record], run_id: str) -> list[Record]:
    target = latest_run(records) if run_id == "latest" else run_id
    return [r for r in records if r.run_id == target]


def compare(baseline: list[Record], current: list[Record], threshold_pct: float) -> list[Delta]:
    base = {r.benchmark: r for r in baseline}
    out = []
    for name in sorted(set(base) & {r.benchmark for r in current}):
        b = base[name]
        c = next(r for r in current if r.benchmark == name)
        pct = ((c.median - b.median) / b.median * 100.0) if b.median else 0.0
        out.append(Delta(name, c.unit, b.median, c.median, round(pct, 2), pct > threshold_pct))
    return out


def has_regression(deltas: list[Delta]) -> bool:
    return any(d.regressed for d in deltas)


def render_table(deltas: list[Delta], threshold_pct: float) -> str:
    lines = [f"{'Benchmark':<40} {'Baseline':>14} {'Current':>14} {'Delta':>9}", "-" * 80]
    for d in deltas:
        tag = "  [REGRESSION]" if d.regressed else ""
        lines.append(
            f"{d.benchmark:<40} {d.baseline_median:>11.1f} {d.unit:<2} {d.current_median:>11.1f} {d.unit:<2} "
            f"{d.delta_pct:>+8.1f}%{tag}"
        )
    n = sum(d.regressed for d in deltas)
    lines.append("-" * 80)
    lines.append(
        f"[FAIL] {n} regression(s) beyond {threshold_pct:g}%"
        if n
        else f"[PASS] no regressions beyond {threshold_pct:g}%"
    )
    return "\n".join(lines)
