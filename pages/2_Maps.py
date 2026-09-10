"""Gridded fields: levels, anomalies, trends, and estimation uncertainty."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from o3dash import export, io, plots, theme, ui
from o3dash.config import BASELINE_PERIOD, METRIC_LABELS

ui.guard("Maps")
units = theme.unit_picker()
ui.embargo_note()

ui.page_header(
    "Maps",
    "Gridded MDA8 ozone on the native 1 degree land grid. Each marker is one "
    "estimation cell, not an interpolated surface.",
)

if not io.require("Maps"):
    st.stop()

grid = io.grid_annual()
years = np.sort(grid["Year"].unique()).astype(int)
metric_cols = [c for c in ["AnnualMean", "OSDMA8", "DJF", "MAM", "JJA", "SON",
                           "SeasonAmp"] if c in grid.columns]

view = st.sidebar.radio(
    "View", ["Level", "Anomaly", "Trend", "Compare two years"],
    help="Level and Anomaly show one year; Trend fits every cell over a period.")
metric = st.sidebar.selectbox(
    "Metric", metric_cols, format_func=lambda m: METRIC_LABELS.get(m, m))

has_var = "Variance" in grid.columns
show_uncert = st.sidebar.checkbox(
    "Show estimation uncertainty instead", value=False, disabled=not has_var,
    help="BME posterior variance. Requires the Variance column in the export.")

value_col = "Variance" if (show_uncert and has_var) else metric


def frame(year: int, col: str) -> pd.DataFrame:
    d = grid.loc[grid["Year"] == year, ["lon", "lat", col]].dropna()
    return d.rename(columns={col: "value"})


def common_range(col: str, subset_years) -> tuple:
    vals = grid.loc[grid["Year"].isin(subset_years), col].dropna()
    if not len(vals):
        return (None, None)
    lo, hi = np.nanpercentile(vals, [2, 98])
    return (float(units.convert(lo)), float(units.convert(hi)))


unit_label = units.label if value_col != "Variance" else f"({units.label})^2"

# ------------------------------------------------------------------ level ---
if view == "Level":
    year = st.select_slider("Year", options=list(years), value=int(years[-1]))
    d = frame(year, value_col)
    d["value"] = units.convert(d["value"]) if value_col != "Variance" \
        else d["value"] * (units.factor ** 2)
    fig = plots.grid_map(
        d, "value", unit=unit_label,
        zrange=common_range(value_col, years) if value_col != "Variance" else None,
        title=f"{METRIC_LABELS.get(metric, metric)}, {year}"
              + (" - estimation variance" if show_uncert else ""))
    export.panel(fig, f"map_{value_col}_{year}",
                 caption="Colour scale is fixed across all years so panels are "
                         "comparable side by side."
                         if value_col != "Variance" else "",
                 key="map_level")

# ---------------------------------------------------------------- anomaly ---
elif view == "Anomaly":
    year = st.select_slider("Year", options=list(years), value=int(years[-1]))
    base = grid[grid["Year"].between(*BASELINE_PERIOD)]
    clim = base.groupby(["lon", "lat"])[metric].mean().rename("clim")
    cur = grid.loc[grid["Year"] == year, ["lon", "lat", metric]].set_index(
        ["lon", "lat"])[metric]
    d = pd.concat([cur, clim], axis=1).dropna().reset_index()
    d["value"] = units.convert(d[metric] - d["clim"])
    fig = plots.grid_map(
        d, "value", diverging=True, unit=unit_label,
        title=f"{METRIC_LABELS.get(metric, metric)} anomaly, {year}")
    export.panel(
        fig, f"map_anomaly_{metric}_{year}",
        caption=f"Departure from the {BASELINE_PERIOD[0]}-{BASELINE_PERIOD[1]} "
                "mean at each cell.",
        key="map_anom")

# ------------------------------------------------------------------ trend ---
elif view == "Trend":
    lo, hi = st.select_slider(
        "Period", options=list(years),
        value=(int(years[0]), int(years[-1])))
    method = st.radio("Estimator", ["Theil-Sen", "OLS with AR(1)"],
                      horizontal=True)
    mask_ns = st.checkbox("Grey out cells where p >= 0.05", value=True)

    est = "theil-sen" if method == "Theil-Sen" else "ols-ar1"
    d = io.cell_trends(metric, lo, hi, est)
    if d is None or not len(d):
        st.info("No cells with enough data over this period.")
        st.stop()
    d = d.assign(value=units.convert(d["slope"]))
    n_total, n_sig = len(d), int((d["p"] < 0.05).sum())
    if mask_ns:
        d = d[d["p"] < 0.05]

    fig = plots.grid_map(
        d, "value", diverging=True, unit=f"{units.label}/dec",
        title=f"{METRIC_LABELS.get(metric, metric)} trend, {lo}-{hi}")
    export.panel(
        fig, f"map_trend_{metric}_{lo}_{hi}",
        caption=f"{n_sig} of {n_total} cells significant at p < 0.05"
                + (" (only these are drawn)." if mask_ns else "."),
        key="map_trend")

# ----------------------------------------------------------- two-year A/B ---
else:
    c1, c2 = st.columns(2)
    y1 = c1.select_slider("Left year", options=list(years), value=int(years[0]))
    y2 = c2.select_slider("Right year", options=list(years), value=int(years[-1]))
    zr = common_range(value_col, [y1, y2])

    for col, yr_sel, key in ((c1, y1, "ab_left"), (c2, y2, "ab_right")):
        d = frame(yr_sel, value_col)
        d["value"] = units.convert(d["value"])
        fig = plots.grid_map(
            d, "value", unit=unit_label, zrange=zr,
            title=f"{METRIC_LABELS.get(metric, metric)}, {yr_sel}")
        fig.update_layout(height=430)
        with col:
            export.panel(fig, f"map_{metric}_{yr_sel}", key=key)

    st.caption("Both panels share one colour scale, so the difference you see "
               "is a difference in the data.")

st.divider()
st.caption(
    "The 0.5 degree and 0.1 degree downscaled products exist but are not "
    "served interactively; static high-resolution panels are produced in "
    "MATLAB for the regions that need them.")
