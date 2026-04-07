# Dashboard

`python/dashboard.py` is an interactive Plotly Dash web app for exploring benchmark results produced by the pipeline.

## Usage

After a pipeline run completes, start the dashboard by passing the run directory:

```bash
uv run python/dashboard.py results/<binary-name>/<run-id>/
```

**Example:**

```bash
uv run python/dashboard.py results/base_strategy_benchmarks/20260101_120000/
```

Open the URL printed in the terminal (typically `http://127.0.0.1:8050`) in your browser.

## Panels

| Panel | Description |
|-------|-------------|
| **Scaling Behavior** | Mean execution time (ns) vs. input data size |
| **Time per Element** | Mean execution time normalized by input size (ns/element) – highlights algorithmic complexity |
| **Coefficient of Variation** | Relative standard deviation (%) – lower is more stable |
| **Standard Deviation** | Absolute spread of timing measurements (ns) |
| **Flamegraph** | Interactive SVG embedded inline; click any frame to zoom |

> **Note:** The Coefficient of Variation and Standard Deviation panels only appear when those statistics are present in `benchmark.json`. They are included when `--benchmark_report_aggregates_only=true` is used (the pipeline default).

## Expected input

The dashboard reads two files from the given directory:

| File | Required | Purpose |
|------|----------|---------|
| `benchmark.json` | Yes | Benchmark timing data |
| `flamegraph.svg` | No | Embedded inline if present |

The JSON must contain benchmarks whose names match the pattern `OnDataScaling/<size>_<metric>` (e.g. `OnDataScaling/256_mean`). Benchmarks that don't match this pattern are silently ignored.
