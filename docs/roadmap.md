# Roadmap

This document outlines planned improvements in two areas: integrating AlgoGauge into a continuous integration (CI) pipeline, and extending the analysis pipeline to support arbitrary Google Benchmark binaries beyond the strategies currently hard-wired in the repository.

> **Update (2026-08-21):** The Tier-1 performance benchmarking work ([ADR 0001](adr/0001-tier1-performance-benchmarking.md)) delivered most of "Arbitrary Benchmark Support" below as a byproduct — see the status table under [Priority order](#priority-order).

---

## CI Integration

Running benchmarks in CI catches performance regressions automatically, without requiring a developer to remember to profile manually.

### Goals

- **Automatic regression detection** – Compare each pull request's benchmark results against a stored baseline and fail the check if mean execution time regresses beyond a configurable threshold (e.g. ±5%).
- **Artifact persistence** – Upload the full timestamped results directory (`benchmark.json`, `flamegraph.svg`, etc.) as a CI artifact so reviewers can inspect timing data and flamegraphs directly from the PR.
- **Trend tracking** – Append each run's aggregate results to a time-series store (e.g. a JSON file committed to a `gh-pages` branch or an external metrics service) to visualize performance over the history of the project.

### Design sketch

```
push / pull_request
        │
        ▼
┌──────────────────────────┐
│  1. Build                │  cmake -B build -DCMAKE_BUILD_TYPE=Release
│                          │  cmake --build build --parallel
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  2. Run pipeline         │  uv run python/benchmark_pipeline.py <binary>
│     (perf disabled in    │  (kernel settings unavailable in most CI
│      hosted runners)     │   environments – see note below)
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  3. Compare vs baseline  │  New script: python/compare_baseline.py
│                          │  Reads benchmark.json, computes % change,
│                          │  exits non-zero on regression
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  4. Upload artifacts     │  actions/upload-artifact or equivalent
└──────────────────────────┘
```

### `perf` in CI

Most hosted CI runners (GitHub Actions, GitLab CI, etc.) run inside containers or VMs where `perf_event_paranoid` cannot be set to `0`. The pipeline will need a `--skip-perf` flag (or environment variable) that disables the `perf record` / flamegraph stages and runs Google Benchmark only. The dashboard and regression-comparison script work entirely from `benchmark.json` and do not need the flamegraph.

### Suggested workflow file location

`.github/workflows/benchmark.yml` – triggered on every push to `main` and on pull requests targeting `main`. Self-hosted runners with `perf` access can be used when flamegraph generation is also desired.

---

## Arbitrary Benchmark Support

Currently the pipeline and dashboard make assumptions tied to the specific benchmarks in this repository (e.g. the `OnDataScaling/<size>` name pattern). Removing these assumptions would let AlgoGauge profile *any* binary that produces valid Google Benchmark JSON output.

### Current limitations

| Assumption | Where it lives |
|------------|----------------|
| Benchmark names follow `OnDataScaling/<size>_<metric>` | `python/dashboard.py` – axis labels, scaling plots |
| Input sizes are powers-of-two bar counts | `python/dashboard.py` – x-axis interpretation |
| A single binary is profiled per run | `python/benchmark_pipeline.py` |

### Proposed changes

#### 1. Schema-agnostic dashboard

- Detect available benchmark names from `benchmark.json` at startup rather than assuming a fixed naming convention.
- Group benchmarks by family (the prefix before `/`) automatically and render one scaling plot per family.
- Fall back gracefully to a raw data table for benchmarks that don't follow a `name/<numeric-param>` pattern.

#### 2. Configurable pipeline via a manifest file

Introduce an optional `algogauge.toml` (or `algogauge.json`) manifest that describes which binaries to run and any per-binary options:

```toml
[[benchmark]]
binary = "build/benchmarks/base_strategy_benchmarks"
repetitions = 30
min_time = "5s"

[[benchmark]]
binary = "build/benchmarks/my_custom_benchmarks"
repetitions = 10
min_time = "2s"
perf = false          # disable perf / flamegraph for this binary
```

When no manifest is present, the pipeline falls back to its current behavior (a single positional argument).

#### 3. Multi-binary dashboard

Extend `dashboard.py` to accept a parent `results/` directory (instead of a single run directory) and render results for all binaries in a tabbed or side-by-side layout.

#### 4. Pluggable output formats

Add an `--export` flag to `benchmark_pipeline.py` that writes a summary CSV or Markdown table alongside the existing JSON, suitable for pasting into PR comments or commit messages.

---

## Priority order

| Item | Value | Complexity | Status |
|------|-------|------------|--------|
| `--skip-perf` flag | High – unblocks CI | Low | **Done** — `algogauge run --skip-perf`; perf-permission failure also now warns and skips automatically instead of aborting |
| Baseline comparison script | High – core CI feature | Medium | **Done** — `algogauge compare <suite>` / `python/algogauge/compare.py`, used locally today; wiring it into an actual CI workflow (below) is still open |
| Schema-agnostic dashboard | Medium – quality-of-life | Medium | **Done** — rewritten dashboard auto-discovers suites/benchmarks from `history/`, no hard-coded naming pattern |
| `algogauge.toml` manifest | Medium – usability | Medium | **Done** — every suite (including the three Tier-1 suites) is declared here |
| Multi-binary dashboard | Low – nice-to-have | High | **Done** — Suites page shows every suite in one dashboard; Trends/Compare/Runs pages are multi-run as well |
| Pluggable export formats | Low – nice-to-have | Low | Not started |
| `.github/workflows/benchmark.yml` CI workflow | High – unblocks automatic regression detection | Medium | Not started — everything it needs (`--skip-perf`, `compare`, manifest) now exists; this is the remaining piece |
