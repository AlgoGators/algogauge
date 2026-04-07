# Prerequisites

## System dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| CMake ≥ 3.28 | Build system | `apt install cmake` |
| C++20 compiler (GCC/Clang) | Compile benchmarks | `apt install g++` |
| Google Benchmark | Micro-benchmark library | `apt install libbenchmark-dev` |
| Google Test | Unit test framework (transitive dep) | `apt install libgtest-dev` |
| NLopt | Optimization library (trade-ngin dep) | `apt install libnlopt-cxx-dev` |
| `perf` | CPU profiling | `apt install linux-perf` |
| Python ≥ 3.12 | Pipeline script and dashboard | [python.org](https://python.org) |
| [uv](https://docs.astral.sh/uv/) | Python package manager | `pip install uv` |

## Linux kernel permissions for `perf`

The benchmark pipeline requires relaxed kernel security settings. Run once per boot (or make them permanent in `/etc/sysctl.conf`):

```bash
sudo sysctl -w kernel.perf_event_paranoid=0
sudo sysctl -w kernel.kptr_restrict=0
```

`perf_event_paranoid` must be `0` (not just `≤ 1`) because the pipeline uses call-graph recording (`-g`). `kptr_restrict=0` allows `perf` to resolve kernel symbols in the flamegraph.
