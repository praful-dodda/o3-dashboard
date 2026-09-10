"""Regional time series, decomposition, and season-timing views."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from o3dash import export, io, plots, theme, timeseries, ui
from o3dash.config import BASELINE_PERIOD, METRIC_LABELS

ui.guard("Time Series")
units = theme.unit_picker()
ui.embargo_note()

ui.page_header(
    "Time Series",
    "Regional trajectories, how much of the change is trend versus season, and "
    "how the shape of the ozone year has moved.",
)

if not io.require("Time Series"):
    st.stop()

weighting = st.sidebar.radio(
    "Weighting", ["area", "pop"], horizontal=True,
    format_func=lambda w: "Area" if w == "area" else "Population")

series = io.regional_series(weighting)
if series is None or not len(series):
    st.warning("No regional series available for this weighting.")
    st.stop()

sets = io.region_sets(series)
region_set = st.sidebar.selectbox("Region set", sets)
regions = io.region_options(series, region_set)

tab_compare, tab_decomp, tab_season, tab_facets = st.tabs(
    ["Compare regions", "Trend and decomposition", "Season shape", "All regions"])

# ------------------------------------------------------- compare regions ----
with tab_compare:
    metrics = sorted(series["Metric"].dropna().unique().tolist())
    metric = st.selectbox("Metric", metrics,
                          index=metrics.index("AnnualMean")
                          if "AnnualMean" in metrics else 0,
                          format_func=lambda m: METRIC_LABELS.get(m, m))
    default = regions[:3]
    chosen = st.multiselect(
        "Regions", regions, default=default,
        help="Colour follows the region, so adding or removing one never "
             "repaints the others.")
    if not chosen:
        st.info("Select at least one region.")
    else:
        if len(chosen) > 8:
            st.warning("Showing the first 8 regions. Use the All regions tab "
                       "for the full set.")
            chosen = chosen[:8]
        sub = series[(series["RegionSet"] == region_set) &
                     (series["Metric"] == metric) &
                     (series["Region"].isin(chosen))].copy()
        sub["Value"] = units.convert(sub["Value"])
        colors = theme.stable_colors(regions)  # stable across filtering
        fig = plots.line_series(
            sub, "Year", "Value", color="Region", colors=colors,
            title=f"{METRIC_LABELS.get(metric, metric)}, {region_set}",
            y_title=units.axis())
        export.panel(fig, f"series_{region_set}_{metric}", key="cmp")

        rows = []
        for reg in chosen:
            d = sub[sub["Region"] == reg].sort_values("Year")
            sen = timeseries.theil_sen(d["Year"], d["Value"])
            ols = timeseries.ols_ar1(d["Year"], d["Value"])
            rows.append({
                "Region": reg,
                f"Start ({units.label})": d["Value"].iloc[0] if len(d) else np.nan,
                f"End ({units.label})": d["Value"].iloc[-1] if len(d) else np.nan,
                f"Sen ({units.label}/dec)": sen.slope_per_decade,
                "Sen p": sen.p_value,
                f"OLS-AR1 ({units.label}/dec)": ols.slope_per_decade,
                "OLS p": ols.p_value,
            })
        st.dataframe(pd.DataFrame(rows).round(3), width="stretch",
                     hide_index=True)
        st.caption("Computed on the displayed slice. Published regional values "
                   "come from the MATLAB trend tables.")

# ---------------------------------------------------------- decomposition ---
with tab_decomp:
    region = st.selectbox("Region", regions, key="decomp_region")
    d = series[(series["RegionSet"] == region_set) &
               (series["Metric"] == "AnnualMean") &
               (series["Region"] == region)].sort_values("Year").copy()
    if not len(d):
        st.info("No annual-mean series for this region.")
    else:
        d["Value"] = units.convert(d["Value"])
        sen = timeseries.theil_sen(d["Year"], d["Value"])
        fig = plots.line_series(d, "Year", "Value",
                                title=f"{region} - annual mean",
                                y_title=units.axis())
        if np.isfinite(sen.slope_per_decade):
            yr = d["Year"].to_numpy(float)
            fig.add_scatter(x=yr, y=sen.fit_line(yr), mode="lines",
                            name="Theil-Sen fit", showlegend=False,
                            line=dict(color=theme.TEXT_MUTED, width=1.5,
                                      dash="dash"), hoverinfo="skip")
            fig.add_annotation(x=yr[-1], y=sen.fit_line(yr)[-1],
                               text=f"  {sen.label(units.label)}",
                               showarrow=False, xanchor="left",
                               font=dict(color=theme.TEXT_SECONDARY, size=11))
            fig.update_layout(margin=dict(r=150))
        export.panel(fig, f"trendfit_{region}", key="decomp_fit")

        st.subheader("Rolling 15-year trend")
        roll = timeseries.rolling_trend(d, "Year", "Value", window=15)
        if len(roll):
            rf = plots.line_series(
                roll, "CentreYear", "SlopePerDecade",
                title="Sen slope in a sliding 15-year window",
                y_title=f"{units.label} per decade")
            rf.add_hline(y=0, line_width=1, line_color=theme.TEXT_MUTED)
            export.panel(rf, f"rolling_{region}",
                         caption="Where this crosses zero, the regional trend "
                                 "changed sign.",
                         key="decomp_roll")
        else:
            st.caption("Series too short for a 15-year window.")

        st.caption(
            "Monthly STL decomposition needs the monthly regional series; the "
            "current export is annual. Add `region_monthly.csv` to enable it.")

# ------------------------------------------------------------ season shape --
with tab_season:
    region = st.selectbox("Region", regions, key="season_region")
    seas = io.seasonal_series()
    if seas is None:
        st.info("`seasonal_means_trends.csv` not available.")
    else:
        sub = seas[(seas["RegionSet"] == region_set) &
                   (seas["Region"] == region)]
        if "Weighting" in sub.columns:
            sub = sub[sub["Weighting"] == weighting]
        sub = sub[sub["Metric"].isin(["DJF", "MAM", "JJA", "SON"])].copy()
        if not len(sub):
            st.info("No seasonal series for this region.")
        else:
            sub["Value"] = units.convert(sub["Value"])
            fig = plots.line_series(
                sub, "Year", "Value", color="Metric",
                title=f"{region} - seasonal means",
                y_title=units.axis())
            export.panel(fig, f"seasonal_{region}", key="season_lines")

            amp = series[(series["RegionSet"] == region_set) &
                         (series["Region"] == region) &
                         (series["Metric"] == "SeasonAmp")].sort_values("Year")
            if len(amp):
                a = amp.copy()
                a["Value"] = units.convert(a["Value"])
                af = plots.line_series(
                    a, "Year", "Value",
                    title=f"{region} - seasonal amplitude",
                    y_title=units.axis("Summer minus winter"))
                export.panel(af, f"amplitude_{region}",
                             caption="A falling amplitude with a rising mean "
                                     "means winter is catching up.",
                             key="season_amp")

    pm = io.peak_month()
    if pm is not None:
        row = pm[(pm["RegionSet"] == region_set) & (pm["Region"] == region)]
        if len(row):
            r = row.iloc[0]
            ui.tiles([
                ("Mean peak month", f"{r.get('MeanPeakMonth', float('nan')):.1f}",
                 "1 = January"),
                ("Peak timing shift",
                 f"{r.get('ShiftDaysPerDecade', float('nan')):+.1f} d",
                 "per decade"),
                ("Season length trend",
                 f"{r.get('SeasonLenTrendPerDecade', float('nan')):+.2f}",
                 "months per decade"),
            ])

# -------------------------------------------------------------- all regions -
with tab_facets:
    metric = st.selectbox("Metric", sorted(series["Metric"].unique()),
                          key="facet_metric",
                          format_func=lambda m: METRIC_LABELS.get(m, m))
    anom = st.checkbox("Show as anomaly from the baseline", value=False,
                       help=f"Baseline {BASELINE_PERIOD[0]}-{BASELINE_PERIOD[1]}")
    sub = series[(series["RegionSet"] == region_set) &
                 (series["Metric"] == metric)].copy()
    if not len(sub):
        st.info("Nothing to show.")
    else:
        sub["Value"] = units.convert(sub["Value"])
        if anom:
            sub["Value"] = sub.groupby("Region", group_keys=False).apply(
                lambda g: timeseries.anomalies(g, "Value",
                                               baseline=BASELINE_PERIOD))
        fig = plots.small_multiples(
            sub, "Year", "Value", "Region", n_cols=4,
            y_title=units.axis(),
            title=f"{METRIC_LABELS.get(metric, metric)} by region"
                  + (" (anomaly)" if anom else ""))
        export.panel(fig, f"facets_{region_set}_{metric}", key="facets")
