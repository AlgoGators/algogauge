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

# WSL2 users: install the full toolchain in one idempotent step (needs sudo)
wsl -d Ubuntu -e sudo bash scripts/setup_wsl.sh

# 2. Install Python dependencies
uv sync --extra dev

# 3. Build benchmark binaries
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# 4. Run every suite declared in algogauge.toml (add --skip-perf if perf is unavailable)
uv run algogauge run

# 5. Compare the last two runs of a suite (exits 1 on a >10% median regression)
uv run algogauge compare base_strategy

# 6. Or do it all from Jupyter
uv run jupyter lab notebooks/
```

> **Note:** `perf` requires relaxed kernel settings. See [docs/prerequisites.md](docs/prerequisites.md) for details. If `perf` isn't available, `--skip-perf` still produces full timing results — only flamegraphs are skipped.

## Repository Structure

```
algogauge/
├── algogauge.toml        # Manifest: every benchmark suite, binary/script, params
├── benchmarks/           # C++ benchmark sources, fixtures, mocks, and utilities
├── docs/                 # Detailed documentation
├── external/trade-ngin/  # Git submodule – trading engine library
├── history/              # Tracked: one JSONL file per suite, one line per run
├── notebooks/            # Reproducible entry points (setup, run-all, per-metric, dashboard)
├── python/
│   ├── algogauge/               # manifest, runner, history, compare, machine, cli
│   ├── benchmark_pipeline.py    # Back-compat shim over algogauge.runner
│   └── dashboard.py             # Plotly Dash result viewer
├── results/              # Gitignored: raw benchmark.json, perf.data, flamegraph.svg per run
├── scripts/
│   ├── setup_wsl.sh          # Idempotent WSL2 Ubuntu toolchain install
│   └── build_notebooks.py    # Regenerates notebooks/*.ipynb deterministically
├── tools/FlameGraph/     # Git submodule – flamegraph generation scripts
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
| Roadmap – CI integration and arbitrary benchmark support | [docs/roadmap.md](docs/roadmap.md) |
