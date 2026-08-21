# Dashboard

`algogauge.dashboard` is an interactive Plotly Dash web app for exploring benchmark results across **every suite and every run** — it reads directly from the committed `history/*.jsonl` files (and, for flamegraphs, the latest run's `results/<suite>/<run-id>/` directory). Unlike the old single-run-folder viewer, nothing here is hard-coded to a specific benchmark name or naming pattern: suites and benchmarks are discovered from whatever is in `history/`.

## Usage

```bash
uv run algogauge dashboard
```

Open the URL printed in the terminal (`http://127.0.0.1:8050` by default). Flags: `--history-dir`, `--results-dir`, `--host`, `--port`, `--debug`.

Or from a notebook (`notebooks/05_dashboard.ipynb`):

```python
from algogauge.dashboard.app import build_app
app = build_app(ROOT / "history", ROOT / "results")
app.run(debug=False, port=8050)
```

Run at least one suite first (`uv run algogauge run`, or notebook 01) so there's data to show — an empty `history/` renders the dashboard with "no runs recorded yet" placeholders rather than erroring.

## Pages

| Page | Description |
|------|-------------|
| **Overview** | The three Tier-1 headline numbers (tick-to-trade p50, ingestion conversion p50, backtest speedup) from each suite's latest valid run, with Δ vs. the previous valid run |
| **Suites** | One tab per suite, auto-discovered from `history/`. Table of every benchmark's median/p95/CV/validity from the latest run, plus a scaling plot per benchmark family with 2+ numeric-param variants (e.g. `ProcessTick/1,8,32,128`), plus the flamegraph if one exists for that run |
| **Trends** | Median over time for every benchmark with 2+ runs, hover shows the trade-ngin git SHA at that run |
| **Compare** | Latest vs. previous valid run per suite, using the same regression logic as `algogauge compare` — rows beyond the 10% threshold are highlighted |
| **Runs** | Every run recorded for every suite: run id, timestamp, validity, benchmark count, trade-ngin/algogauge SHAs, CPU model. Invalid runs (CV > 15%) are shown greyed out, not hidden |

Compare and the per-suite scaling plots are computed once when the dashboard starts (from whatever is in `history/` at that moment) — restart the dashboard (or refresh after `uv run algogauge dashboard` picks up a new run) to see newly-recorded runs.

## What each page needs

| Page | Needs |
|------|-------|
| Overview | At least one valid run of `tick_to_trade` / `ingestion_throughput` / `backtest_speedup`; missing suites just show a placeholder card instead of erroring |
| Suites | At least one run of that suite (valid or not) |
| Trends | At least 2 runs of a given benchmark to draw a line |
| Compare | At least 2 valid runs of a suite |
| Runs | Any runs at all |

## Legacy single-run viewer

`python dashboard.py <run-dir>` still exists as a backwards-compatible shim — it now ignores the folder argument (with a printed note) and launches the same multi-suite dashboard against `history/` + `results/` in the current directory. Prefer `uv run algogauge dashboard` directly.
