#pragma once

#include <benchmark/benchmark.h>

#include "../mocks/mock_postgres_database.hpp"
#include "../utils/test_data_generator.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/strategy/trend_following.hpp"

class TrendFollowingBenchmark : public benchmark::Fixture {
   public:
    void SetUp(const ::benchmark::State&) override {
        trade_ngin::StateManager::reset_instance();

        db = std::make_shared<MockPostgresDatabase>();

        strategy_config.capital_allocation = 1000000.0;
        strategy_config.max_leverage = 4.0;
        strategy_config.asset_classes = {trade_ngin::AssetClass::FUTURES};
        strategy_config.frequencies = {trade_ngin::DataFrequency::DAILY};

        trend_config.weight = 1.0 / 30.0;
        trend_config.risk_target = 0.2;
        trend_config.idm = 2.5;
        trend_config.use_position_buffering = true;

        trend_config.ema_windows = {
            {2, 8}, {4, 16}, {8, 32}, {16, 64}, {32, 128}};

        strategy = std::make_unique<trade_ngin::TrendFollowingStrategy>(
            "trend_benchmark", strategy_config, trend_config, db);

        strategy->initialize();

        bars = bench_utils::create_test_data("ES", 500);
    }

    void TearDown(const ::benchmark::State&) override {
        strategy.reset();
        db.reset();
    }

   protected:
    std::vector<trade_ngin::Bar> bars;

    std::shared_ptr<MockPostgresDatabase> db;

    trade_ngin::StrategyConfig strategy_config;
    trade_ngin::TrendFollowingConfig trend_config;

    std::unique_ptr<trade_ngin::TrendFollowingStrategy> strategy;
};
