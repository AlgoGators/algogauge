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

## Test data

Both fixtures use `bench_utils::create_test_data()` (`benchmarks/utils/test_data_generator.hpp`) to generate synthetic `Bar` data:

- Deterministic (seeded with `srand(42)`)
- Price follows a sine-wave trend plus random noise
- Default start price: 100.0, volatility: 0.20
- Volume: 100,000 – 150,000 units per bar
