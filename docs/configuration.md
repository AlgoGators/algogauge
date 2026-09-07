# Configuration

## `algogauge.toml` manifest

Every benchmark suite is declared once in `algogauge.toml` at the repo root. The `algogauge` CLI, the runner, and the notebooks all read this file — nothing about a suite is hard-coded elsewhere.

```toml
[defaults]
repetitions = 20              # int: Google Benchmark repetitions per case
min_time = "2s"                # str: Google Benchmark --benchmark_min_time
perf = true                    # bool: run perf + flamegraph stages when possible
regression_threshold_pct = 10  # float: default `algogauge compare` threshold

[[benchmark]]
name   = "tick_to_trade"       # str, required, unique: suite id used everywhere (history file, CLI, dashboard)
kind   = "gbench"              # "gbench" | "script", required
binary = "build/benchmarks/tick_to_trade_benchmarks"   # required when kind = "gbench"
# script = "python/algogauge/backtest_parallel.py"     # required when kind = "script"
# args   = ["--symbols", "50"]                          # optional: extra argv passed to a script suite
# repetitions / min_time / perf                         # optional: override the suite's own defaults above
```

Any key omitted on a `[[benchmark]]` entry falls back to `[defaults]`. `kind = "gbench"` suites are Google Benchmark binaries invoked with the flags below; `kind = "script"` suites are any Python script that writes Google-Benchmark-shaped JSON to the `--out` path it's given (see `docs/pipeline.md`).

## Pipeline flags

`algogauge run` (via `python/algogauge/runner.py`) invokes `kind = "gbench"` binaries with:

| Flag | Value | Description |
|------|---------|-------------|
| `--benchmark_repetitions` | from manifest (`repetitions`) | Number of repetitions per benchmark case |
| `--benchmark_min_time` | from manifest (`min_time`) | Minimum wall-clock time per repetition |
| `--benchmark_display_aggregates_only` | `true` | Keep per-repetition timings in the JSON (needed to compute real median/p95/p99) while still hiding them from the console summary |

Note this differs from the old `benchmark_pipeline.py`, which used `--benchmark_report_aggregates_only=true` and discarded per-repetition data — that flag suppressed the raw timings the new percentile calculation needs, so the runner no longer uses it.

The `perf record` sampling frequency is also hard-coded to `-F 999` (999 Hz). Higher values increase profiling overhead; lower values reduce flamegraph resolution. If `perf_event_paranoid`/`kptr_restrict` aren't set correctly, the runner now **warns and skips** the perf/flamegraph stages instead of aborting — timing results are unaffected either way. Pass `--skip-perf` to skip them unconditionally.

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
