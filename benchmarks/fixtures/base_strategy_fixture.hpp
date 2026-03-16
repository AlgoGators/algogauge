#pragma once

#include <benchmark/benchmark.h>

#include "../mocks/mock_postgres_database.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/strategy/base_strategy.hpp"

class BaseStrategyBenchmark : public benchmark::Fixture {
   public:
    void SetUp(const ::benchmark::State&) override {
        trade_ngin::StateManager::reset_instance();

        db = std::make_shared<MockPostgresDatabase>();

        trade_ngin::StrategyConfig config;
        config.capital_allocation = 1000000.0;
        config.max_leverage = 4.0;

        strategy = std::make_unique<trade_ngin::BaseStrategy>(
            "benchmark_strategy", config, db);

        strategy->initialize();

        trade_ngin::RiskLimits limits;
        limits.max_leverage = 4.0;
        limits.max_drawdown = 0.25;
        limits.max_position_size = 100000;
        limits.max_notional_value = 1000000.0;

        strategy->update_risk_limits(limits);

        strategy->start();
    }

    void TearDown(const ::benchmark::State&) override {
        strategy->stop();
        strategy.reset();
        db.reset();
    }

   protected:
    std::shared_ptr<MockPostgresDatabase> db;
    std::unique_ptr<trade_ngin::BaseStrategy> strategy;
};
