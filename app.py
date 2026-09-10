"""Entry point for the surface-ozone dashboard.

Run locally:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import streamlit as st

from o3dash import config, io, theme, ui

ui.guard("Home")
ui.embargo_note()

ui.page_header(
    "Global Surface Ozone, 1990-2022",
    "Monthly MDA8 ozone fields produced by Bayesian Maximum Entropy fusion of "
    "TOAR-II station observations with RAMP-corrected chemical transport model "
    "and satellite products. Explore the maps, regional and country time "
    "series, and population exposure.",
)

st.markdown(
    f"<div style='background:{theme.SURFACE_ALT};border-left:3px solid "
    f"{theme.STATUS['warning']};padding:12px 16px;border-radius:6px;'>"
    f"<strong>Pre-publication material.</strong> Panels may be exported and "
    f"shared as infographics. The underlying gridded data are not published "
    f"and are not downloadable from this application.</div>",
    unsafe_allow_html=True)

st.write("")

left, right = st.columns([3, 2])

with left:
    st.subheader("Pages")
    st.markdown(
        "- **Overview** - the headline numbers and the two hero panels.\n"
        "- **Maps** - annual, seasonal and OSDMA8 fields; trends; anomalies; "
        "estimation uncertainty.\n"
        "- **Time Series** - regional series, seasonal decomposition, "
        "month-by-year heatmaps, area- versus population-weighted views.\n"
        "- **Country Metrics** - per-country levels, trends, rankings and "
        "single-country profile cards.\n"
        "- **Exposure** - population above WHO ozone thresholds through time.\n"
        "- **About** - coverage, methods in brief, and caveats."
    )

with right:
    st.subheader("Coverage")
    st.markdown(
        "| | |\n|---|---|\n"
        "| Period | 1990-2022 (monthly) |\n"
        "| Native grid | 1.0 deg, land |\n"
        "| Downscaled | 0.5 deg, 0.1 deg |\n"
        "| Metrics | annual mean, OSDMA8, seasonal, peak month |\n"
        "| Regions | global, area codes, GBD, WHO, country |\n"
    )
    st.caption("1989 has no TOAR-II data file; the 1990 estimation window is "
               "built from the available months only.")

st.divider()

missing = io.missing_files(list(config.DATA_FILES))
if missing:
    with st.expander(f"Data status - {len(missing)} product(s) not yet exported",
                     expanded=False):
        for name in missing:
            producer, desc = config.DATA_FILES[name]
            st.markdown(f"- `{name}` - {desc}  \n  produced by `{producer}`")
        st.caption(
            "Run `dashboard/matlab_export/exportForDashboard.m` in MATLAB from "
            "the repository root, then `python dashboard/scripts/sync_data.py`.")
else:
    st.success("All data products are present.")

st.caption(config.CITATION)
