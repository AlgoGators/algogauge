# Configuration

## Pipeline flags

The pipeline script hard-codes the following Google Benchmark flags. Edit `python/benchmark_pipeline.py` to adjust them:

| Flag | Default | Description |
|------|---------|-------------|
| `--benchmark_repetitions` | `30` | Number of repetitions per benchmark case |
| `--benchmark_min_time` | `5s` | Minimum wall-clock time per repetition |
| `--benchmark_report_aggregates_only` | `true` | Only emit mean/stddev/cv aggregates, not raw per-rep timings |

The `perf record` sampling frequency is also hard-coded to `-F 999` (999 Hz). Higher values increase profiling overhead; lower values reduce flamegraph resolution.

## Benchmark input sizes

Input sizes for `OnDataScaling` benchmarks are defined in the C++ source files via `BENCHMARK_REGISTER_F`. The default range is **64 to 8192 bars** with a **2× multiplier** between steps.

To change the range or multiplier, edit the registration in the relevant `.cpp` file:

```cpp
// benchmarks/base_strategy_benchmarks.cpp
BENCHMARK_REGISTER_F(BaseStrategyBenchmark, OnDataScaling)
    ->RangeMultiplier(2)   // step multiplier
    ->Range(64, 8192);     // [min, max] number of bars
```

After editing, rebuild with `cmake --build build --parallel` before running the pipeline.

## Trend-following strategy parameters

The `TrendFollowingBenchmark` fixture (`benchmarks/fixtures/trend_following_fixture.hpp`) configures the strategy with these defaults:

| Parameter | Value | Where to change |
|-----------|-------|----------------|
| Capital allocation | $1,000,000 | `strategy_config.capital_allocation` |
| Max leverage | 4× | `strategy_config.max_leverage` |
| Risk target | 0.20 | `trend_config.risk_target` |
| IDM | 2.5 | `trend_config.idm` |
| EMA crossover pairs | (2,8), (4,16), (8,32), (16,64), (32,128) | `trend_config.ema_windows` |
| Position buffering | enabled | `trend_config.use_position_buffering` |
| Max drawdown | 25% | `limits.max_drawdown` |
| Max position size | 100,000 units | `limits.max_position_size` |
| Max notional value | $1,000,000 | `limits.max_notional_value` |

All of these are benchmark-only settings. They do not affect production strategy configuration.
