import json
import re
import sys
import os
import pandas as pd
from dash import Dash, dcc, html
import plotly.express as px

# CLI argument handling
if len(sys.argv) != 2:
    print("Usage: python dashboard.py <folder>")
    sys.exit(1)

folder = sys.argv[1]

if not os.path.exists(folder) or not os.path.isdir(folder):
    print(f"Error: folder '{folder}' not found or is not a directory")
    sys.exit(1)

json_file = os.path.join(folder, "benchmark.json")
svg_file = os.path.join(folder, "flamegraph.svg")

if not os.path.exists(json_file):
    print(f"Error: '{json_file}' not found")
    sys.exit(1)

# Load + parse benchmark.json
with open(json_file) as f:
    data = json.load(f)

records = []
pattern = re.compile(r"OnDataScaling/(\d+)_(\w+)")

for b in data.get("benchmarks", []):
    match = pattern.search(b.get("name", ""))
    if not match:
        continue

    size = int(match.group(1))
    metric = match.group(2)

    records.append({"size": size, "metric": metric, "value": b.get("real_time", 0.0)})

if not records:
    print("Error: no matching benchmark entries found")
    sys.exit(1)

df = pd.DataFrame(records)

# Pivot into wide format
df_wide = df.pivot(index="size", columns="metric", values="value").reset_index()
df_wide = df_wide.sort_values("size")

# Derived metrics
if "mean" in df_wide.columns:
    df_wide["time_per_element"] = df_wide["mean"] / df_wide["size"]
else:
    df_wide["time_per_element"] = None


# Plotly figures with orange theme
def make_fig(df, x, y, title):
    fig = px.line(df, x=x, y=y, markers=True, title=title)
    fig.update_traces(line_color="orange", marker_color="orange")
    return fig


fig_scaling = make_fig(df_wide, "size", "mean", "Scaling Behavior (log-log)")
fig_tpe = make_fig(df_wide, "size", "time_per_element", "Time per Element (ns)")
fig_cv = (
    make_fig(df_wide, "size", "cv", "Coefficient of Variation (%)")
    if "cv" in df_wide.columns
    else None
)
fig_std = (
    make_fig(df_wide, "size", "stddev", "Standard Deviation (ns)")
    if "stddev" in df_wide.columns
    else None
)

# Dash app
app = Dash(__name__)

graph_list = [dcc.Graph(figure=fig_scaling), dcc.Graph(figure=fig_tpe)]
if fig_cv:
    graph_list.append(dcc.Graph(figure=fig_cv))
if fig_std:
    graph_list.append(dcc.Graph(figure=fig_std))

# Flamegraph iframe
if os.path.exists(svg_file):
    flamegraph_div = html.Div(
        [
            html.H2("Flamegraph", style={"color": "orange"}),
            html.Iframe(
                srcDoc=open(svg_file).read(),
                style={"width": "100%", "height": "800px", "border": "none"},
            ),
        ]
    )
    graph_list.append(flamegraph_div)  # Gives error but still works

app.layout = html.Div(
    [
        html.H1(
            f"Benchmark Dashboard: {os.path.basename(folder)}",
        ),
        *graph_list,
    ],
)

if __name__ == "__main__":
    app.run(debug=True)
