# Benchmark Pipeline

`python/benchmark_pipeline.py` orchestrates the full profiling run for a given benchmark binary. It must be invoked from the **repository root** so that the `tools/FlameGraph` scripts are found at their expected relative paths.

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
