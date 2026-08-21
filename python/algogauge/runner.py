"""Run one benchmark suite: Google Benchmark (or a script), optional perf + flamegraph, history append."""

from __future__ import annotations

import datetime as _dt
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import gbench, history, machine
from .history import Record
from .manifest import Defaults, Suite


@dataclass
class RunResult:
    suite: str
    run_id: str
    result_dir: Path
    records: list[Record]
    perf_ran: bool


def new_run_id(now: _dt.datetime | None = None) -> str:
    return (now or _dt.datetime.now()).strftime("%Y%m%d_%H%M%S")


def gbench_command(binary: Path, suite: Suite, out_json: Path) -> list[str]:
    return [
        str(binary),
        f"--benchmark_out={out_json}",
        "--benchmark_out_format=json",
        f"--benchmark_min_time={suite.min_time}",
        f"--benchmark_repetitions={suite.repetitions}",
        "--benchmark_display_aggregates_only=true",
    ]


def check_perf_permissions() -> None:
    for knob, want in (("perf_event_paranoid", "0"), ("kptr_restrict", "0")):
        try:
            val = Path(f"/proc/sys/kernel/{knob}").read_text().strip()
        except OSError as e:
            raise RuntimeError(f"cannot read {knob}: {e}") from e
        if val != want:
            raise RuntimeError(
                f"{knob} must be {want} (is {val}). Run: sudo sysctl -w kernel.{knob}={want}"
            )


def _tee(executor, cmd: list[str], stdout_file: Path | None, cwd: Path) -> None:
    print(f"Running: {' '.join(map(str, cmd))}")
    if stdout_file is None:
        r = executor(cmd, cwd=str(cwd), check=False)
        rc = getattr(r, "returncode", 0)
    else:
        r = executor(cmd, cwd=str(cwd), check=False, capture_output=True, text=True)
        rc = getattr(r, "returncode", 0)
        out = getattr(r, "stdout", "") or ""
        stdout_file.write_text(out, encoding="utf-8")
        if out:
            print(out, end="")
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)


def _perf_stages(executor, binary: Path, suite: Suite, rd: Path, repo_root: Path) -> None:
    fg = repo_root / "tools" / "FlameGraph"
    _tee(
        executor,
        [
            "perf",
            "record",
            "-F",
            "999",
            "-g",
            "-o",
            str(rd / "perf.data"),
            "--",
            str(binary),
            f"--benchmark_min_time={suite.min_time}",
        ],
        None,
        repo_root,
    )
    _tee(executor, ["perf", "script", "-i", str(rd / "perf.data")], rd / "perf.script", repo_root)
    _tee(
        executor,
        [str(fg / "stackcollapse-perf.pl"), str(rd / "perf.script")],
        rd / "perf.folded",
        repo_root,
    )
    _tee(
        executor,
        [str(fg / "flamegraph.pl"), str(rd / "perf.folded")],
        rd / "flamegraph.svg",
        repo_root,
    )


def run_suite(
    suite: Suite,
    defaults: Defaults,
    repo_root: Path,
    *,
    skip_perf: bool = False,
    results_dir: Path | None = None,
    history_dir: Path | None = None,
    run_id: str | None = None,
    executor=subprocess.run,
) -> RunResult:
    repo_root = Path(repo_root)
    run_id = run_id or new_run_id()
    rd = (results_dir or repo_root / "results") / suite.name / run_id
    rd.mkdir(parents=True, exist_ok=True)
    out_json = rd / "benchmark.json"
    print(f"Suite: {suite.name}\nResults: {rd}")

    if suite.kind == "gbench":
        binary = repo_root / suite.binary
        _tee(executor, gbench_command(binary, suite, out_json), rd / "benchmark.txt", repo_root)
    else:
        script = repo_root / suite.script
        _tee(
            executor,
            [sys.executable, str(script), *suite.args, "--out", str(out_json)],
            rd / "benchmark.txt",
            repo_root,
        )

    perf_ran = False
    if suite.kind == "gbench" and suite.perf and not skip_perf:
        try:
            check_perf_permissions()
            _perf_stages(executor, repo_root / suite.binary, suite, rd, repo_root)
            perf_ran = True
        except RuntimeError as e:
            print(f"WARNING: {e}\nskipping perf/flamegraph stages (timing results are unaffected)")

    stats = gbench.parse(out_json)
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    records = history.from_stats(
        run_id, suite.name, stats, machine.collect(repo_root), ts, perf_ran
    )
    history.append(history_dir or repo_root / "history", records)
    print(
        f"Recorded {len(records)} benchmark(s) to history; {sum(not r.valid for r in records)} invalid"
    )
    return RunResult(suite.name, run_id, rd, records, perf_ran)
