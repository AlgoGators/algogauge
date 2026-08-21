"""Generate notebooks/*.ipynb deterministically. Run: python scripts/build_notebooks.py"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

BOOT = """import sys, pathlib
ROOT = pathlib.Path.cwd().resolve()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "python"))
import os; os.chdir(ROOT)
print("repo root:", ROOT)"""


def _nb(cells):
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
    }
    nb.cells = cells
    for i, c in enumerate(nb.cells):
        c["id"] = f"cell-{i:03d}"
    return nb


def setup_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 00 · Set up WSL2 for AlgoGauge\n\n"
                "Run this once on a fresh WSL2 Ubuntu 24.04. "
                "Step 1 needs `sudo`, so it is printed for you to run in a terminal; the rest runs here."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_markdown_cell(
                "## 1. System packages (run in a terminal, needs your password)"
            ),
            nbf.v4.new_code_cell(
                'print("wsl -d Ubuntu -e sudo bash", ROOT / "scripts" / "setup_wsl.sh")'
            ),
            nbf.v4.new_markdown_cell("## 2. Verify toolchain"),
            nbf.v4.new_code_cell(
                """import shutil, subprocess
for tool in ["g++", "cmake", "ninja", "perf", "uv", "git"]:
    print(f"{tool:<6}", shutil.which(tool) or "MISSING")
paranoid_path = pathlib.Path("/proc/sys/kernel/perf_event_paranoid")
print("perf_event_paranoid =", paranoid_path.read_text().strip() if paranoid_path.exists() else "n/a")"""
            ),
            nbf.v4.new_markdown_cell("## 3. Submodules + Python deps"),
            nbf.v4.new_code_cell(
                """subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
subprocess.run(["uv", "sync", "--extra", "dev"], check=True)"""
            ),
            nbf.v4.new_markdown_cell("## 4. Build benchmarks (Release)"),
            nbf.v4.new_code_cell(
                """subprocess.run(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"], check=True)
subprocess.run(["cmake", "--build", "build", "--parallel"], check=True)"""
            ),
            nbf.v4.new_markdown_cell("## 5. Smoke run (no perf)"),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner
m = manifest.load(ROOT / "algogauge.toml")
res = runner.run_suite(m.suites[0], m.defaults, ROOT, skip_perf=True)
print(res.run_id, len(res.records), "benchmarks recorded")"""
            ),
        ]
    )


def run_all_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 01 · Run all benchmark suites\n\n"
                "Runs every suite in `algogauge.toml`, appends to `history/`, and prints the headline "
                "numbers plus a Markdown table you can paste anywhere."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_code_cell(
                """SKIP_PERF = False   # set True to skip flamegraphs (faster; needed if perf is unavailable)
SUITES = None       # e.g. ["tick_to_trade"]; None = all"""
            ),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner, cli
m = manifest.load(ROOT / "algogauge.toml")
results = {}
for s in m.suites:
    if SUITES and s.name not in SUITES:
        continue
    results[s.name] = runner.run_suite(s, m.defaults, ROOT, skip_perf=SKIP_PERF)"""
            ),
            nbf.v4.new_markdown_cell("## Summary"),
            nbf.v4.new_code_cell(
                """from IPython.display import Markdown, display
for name, res in results.items():
    display(Markdown(f"### {name}  (run `{res.run_id}`, perf={'on' if res.perf_ran else 'off'})\\n" + cli.summary_markdown(res.records)))"""
            ),
            nbf.v4.new_markdown_cell("## Regression check vs previous run"),
            nbf.v4.new_code_cell(
                """for name in results:
    print(f"\\n== {name} ==")
    cli.main(["compare", name, "--history-dir", str(ROOT / "history"), "--threshold", str(m.defaults.regression_threshold_pct)])"""
            ),
        ]
    )


def tick_to_trade_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 02 · Tick-to-trade latency\n\n"
                "Runs only the `tick_to_trade` suite: one new bar in, "
                "`PortfolioManager::process_market_data()` → `get_recent_executions()` timed. "
                "In-process, mock database, mock broker -- this is engine decision latency, "
                "not wire latency to a real broker. See "
                "docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.1."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner, cli
m = manifest.load(ROOT / "algogauge.toml")
suite = m.get("tick_to_trade")
res = runner.run_suite(suite, m.defaults, ROOT, skip_perf=False)
print(f"run {res.run_id}, perf={'on' if res.perf_ran else 'off'}")"""
            ),
            nbf.v4.new_markdown_cell("## Results by symbol-universe size"),
            nbf.v4.new_code_cell(
                """from IPython.display import Markdown, display
display(Markdown(cli.summary_markdown(res.records)))"""
            ),
            nbf.v4.new_markdown_cell(
                "## Latency vs. universe size\n\n"
                "Median and p95 microseconds per tick, one point per `symbols` variant "
                "(1 / 8 / 32 / 128), showing how decision latency scales with the size of "
                "the traded universe."
            ),
            nbf.v4.new_code_cell(
                """import pandas as pd
import plotly.express as px

rows = [
    {"symbols": int(r.param), "median_us": r.median, "p95_us": r.p95, "executions_per_tick": r.counters.get("executions_per_tick")}
    for r in res.records
    if r.param is not None
]
df = pd.DataFrame(rows).sort_values("symbols")
display(df)
fig = px.line(df.melt(id_vars="symbols", value_vars=["median_us", "p95_us"]),
             x="symbols", y="value", color="variable", markers=True,
             title="Tick-to-trade latency vs. symbol-universe size", log_x=True)
fig.show()"""
            ),
            nbf.v4.new_markdown_cell("## Flamegraph (if perf ran)"),
            nbf.v4.new_code_cell(
                """flamegraph = res.result_dir / "flamegraph.svg"
if flamegraph.exists():
    from IPython.display import SVG, display as _display
    _display(SVG(filename=str(flamegraph)))
else:
    print("no flamegraph for this run (perf was skipped or unavailable)")"""
            ),
        ]
    )


def ingestion_throughput_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 03 · Data-ingestion throughput\n\n"
                "Runs only the `ingestion_throughput` suite: Arrow-table-to-Bar conversion "
                "(Stage A), single-threaded `MarketDataBus::publish()` fan-out (Stage B), and "
                "concurrent-publisher contention (Stage C). Synthetic in-memory data only -- "
                "no socket or disk I/O. See "
                "docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md section 3.2."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner, cli
m = manifest.load(ROOT / "algogauge.toml")
suite = m.get("ingestion_throughput")
res = runner.run_suite(suite, m.defaults, ROOT, skip_perf=False)
print(f"run {res.run_id}, perf={'on' if res.perf_ran else 'off'}")"""
            ),
            nbf.v4.new_markdown_cell("## Results"),
            nbf.v4.new_code_cell(
                """from IPython.display import Markdown, display
display(Markdown(cli.summary_markdown(res.records)))"""
            ),
            nbf.v4.new_markdown_cell(
                "## Stage A: conversion throughput vs. table size\n\n"
                "Rows/second implied by median latency, one point per `rows` variant."
            ),
            nbf.v4.new_code_cell(
                """import pandas as pd
import plotly.express as px

conv = pd.DataFrame([
    {"rows": int(r.param), "median_us": r.median, "rows_per_sec": r.counters.get("items_per_second")}
    for r in res.records
    if r.family == "ArrowToBars" and r.param is not None
]).sort_values("rows")
display(conv)
if not conv.empty:
    px.line(conv, x="rows", y="median_us", markers=True, log_x=True, log_y=True,
           title="Arrow-to-Bar conversion latency vs. table size").show()"""
            ),
            nbf.v4.new_markdown_cell(
                "## Stage C: contention -- latency vs. concurrent publisher threads\n\n"
                "Rising median latency as `threads` increases is the mutex contention "
                "in `MarketDataBus::publish()` becoming visible."
            ),
            nbf.v4.new_code_cell(
                """cont = pd.DataFrame([
    {"threads": int(r.param), "median_us": r.median, "p95_us": r.p95}
    for r in res.records
    if r.family == "PublishContended" and r.param is not None
]).sort_values("threads")
display(cont)
if not cont.empty:
    px.line(cont.melt(id_vars="threads", value_vars=["median_us", "p95_us"]),
           x="threads", y="value", color="variable", markers=True,
           title="MarketDataBus::publish() contention vs. thread count").show()"""
            ),
            nbf.v4.new_markdown_cell("## Flamegraph (if perf ran)"),
            nbf.v4.new_code_cell(
                """flamegraph = res.result_dir / "flamegraph.svg"
if flamegraph.exists():
    from IPython.display import SVG, display as _display
    _display(SVG(filename=str(flamegraph)))
else:
    print("no flamegraph for this run (perf was skipped or unavailable)")"""
            ),
        ]
    )


NOTEBOOKS = (
    ("00_setup_wsl.ipynb", setup_nb),
    ("01_run_all_benchmarks.ipynb", run_all_nb),
    ("02_tick_to_trade.ipynb", tick_to_trade_nb),
    ("03_ingestion_throughput.ipynb", ingestion_throughput_nb),
)


def build(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for name, make_nb in NOTEBOOKS:
        p = out_dir / name
        nbf.write(make_nb(), str(p))
        out.append(p)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for p in build(root / "notebooks"):
        print("wrote", p.relative_to(root))
    sys.exit(0)
