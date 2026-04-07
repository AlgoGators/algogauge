import json
import re
import pandas as pd
from dash import Dash, dcc, html
import plotly.express as px

# ---------------------------
# Load + parse benchmark.json
# ---------------------------
with open("benchmark.json") as f:
    data = json.load(f)

records = []

pattern = re.compile(r"OnDataScaling/(\d+)_(\w+)")

for b in data["benchmarks"]:
    match = pattern.search(b["name"])
    if not match:
        continue

    size = int(match.group(1))
    metric = match.group(2)

    records.append({"size": size, "metric": metric, "value": b["real_time"]})

df = pd.DataFrame(records)

# Pivot into wide format
df_wide = df.pivot(index="size", columns="metric", values="value").reset_index()
df_wide = df_wide.sort_values("size")

# Derived metrics
df_wide["time_per_element"] = df_wide["mean"] / df_wide["size"]

# ---------------------------
# Plotly figures
# ---------------------------

# Scaling curve
fig_scaling = px.line(
    df_wide,
    x="size",
    y="mean",
    log_x=True,
    log_y=True,
    markers=True,
    title="Scaling Behavior (log-log)",
)

# Time per element
fig_tpe = px.line(
    df_wide, x="size", y="time_per_element", markers=True, title="Time per Element (ns)"
)

# Variability (CV)
fig_cv = px.line(
    df_wide, x="size", y="cv", markers=True, title="Coefficient of Variation (%)"
)

# Stddev
fig_std = px.line(
    df_wide, x="size", y="stddev", markers=True, title="Standard Deviation (ns)"
)

# ---------------------------
# Dash app
# ---------------------------
app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1("Benchmark Dashboard"),
        html.Div(
            [
                dcc.Graph(figure=fig_scaling),
            ]
        ),
        html.Div(
            [
                dcc.Graph(figure=fig_tpe),
            ]
        ),
        html.Div(
            [
                dcc.Graph(figure=fig_cv),
            ]
        ),
        html.Div(
            [
                dcc.Graph(figure=fig_std),
            ]
        ),
    ]
)

if __name__ == "__main__":
    app.run(debug=True)
