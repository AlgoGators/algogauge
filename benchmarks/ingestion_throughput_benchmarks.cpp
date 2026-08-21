// Data-ingestion throughput: how many market-data messages/bars per second
// the pipeline can convert and fan out. See
// docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.2.
//
// Stage A -- conversion: DataConversionUtils::arrow_table_to_bars() over
// synthetic in-memory Arrow tables of increasing size.
// Stage B -- bus fan-out: MarketDataBus::publish() with a varying subscriber
// count (single publisher thread).
// Stage C -- contention: MarketDataBus::publish() called concurrently from
// multiple std::thread publishers against the mutex-guarded singleton, to
// expose lock contention under load.
//
// All synthetic, in-memory data. No socket or disk I/O anywhere in this file.

#include <benchmark/benchmark.h>

#include <atomic>
#include <chrono>
#include <string>
#include <thread>
#include <vector>

#include "fixtures/ingestion_fixture.hpp"

using namespace trade_ngin;

// ---------------------------------------------------------------------------
// Stage A: Arrow table -> vector<Bar>
// ---------------------------------------------------------------------------
BENCHMARK_DEFINE_F(IngestionBenchmark, ArrowToBars)
(benchmark::State& state) {
    const int64_t rows = state.range(0);
    auto table = make_table(rows);

    for (auto _ : state) {
        auto result = DataConversionUtils::arrow_table_to_bars(table);
        benchmark::DoNotOptimize(result);
        if (result.is_error()) {
            state.SkipWithError(("arrow_table_to_bars failed: " +
                                 std::string(result.error()->what()))
                                    .c_str());
            break;
        }
    }
    state.SetItemsProcessed(static_cast<int64_t>(state.iterations()) * rows);
}

// No ->ArgNames() on any registration below: algogauge/gbench.py splits a
// benchmark name on the first "/" and expects the param half to be a bare
// number (int(r.param) in the notebooks) -- ArgNames would produce
// "ArrowToBars/rows:1000" instead of "ArrowToBars/1000" and break that
// parsing. Keep in sync with tick_to_trade_benchmarks.cpp.
BENCHMARK_REGISTER_F(IngestionBenchmark, ArrowToBars)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMicrosecond);

// ---------------------------------------------------------------------------
// Stage B: MarketDataBus::publish() fan-out, single publisher thread
// ---------------------------------------------------------------------------
BENCHMARK_DEFINE_F(IngestionBenchmark, Publish)
(benchmark::State& state) {
    const int num_subscribers = static_cast<int>(state.range(0));
    auto& bus = MarketDataBus::instance();

    std::atomic<uint64_t> received{0};
    std::vector<std::string> ids;
    ids.reserve(num_subscribers);
    for (int i = 0; i < num_subscribers; ++i) {
        auto id = next_subscriber_id("ingestion_publish");
        SubscriberInfo info;
        info.id = id;
        info.event_types = {MarketDataEventType::BAR};
        info.callback = [&received](const MarketDataEvent&) {
            received.fetch_add(1, std::memory_order_relaxed);
        };
        bus.subscribe(info);
        ids.push_back(id);
    }

    MarketDataEvent event;
    event.type = MarketDataEventType::BAR;
    event.symbol = "SYM";
    event.timestamp = std::chrono::system_clock::now();
    event.numeric_fields = {{"close", 100.0}, {"volume", 100000.0}};

    for (auto _ : state) {
        bus.publish(event);
        benchmark::ClobberMemory();
    }

    for (const auto& id : ids) {
        bus.unsubscribe(id);
    }

    if (state.iterations() > 0 && received.load() == 0) {
        state.SkipWithError(
            "Publish delivered zero events to subscribers; fan-out is not being exercised");
    }
    state.counters["deliveries_per_publish"] =
        benchmark::Counter(static_cast<double>(received.load()), benchmark::Counter::kAvgIterations);
    state.SetItemsProcessed(state.iterations());
}

BENCHMARK_REGISTER_F(IngestionBenchmark, Publish)
    ->Arg(1)
    ->Arg(4)
    ->Arg(16)
    ->Unit(benchmark::kNanosecond);

// ---------------------------------------------------------------------------
// Stage C: concurrent publishers -- exposes mutex contention in the bus
// ---------------------------------------------------------------------------
BENCHMARK_DEFINE_F(IngestionBenchmark, PublishContended)
(benchmark::State& state) {
    const int num_threads = static_cast<int>(state.range(0));
    constexpr int kPublishesPerThread = 2000;

    auto& bus = MarketDataBus::instance();

    std::atomic<uint64_t> received{0};
    auto sub_id = next_subscriber_id("ingestion_contended");
    SubscriberInfo info;
    info.id = sub_id;
    info.event_types = {MarketDataEventType::BAR};
    info.callback = [&received](const MarketDataEvent&) {
        received.fetch_add(1, std::memory_order_relaxed);
    };
    bus.subscribe(info);

    MarketDataEvent event;
    event.type = MarketDataEventType::BAR;
    event.symbol = "SYM";
    event.timestamp = std::chrono::system_clock::now();

    for (auto _ : state) {
        std::vector<std::thread> workers;
        workers.reserve(num_threads);
        for (int t = 0; t < num_threads; ++t) {
            workers.emplace_back([&bus, &event]() {
                for (int i = 0; i < kPublishesPerThread; ++i) {
                    bus.publish(event);
                }
            });
        }
        for (auto& worker : workers) {
            worker.join();
        }
    }

    bus.unsubscribe(sub_id);

    if (received.load() == 0) {
        state.SkipWithError("PublishContended delivered zero events; the bus is not being exercised");
    }
    state.SetItemsProcessed(static_cast<int64_t>(state.iterations()) * num_threads * kPublishesPerThread);
    state.counters["deliveries"] = benchmark::Counter(static_cast<double>(received.load()));
}

BENCHMARK_REGISTER_F(IngestionBenchmark, PublishContended)
    ->Arg(1)
    ->Arg(4)
    ->Arg(16)
    ->Unit(benchmark::kMicrosecond)
    ->UseRealTime();

BENCHMARK_MAIN();
