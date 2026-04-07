#pragma once

#include <benchmark/benchmark.h>

#include "../mocks/mock_postgres_database.hpp"
#include "trade_ngin/core/logger.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/strategy/trend_following.hpp"

class TrendFollowingBenchmark : public benchmark::Fixture {
   public:
    void SetUp(const ::benchmark::State&) override {
        trade_ngin::StateManager::reset_instance();
        trade_ngin::Logger::reset_for_tests();

        // Initialize logger
        auto& logger = trade_ngin::Logger::instance();
        trade_ngin::LoggerConfig logger_config;
        logger_config.min_level = trade_ngin::LogLevel::DEBUG;
        logger_config.destination = trade_ngin::LogDestination::CONSOLE;
        logger_config.log_directory = "logs";
        logger_config.filename_prefix = "benchmark";
        logger.initialize(logger_config);

        // Initialize mock database
        db = std::make_shared<MockPostgresDatabase>();

        // Configs
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

        // Limits
        trade_ngin::RiskLimits limits;
        limits.max_leverage = 4.0;
        limits.max_drawdown = 0.25;
        limits.max_position_size = 100000;
        limits.max_notional_value = 1000000.0;

        strategy->update_risk_limits(limits);

        strategy->initialize();
    }

    void TearDown(const ::benchmark::State&) override {
        strategy->stop();
        strategy.reset();
        db.reset();
    }

   protected:
    std::shared_ptr<MockPostgresDatabase> db;

    trade_ngin::StrategyConfig strategy_config;
    trade_ngin::TrendFollowingConfig trend_config;

    std::unique_ptr<trade_ngin::TrendFollowingStrategy> strategy;
};
