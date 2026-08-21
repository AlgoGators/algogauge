# Available Benchmarks

## `base_strategy_benchmarks`

Binary: `build/benchmarks/base_strategy_benchmarks`

Benchmarks the `trade_ngin::BaseStrategy` class using the `BaseStrategyBenchmark` fixture.

**Fixture setup** (`benchmarks/fixtures/base_strategy_fixture.hpp`):

- Initializes a `BaseStrategy` with $1,000,000 capital and 4× max leverage
- Applies risk limits: 4× max leverage, 25% max drawdown, $1,000,000 max notional
- Uses `MockPostgresDatabase` (no real DB connection)
- Calls `strategy->initialize()` and `strategy->start()` before each benchmark

| Benchmark | Description |
|-----------|-------------|
| `PauseStrategy` | Measures the round-trip cost of `strategy->pause()` + `strategy->resume()` |
| `OnDataScaling` | Measures `strategy->on_data()` latency across input sizes 64 – 8192 bars |

---

## `trend_following_benchmarks`

Binary: `build/benchmarks/trend_following_benchmarks`

Benchmarks the `trade_ngin::TrendFollowingStrategy` class using the `TrendFollowingBenchmark` fixture.

**Fixture setup** (`benchmarks/fixtures/trend_following_fixture.hpp`):

- Strategy configured for FUTURES / DAILY data with $1,000,000 capital and 4× max leverage
- Trend config: risk target 0.20, IDM 2.5, position buffering enabled
- EMA crossover pairs: (2,8), (4,16), (8,32), (16,64), (32,128)
- Risk limits match the base strategy fixture

| Benchmark | Description |
|-----------|-------------|
| `OnDataScaling` | Measures `strategy->on_data()` latency across input sizes 64 – 8192 bars |

---

## `tick_to_trade_benchmarks`

Binary: `build/benchmarks/tick_to_trade_benchmarks`

Tier-1 metric (see `docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md` §3.1): how long from a new bar arriving to an order/execution being emitted. Benchmarks `PortfolioManager::process_market_data()` → `PortfolioManager::get_recent_executions()` using the `TickToTradeBenchmark` fixture.

**Fixture setup** (`benchmarks/fixtures/tick_to_trade_fixture.hpp`):

- A real `PortfolioManager` wrapping one real `TrendFollowingStrategy` (same config as `trend_following_benchmarks`), against a `MockPostgresDatabase` — no network, no real broker, no real DB.
- Per variant, warms up with 256 historical bars (one call per simulated day, all symbols at once — mirrors `BacktestCoordinator::process_day()`) so EMAs are populated and the strategy is actually producing target position changes, then clears execution history before timing starts.

| Benchmark | Description |
|-----------|-------------|
| `ProcessTick/1` | One new bar → executions, single-symbol universe |
| `ProcessTick/8` | Same, 8-symbol universe |
| `ProcessTick/32` | Same, 32-symbol universe |
| `ProcessTick/128` | Same, 128-symbol universe |

Each result also reports an `executions_per_tick` counter. If a run produces zero executions across every iteration, the benchmark fails loudly (`state.SkipWithError`) instead of reporting a misleadingly fast "0 executions in 0 time" number.

**Honesty notes:** this is in-process engine decision latency only — it does not include exchange/broker round-trip time, network I/O, or a real database. See the design spec for the full rationale.

---

## `ingestion_throughput_benchmarks`

Binary: `build/benchmarks/ingestion_throughput_benchmarks`

Tier-1 metric (see `docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md` §3.2): how many market-data messages/bars per second the pipeline can convert and fan out. Uses the `IngestionBenchmark` fixture (`benchmarks/fixtures/ingestion_fixture.hpp`) — synthetic in-memory data only, no socket or disk I/O.

| Benchmark | Stage | Description |
|-----------|-------|-------------|
| `ArrowToBars/1000..1000000` | A: conversion | `DataConversionUtils::arrow_table_to_bars()` over synthetic OHLCV Arrow tables of 1k/10k/100k/1M rows |
| `Publish/1,4,16` | B: fan-out | `MarketDataBus::publish()`, single publisher thread, varying subscriber count |
| `PublishContended/1,4,16` | C: contention | `MarketDataBus::publish()` called concurrently from N `std::thread` publishers against the mutex-guarded singleton bus, exposing lock contention as thread count rises |

Each `Publish`/`PublishContended` run fails loudly via `state.SkipWithError(...)` if zero events were actually delivered to subscribers, so a broken fixture can't silently report a fast "0 delivery" number.

---

## `backtest_speedup` (script suite)

Driver: `build/benchmarks/bt_bench_runner` (plain executable, not Google Benchmark) · Harness: `python/algogauge/backtest_parallel.py`

Tier-1 metric (see `docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md` §3.3): how much faster a large simulation runs when parallelized vs. serial. `bt_bench_runner --symbols N --years Y --seed S` runs one full multi-year, multi-symbol synthetic backtest through `PortfolioManager` + `TrendFollowingStrategy` (the same decision path as `tick_to_trade_benchmarks`, run day-by-day for the whole history) and prints wall-clock time plus a result checksum as one line of JSON.

`backtest_parallel.py` runs 8 such jobs (different seeds, default) serially, then via a `ProcessPoolExecutor` at 1/2/4/8/16 workers, and reports:

| Benchmark | Description |
|-----------|-------------|
| `BacktestSpeedup/1` | Wall-clock, speedup, and efficiency at 1 worker |
| `BacktestSpeedup/2`, `/4`, `/8`, `/16` | Same, at increasing worker counts |

Each worker-count's results are checked against the serial run's checksums for the same seeds — a **correctness guard**, not just a timing measurement: a mismatch means parallel execution changed the result, and the harness fails loudly instead of reporting a speedup number for a broken run.

**Honesty notes:** trade-ngin's engine is single-threaded (no `std::thread`/`std::async`/OpenMP anywhere in `src/` or `apps/`). This measures speedup across *independent* backtests (parameter sweeps, walk-forward folds, Monte-Carlo seeds) run in separate OS processes — not multi-threading inside a single backtest. `bt_bench_runner` is built directly on `PortfolioManager::process_market_data()` rather than `BacktestCoordinator`, reusing the same strategy/portfolio wiring as `tick_to_trade_benchmarks` rather than introducing `BacktestCoordinator`'s `InstrumentRegistry`/contract-roll dependencies into this harness.

---

## Test data

Both fixtures use `bench_utils::create_test_data()` (`benchmarks/utils/test_data_generator.hpp`) to generate synthetic `Bar` data:

- Deterministic (seeded with `srand(42)`)
- Price follows a sine-wave trend plus random noise
- Default start price: 100.0, volatility: 0.20
- Volume: 100,000 – 150,000 units per bar
