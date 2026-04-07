# AlgoGauge

AlgoGauge is a benchmarking and profiling suite for [trade-ngin](https://github.com/AlgoGators/trade-ngin) trading strategies. It combines Google Benchmark for micro-benchmarks, Linux `perf` for CPU profiling, and a Plotly Dash dashboard for interactive visualization of results.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Repository Structure](#repository-structure)
- [Setup](#setup)
- [Build](#build)
- [Workflow](#workflow)
  - [Step 1 – Run the Benchmark Pipeline](#step-1--run-the-benchmark-pipeline)
  - [Step 2 – View Results with the Dashboard](#step-2--view-results-with-the-dashboard)
- [Output Artifacts](#output-artifacts)
- [Available Benchmarks](#available-benchmarks)
- [Configuration](#configuration)

---

## Overview

The benchmarking workflow consists of three stages:

1. **Compile** – Build the C++ benchmark binaries with CMake.
2. **Profile** – Run the benchmark pipeline script, which executes the binary with Google Benchmark, collects CPU profiling data with `perf`, and generates a flamegraph.
3. **Visualize** – Launch the Dash dashboard to explore scaling behavior, timing metrics, and the flamegraph interactively.

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| CMake ≥ 3.28 | Build system | `apt install cmake` |
| C++20 compiler (GCC/Clang) | Compile benchmarks | `apt install g++` |
| Google Benchmark | Micro-benchmark library | `apt install libbenchmark-dev` |
| Google Test | Unit test framework (transitive dep) | `apt install libgtest-dev` |
| NLopt | Optimization library (trade-ngin dep) | `apt install libnlopt-cxx-dev` |
| `perf` | CPU profiling | `apt install linux-perf` |
| Python ≥ 3.12 | Pipeline script and dashboard | [python.org](https://python.org) |
| [uv](https://docs.astral.sh/uv/) | Python package manager | `pip install uv` |

### Linux kernel permissions for `perf`

The pipeline requires relaxed kernel security settings. Run once per boot (or make them permanent in `/etc/sysctl.conf`):

```bash
sudo sysctl -w kernel.perf_event_paranoid=0
sudo sysctl -w kernel.kptr_restrict=0
```

---

## Repository Structure

```
algogauge/
├── benchmarks/                  # C++ benchmark sources
│   ├── CMakeLists.txt           # Benchmark build rules
│   ├── base_strategy_benchmarks.cpp
│   ├── trend_following_benchmarks.cpp
│   ├── fixtures/                # Google Benchmark fixture classes
│   │   ├── base_strategy_fixture.hpp
│   │   └── trend_following_fixture.hpp
│   ├── mocks/                   # Test doubles
│   │   └── mock_postgres_database.hpp
│   └── utils/                   # Shared helpers
│       └── test_data_generator.hpp
├── external/
│   └── trade-ngin/              # Git submodule – trading engine library
├── python/
│   ├── benchmark_pipeline.py    # Orchestrates benchmark + perf + flamegraph
│   └── dashboard.py             # Dash web app for result visualization
├── tools/
│   └── FlameGraph/              # Git submodule – Brendan Gregg's FlameGraph scripts
├── CMakeLists.txt               # Top-level CMake configuration
├── pyproject.toml               # Python project metadata and dependencies
└── uv.lock                      # Locked Python dependency versions
```

---

## Setup

### 1. Clone the repository with submodules

```bash
git clone --recurse-submodules https://github.com/AlgoGators/algogauge.git
cd algogauge
```

If you already cloned without `--recurse-submodules`, initialize them now:

```bash
git submodule update --init --recursive
```

### 2. Install Python dependencies

```bash
uv sync
```

This creates a virtual environment and installs all packages listed in `pyproject.toml` (Dash, Pandas, Plotly, etc.) using the locked versions in `uv.lock`.

---

## Build

Configure and compile the C++ benchmark binaries:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The compiled benchmark binaries are placed in the `build/benchmarks/` directory:

- `build/benchmarks/base_strategy_benchmarks`
- `build/benchmarks/trend_following_benchmarks`

---

## Workflow

### Step 1 – Run the Benchmark Pipeline

The pipeline script orchestrates the full profiling run for a given benchmark binary. It must be invoked from the **repository root** so that the `tools/FlameGraph` scripts are found at the expected relative path.

```bash
uv run python/benchmark_pipeline.py <path-to-benchmark-binary>
```

**Examples:**

```bash
# Benchmark the base strategy
uv run python/benchmark_pipeline.py build/benchmarks/base_strategy_benchmarks

# Benchmark the trend-following strategy
uv run python/benchmark_pipeline.py build/benchmarks/trend_following_benchmarks
```

#### What the pipeline does

1. **Validates kernel permissions** – checks `perf_event_paranoid` and `kptr_restrict`.
2. **Runs Google Benchmark** – executes the binary with:
   - 30 repetitions per benchmark
   - 5-second minimum time per repetition
   - Aggregates-only reporting
   - Output saved as JSON and plain text
3. **Runs `perf record`** – profiles the binary at 999 Hz, recording call graphs.
4. **Runs `perf script`** – converts the binary `perf.data` into a human-readable call stack trace.
5. **Collapses stacks** – calls `stackcollapse-perf.pl` to fold the trace into a format suitable for flamegraph generation.
6. **Generates flamegraph** – calls `flamegraph.pl` to produce an interactive SVG.

All outputs are stored under `results/<binary-name>/<YYYYMMDD_HHMMSS>/`.

---

### Step 2 – View Results with the Dashboard

After the pipeline completes, start the interactive Dash dashboard:

```bash
uv run python/dashboard.py results/<binary-name>/<run-id>/
```

**Example:**

```bash
uv run python/dashboard.py results/base_strategy_benchmarks/20260101_120000/
```

Open the URL printed in the terminal (typically `http://127.0.0.1:8050`) in your browser.

#### Dashboard panels

| Panel | Description |
|-------|-------------|
| **Scaling Behavior** | Mean execution time (ns) vs. data size on a log-log scale |
| **Time per Element** | Mean execution time normalized by input size (ns/element) |
| **Coefficient of Variation** | Relative standard deviation (%) – measures benchmark stability |
| **Standard Deviation** | Absolute spread of timing measurements (ns) |
| **Flamegraph** | Interactive SVG flamegraph embedded inline |

> **Note:** The Coefficient of Variation and Standard Deviation panels are only shown when those statistics are present in the benchmark JSON output.

---

## Output Artifacts

Each pipeline run creates a timestamped directory under `results/`:

```
results/
└── <binary-name>/
    └── <YYYYMMDD_HHMMSS>/
        ├── benchmark.json    # Google Benchmark output (JSON)
        ├── benchmark.txt     # Google Benchmark output (human-readable)
        ├── perf.data         # Raw perf profiling data
        ├── perf.script       # Decoded perf call stacks
        ├── perf.folded       # Collapsed stack frames
        └── flamegraph.svg    # Interactive flamegraph
```

---

## Available Benchmarks

### `base_strategy_benchmarks`

Benchmarks the `trade_ngin::BaseStrategy` class.

| Benchmark | Description |
|-----------|-------------|
| `PauseStrategy` | Measures the cost of pausing and resuming a strategy |
| `OnDataScaling` | Measures `on_data()` latency across input sizes 64 – 8192 bars |

### `trend_following_benchmarks`

Benchmarks the `trade_ngin::TrendFollowingStrategy` class with 5 EMA crossover pairs.

| Benchmark | Description |
|-----------|-------------|
| `OnDataScaling` | Measures `on_data()` latency across input sizes 64 – 8192 bars |

---

## Configuration

### Benchmark parameters (pipeline)

The pipeline script hard-codes the following Google Benchmark flags. Edit `python/benchmark_pipeline.py` to adjust them:

| Flag | Default | Description |
|------|---------|-------------|
| `--benchmark_repetitions` | `30` | Number of repetitions per benchmark |
| `--benchmark_min_time` | `5s` | Minimum wall-clock time per repetition |
| `--benchmark_report_aggregates_only` | `true` | Only report mean/stddev/cv, not each individual repetition |

### Benchmark sizing

Input sizes for `OnDataScaling` benchmarks are defined in the C++ source files. The default range is **64 to 8192 bars** with a **2× multiplier** between steps. To change this, edit the `BENCHMARK_REGISTER_F` call in the relevant `.cpp` file:

```cpp
BENCHMARK_REGISTER_F(BaseStrategyBenchmark, OnDataScaling)
    ->RangeMultiplier(2)
    ->Range(64, 8192);
```

### Trend-following strategy parameters

The `TrendFollowingBenchmark` fixture in `benchmarks/fixtures/trend_following_fixture.hpp` configures the strategy with the following defaults:

| Parameter | Value |
|-----------|-------|
| Capital allocation | $1,000,000 |
| Max leverage | 4× |
| Risk target | 0.20 |
| IDM | 2.5 |
| EMA crossover pairs | (2,8), (4,16), (8,32), (16,64), (32,128) |
| Position buffering | enabled |
