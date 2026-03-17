#!/usr/bin/env bash

set -e

BIN=$1
NAME=$(basename "$BIN")

if [ -z "$BIN" ]; then
    echo "usage: run_benchmark_pipeline.sh <benchmark_binary>"
    exit 1
fi

# Ensure sufficient permissions for perf
if ! cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null | grep -q -E '0'; then
    echo "Error: perf is not properly configured. Please run 'sudo sysctl -w kernel.perf_event_paranoid=1' or 'sudo sysctl -w kernel.perf_event_paranoid=0' to allow perf to record user-space events."
    exit 1
fi
if ! cat /proc/sys/kernel/kptr_restrict 2>/dev/null | grep -q -E '0'; then
    echo "Error: perf is not properly configured. Please run 'sudo sysctl -w kernel.perf_event_paranoid=1' or 'sudo sysctl -w kernel.perf_event_paranoid=0' to allow perf to record user-space events."
    exit 1
fi

RUN_ID=$(date +"%Y%m%d_%H%M%S")

RESULT_DIR=results/$NAME/$RUN_ID

mkdir -p $RESULT_DIR

echo "Running benchmark: $NAME"
echo "Results directory: $RESULT_DIR"

# Run Google Benchmark
./$BIN \
    --benchmark_out=$RESULT_DIR/benchmark.json \
    --benchmark_out_format=json \
    --benchmark_min_time=5s \
    --benchmark_repetitions=30 \
    --benchmark_report_aggregates_only=true \
    | tee $RESULT_DIR/benchmark.txt

# perf recording
perf record \
    -F 999 \
    -g \
    -o $RESULT_DIR/perf.data \
    -- ./$BIN --benchmark_min_time=5s

# Convert to stack trace
perf script -i $RESULT_DIR/perf.data \
    > $RESULT_DIR/perf.script

# Generate flamegraph
tools/FlameGraph/stackcollapse-perf.pl \
    $RESULT_DIR/perf.script \
    > $RESULT_DIR/perf.folded

tools/FlameGraph/flamegraph.pl \
    $RESULT_DIR/perf.folded \
    > $RESULT_DIR/flamegraph.svg

# TODO python analysis of benchmark.json to extract more insights

echo ""
echo "Benchmark complete"
echo "Results stored in:"
echo "$RESULT_DIR"
