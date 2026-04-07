# Setup & Build

## 1. Clone the repository with submodules

AlgoGauge depends on two git submodules:

- `external/trade-ngin` – the trading engine library being benchmarked
- `tools/FlameGraph` – Brendan Gregg's flamegraph generation scripts

Clone both at once:

```bash
git clone --recurse-submodules https://github.com/AlgoGators/algogauge.git
cd algogauge
```

If you already cloned without `--recurse-submodules`, initialize them now:

```bash
git submodule update --init --recursive
```

## 2. Install Python dependencies

```bash
uv sync
```

This creates a virtual environment and installs all packages listed in `pyproject.toml` (Dash, Pandas, Plotly, etc.) using the exact versions pinned in `uv.lock`.

## 3. Build the C++ benchmark binaries

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The compiled binaries are placed in `build/benchmarks/`:

| Binary | Strategy |
|--------|----------|
| `build/benchmarks/base_strategy_benchmarks` | `trade_ngin::BaseStrategy` |
| `build/benchmarks/trend_following_benchmarks` | `trade_ngin::TrendFollowingStrategy` |

> **Tip:** Pass `-DCMAKE_BUILD_TYPE=RelWithDebInfo` instead of `Release` to keep debug symbols while still benefiting from optimizations. This produces richer flamegraphs without changing benchmark results.
