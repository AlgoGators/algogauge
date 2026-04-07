#include <benchmark/benchmark.h>

#include "fixtures/base_strategy_fixture.hpp"
#include "utils/test_data_generator.hpp"

using namespace trade_ngin;

BENCHMARK_F(BaseStrategyBenchmark, PauseStrategy)
(benchmark::State& state) {
    for (auto _ : state) {
        strategy->pause();

        benchmark::DoNotOptimize(strategy);

        strategy->resume();
    }
}

BENCHMARK_DEFINE_F(BaseStrategyBenchmark, OnDataScaling)
(benchmark::State& state) {
    auto data = bench_utils::create_test_data("ES", state.range(0));

    for (auto _ : state) {
        strategy->on_data(data);
        benchmark::ClobberMemory();
    }
}

BENCHMARK_REGISTER_F(BaseStrategyBenchmark, OnDataScaling)
    ->RangeMultiplier(2)
    ->Range(64, 8192);

BENCHMARK_MAIN();
