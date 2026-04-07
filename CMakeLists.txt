cmake_minimum_required(VERSION 3.28)
project(algogauge VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# Dependencies
find_package(GTest REQUIRED)
find_package(benchmark REQUIRED)

# trade-ngin
# TODO necessary for trade-ngin, but should be changed in the future
set(NLopt_DIR "/usr/lib/x86_64-linux-gnu/cmake/nlopt_cxx")
find_package(NLopt REQUIRED)
add_subdirectory(external/trade-ngin)

# Benchmark files
add_subdirectory(benchmarks)

# Export compile commands
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_compile_options(-fno-omit-frame-pointer -g)
