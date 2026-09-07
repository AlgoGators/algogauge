# AlgoGauge Tier-1 Performance Benchmarking — Design Plan

_Date: 2026-08-21 · Status: APPROVED 2026-08-21 · Target repo: [AlgoGators/algogauge](https://github.com/AlgoGators/algogauge)_


---

## 0. Decisions (resolved 2026-08-21)

| # | Decision / action | Why I can't decide it alone | My default if you say "go" |
|---|---|---|---|
| 1 | **Approve the layout in §2** (or tell me what to change) | It's the skeleton everything else hangs on | — |
| 2 | **Install the WSL2 toolchain.** The setup script needs `sudo apt install …` inside Ubuntu, which needs your password. Run `! wsl -d Ubuntu -e sudo bash notebooks/setup_wsl.sh` when I hand you the script, *or* grant passwordless sudo in WSL | I can't type your sudo password | You run the one-liner |
| 3 | **Where should the work land?** A branch + PR on algogauge (`feat/tier1-benchmarks`), or direct to `main`? Do you have write access to algogauge? | Pushing to a team repo | Branch + PR |
| 4 | **"Massive simulation" size** for the backtest-speedup metric | Sets the headline number's meaning | 50 symbols × 10 years synthetic daily bars, 8 independent backtests |
| 5 | **Regression threshold** for the history/compare step | Team policy | 10% on median |
| 6 | *(Unrelated, from the PR loop)* **PR #60 & #57 coverage**: CI has no Postgres, so raw DB-query lines can never be covered. (a) I refactor `config_loader`'s queries through `DatabaseInterface` so the mock covers them, or (b) team adds a Postgres service container to CI (fixes #57 too) | (b) is an infra change | (a) for #60 now; recommend (b) to the team |

Everything else below has a reasonable default baked in.

---

## 1. Goal

Answer these three questions with **real, repeatable, machine-attributed numbers** instead of guesses:

1. **Tick-to-trade latency** — how long from a market-data bar arriving to an order/execution being emitted by trade-ngin? (µs)
2. **Data-ingestion throughput** — how many market-data messages/bars per second can the pipeline convert and fan out? (msg/s)
3. **Backtest speedup** — how much faster does a large simulation run when parallelised vs. serial? (× speedup, scaling efficiency)

Scope: **trade-ngin only**, but structured so `data-ngin` / `AlgoSys v2` plug in later as extra submodules + manifest entries. Runs on **WSL2 Ubuntu 24.04** on your laptop (16 cores / 8 GB). Results persist as **compact committed summaries**; raw profiles stay local.

### What exists today in algogauge
- Google Benchmark C++ harness for `BaseStrategy` / `TrendFollowingStrategy` (`benchmarks/`), with `MockPostgresDatabase` and a synthetic bar generator.
- `python/benchmark_pipeline.py`: runs one binary → `perf record` → FlameGraph.
- `python/dashboard.py`: Plotly Dash, hard-wired to one benchmark family (`OnDataScaling/<size>`), one run at a time.
- `docs/roadmap.md` already asks for: a manifest, schema-agnostic dashboard, multi-run comparison, baseline regression, CI. This plan delivers those because the three metrics need them anyway.

### What exists today in trade-ngin (measurement points, verified)
| Metric | Entry point | File |
|---|---|---|
| Tick-to-trade | `PortfolioManager::process_market_data(bars)` → `Strategy::on_data()` → target positions → `ExecutionReport`s via `get_recent_executions()` | `include/trade_ngin/portfolio/portfolio_manager.hpp:129,164` |
| Ingestion | `ConversionUtils::arrow_table_to_bars(table)`; `MarketDataBus::publish(event)` (mutex-guarded fan-out) | `data/conversion_utils.hpp:17`, `data/market_data_bus.hpp:76` |
| Backtest | `BacktestCoordinator::run_portfolio(portfolio, symbols, start, end)` — takes an injected DB, so the mock works with no Postgres | `backtest/backtest_coordinator.hpp:150` |
| Mock DB | `MockPostgresDatabase` returns synthetic Arrow tables from `get_market_data()` | `tests/data/test_db_utils.hpp:86` |

trade-ngin is **single-threaded** (no `std::thread`/`std::async`/OpenMP anywhere in `src/` or `apps/`), so the backtest speedup is measured at the **harness level** (many independent backtests in a process pool), not inside the engine. The ADR states this explicitly so the number is never misrepresented.

---

## 2. Architecture & repo layout  ← **needs your approval**

```
algogauge/
├── algogauge.toml                 # manifest: every suite, binary/script, params, perf on/off
├── docs/adr/
│   └── 0001-tier1-performance-benchmarking.md
├── benchmarks/                    # existing Google Benchmark harness
│   ├── tick_to_trade_benchmarks.cpp          # NEW
│   ├── ingestion_throughput_benchmarks.cpp   # NEW
│   ├── fixtures/tick_to_trade_fixture.hpp    # NEW
│   ├── fixtures/ingestion_fixture.hpp        # NEW
│   └── (existing strategy benchmarks untouched)
├── python/algogauge/              # loose scripts → small package
│   ├── manifest.py        # load/validate algogauge.toml
│   ├── runner.py          # run a suite → results/<suite>/<run-id>/ (generalised pipeline, --skip-perf)
│   ├── backtest_parallel.py   # serial vs process-pool backtest harness
│   ├── history.py         # append compact record → history/<suite>.jsonl; load for trends
│   ├── compare.py         # baseline vs current; non-zero exit on regression
│   ├── machine.py         # CPU model, cores, kernel, trade-ngin SHA, compiler flags
│   └── dashboard/         # Dash app: schema-agnostic, multi-suite, multi-run
├── notebooks/
│   ├── 00_setup_wsl.ipynb
│   ├── 01_run_all_benchmarks.ipynb
│   ├── 02_tick_to_trade.ipynb
│   ├── 03_ingestion_throughput.ipynb
│   ├── 04_backtest_speedup.ipynb
│   └── 05_dashboard.ipynb
├── history/                       # TRACKED: one .jsonl per suite, one line per run
└── results/                       # gitignored: raw benchmark.json, perf.data, flamegraph.svg
```

**Data flow:** notebook/CLI → `runner.py` reads manifest → runs C++ binary (or `backtest_parallel.py`) → writes raw run dir → `history.py` appends one compact record → dashboard & notebooks read `history/` for trends and `results/` for latest raw detail.

**Boundaries:** C++ suites know nothing about Python. The runner knows nothing about specific suites (manifest-driven). The dashboard knows only the result/history schema. Adding another repo = new submodule + new `[[benchmark]]` block + its own suite file.

**Existing code fate:** `benchmark_pipeline.py` → `runner.py` (generalised; keeps perf/flamegraph; gains `--skip-perf`). `dashboard.py` → rewritten. The two existing strategy suites keep working via the manifest, unchanged.

---

## 3. Measurement design (one subsection per metric)

### 3.1 Tick-to-trade latency (`tick_to_trade_benchmarks`)
- **Fixture:** `PortfolioManager` with one `TrendFollowingStrategy` (same config as the existing fixture), `MockPostgresDatabase`, warmed up with 256 bars so EMAs are populated and the strategy is actually emitting position changes.
- **Timed region:** one call to `process_market_data({bar})` for a single new bar, then read `get_recent_executions()`. Nothing else. Clock: Google Benchmark's `manual_time` with `std::chrono::steady_clock` so fixture reset is excluded.
- **Variants:** `SingleSymbol`, `Symbols/8`, `Symbols/32`, `Symbols/128` (one bar per symbol per tick) — shows how latency scales with universe size.
- **Reported:** median, p95, p99 in µs; executions emitted per tick (sanity: must be > 0 or the run is flagged invalid).
- **Honesty notes for the ADR:** this is in-process, no network, no broker, mock DB. It measures engine decision latency, not wire latency.

### 3.2 Data-ingestion throughput (`ingestion_throughput_benchmarks`)
- **Stage A — conversion:** `arrow_table_to_bars()` over tables of 1k / 10k / 100k / 1M rows. Reported as rows/s.
- **Stage B — bus fan-out:** `MarketDataBus::publish()` with 1 / 4 / 16 subscribers, 100k events. Reported as msg/s and ns/msg; since the bus is mutex-guarded, also a `Contended/<threads>` variant publishing from N threads concurrently to expose lock contention.
- **Stage C — end-to-end:** Arrow table → bars → publish, reported as the bottleneck-limited msg/s.
- **Honesty notes:** synthetic in-memory data; no socket/disk I/O.

### 3.3 Backtest speedup (`backtest_parallel.py`)
- A tiny C++ driver binary `bt_bench_runner` (in `benchmarks/`) runs one `BacktestCoordinator::run_portfolio()` over synthetic data for given `--symbols N --years Y --seed S` and prints wall-clock + results checksum.
- `backtest_parallel.py` runs K independent jobs (different seeds) **serially**, then via `ProcessPoolExecutor` at worker counts 1, 2, 4, 8, 16. Reports total wall-clock per worker count, speedup vs serial, parallel efficiency (speedup / workers), and verifies result checksums match between serial and parallel (correctness guard).
- Default size: 50 symbols × 10 years daily, K = 8 jobs (your call, §0 #4).
- **Honesty notes:** speedup is across *independent* backtests (parameter sweeps, walk-forward folds, Monte-Carlo seeds); a single backtest is still single-threaded.

### 3.4 Common to all suites
- Every run records: trade-ngin submodule SHA, algogauge SHA, CPU model, core count, kernel, compiler + flags, `perf_event_paranoid`, timestamp, and whether perf was enabled.
- Google Benchmark settings: `--benchmark_repetitions=20 --benchmark_min_time=2s --benchmark_report_aggregates_only=true`, overridable per-suite in the manifest.
- A run is marked `invalid` (still stored, shown greyed in dashboard) if CV > 15% or sanity checks fail.

---

## 4. Manifest (`algogauge.toml`)

```toml
[defaults]
repetitions = 20
min_time = "2s"
perf = true
regression_threshold_pct = 10

[[benchmark]]
name   = "tick_to_trade"
kind   = "gbench"
binary = "build/benchmarks/tick_to_trade_benchmarks"

[[benchmark]]
name   = "ingestion_throughput"
kind   = "gbench"
binary = "build/benchmarks/ingestion_throughput_benchmarks"

[[benchmark]]
name   = "backtest_speedup"
kind   = "script"
script = "python/algogauge/backtest_parallel.py"
args   = ["--symbols", "50", "--years", "10", "--jobs", "8", "--workers", "1,2,4,8,16"]
perf   = false

[[benchmark]]   # existing suites, unchanged
name   = "base_strategy"
kind   = "gbench"
binary = "build/benchmarks/base_strategy_benchmarks"

[[benchmark]]
name   = "trend_following"
kind   = "gbench"
binary = "build/benchmarks/trend_following_benchmarks"
```

---

## 5. History & regression

- `history/<suite>.jsonl`, one line per run: `{run_id, suite, benchmark, median_ns, p95_ns, mean_ns, stddev_ns, cv_pct, iterations, unit, valid, machine:{…}, trade_ngin_sha, algogauge_sha, ts}`.
- `compare.py --baseline <run-id|latest-valid> --current <run-id>` prints a table and exits 1 if any benchmark's median regressed beyond the threshold. Usable locally and in CI later.
- Raw artefacts (`benchmark.json`, `perf.data`, `flamegraph.svg`) stay in gitignored `results/`.

---

## 6. Dashboard (Plotly Dash, rewritten)

Pages (left nav):
1. **Overview** — three big headline cards: *Tick-to-trade p50/p95 µs*, *Ingestion msg/s*, *Backtest speedup ×* from the latest valid run; each card shows Δ vs previous run and links to its drill-down.
2. **Suite drill-down** (one per suite, auto-discovered from the manifest) — benchmark table (median/p95/CV), scaling plots auto-grouped by `family/<param>`, raw table fallback for non-parametric names, flamegraph tab if present.
3. **Trends** — any benchmark's median over time from `history/`, with trade-ngin SHA on hover, machine filter, regression-threshold band.
4. **Compare** — pick two runs, side-by-side table with Δ%, highlighting regressions.
5. **Runs** — list of all runs with validity flag, machine, SHA; click to open.

Launch: `uv run algogauge dashboard` (reads `history/` + `results/`), or from `05_dashboard.ipynb`. Style keeps the existing orange theme.

---

## 7. Notebooks (the repeatable entry points)

| Notebook | Does |
|---|---|
| `00_setup_wsl.ipynb` | Prints/validates the `sudo apt` line (you run it), installs `uv`, syncs Python deps, inits submodules, builds with CMake, runs a smoke benchmark, checks `perf_event_paranoid`. Idempotent. |
| `01_run_all_benchmarks.ipynb` | Runs every manifest suite via `runner.py`, appends to history, prints the three headline numbers + a Markdown table you can paste anywhere. |
| `02_tick_to_trade.ipynb` | Runs only that suite, explains each variant, plots latency distribution and scaling vs symbols, embeds flamegraph, shows where the µs go. |
| `03_ingestion_throughput.ipynb` | Same for ingestion: conversion vs bus vs end-to-end, contention plot vs threads. |
| `04_backtest_speedup.ipynb` | Runs the parallel harness, plots speedup & efficiency vs workers (with Amdahl overlay), verifies checksums. |
| `05_dashboard.ipynb` | Starts the dashboard in-process and shows the URL. |

Notebooks call the package (`from algogauge import runner, history`) — no logic lives in notebooks, so CLI and notebook paths are identical.

---

## 8. ADR — `docs/adr/0001-tier1-performance-benchmarking.md`

Sections: Context (why these three metrics; what questions they answer) · Decision (harness-level measurement, mock DB, synthetic data, manifest-driven, committed compact history) · Exact definition of each metric, what it includes/excludes, and **how to phrase it honestly** (e.g. "engine decision latency, in-process, mock broker") · Validity rules · How to add a new system (data-ngin / AlgoSys v2) · Consequences & alternatives rejected (engine-level threading, Python-side timing via pybind) · Status.

---

## 9. WSL2 setup (what `00_setup_wsl.ipynb` will do)

Current state: Ubuntu 24.04, 16 cores, 8 GB RAM, 940 GB free, **no** g++/cmake/perf/uv/jupyter.

```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build pkg-config git \
  libeigen3-dev nlohmann-json3-dev libpqxx-dev libnlopt-cxx-dev libgtest-dev \
  libbenchmark-dev libcurl4-openssl-dev linux-tools-generic
# Apache Arrow (apt.apache.org repo) — same steps as trade-ngin/requirements/install_ubuntu.sh
sudo sysctl kernel.perf_event_paranoid=0 kernel.kptr_restrict=0   # for perf/flamegraphs
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Note: WSL2's stock kernel may lack `perf`; if so the runner's `--skip-perf` path still produces all timing numbers — only flamegraphs are lost. Documented in the ADR.

---

## 10. Testing
- Python package: pytest for `manifest`, `history`, `compare` (schema, append/load, regression detection, invalid-run handling) — TDD.
- C++ suites: each has a `_smoke` test target asserting the fixture produces ≥1 execution / ≥1 delivered event so a "0 µs" result can't pass silently.
- `backtest_parallel.py`: checksum equality serial vs parallel is a hard assertion.
- Dashboard: a headless Dash test that loads sample `history/` fixtures and renders each page without error.

---

## 11. Implementation order — delivered as separate PRs, in this sequence
| PR | Branch | Contents |
|---|---|---|
| 0 | `docs/tier1-benchmarking-spec` | This spec. |
| 1 | `feat/python-package-and-manifest` | `python/algogauge/` package (manifest, machine, history, compare, runner ← generalised pipeline) + pytest suite + `algogauge.toml` + `history/` dir + notebooks 00/01 + `setup_wsl.sh`. Existing suites still run. |
| 2 | `feat/tick-to-trade-suite` | `tick_to_trade_benchmarks` + fixture + smoke test + notebook 02 + manifest entry. |
| 3 | `feat/ingestion-throughput-suite` | `ingestion_throughput_benchmarks` + fixture + smoke test + notebook 03 + manifest entry. |
| 4 | `feat/backtest-speedup-harness` | `bt_bench_runner` + `backtest_parallel.py` + checksum test + notebook 04 + manifest entry. |
| 5 | `feat/dashboard-v2` | Dashboard rewrite (Overview/Suite/Trends/Compare/Runs) + headless render tests + notebook 05. |
| 6 | `docs/adr-0001-and-first-history` | ADR 0001, README/docs update, first committed history run from this machine. |

PRs 2–4 are independent of each other and depend only on PR 1. PR 5 depends on 1 (and is best reviewed after 2–4 produce real data). PR 6 comes last.

Decisions locked: backtest default 50 symbols × 10 years × 8 jobs; regression threshold 10% on median; WSL2 sudo line is run by the repo owner.

---

## 12. Out of scope (deliberately)
- Threading inside trade-ngin's engine (separate trade-ngin PR later; the harness will then measure it).
- CI benchmark workflow (roadmap item; `--skip-perf` + `compare.py` make it a small follow-up).
- data-ngin / AlgoSys v2 suites (plug in via manifest later).
