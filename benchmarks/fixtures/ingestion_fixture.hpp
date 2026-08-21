#pragma once

#include <arrow/api.h>
#include <benchmark/benchmark.h>

#include <atomic>
#include <memory>
#include <string>

#include "trade_ngin/core/logger.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/data/conversion_utils.hpp"
#include "trade_ngin/data/market_data_bus.hpp"

// Fixture for the data-ingestion throughput suite. See
// docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.2.
// Stage A benchmarks DataConversionUtils::arrow_table_to_bars() over synthetic
// in-memory Arrow tables. Stage B/C benchmark MarketDataBus::publish() fan-out,
// including under concurrent publishers to expose the bus's internal mutex
// contention. No socket or disk I/O anywhere in this suite.
class IngestionBenchmark : public benchmark::Fixture {
   public:
    void SetUp(const ::benchmark::State&) override {
        trade_ngin::StateManager::reset_instance();
        trade_ngin::Logger::reset_for_tests();

        auto& logger = trade_ngin::Logger::instance();
        trade_ngin::LoggerConfig logger_config;
        logger_config.min_level = trade_ngin::LogLevel::DEBUG;
        logger_config.destination = trade_ngin::LogDestination::CONSOLE;
        logger_config.log_directory = "logs";
        logger_config.filename_prefix = "benchmark";
        logger.initialize(logger_config);
    }

    void TearDown(const ::benchmark::State&) override {}

    // Builds a synthetic OHLCV Arrow table with the exact schema
    // DataConversionUtils::arrow_table_to_bars() requires: time, symbol,
    // open, high, low, close, volume. Deterministic, no I/O.
    static std::shared_ptr<arrow::Table> make_table(int64_t rows) {
        arrow::TimestampBuilder time_builder(arrow::timestamp(arrow::TimeUnit::SECOND),
                                             arrow::default_memory_pool());
        arrow::StringBuilder symbol_builder;
        arrow::DoubleBuilder open_builder;
        arrow::DoubleBuilder high_builder;
        arrow::DoubleBuilder low_builder;
        arrow::DoubleBuilder close_builder;
        arrow::DoubleBuilder volume_builder;

        double price = 100.0;
        constexpr int64_t kBaseTimestampSeconds = 1700000000;
        for (int64_t i = 0; i < rows; ++i) {
            price *= 1.0 + (((i % 7) - 3) * 0.001);
            (void)time_builder.Append(kBaseTimestampSeconds + i * 86400);
            (void)symbol_builder.Append("SYM");
            (void)open_builder.Append(price);
            (void)high_builder.Append(price * 1.01);
            (void)low_builder.Append(price * 0.99);
            (void)close_builder.Append(price * 1.001);
            (void)volume_builder.Append(100000.0 + static_cast<double>(i % 5000));
        }

        std::shared_ptr<arrow::Array> time_array;
        std::shared_ptr<arrow::Array> symbol_array;
        std::shared_ptr<arrow::Array> open_array;
        std::shared_ptr<arrow::Array> high_array;
        std::shared_ptr<arrow::Array> low_array;
        std::shared_ptr<arrow::Array> close_array;
        std::shared_ptr<arrow::Array> volume_array;
        (void)time_builder.Finish(&time_array);
        (void)symbol_builder.Finish(&symbol_array);
        (void)open_builder.Finish(&open_array);
        (void)high_builder.Finish(&high_array);
        (void)low_builder.Finish(&low_array);
        (void)close_builder.Finish(&close_array);
        (void)volume_builder.Finish(&volume_array);

        auto schema = arrow::schema({
            arrow::field("time", arrow::timestamp(arrow::TimeUnit::SECOND)),
            arrow::field("symbol", arrow::utf8()),
            arrow::field("open", arrow::float64()),
            arrow::field("high", arrow::float64()),
            arrow::field("low", arrow::float64()),
            arrow::field("close", arrow::float64()),
            arrow::field("volume", arrow::float64()),
        });

        return arrow::Table::Make(schema, {time_array, symbol_array, open_array, high_array,
                                           low_array, close_array, volume_array});
    }

    // Monotonic counter so successive benchmark variants (which all talk to
    // the same process-wide MarketDataBus singleton) never collide on
    // subscriber id, even though each variant subscribes and unsubscribes
    // around its own timing loop.
    static std::atomic<uint64_t> subscriber_seq;

    static std::string next_subscriber_id(const std::string& prefix) {
        return prefix + "_" + std::to_string(subscriber_seq.fetch_add(1));
    }
};

inline std::atomic<uint64_t> IngestionBenchmark::subscriber_seq{0};
