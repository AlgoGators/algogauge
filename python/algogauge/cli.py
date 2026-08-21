"""Command-line interface: algogauge list | run | compare."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import compare as cmp
from . import history, manifest, runner
from .history import Record


def _root(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent


def summary_markdown(records: list[Record]) -> str:
    lines = ["| benchmark | median | p95 | unit | valid |", "|---|---:|---:|---|---|"]
    for r in sorted(records, key=lambda r: r.benchmark):
        lines.append(
            f"| {r.benchmark} | {r.median:.1f} | {r.p95:.1f} | {r.unit} | {'yes' if r.valid else 'no'} |"
        )
    return "\n".join(lines)


def _cmd_list(a) -> int:
    m = manifest.load(a.manifest)
    for s in m.suites:
        print(
            f"{s.name:<28} {s.kind:<7} {s.binary or s.script:<48} perf={'on' if s.perf else 'off'}"
        )
    return 0


def _cmd_run(a) -> int:
    m = manifest.load(a.manifest)
    root = _root(a.manifest)
    names = a.suites or [s.name for s in m.suites]
    failed = 0
    for n in names:
        try:
            s = m.get(n)
            res = runner.run_suite(s, m.defaults, root, skip_perf=a.skip_perf)
            print(f"\n### {s.name}  (run {res.run_id})\n{summary_markdown(res.records)}\n")
        except Exception as e:  # noqa: BLE001 - report and continue with the next suite
            failed += 1
            print(f"ERROR running suite '{n}': {e}")
    return 1 if failed else 0


def _cmd_dashboard(a) -> int:
    from .dashboard.app import (
        build_app,
    )  # imported lazily: dash is an optional-ish, heavier dependency

    app = build_app(a.history_dir, a.results_dir)
    app.run(debug=a.debug, host=a.host, port=a.port)
    return 0


def _cmd_compare(a) -> int:
    recs = history.load(a.history_dir, a.suite)
    runs = sorted({(r.ts, r.run_id) for r in recs if r.valid})
    if len(runs) < 2 and (a.baseline == "auto" or a.current == "latest"):
        print(f"need at least two valid runs of '{a.suite}' in {a.history_dir} (have {len(runs)})")
        return 2
    current_id = runs[-1][1] if a.current == "latest" else a.current
    baseline_id = (
        next((rid for ts, rid in reversed(runs) if rid != current_id), None)
        if a.baseline == "auto"
        else a.baseline
    )
    base = cmp.select_run(recs, baseline_id)
    cur = cmp.select_run(recs, current_id)
    deltas = cmp.compare(base, cur, a.threshold)
    print(f"baseline={baseline_id}  current={current_id}")
    print(cmp.render_table(deltas, a.threshold))
    return 1 if cmp.has_regression(deltas) else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="algogauge")
    sub = p.add_subparsers(dest="cmd", required=True)
    default_manifest = Path.cwd() / "algogauge.toml"

    l = sub.add_parser("list", help="list suites in the manifest")
    l.add_argument("--manifest", type=Path, default=default_manifest)
    l.set_defaults(fn=_cmd_list)

    r = sub.add_parser("run", help="run one or more suites")
    r.add_argument("suites", nargs="*")
    r.add_argument("--manifest", type=Path, default=default_manifest)
    r.add_argument("--skip-perf", action="store_true")
    r.set_defaults(fn=_cmd_run)

    c = sub.add_parser("compare", help="compare two runs of a suite")
    c.add_argument("suite")
    c.add_argument("--history-dir", type=Path, default=Path.cwd() / "history")
    c.add_argument(
        "--baseline", default="auto", help="run id; default: latest valid run before --current"
    )
    c.add_argument("--current", default="latest")
    c.add_argument("--threshold", type=float, default=10.0)
    c.set_defaults(fn=_cmd_compare)

    d = sub.add_parser("dashboard", help="launch the results dashboard")
    d.add_argument("--history-dir", type=Path, default=Path.cwd() / "history")
    d.add_argument("--results-dir", type=Path, default=Path.cwd() / "results")
    d.add_argument("--host", default="127.0.0.1")
    d.add_argument("--port", type=int, default=8050)
    d.add_argument("--debug", action="store_true")
    d.set_defaults(fn=_cmd_dashboard)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
