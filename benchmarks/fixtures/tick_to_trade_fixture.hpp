#pragma once

#include <benchmark/benchmark.h>

#include <memory>
#include <string>
#include <vector>

#include "../mocks/mock_postgres_database.hpp"
#include "trade_ngin/core/logger.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/portfolio/portfolio_manager.hpp"
#include "trade_ngin/strategy/trend_following.hpp"

// Fixture for the tick-to-trade latency suite: a real PortfolioManager wrapping
// a real TrendFollowingStrategy against a MockPostgresDatabase (no network, no
// broker, no real DB). See docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md
// section 3.1 for what this does and does not measure.
class TickToTradeBenchmark : public benchmark::Fixture {
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

    // Builds a PortfolioManager with one TrendFollowingStrategy sized for the
    // given symbol universe. The strategy's own MockPostgresDatabase is kept
    // alive by the strategy's internal shared_ptr member.
    std::shared_ptr<trade_ngin::PortfolioManager> build_portfolio(
        const std::vector<std::string>& symbols) {
        auto db = std::make_shared<MockPostgresDatabase>();

        trade_ngin::StrategyConfig strategy_config;
        strategy_config.capital_allocation = 1000000.0;
        strategy_config.max_leverage = 4.0;
        strategy_config.asset_classes = {trade_ngin::AssetClass::FUTURES};
        strategy_config.frequencies = {trade_ngin::DataFrequency::DAILY};

        trade_ngin::TrendFollowingConfig trend_config;
        trend_config.weight = 1.0;
        trend_config.risk_target = 0.2;
        trend_config.idm = 2.5;
        trend_config.use_position_buffering = true;
        trend_config.ema_windows = {{2, 8}, {4, 16}, {8, 32}, {16, 64}, {32, 128}};

        auto strategy = std::make_shared<trade_ngin::TrendFollowingStrategy>(
            "tick_to_trade_strategy", strategy_config, trend_config, db);

        trade_ngin::RiskLimits limits;
        limits.max_leverage = 4.0;
        limits.max_drawdown = 0.25;
        limits.max_position_size = 100000;
        limits.max_notional_value = 1000000.0;
        strategy->update_risk_limits(limits);
        strategy->initialize();

        trade_ngin::PortfolioConfig portfolio_config;
        portfolio_config.total_capital = trade_ngin::Decimal(1000000.0);
        portfolio_config.use_optimization = false;
        portfolio_config.use_risk_management = false;

        auto portfolio = std::make_shared<trade_ngin::PortfolioManager>(
            portfolio_config, "tick_to_trade_portfolio");
        portfolio->add_strategy(strategy, /*initial_allocation=*/1.0,
                                /*use_optimization=*/false,
                                /*use_risk_management=*/false);

        (void)symbols;  // symbols are used by the caller to build per-symbol bars
        return portfolio;
    }
};
