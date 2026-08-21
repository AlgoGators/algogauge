# ADR 0001: Tier-1 Performance Benchmarking

**Status:** Accepted
**Date:** 2026-08-21
**Supersedes:** N/A · **Full design:** [`docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md`](../superpowers/specs/2026-08-21-tier1-benchmarking-design.md)

## Context

Three questions kept coming up without a real, repeatable answer:

1. **Tick-to-trade latency** — how long from a market-data bar arriving to trade-ngin producing an order/execution?
2. **Data-ingestion throughput** — how many market-data messages/bars per second can the pipeline convert and fan out?
3. **Backtest speedup** — how much faster does a large simulation run when parallelized vs. serial?

Before this work, none of these had a measured number — only estimates or nothing at all. AlgoGauge already had a Google Benchmark + `perf` + Dash pipeline for two strategy-level benchmarks (`base_strategy`, `trend_following`), and its own roadmap (`docs/roadmap.md`) already asked for a manifest, a schema-agnostic dashboard, multi-run comparison, and baseline regression checking — this work needed all of those anyway, so it built them rather than duplicating a one-off pipeline.

## Decision

- **Measure against trade-ngin's real code**, not a re-implementation: `PortfolioManager::process_market_data()`, `DataConversionUtils::arrow_table_to_bars()`, `MarketDataBus::publish()`. Structured so `data-ngin` / `AlgoSys v2` can be added later as additional submodules + manifest entries — not built now because neither exists in this workspace.
- **Mock database, synthetic data, in-process** for every suite. No live PostgreSQL, no real broker, no network I/O. This is a deliberate, stated trade-off: it makes every run reproducible on any machine with no external dependencies, at the cost of not measuring real I/O latency (see "What each metric does NOT measure" below).
- **`algogauge.toml` manifest** is the single source of truth for what suites exist and how they run — the runner, CLI, dashboard, and notebooks are all manifest-driven and suite-agnostic. Adding a benchmark means adding a manifest entry, not touching the runner or dashboard.
- **Committed compact history** (`history/<suite>.jsonl`), one line per benchmark per run, carries enough metadata (machine, trade-ngin/algogauge git SHA, timestamp) to make every number attributable and comparable over time. Raw artifacts (`benchmark.json`, `perf.data`, flamegraphs) stay local and gitignored — they're reproducible from the committed inputs, the summary is not.
- **A run can fail loudly.** Every new suite has a runtime sanity guard (`SkipWithError` in C++, a checksum-verification `RuntimeError` in the backtest harness) so a broken fixture can't silently report a fast "0 work done" number. A result is also marked `invalid` (kept, not hidden) when its coefficient of variation exceeds 15%.

## What each metric measures — and does not

### Tick-to-trade latency (`tick_to_trade` suite)
**Measures:** wall-clock time for `PortfolioManager::process_market_data()` (one new bar per symbol) → `get_recent_executions()`, for a real `TrendFollowingStrategy` after a 256-bar warmup, at 1/8/32/128-symbol universe sizes. This is real strategy decision code, not a stub.

**Does NOT measure:** network round-trip to a real broker, real database I/O, order-routing/exchange latency, or anything outside the engine's own decision path. Report this number as **"engine decision latency"**, never as "end-to-end tick-to-trade latency" or "time to fill" — those would require a real broker/exchange in the loop, which this suite deliberately does not have.

### Data-ingestion throughput (`ingestion_throughput` suite)
**Measures:** (A) `DataConversionUtils::arrow_table_to_bars()` over synthetic in-memory Arrow tables of 1k–1M rows; (B) `MarketDataBus::publish()` fan-out to 1/4/16 subscribers; (C) the same publish path under 1/4/16 concurrent `std::thread` publishers, exposing the bus's mutex contention.

**Does NOT measure:** reading from a real market-data feed, disk I/O, network deserialization, or a real subscriber doing real work in its callback (the benchmark callbacks just increment a counter). Report as **"in-process conversion/fan-out throughput on synthetic data"**, not "live feed ingestion rate."

### Backtest speedup (`backtest_speedup` suite)
**Measures:** wall-clock speedup and parallel efficiency of running 8 independent synthetic backtests (50 symbols × 10 years, by default) serially vs. across a process pool of 1/2/4/8/16 workers, using the same `PortfolioManager` decision path as the tick-to-trade suite. Every parallel result's checksum is verified against the serial baseline for the same seed — this is a correctness guard, not just a timing number.

**Does NOT measure — and this is the one that matters most:** multi-threading inside a single backtest. As of this writing, **trade-ngin's engine is single-threaded** — there is no `std::thread`, `std::async`, or OpenMP anywhere in `src/` or `apps/` (verified by direct search, not assumption). This suite measures speedup across *independent* backtests run in separate OS processes (parameter sweeps, walk-forward folds, Monte-Carlo seeds) — a real and useful number, but never phrase it as "the backtest engine got N× faster." If trade-ngin's engine gains internal parallelism later, that would be a *new* metric, not a change to this one.

`bt_bench_runner` (the driver binary) is built directly on `PortfolioManager` rather than `BacktestCoordinator`, deliberately reusing the exact strategy/portfolio wiring already used by `tick_to_trade_benchmarks.cpp` instead of introducing `BacktestCoordinator`'s `InstrumentRegistry`/contract-roll handling into a second, separately-maintained code path.

## Validity rules

- A record is `valid: true` unless its coefficient of variation exceeds 15% (`cv_pct > 15`), in which case it's stored with `valid: false` and an `invalid_reason` — visible in the dashboard (greyed out) and excluded from `latest_run()`/regression comparisons by default, never silently dropped.
- `algogauge compare` and the dashboard's Compare page flag a regression when a benchmark's **median** moves beyond the manifest's `regression_threshold_pct` (default 10%) between the latest and previous valid run.
- C++ suites assert real work happened (executions > 0, deliveries > 0) before reporting a timing number; the backtest harness asserts serial/parallel checksums match. A run that fails these guards exits non-zero instead of polluting `history/` with a misleadingly fast result.

## How to add a new system (e.g. `data-ngin`, `AlgoSys v2`)

1. Add it as a git submodule under `external/<name>` (same pattern as `external/trade-ngin`).
2. Write a benchmark suite against its real entry points, following the pattern in this ADR: mock/synthetic inputs, a runtime sanity guard, honest documentation of what is and isn't measured.
3. Add a `[[benchmark]]` entry to `algogauge.toml`. The runner, history store, compare tool, and dashboard need no changes — they're already suite-agnostic.
4. Add a notebook if the metric deserves its own deep-dive (optional; `01_run_all_benchmarks.ipynb` covers every manifest suite regardless).

## Consequences

**Positive:** three previously-unmeasured, frequently-asked-about numbers now have real, repeatable, machine-attributed answers. The roadmap items (manifest, schema-agnostic dashboard, regression detection) landed as a side effect of building this properly instead of as a one-off script. Extending to another repo is a manifest entry, not a rewrite.

**Negative / accepted trade-offs:**
- None of these numbers include real I/O (network, disk, live database, real broker). If someone needs *that* number, it needs a new, clearly-separately-named suite — extending these three to claim otherwise would be dishonest.
- `bt_bench_runner` bypasses `BacktestCoordinator`, so it doesn't exercise `InstrumentRegistry`/contract-roll logic. A future PR could add a second, `BacktestCoordinator`-based suite if that code path specifically needs its own performance number.
- The backtest-speedup suite is fairly expensive to run at its default size (50 symbols × 10 years × 8 jobs × up to 16 workers); the manifest entry documents this and the numbers are tunable via its `args`.

### Alternatives considered and rejected
- **Add real multi-threading inside trade-ngin's engine first, then benchmark it.** Rejected for this work: that's a change to the production trading engine, needs its own design/review/PR, and risks correctness bugs in live code — measuring "harness-level" parallelism first (this ADR's approach) is safe and still answers a real question about backtest throughput.
- **Measure from Python via the pybind wrapper.** Rejected for tick-to-trade specifically: Python-side call overhead (microseconds) would swamp the C++ decision latency being measured, and the wrapper PR was blocked/unmerged at the time this was built.

## Status

Accepted and implemented across PRs 1–6 on `AlgoGators/algogauge`:
1. Python package, manifest, history, compare, runner, notebooks 00/01
2. `tick_to_trade` suite + notebook 02
3. `ingestion_throughput` suite + notebook 03
4. `backtest_speedup` harness + notebook 04
5. Dashboard rewrite (Overview/Suites/Trends/Compare/Runs) + notebook 05
6. This ADR + docs

**Not yet done, tracked as follow-ups:** the C++ suites (2–4) have not yet been built or run — that needs the WSL2 toolchain installed via `scripts/setup_wsl.sh`, which requires a one-time `sudo` step only the machine's owner can run. Until that happens, `history/` has no committed runs yet for `tick_to_trade`, `ingestion_throughput`, or `backtest_speedup`. The first real run should be committed as its own small follow-up PR once the toolchain is in place, rather than fabricated here.
