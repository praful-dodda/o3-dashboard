"""Headline numbers and the two hero panels."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from o3dash import export, io, plots, theme, timeseries, ui
from o3dash.config import FULL_PERIOD

ui.guard("Overview")
units = theme.unit_picker()
ui.embargo_note()

ui.page_header(
    "Overview",
    "Where global surface ozone stood in 1990, where it stands now, and how "
    "much of that change is statistically resolvable.",
)

if not io.require("Overview"):
    st.stop()


def _global_series(weighting: str, metric: str = "AnnualMean") -> pd.DataFrame:
    df = io.regional_series(weighting)
    if df is None:
        return pd.DataFrame()
    sub = df[(df["RegionSet"] == "Global") & (df["Metric"] == metric)]
    return sub.sort_values("Year")[["Year", "Value"]].copy()


area = _global_series("area")
pop = _global_series("pop")

# ------------------------------------------------------------------ tiles ---
tile_items = []
if len(area):
    first, last = area.iloc[0], area.iloc[-1]
    tile_items.append((
        f"Global mean, {int(last.Year)}",
        f"{units.convert(last.Value):.1f} {units.label}",
        f"{units.convert(first.Value):.1f} in {int(first.Year)}"))

    tr = timeseries.theil_sen(area["Year"], area["Value"])
    tone = "warning" if tr.significant and tr.slope_per_decade > 0 else None
    tile_items.append((
        "Trend, area-weighted",
        f"{units.convert(tr.slope_per_decade):+.2f}",
        f"{units.label} per decade{'' if tr.significant else ', n.s.'}",
        tone))

if len(pop):
    tr_pop = timeseries.theil_sen(pop["Year"], pop["Value"])
    tile_items.append((
        "Trend, population-weighted",
        f"{units.convert(tr_pop.slope_per_decade):+.2f}",
        f"{units.label} per decade{'' if tr_pop.significant else ', n.s.'}",
        "warning" if tr_pop.significant and tr_pop.slope_per_decade > 0 else None))

pm = io.peak_month()
if pm is not None and len(pm):
    g = pm[pm["RegionSet"] == "Global"]
    if len(g) and "ShiftDaysPerDecade" in g.columns:
        shift = float(g["ShiftDaysPerDecade"].iloc[0])
        tile_items.append((
            "Peak-month shift",
            f"{shift:+.1f} d",
            "per decade, global mean timing"))

if tile_items:
    ui.tiles(tile_items[:4])
    st.caption(
        "Trends are Theil-Sen with a Mann-Kendall significance test, computed "
        f"over {FULL_PERIOD[0]}-{FULL_PERIOD[1]} on the series shown below.")

st.write("")

# ------------------------------------------------------------ hero panels ---
left, right = st.columns([1, 1])

with left:
    if len(area) and len(pop):
        combined = pd.concat([
            area.assign(Series="Area-weighted"),
            pop.assign(Series="Population-weighted"),
        ])
        combined["Value"] = units.convert(combined["Value"])
        fig = plots.line_series(
            combined, "Year", "Value", color="Series",
            title="Global annual mean MDA8 ozone",
            y_title=units.axis())
        export.panel(fig, "global_annual_mean",
                     caption="The gap between the two lines is the share of "
                             "the population living where ozone exceeds the "
                             "global land average.",
                     key="hero_line")
    elif len(area):
        area2 = area.assign(Value=units.convert(area["Value"]))
        fig = plots.line_series(area2, "Year", "Value",
                                title="Global annual mean MDA8 ozone",
                                y_title=units.axis())
        export.panel(fig, "global_annual_mean", key="hero_line")

with right:
    sl = io.cell_trends("AnnualMean", *FULL_PERIOD)
    if sl is None:
        st.info(
            "The hero trend map needs `grid_annual.parquet`. Run "
            "`matlab_export/exportGridFields.m` to enable the Maps page and "
            "this panel.")
    else:
        sl = sl.assign(value=units.convert(sl["slope"]))
        fig = plots.grid_map(
            sl, "value", diverging=True,
            title=f"Annual-mean trend, {FULL_PERIOD[0]}-{FULL_PERIOD[1]}",
            unit=f"{units.label}/dec")
        export.panel(fig, "global_trend_map",
                     caption="Theil-Sen slope per grid cell. Red is rising "
                             "ozone, blue falling.",
                     key="hero_map")

st.divider()

# ---------------------------------------------------------- regional split ---
series = io.regional_series("area")
if series is not None:
    sub = series[(series["RegionSet"] == "areacode") &
                 (series["Metric"] == "AnnualMean")].copy()
    if len(sub):
        sub["Value"] = units.convert(sub["Value"])
        fig = plots.line_series(
            sub, "Year", "Value", color="Region",
            title="Annual mean MDA8 by region",
            y_title=units.axis())
        export.panel(fig, "regional_annual_mean",
                     caption="Regional trajectories diverge after the mid-2000s.",
                     key="regional_line")
