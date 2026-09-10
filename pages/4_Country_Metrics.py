"""Per-country levels, trends, rankings, and single-country profile cards."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from o3dash import export, io, plots, theme, timeseries, ui

ui.guard("Country Metrics")
units = theme.unit_picker()
ui.embargo_note()

ui.page_header(
    "Country Metrics",
    "Country roll-ups of the gridded fields, population-weighted. Countries "
    "covered by very few grid cells are shown with that caveat attached.",
)

if not io.require("Country Metrics"):
    st.stop()

ct = io.country_trends().copy()
cs = io.country_series()

LEVEL_COLS = {"MeanAnnual_recent": "Recent annual mean",
              "MeanOSDMA8_recent": "Recent OSDMA8"}
SLOPE_COLS = {"SlopeAnnual_ppb_per_decade": "Annual-mean trend",
              "SlopeOSDMA8_ppb_per_decade": "OSDMA8 trend"}

min_cells = st.sidebar.slider(
    "Minimum grid cells per country", 1, 25, 3,
    help="Small countries may be represented by a single 1 degree cell. "
         "Raising this filters out roll-ups that are not really spatial means.")
min_pop = st.sidebar.number_input(
    "Minimum population", min_value=0, value=0, step=1_000_000)

filt = ct[(ct["nCells"] >= min_cells) & (ct["Pop"] >= min_pop)].copy()
st.caption(f"{len(filt)} of {len(ct)} countries pass the coverage filter.")

tab_map, tab_rank, tab_profile, tab_compare = st.tabs(
    ["Map", "Rankings", "Country profile", "Compare two"])

# -------------------------------------------------------------------- map ---
with tab_map:
    layer = st.radio(
        "Layer", ["Recent level", "Trend", "Trend agreement"], horizontal=True,
        help="Trend agreement is the fraction of a country's cells whose own "
             "trend is significant at p < 0.05.")
    if layer == "Recent level":
        col = st.selectbox("Metric", list(LEVEL_COLS),
                           format_func=LEVEL_COLS.get)
        d = filt.dropna(subset=[col]).copy()
        d["value"] = units.convert(d[col])
        fig = plots.choropleth(d, "ISO3", "value", hover_name="CountryName",
                               unit=units.label,
                               title=f"{LEVEL_COLS[col]} ({units.label})")
        cap = "Population-weighted mean over the most recent 10 years."
    elif layer == "Trend":
        col = st.selectbox("Metric", list(SLOPE_COLS),
                           format_func=SLOPE_COLS.get)
        d = filt.dropna(subset=[col]).copy()
        d["value"] = units.convert(d[col])
        fig = plots.choropleth(d, "ISO3", "value", hover_name="CountryName",
                               unit=f"{units.label}/dec", diverging=True,
                               title=f"{SLOPE_COLS[col]} ({units.label}/decade)")
        cap = "Red is rising ozone, blue falling. Neutral grey is no change."
    else:
        d = filt.dropna(subset=["FracCellsSignif"]).copy()
        d["value"] = d["FracCellsSignif"] * 100
        fig = plots.choropleth(d, "ISO3", "value", hover_name="CountryName",
                               unit="% of cells",
                               title="Cells with a significant trend (p < 0.05)")
        cap = ("Where this is low, the country mean trend is not backed by its "
               "own grid cells -- read the trend map with that in mind.")
    export.panel(fig, f"country_map_{layer}", caption=cap, key="cmap")

# --------------------------------------------------------------- rankings ---
with tab_rank:
    col = st.selectbox("Rank by", list(SLOPE_COLS) + list(LEVEL_COLS),
                       format_func=lambda c: {**SLOPE_COLS, **LEVEL_COLS}[c],
                       key="rank_col")
    n = st.slider("How many", 10, 50, 20, step=5)
    direction = st.radio("End", ["Highest", "Lowest"], horizontal=True)

    d = filt.dropna(subset=[col]).copy()
    d["value"] = units.convert(d[col])
    d = d.sort_values("value", ascending=(direction == "Lowest")).head(n)
    unit_txt = f"{units.label}/decade" if col in SLOPE_COLS else units.label
    col_label = {**SLOPE_COLS, **LEVEL_COLS}[col]
    fig = plots.ranked_bar(
        d, "CountryName", "value",
        title=f"{direction} {n}: {col_label}",
        x_title=unit_txt)
    export.panel(fig, f"country_rank_{col}", key="rank")

    show = d[["CountryName", "ISO3", "nCells", "Pop", "value",
              "FracCellsSignif"]].rename(
        columns={"value": unit_txt, "FracCellsSignif": "Frac. cells signif."})
    st.dataframe(show.round(3), width="stretch", hide_index=True)

# ---------------------------------------------------------------- profile ---
with tab_profile:
    names = sorted(filt["CountryName"].dropna().unique().tolist())
    if not names:
        st.info("No countries pass the current filter.")
    else:
        name = st.selectbox("Country", names)
        row = filt[filt["CountryName"] == name].iloc[0]

        ui.tiles([
            ("Recent annual mean",
             f"{units.convert(row['MeanAnnual_recent']):.1f} {units.label}",
             "population-weighted, last 10 yr"),
            ("Recent OSDMA8",
             f"{units.convert(row['MeanOSDMA8_recent']):.1f} {units.label}",
             "ozone-season metric"),
            ("Annual-mean trend",
             f"{units.convert(row['SlopeAnnual_ppb_per_decade']):+.2f}",
             f"{units.label} per decade",
             "warning" if row["SlopeAnnual_ppb_per_decade"] > 0 else None),
            ("Grid cells", f"{int(row['nCells'])}",
             f"{row['FracCellsSignif'] * 100:.0f}% with a significant trend"),
        ])
        st.write("")

        if cs is None:
            st.info(
                "The per-country annual series is not exported yet. Run "
                "`matlab_export/exportCountrySeries.m` to enable the series "
                "panel here; `country_trends.csv` alone carries only the "
                "recent means and slopes shown above.")
        else:
            sub = cs[cs["CountryName"] == name].sort_values("Year").copy()
            metric_col = st.radio(
                "Metric", [c for c in ["AnnualMean", "OSDMA8"] if c in sub.columns],
                horizontal=True, key="profile_metric")
            sub["Value"] = units.convert(sub[metric_col])
            fig = plots.line_series(sub, "Year", "Value",
                                    title=f"{name} - {metric_col}",
                                    y_title=units.axis())
            sen = timeseries.theil_sen(sub["Year"], sub["Value"])
            if np.isfinite(sen.slope_per_decade):
                yr = sub["Year"].to_numpy(float)
                fig.add_scatter(x=yr, y=sen.fit_line(yr), mode="lines",
                                showlegend=False, hoverinfo="skip",
                                line=dict(color=theme.TEXT_MUTED, width=1.5,
                                          dash="dash"))
            export.panel(
                fig, f"country_profile_{row['ISO3']}",
                caption=f"Theil-Sen {sen.label(units.label)} over the "
                        "displayed period.",
                key="profile_series")

        if int(row["nCells"]) < 3:
            st.warning(
                f"{name} is covered by {int(row['nCells'])} grid cell(s). Treat "
                "this as a point estimate rather than a national mean.")

# ---------------------------------------------------------------- compare ---
with tab_compare:
    names = sorted(filt["CountryName"].dropna().unique().tolist())
    c1, c2 = st.columns(2)
    a = c1.selectbox("First", names, index=0 if names else None, key="cmp_a")
    b = c2.selectbox("Second", names,
                     index=min(1, len(names) - 1) if names else None, key="cmp_b")
    if cs is None:
        st.info("Per-country series required for the comparison view.")
    elif a and b:
        sub = cs[cs["CountryName"].isin([a, b])].copy()
        metric_col = "AnnualMean" if "AnnualMean" in sub.columns else sub.columns[-1]
        sub["Value"] = units.convert(sub[metric_col])
        colors = {a: theme.CATEGORICAL[0], b: theme.CATEGORICAL[1]}
        fig = plots.line_series(sub, "Year", "Value", color="CountryName",
                                colors=colors, title=f"{a} vs {b}",
                                y_title=units.axis())
        export.panel(fig, f"country_compare_{a}_{b}", key="cmp_series")

        rows = []
        for nm in (a, b):
            r = filt[filt["CountryName"] == nm].iloc[0]
            rows.append({
                "Country": nm,
                f"Recent mean ({units.label})":
                    units.convert(r["MeanAnnual_recent"]),
                f"Trend ({units.label}/dec)":
                    units.convert(r["SlopeAnnual_ppb_per_decade"]),
                "Cells": int(r["nCells"]),
                "Frac. signif.": r["FracCellsSignif"],
            })
        st.dataframe(pd.DataFrame(rows).round(3), width="stretch",
                     hide_index=True)
