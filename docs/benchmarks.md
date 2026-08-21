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
| `ProcessTick/symbols:1` | One new bar → executions, single-symbol universe |
| `ProcessTick/symbols:8` | Same, 8-symbol universe |
| `ProcessTick/symbols:32` | Same, 32-symbol universe |
| `ProcessTick/symbols:128` | Same, 128-symbol universe |

Each result also reports an `executions_per_tick` counter. If a run produces zero executions across every iteration, the benchmark fails loudly (`state.SkipWithError`) instead of reporting a misleadingly fast "0 executions in 0 time" number.

**Honesty notes:** this is in-process engine decision latency only — it does not include exchange/broker round-trip time, network I/O, or a real database. See the design spec for the full rationale.

---

## Test data

Both fixtures use `bench_utils::create_test_data()` (`benchmarks/utils/test_data_generator.hpp`) to generate synthetic `Bar` data:

- Deterministic (seeded with `srand(42)`)
- Price follows a sine-wave trend plus random noise
- Default start price: 100.0, volatility: 0.20
- Volume: 100,000 – 150,000 units per bar
