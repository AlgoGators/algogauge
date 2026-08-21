// Tick-to-trade latency: how long from a new bar arriving to an order/execution
// being emitted by trade-ngin's decision path. See
// docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.1.
//
// What this measures: PortfolioManager::process_market_data() for one new bar
// per symbol, then PortfolioManager::get_recent_executions(). In-process, mock
// database, mock broker (no network I/O). This is engine decision latency, not
// wire latency to a real broker.

#include <benchmark/benchmark.h>

#include <string>
#include <unordered_map>
#include <vector>

#include "fixtures/tick_to_trade_fixture.hpp"
#include "utils/test_data_generator.hpp"

using namespace trade_ngin;

namespace {
constexpr int kWarmupBars = 256;

std::vector<std::string> make_symbols(int n) {
    std::vector<std::string> symbols;
    symbols.reserve(n);
    for (int i = 0; i < n; ++i) {
        symbols.push_back("SYM" + std::to_string(i));
    }
    return symbols;
}
}  // namespace

BENCHMARK_DEFINE_F(TickToTradeBenchmark, ProcessTick)
(benchmark::State& state) {
    const int num_symbols = static_cast<int>(state.range(0));
    const auto symbols = make_symbols(num_symbols);

    auto portfolio = build_portfolio(symbols);

    // Generate kWarmupBars + 1 historical bars per symbol: the extra bar is
    // the "new tick" that gets timed.
    std::unordered_map<std::string, std::vector<Bar>> series;
    series.reserve(symbols.size());
    for (const auto& symbol : symbols) {
        series[symbol] = bench_utils::create_test_data(symbol, kWarmupBars + 1);
    }

    // Warm up so EMAs are populated and the strategy is actually producing
    // target position changes, replaying one day (all symbols) at a time --
    // this mirrors how BacktestCoordinator::process_day() feeds bars.
    for (int day = 0; day < kWarmupBars; ++day) {
        std::vector<Bar> day_bars;
        day_bars.reserve(symbols.size());
        for (const auto& symbol : symbols) {
            day_bars.push_back(series[symbol][day]);
        }
        portfolio->process_market_data(day_bars, /*skip_execution_generation=*/true);
    }
    portfolio->clear_all_executions();

    std::vector<Bar> new_bars;
    new_bars.reserve(symbols.size());
    for (const auto& symbol : symbols) {
        new_bars.push_back(series[symbol][kWarmupBars]);
    }

    std::size_t total_executions = 0;
    for (auto _ : state) {
        portfolio->process_market_data(new_bars);
        auto executions = portfolio->get_recent_executions();
        total_executions += executions.size();
        benchmark::DoNotOptimize(executions);
        portfolio->clear_execution_history();
        benchmark::ClobberMemory();
    }

    // Sanity guard: a "0 microseconds, 0 executions" result is a broken
    // benchmark, not a fast one -- fail loudly instead of reporting silently
    // wrong numbers.
    if (state.iterations() > 0 && total_executions == 0) {
        state.SkipWithError(
            "TickToTradeBenchmark produced zero executions across all iterations; "
            "the fixture is not exercising the decision path, results are invalid");
    }
    state.counters["executions_per_tick"] =
        benchmark::Counter(static_cast<double>(total_executions), benchmark::Counter::kAvgIterations);
}

BENCHMARK_REGISTER_F(TickToTradeBenchmark, ProcessTick)
    ->Arg(1)
    ->Arg(8)
    ->Arg(32)
    ->Arg(128)
    ->ArgNames({"symbols"})
    ->Unit(benchmark::kMicrosecond);

BENCHMARK_MAIN();
