## Unreleased

### Feat

- `algogauge` Python package: manifest (`algogauge.toml`), runner, committed `history/`, `compare` regression check, CLI
- Notebooks 00 (WSL setup) and 01 (run all)

### Refactor

- `benchmark_pipeline.py` is now a shim over `algogauge.runner`; perf permission failure warns and skips instead of aborting

## 0.2.0 (2026-04-07)

### Feat

- make dasboard orange
- benchmarks for strategy

### Refactor

- standardize strategy benchmarks
- convert pipeline script to python
- using git submodules
