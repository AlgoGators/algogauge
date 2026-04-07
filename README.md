# AlgoGauge

AlgoGauge is a benchmarking and profiling suite for [trade-ngin](https://github.com/AlgoGators/trade-ngin) trading strategies. It combines Google Benchmark for micro-benchmarks, Linux `perf` for CPU profiling, and a Plotly Dash dashboard for interactive visualization of results.

## Workflow

1. **Compile** – Build the C++ benchmark binaries with CMake.
2. **Profile** – Run the pipeline script (`python/benchmark_pipeline.py`), which executes Google Benchmark, collects CPU profiling data with `perf`, and generates a flamegraph.
3. **Visualize** – Launch the Dash dashboard (`python/dashboard.py`) to explore results interactively.

## Quick Start

```bash
# 1. Clone (includes submodules)
git clone --recurse-submodules https://github.com/AlgoGators/algogauge.git
cd algogauge

# 2. Install Python dependencies
uv sync

# 3. Build benchmark binaries
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# 4. Run the benchmark pipeline (from repo root)
uv run python/benchmark_pipeline.py build/benchmarks/base_strategy_benchmarks

# 5. View results in the dashboard
uv run python/dashboard.py results/base_strategy_benchmarks/<run-id>/
```

> **Note:** `perf` requires relaxed kernel settings. See [docs/prerequisites.md](docs/prerequisites.md) for details.

## Repository Structure

```
algogauge/
├── benchmarks/          # C++ benchmark sources, fixtures, mocks, and utilities
├── docs/                # Detailed documentation
├── external/trade-ngin/ # Git submodule – trading engine library
├── python/
│   ├── benchmark_pipeline.py   # Orchestrates benchmark + perf + flamegraph
│   └── dashboard.py            # Plotly Dash result viewer
├── tools/FlameGraph/    # Git submodule – flamegraph generation scripts
├── CMakeLists.txt
└── pyproject.toml
```

## Documentation

| Topic | File |
|-------|------|
| System dependencies and kernel settings | [docs/prerequisites.md](docs/prerequisites.md) |
| Cloning, Python setup, and CMake build | [docs/setup.md](docs/setup.md) |
| Benchmark pipeline stages and output artifacts | [docs/pipeline.md](docs/pipeline.md) |
| Dashboard usage and panels | [docs/dashboard.md](docs/dashboard.md) |
| Available benchmarks and fixture details | [docs/benchmarks.md](docs/benchmarks.md) |
| Pipeline flags, input sizes, and strategy parameters | [docs/configuration.md](docs/configuration.md) |
