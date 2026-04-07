import json
import re
import sys
import os
import pandas as pd
from dash import Dash, dcc, html
import plotly.express as px

# TODO extension to any arbitrary benchmark pattern, not just OnDataScaling

# CLI argument handling
if len(sys.argv) != 2:
    print("Usage: python dashboard.py <benchmark.json>")
    sys.exit(1)

filename = sys.argv[1]

if not os.path.exists(filename):
    print(f"Error: file '{filename}' not found")
    sys.exit(1)

# Load + parse benchmark.json
with open(filename) as f:
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

# Plotly figures
fig_scaling = px.line(
    df_wide,
    x="size",
    y="mean",
    log_x=True,
    log_y=True,
    markers=True,
    title="Scaling Behavior (log-log)",
)

fig_tpe = px.line(
    df_wide, x="size", y="time_per_element", markers=True, title="Time per Element (ns)"
)

fig_cv = px.line(
    df_wide, x="size", y="cv", markers=True, title="Coefficient of Variation (%)"
)

fig_std = px.line(
    df_wide, x="size", y="stddev", markers=True, title="Standard Deviation (ns)"
)

# Dash app
app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1(f"Benchmark Dashboard: {os.path.basename(filename)}"),
        dcc.Graph(figure=fig_scaling),
        dcc.Graph(figure=fig_tpe),
        dcc.Graph(figure=fig_cv),
        dcc.Graph(figure=fig_std),
    ]
)

if __name__ == "__main__":
    app.run(debug=True)
