add_executable(order_manager_benchmark
    order_manager_benchmark.cpp
)

target_link_libraries(order_manager_benchmark
    PRIVATE
        benchmark::benchmark
        trade_ngin
        # /home/inferna/code/AlgoGators/algogauge/build/bin/Release/libtrade_ngin.so
)
