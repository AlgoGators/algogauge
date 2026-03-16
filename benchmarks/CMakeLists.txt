# Function for adding a benchmark target
function(add_benchmark NAME)
    add_executable(${NAME} ${ARGN})

    target_link_libraries(${NAME}
        PRIVATE
            trade_ngin
            benchmark::benchmark
            benchmark::benchmark_main
    )
endfunction()

add_benchmark(base_strategy_benchmarks
    base_strategy_benchmarks.cpp
)

add_benchmark(trend_following_benchmarks
    trend_following_benchmarks.cpp
)
