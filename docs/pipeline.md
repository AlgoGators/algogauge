# Benchmark Pipeline

## Manifest-driven runner (current)

`uv run algogauge run [SUITE ...]` is the current entry point. It reads `algogauge.toml` (see `docs/configuration.md`), runs each named suite (all suites if none are named) via `python/algogauge/runner.py`, and:

1. Runs the suite's binary (`kind = "gbench"`) or script (`kind = "script"`), writing `results/<suite>/<run-id>/benchmark.json` + `benchmark.txt`.
2. Runs the `perf` + FlameGraph stages, unless `--skip-perf` is passed or `suite.perf = false` in the manifest. If the kernel's `perf_event_paranoid`/`kptr_restrict` settings block `perf`, the runner **prints a warning and skips profiling instead of aborting** — timing numbers are produced either way.
3. Parses `benchmark.json` with `python/algogauge/gbench.py`, computing real median/p95/p99 from the per-repetition timings (see `docs/configuration.md` for why `--benchmark_display_aggregates_only` replaced the old `--benchmark_report_aggregates_only` flag).
4. Appends one compact JSON line per benchmark to `history/<suite>.jsonl` via `python/algogauge/history.py`. Each record carries: `run_id, suite, benchmark, family, param, unit, median, p95, p99, mean, stddev, cv_pct, samples, iterations, counters, valid, invalid_reason, machine, trade_ngin_sha, algogauge_sha, ts, perf`.
5. A record is marked `valid: false` (`invalid_reason: "cv_pct > 15"`) when its coefficient of variation exceeds 15% — still stored, but excluded from `latest_run()`/dashboard trend lines by default so a noisy run can't silently become the new baseline.

Compare two runs of a suite with `uv run algogauge compare <suite>` (defaults to the latest two valid runs; exits `1` on any benchmark whose median regressed beyond the threshold — see `docs/configuration.md`). `uv run algogauge list` shows every suite in the manifest.

`benchmark_pipeline.py <binary>` still works as a thin backwards-compatible shim over the same runner (single ad-hoc binary, not manifest-driven) — prefer `algogauge run` for anything tracked in `algogauge.toml`.

## Legacy direct usage

`python/benchmark_pipeline.py` orchestrates a profiling run for one ad-hoc benchmark binary, outside the manifest. It must be invoked from the **repository root** so that the `tools/FlameGraph` scripts are found at their expected relative paths.

## Usage

```bash
uv run python/benchmark_pipeline.py <path-to-benchmark-binary>
```

**Examples:**

```bash
# Base strategy
uv run python/benchmark_pipeline.py build/benchmarks/base_strategy_benchmarks

# Trend-following strategy
uv run python/benchmark_pipeline.py build/benchmarks/trend_following_benchmarks
```

## Pipeline stages

The script runs the following stages in order:

| # | Stage | Tool | Output |
|---|-------|------|--------|
| 1 | Validate kernel permissions | (built-in check) | — |
| 2 | Run micro-benchmarks | Google Benchmark | `benchmark.json`, `benchmark.txt` |
| 3 | Record CPU profile | `perf record -F 999 -g` | `perf.data` |
| 4 | Decode profile | `perf script` | `perf.script` |
| 5 | Collapse stack frames | `stackcollapse-perf.pl` | `perf.folded` |
| 6 | Generate flamegraph | `flamegraph.pl` | `flamegraph.svg` |

### Stage details

1. **Kernel permission check** – Reads `/proc/sys/kernel/perf_event_paranoid` and `/proc/sys/kernel/kptr_restrict`. The script aborts with a helpful message if either setting is wrong. See [prerequisites.md](prerequisites.md) for the required values.

2. **Google Benchmark** – Runs the binary with:
   - `--benchmark_repetitions=30`
   - `--benchmark_min_time=5s`
   - `--benchmark_report_aggregates_only=true`

   Results are written as both JSON (consumed by the dashboard) and plain text (human-readable summary).

3. **`perf record`** – Profiles the binary at 999 Hz with call-graph recording enabled (`-g`). The raw profile is saved as `perf.data`.

4. **`perf script`** – Decodes `perf.data` into a human-readable call-stack trace (`perf.script`).

5. **Stack collapse** – `stackcollapse-perf.pl` folds the decoded stacks into the single-line-per-stack format expected by `flamegraph.pl`.

6. **Flamegraph** – `flamegraph.pl` converts the folded stacks into an interactive SVG. Click on any frame in the browser to zoom into that call tree.

## Output artifacts

Each run creates a timestamped directory under `results/`:

```
results/
└── <binary-name>/
    └── <YYYYMMDD_HHMMSS>/
        ├── benchmark.json    # Google Benchmark output (JSON) – used by dashboard
        ├── benchmark.txt     # Google Benchmark output (human-readable)
        ├── perf.data         # Raw perf profiling data
        ├── perf.script       # Decoded perf call stacks
        ├── perf.folded       # Collapsed stack frames
        └── flamegraph.svg    # Interactive flamegraph
```

Pass the run directory path to `dashboard.py` to explore the results visually. See [dashboard.md](dashboard.md).
