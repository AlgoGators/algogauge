// Standalone driver for the backtest-speedup Tier-1 metric. See
// docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.3.
//
// Runs one full multi-year, multi-symbol replay through the same decision
// path as tick_to_trade_benchmarks.cpp -- PortfolioManager wrapping a real
// TrendFollowingStrategy -- and prints a single line of JSON with wall-clock
// time and a checksum of the result. python/algogauge/backtest_parallel.py
// runs many copies of this binary (different seeds) serially, then across a
// process pool, to measure speedup on independent backtests.
//
// Deliberately built directly on PortfolioManager::process_market_data()
// rather than BacktestCoordinator: this reuses the same strategy/portfolio
// wiring already used (and documented) by tick_to_trade_benchmarks.cpp,
// avoiding a second, less-exercised code path (BacktestCoordinator's
// InstrumentRegistry/contract-roll handling) for this harness binary.
//
// Not a Google Benchmark binary -- plain main(), no benchmark:: dependency.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

#include "mocks/mock_postgres_database.hpp"
#include "trade_ngin/core/logger.hpp"
#include "trade_ngin/core/state_manager.hpp"
#include "trade_ngin/portfolio/portfolio_manager.hpp"
#include "trade_ngin/strategy/trend_following.hpp"

namespace {

using namespace trade_ngin;

// Deterministic per-symbol synthetic daily series, seeded explicitly (does
// not use bench_utils::create_test_data(), which hard-codes srand(42) and
// would make every "different seed" job identical).
std::vector<Bar> generate_series(const std::string& symbol, int num_days, unsigned seed) {
    std::mt19937 rng(seed);
    std::normal_distribution<double> noise(0.0, 0.01);

    std::vector<Bar> bars;
    bars.reserve(num_days);

    auto now = std::chrono::system_clock::now();
    double price = 100.0;

    for (int i = 0; i < num_days; ++i) {
        double trend = std::sin(i * 0.05) * 0.004;
        price = std::max(1.0, price * (1.0 + trend + noise(rng)));

        Bar bar;
        bar.symbol = symbol;
        bar.timestamp = now - std::chrono::hours(24 * (num_days - i));
        bar.open = price;
        bar.close = price * (1.0 + noise(rng) * 0.1);

        double open = bar.open.as_double();
        double close = bar.close.as_double();
        bar.high = std::max(open, close) * 1.01;
        bar.low = std::min(open, close) * 0.99;
        bar.volume = 100000.0 + static_cast<double>(i % 5000);

        bars.push_back(bar);
    }
    return bars;
}

struct RunResult {
    double total_return{0.0};
    int total_executions{0};
    int days{0};
};

RunResult run_backtest(int num_symbols, int num_days, unsigned seed) {
    StateManager::reset_instance();
    Logger::reset_for_tests();

    auto& logger = Logger::instance();
    LoggerConfig logger_config;
    logger_config.min_level = LogLevel::DEBUG;
    logger_config.destination = LogDestination::CONSOLE;
    logger_config.log_directory = "logs";
    logger_config.filename_prefix = "bt_bench_runner";
    logger.initialize(logger_config);

    std::vector<std::string> symbols;
    symbols.reserve(num_symbols);
    for (int i = 0; i < num_symbols; ++i) {
        symbols.push_back("SYM" + std::to_string(i));
    }

    std::unordered_map<std::string, std::vector<Bar>> series;
    series.reserve(symbols.size());
    for (int s = 0; s < num_symbols; ++s) {
        series[symbols[s]] = generate_series(symbols[s], num_days, seed + static_cast<unsigned>(s));
    }

    auto db = std::make_shared<MockPostgresDatabase>();

    StrategyConfig strategy_config;
    strategy_config.capital_allocation = 1000000.0;
    strategy_config.max_leverage = 4.0;
    strategy_config.asset_classes = {AssetClass::FUTURES};
    strategy_config.frequencies = {DataFrequency::DAILY};

    TrendFollowingConfig trend_config;
    trend_config.weight = 1.0;
    trend_config.risk_target = 0.2;
    trend_config.idm = 2.5;
    trend_config.use_position_buffering = true;
    trend_config.ema_windows = {{2, 8}, {4, 16}, {8, 32}, {16, 64}, {32, 128}};

    auto strategy = std::make_shared<TrendFollowingStrategy>("bt_bench_strategy", strategy_config,
                                                             trend_config, db);

    RiskLimits limits;
    limits.max_leverage = 4.0;
    limits.max_drawdown = 0.25;
    limits.max_position_size = 100000;
    limits.max_notional_value = 1000000.0;
    strategy->update_risk_limits(limits);
    strategy->initialize();

    PortfolioConfig portfolio_config;
    portfolio_config.total_capital = Decimal(1000000.0);
    portfolio_config.use_optimization = false;
    portfolio_config.use_risk_management = false;

    auto portfolio = std::make_shared<PortfolioManager>(portfolio_config, "bt_bench_portfolio");
    portfolio->add_strategy(strategy, /*initial_allocation=*/1.0, /*use_optimization=*/false,
                            /*use_risk_management=*/false);

    int total_executions = 0;
    for (int day = 0; day < num_days; ++day) {
        std::vector<Bar> day_bars;
        day_bars.reserve(symbols.size());
        for (const auto& symbol : symbols) {
            day_bars.push_back(series[symbol][day]);
        }
        portfolio->process_market_data(day_bars);
        total_executions += static_cast<int>(portfolio->get_recent_executions().size());
        portfolio->clear_execution_history();
    }

    double portfolio_value = portfolio->get_portfolio_value({});

    RunResult result;
    result.total_return = (portfolio_value - 1000000.0) / 1000000.0;
    result.total_executions = total_executions;
    result.days = num_days;
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    int num_symbols = 50;
    int num_years = 10;
    unsigned seed = 42;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto next = [&](const char* flag) -> std::string {
            if (i + 1 >= argc) {
                std::cerr << "missing value for " << flag << "\n";
                std::exit(2);
            }
            return argv[++i];
        };
        if (arg == "--symbols") {
            num_symbols = std::stoi(next("--symbols"));
        } else if (arg == "--years") {
            num_years = std::stoi(next("--years"));
        } else if (arg == "--seed") {
            seed = static_cast<unsigned>(std::stoul(next("--seed")));
        } else {
            std::cerr << "unknown argument: " << arg << "\n";
            std::exit(2);
        }
    }

    if (num_symbols <= 0 || num_years <= 0) {
        std::cerr << "--symbols and --years must be positive\n";
        return 2;
    }

    const int num_days = num_years * 252;  // trading days/year, not calendar days

    auto start = std::chrono::steady_clock::now();
    RunResult result = run_backtest(num_symbols, num_days, seed);
    auto end = std::chrono::steady_clock::now();
    double wall_seconds = std::chrono::duration<double>(end - start).count();

    // Checksum lets the Python harness confirm serial and parallel execution
    // produced an identical result for the same (symbols, years, seed) --
    // a correctness guard, not a security hash.
    char checksum_buf[64];
    std::snprintf(checksum_buf, sizeof(checksum_buf), "%.6f|%d|%d", result.total_return,
                 result.total_executions, result.days);

    std::printf(
        "{\"wall_seconds\": %.6f, \"symbols\": %d, \"years\": %d, \"seed\": %u, "
        "\"total_return\": %.6f, \"total_executions\": %d, \"checksum\": \"%s\"}\n",
        wall_seconds, num_symbols, num_years, seed, result.total_return, result.total_executions,
        checksum_buf);

    return 0;
}
