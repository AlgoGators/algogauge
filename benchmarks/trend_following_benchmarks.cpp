#include <benchmark/benchmark.h>

#include "fixtures/trend_following_fixture.hpp"

using namespace trade_ngin;

BENCHMARK_F(TrendFollowingBenchmark, OnDataProcessing)
(benchmark::State& state) {
    for (auto _ : state) {
        strategy->on_data(bars);
        benchmark::DoNotOptimize(strategy);
    }
}

BENCHMARK_DEFINE_F(TrendFollowingBenchmark, OnDataScaling)
(benchmark::State& state) {
    auto data = bench_utils::create_test_data("ES", state.range(0));

    for (auto _ : state) {
        strategy->on_data(data);
        benchmark::ClobberMemory();
    }
}

BENCHMARK_REGISTER_F(TrendFollowingBenchmark, OnDataScaling)->Range(64, 8192);

BENCHMARK_MAIN();
