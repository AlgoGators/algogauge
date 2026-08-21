## Unreleased

### Feat

- `algogauge` Python package: manifest (`algogauge.toml`), runner, committed `history/`, `compare` regression check, CLI
- Three Tier-1 performance suites: `tick_to_trade`, `ingestion_throughput`, `backtest_speedup` (see ADR 0001)
- Dashboard rewrite: schema-agnostic, multi-suite, multi-run (Overview / Suites / Trends / Compare / Runs pages); `algogauge dashboard` CLI subcommand
- Notebooks 00–05 (WSL setup, run-all, one per Tier-1 metric, dashboard)
- `docs/adr/0001-tier1-performance-benchmarking.md`

### Refactor

- `benchmark_pipeline.py` is now a shim over `algogauge.runner`; perf permission failure warns and skips instead of aborting
- `dashboard.py` is now a shim over `algogauge.dashboard`; the legacy single-run-folder argument is ignored (with a printed note)

## 0.2.0 (2026-04-07)

### Feat

- make dasboard orange
- benchmarks for strategy

### Refactor

- standardize strategy benchmarks
- convert pipeline script to python
- using git submodules
