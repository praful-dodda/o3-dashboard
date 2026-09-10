"""Population living above WHO ozone thresholds, through time."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from o3dash import export, io, plots, theme, timeseries, ui
from o3dash.config import UG_PER_PPB

ui.guard("Exposure")
ui.embargo_note()

ui.page_header(
    "Exposure",
    "How much of the world's population lives where ozone exceeds each WHO "
    "reference level, and whether that share is moving.",
)

if not io.require("Exposure"):
    st.stop()

exp = io.exposure_by_threshold().copy()
trends = io.exposure_trends()

thresholds = sorted(exp["Threshold_ugm3"].dropna().unique().tolist())
chosen = st.sidebar.multiselect(
    "Thresholds", thresholds, default=thresholds,
    format_func=lambda t: f"{t:.0f} µg m⁻³ "
                          f"({t / UG_PER_PPB:.0f} ppb)")
if not chosen:
    st.info("Select at least one threshold.")
    st.stop()

sub = exp[exp["Threshold_ugm3"].isin(chosen)].copy()
sub["Threshold"] = sub["Threshold_ugm3"].map(
    lambda t: f"{t:.0f} µg m⁻³")

# ------------------------------------------------------------------ tiles ---
latest = int(sub["Year"].max())
tile_items = []
for t in sorted(chosen)[:4]:
    row = sub[(sub["Threshold_ugm3"] == t) & (sub["Year"] == latest)]
    if not len(row):
        continue
    r = row.iloc[0]
    first = sub[(sub["Threshold_ugm3"] == t)].sort_values("Year").iloc[0]
    delta = r["PctPopAbove"] - first["PctPopAbove"]
    tile_items.append((
        f"Above {t:.0f} µg m⁻³",
        f"{r['PctPopAbove']:.1f}%",
        f"{delta:+.1f} pp since {int(first['Year'])}",
        "critical" if delta > 2 else ("good" if delta < -2 else None)))
if tile_items:
    ui.tiles(tile_items)
    st.caption(f"Share of world population, {latest}. pp = percentage points.")

st.write("")

# ------------------------------------------------------------- population ---
measure = st.radio(
    "Measure", ["PctPopAbove", "PctAreaAbove", "PopAbove"], horizontal=True,
    format_func=lambda m: {"PctPopAbove": "% of population",
                           "PctAreaAbove": "% of land area",
                           "PopAbove": "People (absolute)"}[m])

d = sub.copy()
if measure == "PopAbove":
    d["Value"] = d[measure] / 1e9
    y_title = "Billion people above threshold"
else:
    d["Value"] = d[measure]
    y_title = "% above threshold"

fig = plots.line_series(
    d, "Year", "Value", color="Threshold",
    title="Exposure above WHO ozone reference levels", y_title=y_title)
export.panel(
    fig, f"exposure_{measure}",
    caption="Thresholds are ordered levels, so they read as one family rather "
            "than unrelated categories.",
    key="exposure_lines")

st.divider()

# ------------------------------------------------------------------ trends --
left, right = st.columns([3, 2])

with left:
    st.subheader("Trend in exposed share")
    if trends is not None and len(trends):
        t = trends[trends["Threshold_ugm3"].isin(chosen)].copy()
        t["Threshold"] = t["Threshold_ugm3"].map(
            lambda v: f"{v:.0f} µg m⁻³")
        t["Significant"] = t["pValue"] < 0.05
        show = t[["Threshold", "StartPct", "EndPct",
                  "SlopePctPop_per_decade", "pValue", "Significant"]].rename(
            columns={"StartPct": "Start %", "EndPct": "End %",
                     "SlopePctPop_per_decade": "pp per decade",
                     "pValue": "p"})
        st.dataframe(show.round(3), width="stretch", hide_index=True)

        db = t.copy()
        fig2 = plots.dumbbell(db, "Threshold", "StartPct", "EndPct",
                              "Start of record", "End of record",
                              title="Exposed share, first year vs last",
                              x_title="% of world population")
        export.panel(fig2, "exposure_dumbbell", key="exposure_db")
    else:
        st.caption("`exposure_trends.csv` not available.")

with right:
    st.subheader("Reading this")
    st.markdown(
        "- **Percent of population** moves with both ozone and where people "
        "live; **percent of land area** isolates the atmospheric signal.\n"
        "- A flat percentage with a growing population still means more "
        "people exposed - switch the measure to *People (absolute)*.\n"
        "- Thresholds are peak-season metrics as defined in the analysis, not "
        "annual means, so they are not directly comparable to the Overview "
        "headline number."
    )
    st.caption(f"Conversion uses {UG_PER_PPB} µg m⁻³ per ppb, "
               "matching the analysis.")
