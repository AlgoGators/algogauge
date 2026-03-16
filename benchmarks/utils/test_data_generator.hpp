#pragma once

#include <cmath>
#include <cstdlib>
#include <vector>

#include "trade_ngin/core/types.hpp"

namespace bench_utils {

inline std::vector<trade_ngin::Bar> create_test_data(const std::string& symbol,
                                                     int num_bars,
                                                     double start_price = 100.0,
                                                     double volatility = 0.2) {
    std::vector<trade_ngin::Bar> data;

    auto now = std::chrono::system_clock::now();
    double price = start_price;

    srand(42);

    data.reserve(num_bars);

    for (int i = 0; i < num_bars; ++i) {
        trade_ngin::Bar bar;

        bar.symbol = symbol;
        bar.timestamp = now - std::chrono::hours(24 * (num_bars - i));

        double trend = std::sin(i * 0.1) * 0.005;
        double random =
            (static_cast<double>(rand()) / RAND_MAX - 0.5) * volatility;

        price = std::max(0.1 * start_price, price * (1.0 + trend + random));

        bar.open = price;
        bar.close = price * (1.0 + random);

        double open = bar.open.as_double();
        double close = bar.close.as_double();

        bar.high = std::max(open, close) * 1.01;
        bar.low = std::min(open, close) * 0.99;

        bar.volume = 100000 + rand() % 50000;

        data.push_back(bar);
    }

    return data;
}

}  // namespace bench_utils
