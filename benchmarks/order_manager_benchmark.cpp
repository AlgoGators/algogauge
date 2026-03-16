#include <benchmark/benchmark.h>

#include "trade_ngin/order/order_manager.hpp"

using namespace trade_ngin;

static Order create_test_order() {
    Order order;
    order.symbol = "AAPL";
    order.quantity = Decimal(100);
    order.price = Decimal(150.0);
    order.side = Side::BUY;
    order.type = OrderType::LIMIT;
    return order;
}

static void BM_SubmitOrder(benchmark::State& state) {
    OrderManagerConfig config;
    OrderManager manager(config);
    manager.initialize();

    Order order = create_test_order();

    for (auto _ : state) {
        auto result = manager.submit_order(order, "strategy_1");
        benchmark::DoNotOptimize(result);
    }
}

static void BM_SubmitOrderBatch(benchmark::State& state) {
    OrderManagerConfig config;
    OrderManager manager(config);
    manager.initialize();

    Order order = create_test_order();

    for (auto _ : state) {
        for (int i = 0; i < 100; ++i) {
            auto result = manager.submit_order(order, "strategy_1");
            benchmark::DoNotOptimize(result);
        }
    }
}

BENCHMARK(BM_SubmitOrder)->Threads(1)->Iterations(10000);
BENCHMARK(BM_SubmitOrderBatch)->Threads(1)->Iterations(100);

BENCHMARK_MAIN();
