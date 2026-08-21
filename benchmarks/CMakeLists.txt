# Function for adding a benchmark target
function(add_benchmark NAME)
    add_executable(${NAME} ${ARGN})

    target_link_libraries(${NAME}
        PRIVATE
            trade_ngin
            benchmark::benchmark
    )

    target_compile_options(${NAME}
        PRIVATE
        -O3
        -g
        -fno-omit-frame-pointer
        -march=native
        -DNDEBUG
    )
endfunction()

add_benchmark(base_strategy_benchmarks
    base_strategy_benchmarks.cpp
)

add_benchmark(trend_following_benchmarks
    trend_following_benchmarks.cpp
)

# Plain driver for the backtest-speedup harness -- not a Google Benchmark
# binary, invoked directly by python/algogauge/backtest_parallel.py.
add_executable(bt_bench_runner bt_bench_runner.cpp)
target_link_libraries(bt_bench_runner PRIVATE trade_ngin)
target_include_directories(bt_bench_runner PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(bt_bench_runner
    PRIVATE
    -O3
    -g
    -fno-omit-frame-pointer
    -march=native
    -DNDEBUG
)
