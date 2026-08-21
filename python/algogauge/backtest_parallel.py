"""Backtest-speedup harness (Tier-1 metric, design spec section 3.3).

Runs K independent backtests (`build/benchmarks/bt_bench_runner`, one process
per job) serially, then across a process pool at increasing worker counts,
and reports wall-clock speedup and parallel efficiency vs. serial. Verifies
that a parallel run produces the exact same result (via a checksum printed
by bt_bench_runner) as the serial run for the same job -- a correctness
guard, not just a timing measurement.

trade-ngin's engine is single-threaded (no std::thread/std::async/OpenMP
anywhere in src/ or apps/ as of the design spec), so this measures speedup
across *independent* backtests (parameter sweeps, walk-forward folds,
Monte-Carlo seeds) -- not multi-threading inside one backtest. See
docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.3
for the full rationale.

Invoked by algogauge.runner as a `kind = "script"` suite: writes
Google-Benchmark-shaped JSON to the path given via --out so it flows through
the same gbench.parse() -> history.append() pipeline as the gbench suites.

Usage: python backtest_parallel.py --symbols 50 --years 10 --jobs 8
                                   --workers 1,2,4,8,16 --out results.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def default_binary(repo_root: Path) -> Path:
    return repo_root / "build" / "benchmarks" / "bt_bench_runner"


def run_job(binary: str, symbols: int, years: int, seed: int) -> dict:
    """Run one bt_bench_runner job and parse its single-line JSON stdout."""
    proc = subprocess.run(
        [binary, "--symbols", str(symbols), "--years", str(years), "--seed", str(seed)],
        capture_output=True,
        text=True,
        check=True,
        timeout=3600,
    )
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def run_batch_serial(
    binary: str, symbols: int, years: int, seeds: list[int]
) -> tuple[float, list[dict]]:
    start = time.perf_counter()
    results = [run_job(binary, symbols, years, seed) for seed in seeds]
    elapsed = time.perf_counter() - start
    return elapsed, results


def run_batch_parallel(
    binary: str, symbols: int, years: int, seeds: list[int], workers: int
) -> tuple[float, list[dict]]:
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(
                run_job, [binary] * len(seeds), [symbols] * len(seeds), [years] * len(seeds), seeds
            )
        )
    elapsed = time.perf_counter() - start
    return elapsed, results


def verify_checksums(serial_results: list[dict], parallel_results: list[dict]) -> None:
    """Raise if a parallel run's result doesn't match the serial run for the same seed."""
    by_seed = {r["seed"]: r["checksum"] for r in serial_results}
    for r in parallel_results:
        expected = by_seed.get(r["seed"])
        if expected is None:
            raise RuntimeError(f"parallel result for unknown seed {r['seed']}")
        if r["checksum"] != expected:
            raise RuntimeError(
                f"checksum mismatch for seed {r['seed']}: serial={expected!r} parallel={r['checksum']!r} "
                "-- parallel execution produced a different backtest result than serial"
            )


def build_gbench_json(worker_results: list[dict]) -> dict:
    """Shape results as Google-Benchmark-style JSON so gbench.parse() can read them."""
    benchmarks = []
    for wr in worker_results:
        benchmarks.append(
            {
                "name": f"BacktestSpeedup/{wr['workers']}",
                "run_name": f"BacktestSpeedup/{wr['workers']}",
                "run_type": "iteration",
                "repetitions": 1,
                "repetition_index": 0,
                "iterations": 1,
                "real_time": wr["elapsed_seconds"],
                "cpu_time": wr["elapsed_seconds"],
                "time_unit": "s",
                "speedup": wr["speedup"],
                "efficiency": wr["efficiency"],
                "jobs": wr["jobs"],
            }
        )
    return {
        "context": {"executable": "backtest_parallel.py"},
        "benchmarks": benchmarks,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols", type=int, default=50)
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--jobs", type=int, default=8, help="number of independent backtests per batch")
    p.add_argument(
        "--workers", default="1,2,4,8,16", help="comma-separated worker counts to measure"
    )
    p.add_argument(
        "--binary",
        default=None,
        help="path to bt_bench_runner (default: build/benchmarks/bt_bench_runner)",
    )
    p.add_argument("--out", required=True, help="path to write Google-Benchmark-shaped JSON")
    args = p.parse_args(argv)

    repo_root = Path.cwd()
    binary = args.binary or str(default_binary(repo_root))
    if not Path(binary).exists():
        print(
            f"ERROR: bt_bench_runner not found at {binary} -- build it first "
            "(cmake --build build --parallel)",
            file=sys.stderr,
        )
        return 1

    seeds = [42 + i for i in range(args.jobs)]
    worker_counts = [int(w) for w in args.workers.split(",") if w.strip()]

    print(f"Serial baseline: {args.jobs} jobs, {args.symbols} symbols x {args.years} years each")
    serial_elapsed, serial_results = run_batch_serial(binary, args.symbols, args.years, seeds)
    print(f"  {serial_elapsed:.2f}s")

    worker_results = []
    for workers in worker_counts:
        print(f"Parallel: {workers} worker(s)")
        elapsed, parallel_results = run_batch_parallel(
            binary, args.symbols, args.years, seeds, workers
        )
        verify_checksums(serial_results, parallel_results)
        speedup = serial_elapsed / elapsed if elapsed > 0 else 0.0
        efficiency = speedup / workers if workers > 0 else 0.0
        print(f"  {elapsed:.2f}s  speedup={speedup:.2f}x  efficiency={efficiency:.2f}")
        worker_results.append(
            {
                "workers": workers,
                "elapsed_seconds": elapsed,
                "speedup": speedup,
                "efficiency": efficiency,
                "jobs": args.jobs,
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(build_gbench_json(worker_results), indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
