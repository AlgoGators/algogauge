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

add_benchmark(tick_to_trade_benchmarks
    tick_to_trade_benchmarks.cpp
)
