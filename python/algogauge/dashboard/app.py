"""AlgoGauge dashboard: schema-agnostic, multi-suite, multi-run.

Reads history/*.jsonl (via algogauge.history) and, for flamegraphs, the
latest run's raw results/ directory. Layout-builder functions are pure
(records/data in, Dash component tree out) so they can be unit tested
without a running server -- see tests/test_dashboard.py.

Pages: Overview (headline Tier-1 numbers) / Suites (per-suite drill-down,
auto-discovered) / Trends (median over time) / Compare (latest vs. previous
valid run per suite) / Runs (every run, validity, machine, SHA).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, dash_table, dcc, html

from .. import compare as compare_mod
from ..history import Record
from . import data as dd

ACCENT = "orange"

# (suite, benchmark, extractor, label) -- the three Tier-1 headline numbers.
# A suite/benchmark that hasn't been run yet just doesn't render a card.
HEADLINE_METRICS = [
    ("tick_to_trade", "ProcessTick/8", lambda r: r.median, "Tick-to-Trade p50 (8 symbols)"),
    ("ingestion_throughput", "ArrowToBars/100000", lambda r: r.median, "Ingestion: 100k rows, p50"),
    (
        "backtest_speedup",
        "BacktestSpeedup/8",
        lambda r: r.counters.get("speedup", float("nan")),
        "Backtest Speedup (8 workers)",
    ),
]


def _line_fig(df: pd.DataFrame, x: str, y, title: str, log_x: bool = False):
    fig = px.line(df, x=x, y=y, markers=True, title=title, log_x=log_x)
    fig.update_traces(line_color=ACCENT, marker_color=ACCENT)
    fig.update_layout(margin={"l": 40, "r": 20, "t": 40, "b": 40})
    return fig


def _headline_card(
    all_history: dict[str, list[Record]], suite: str, benchmark: str, extractor, label: str
):
    records = dd.benchmark_records(all_history.get(suite, []), benchmark)
    metric = dd.headline_metric(records, extractor)
    if metric is None:
        return html.Div(
            [
                html.H3(label, style={"color": "#888"}),
                html.P(f"no data yet ({suite})", style={"color": "#888"}),
            ],
            style={
                "border": f"1px solid {ACCENT}",
                "borderRadius": "8px",
                "padding": "16px",
                "flex": "1",
            },
        )
    delta = metric["delta_pct"]
    delta_text = "—" if delta is None else f"{delta:+.1f}% vs previous run"
    return html.Div(
        [
            html.H3(label, style={"color": ACCENT, "margin": "0 0 8px 0"}),
            html.Div(
                f"{metric['value']:.2f} {metric['unit']}",
                style={"fontSize": "28px", "fontWeight": "bold"},
            ),
            html.Div(delta_text, style={"color": "#666"}),
            html.Div(f"run {metric['run_id']}", style={"color": "#aaa", "fontSize": "12px"}),
        ],
        style={
            "border": f"1px solid {ACCENT}",
            "borderRadius": "8px",
            "padding": "16px",
            "flex": "1",
        },
    )


def build_overview_layout(all_history: dict[str, list[Record]]) -> html.Div:
    cards = [
        _headline_card(all_history, suite, benchmark, extractor, label)
        for suite, benchmark, extractor, label in HEADLINE_METRICS
    ]
    return html.Div(
        [
            html.H2("Overview", style={"color": ACCENT}),
            html.Div(cards, style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),
        ]
    )


def build_suite_layout(
    suite_name: str, records: list[Record], results_dir: Path | None = None
) -> html.Div:
    latest = dd.latest_run_records(records, valid_only=False)
    if not latest:
        return html.Div(
            [html.H2(suite_name, style={"color": ACCENT}), html.P("no runs recorded yet")]
        )

    table_rows = [
        {
            "benchmark": r.benchmark,
            "median": round(r.median, 3),
            "p95": round(r.p95, 3),
            "unit": r.unit,
            "cv_pct": round(r.cv_pct, 2),
            "valid": r.valid,
        }
        for r in sorted(latest, key=lambda r: r.benchmark)
    ]
    table = dash_table.DataTable(
        data=table_rows,
        columns=[
            {"name": c, "id": c} for c in ("benchmark", "median", "p95", "unit", "cv_pct", "valid")
        ],
        style_header={"backgroundColor": ACCENT, "color": "white"},
        style_cell={"textAlign": "left", "padding": "6px"},
    )

    graphs = []
    for family, recs in dd.group_by_family(latest).items():
        params = [r.param for r in recs]
        if all(p is not None for p in params) and len(recs) > 1:
            df = pd.DataFrame(
                {
                    "param": [float(p) for p in params],
                    "median": [r.median for r in recs],
                    "p95": [r.p95 for r in recs],
                }
            ).melt(id_vars="param", value_vars=["median", "p95"])
            fig = px.line(
                df,
                x="param",
                y="value",
                color="variable",
                markers=True,
                title=f"{family}: scaling",
                log_x=True,
            )
            fig.update_layout(margin={"l": 40, "r": 20, "t": 40, "b": 40})
            graphs.append(dcc.Graph(figure=fig))

    flamegraph_div = None
    if results_dir is not None:
        run_id = latest[0].run_id
        svg_path = Path(results_dir) / suite_name / run_id / "flamegraph.svg"
        if svg_path.exists():
            flamegraph_div = html.Div(
                [
                    html.H3("Flamegraph", style={"color": ACCENT}),
                    html.Iframe(
                        srcDoc=svg_path.read_text(encoding="utf-8"),
                        style={"width": "100%", "height": "700px", "border": "none"},
                    ),
                ]
            )

    children = [
        html.H2(suite_name, style={"color": ACCENT}),
        html.P(f"latest run: {latest[0].run_id}"),
        table,
        *graphs,
    ]
    if flamegraph_div is not None:
        children.append(flamegraph_div)
    return html.Div(children)


def build_trends_layout(all_history: dict[str, list[Record]]) -> html.Div:
    sections = []
    for suite, records in sorted(all_history.items()):
        by_benchmark: dict[str, list[Record]] = {}
        for r in records:
            by_benchmark.setdefault(r.benchmark, []).append(r)
        graphs = []
        for benchmark, recs in sorted(by_benchmark.items()):
            recs = sorted(recs, key=lambda r: r.ts)
            if len(recs) < 2:
                continue
            df = pd.DataFrame(
                {
                    "ts": [r.ts for r in recs],
                    "median": [r.median for r in recs],
                    "valid": [r.valid for r in recs],
                    "trade_ngin_sha": [r.trade_ngin_sha for r in recs],
                }
            )
            fig = px.line(
                df,
                x="ts",
                y="median",
                markers=True,
                title=f"{suite}/{benchmark}: median over time",
                hover_data=["trade_ngin_sha", "valid"],
            )
            fig.update_traces(line_color=ACCENT, marker_color=ACCENT)
            fig.update_layout(margin={"l": 40, "r": 20, "t": 40, "b": 40})
            graphs.append(dcc.Graph(figure=fig))
        if graphs:
            sections.append(html.Div([html.H3(suite, style={"color": ACCENT}), *graphs]))
    if not sections:
        return html.Div(
            [
                html.H2("Trends", style={"color": ACCENT}),
                html.P("need at least 2 runs of a suite to show a trend"),
            ]
        )
    return html.Div([html.H2("Trends", style={"color": ACCENT}), *sections])


def build_compare_layout(all_history: dict[str, list[Record]]) -> html.Div:
    """Latest valid run vs. the previous valid run, per suite -- computed at
    build time (refresh the dashboard after a new run to update)."""
    sections = []
    for suite, records in sorted(all_history.items()):
        latest = dd.latest_run_records(records)
        if not latest:
            continue
        prev_run_id = latest[0].run_id
        previous = dd.previous_run_records(records, prev_run_id)
        if not previous:
            sections.append(
                html.Div(
                    [
                        html.H3(suite, style={"color": ACCENT}),
                        html.P(f"only one valid run ({prev_run_id}) -- nothing to compare yet"),
                    ]
                )
            )
            continue
        deltas = compare_mod.compare(previous, latest, threshold_pct=10.0)
        rows = [
            {
                "benchmark": d.benchmark,
                "baseline": round(d.baseline_median, 3),
                "current": round(d.current_median, 3),
                "unit": d.unit,
                "delta_pct": d.delta_pct,
                "regressed": d.regressed,
            }
            for d in deltas
        ]
        table = dash_table.DataTable(
            data=rows,
            columns=[
                {"name": c, "id": c}
                for c in ("benchmark", "baseline", "current", "unit", "delta_pct", "regressed")
            ],
            style_header={"backgroundColor": ACCENT, "color": "white"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_data_conditional=[
                {"if": {"filter_query": "{regressed} = true"}, "backgroundColor": "#ffe0e0"}
            ],
        )
        sections.append(
            html.Div(
                [
                    html.H3(
                        f"{suite}: {previous[0].run_id} → {latest[0].run_id}",
                        style={"color": ACCENT},
                    ),
                    table,
                ]
            )
        )
    if not sections:
        return html.Div(
            [html.H2("Compare", style={"color": ACCENT}), html.P("no runs recorded yet")]
        )
    return html.Div([html.H2("Compare", style={"color": ACCENT}), *sections])


def build_runs_layout(all_history: dict[str, list[Record]]) -> html.Div:
    sections = []
    for suite, records in sorted(all_history.items()):
        rows = dd.runs_for_suite(records)
        rows = [
            {
                "run_id": r["run_id"],
                "ts": r["ts"],
                "valid": r["valid"],
                "n_benchmarks": r["n_benchmarks"],
                "trade_ngin_sha": r["trade_ngin_sha"],
                "algogauge_sha": r["algogauge_sha"],
                "cpu": r["machine"].get("cpu_model", "unknown"),
            }
            for r in reversed(rows)
        ]
        table = dash_table.DataTable(
            data=rows,
            columns=[
                {"name": c, "id": c}
                for c in (
                    "run_id",
                    "ts",
                    "valid",
                    "n_benchmarks",
                    "trade_ngin_sha",
                    "algogauge_sha",
                    "cpu",
                )
            ],
            style_header={"backgroundColor": ACCENT, "color": "white"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_data_conditional=[
                {
                    "if": {"filter_query": "{valid} = false"},
                    "backgroundColor": "#f0f0f0",
                    "color": "#999",
                }
            ],
        )
        sections.append(html.Div([html.H3(suite, style={"color": ACCENT}), table]))
    if not sections:
        return html.Div([html.H2("Runs", style={"color": ACCENT}), html.P("no runs recorded yet")])
    return html.Div([html.H2("Runs", style={"color": ACCENT}), *sections])


def build_app(history_dir: Path, results_dir: Path | None = None) -> Dash:
    all_history = dd.load_history(history_dir)

    suite_tabs = [
        dcc.Tab(
            label=suite,
            value=f"suite-{suite}",
            children=[build_suite_layout(suite, records, results_dir)],
        )
        for suite, records in sorted(all_history.items())
    ]

    app = Dash(__name__, title="AlgoGauge")
    app.layout = html.Div(
        [
            html.H1("AlgoGauge", style={"color": ACCENT}),
            dcc.Tabs(
                id="top-tabs",
                value="overview",
                children=[
                    dcc.Tab(
                        label="Overview",
                        value="overview",
                        children=[build_overview_layout(all_history)],
                    ),
                    dcc.Tab(
                        label="Suites",
                        value="suites",
                        children=[dcc.Tabs(children=suite_tabs)]
                        if suite_tabs
                        else [html.P("no suites recorded yet")],
                    ),
                    dcc.Tab(
                        label="Trends", value="trends", children=[build_trends_layout(all_history)]
                    ),
                    dcc.Tab(
                        label="Compare",
                        value="compare",
                        children=[build_compare_layout(all_history)],
                    ),
                    dcc.Tab(label="Runs", value="runs", children=[build_runs_layout(all_history)]),
                ],
            ),
        ],
        style={"fontFamily": "sans-serif", "margin": "24px"},
    )
    return app
