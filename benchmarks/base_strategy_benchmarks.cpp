#include <benchmark/benchmark.h>

#include "fixtures/base_strategy_fixture.hpp"

using namespace trade_ngin;

BENCHMARK_F(BaseStrategyBenchmark, PauseStrategy)
(benchmark::State& state) {
    for (auto _ : state) {
        strategy->pause();

        benchmark::DoNotOptimize(strategy);

        strategy->resume();
    }
}

BENCHMARK_F(BaseStrategyBenchmark, ProcessExecution)
(benchmark::State& state) {
    ExecutionReport report;

    report.symbol = "ES";
    report.side = Side::BUY;
    report.filled_quantity = 10;
    report.fill_price = 5000;

    for (auto _ : state) {
        strategy->on_execution(report);

        benchmark::ClobberMemory();
    }
}

BENCHMARK_MAIN();
