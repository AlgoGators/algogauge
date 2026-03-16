#pragma once

#include <memory>
#include <unordered_map>
#include <vector>

#include "trade_ngin/data/postgres_database.hpp"

class MockPostgresDatabase : public trade_ngin::PostgresDatabase {
   public:
    MockPostgresDatabase() : PostgresDatabase("mock://benchmarkdb") {}

    trade_ngin::Result<void> connect() override {
        connected = true;
        return {};
    }

    void disconnect() override { connected = false; }

    bool is_connected() const override { return connected; }

    trade_ngin::Result<std::shared_ptr<arrow::Table>> get_market_data(
        const std::vector<std::string>&, const trade_ngin::Timestamp&,
        const trade_ngin::Timestamp&, trade_ngin::AssetClass,
        trade_ngin::DataFrequency = trade_ngin::DataFrequency::DAILY,
        const std::string& = "ohlcv") override {
        return nullptr;
    }

    trade_ngin::Result<void> store_executions(
        const std::vector<trade_ngin::ExecutionReport>& executions,
        const std::string&, const std::string&, const std::string&,
        const std::string&) override {
        executions_stored = executions;
        return {};
    }

    trade_ngin::Result<void> store_positions(
        const std::vector<trade_ngin::Position>& positions, const std::string&,
        const std::string&, const std::string&, const std::string&) override {
        positions_stored = positions;
        return {};
    }

    trade_ngin::Result<void> store_signals(
        const std::unordered_map<std::string, double>& signals,
        const std::string&, const std::string&, const std::string&,
        const trade_ngin::Timestamp&, const std::string&) override {
        signals_stored = signals;
        return {};
    }

    trade_ngin::Result<std::vector<std::string>> get_symbols(
        trade_ngin::AssetClass,
        trade_ngin::DataFrequency = trade_ngin::DataFrequency::DAILY,
        const std::string& = "ohlcv") override {
        return std::vector<std::string>{};
    }

    trade_ngin::Result<std::shared_ptr<arrow::Table>> execute_query(
        const std::string&) override {
        return nullptr;
    }

    bool connected{false};

    std::vector<trade_ngin::ExecutionReport> executions_stored;
    std::vector<trade_ngin::Position> positions_stored;
    std::unordered_map<std::string, double> signals_stored;
};
