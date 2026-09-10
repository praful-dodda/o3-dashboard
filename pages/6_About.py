"""Coverage, methods in brief, and the caveats that travel with the figures."""
from __future__ import annotations

import streamlit as st

from o3dash import config, io, ui

ui.guard("About")
ui.embargo_note()

ui.page_header(
    "About this dataset",
    "What the fields are, how they were made, and what they cannot be asked "
    "to answer.",
)

st.subheader("Product")
st.markdown(
    "Global monthly maximum daily 8-hour average (MDA8) surface ozone, "
    "1990-2022, on a 1 degree land grid, with 0.5 degree and 0.1 degree "
    "downscaled versions. Each estimate carries a posterior variance.\n\n"
    "Fields are produced by **Bayesian Maximum Entropy** fusion: TOAR-II "
    "station observations enter as hard data; RAMP-corrected chemical "
    "transport model and satellite products enter as soft data with their own "
    "uncertainty. A separable space-time global offset is removed before "
    "estimation and added back afterwards."
)

st.subheader("Metrics")
st.markdown(
    "| Metric | Definition |\n|---|---|\n"
    "| Annual mean | Mean of the twelve monthly MDA8 values |\n"
    "| OSDMA8 | Highest 6-month running mean of monthly MDA8 (ozone season) |\n"
    "| DJF / MAM / JJA / SON | Calendar-season means |\n"
    "| Seasonal amplitude | Highest minus lowest seasonal mean |\n"
    "| Peak month | Calendar month of the annual maximum |\n"
)

st.subheader("Weighting")
st.markdown(
    "Regional and country values are reported **area-weighted** "
    "(cos-latitude) and **population-weighted** (2019 population mapped onto "
    "the grid). They answer different questions: area-weighted describes the "
    "atmosphere, population-weighted describes exposure. The two diverge, and "
    "that divergence is itself a result."
)

st.subheader("Fusion configuration")
st.markdown(
    "The soft-data configuration used for each year is the best-performing "
    "one for that era, selected by checkerboard cross-validation against "
    "held-out stations. Configuration-by-configuration skill numbers are part "
    "of the manuscript and are not reproduced here."
)

st.subheader("Caveats")
st.markdown(
    "- **1989 has no TOAR-II data file.** The 1990 estimation window is built "
    "from the months that exist; treat 1990 as the weakest year in the record.\n"
    "- **Station density is not uniform.** Europe, North America and East Asia "
    "are well constrained; much of Africa, South America and central Asia "
    "leans on the soft data. Uncertainty maps show where.\n"
    "- **Country roll-ups inherit the grid.** A country covered by one or two "
    "1 degree cells is a point estimate wearing a national label. The country "
    "pages expose the cell count and the fraction of cells with a significant "
    "trend so this is visible rather than buried.\n"
    "- **Trends are sensitive to the window.** Slopes over 1990-2022 and over "
    "sub-periods can differ in sign; the rolling-trend view exists to make "
    "that explicit rather than to hide it.\n"
    "- **Downscaled products add spatial detail, not new information.** The "
    "0.1 degree fields redistribute the coarse estimate using a modelled "
    "spatial pattern; they do not resolve sub-grid sources."
)

st.subheader("Units")
st.markdown(
    f"Values are stored in ppb and converted for display at "
    f"**{config.UG_PER_PPB} µg m⁻³ per ppb**, the value used throughout the "
    "analysis. Use the sidebar toggle on any page to switch."
)

st.divider()

st.subheader("Data products behind these pages")
rows = ["| File | Contents | Produced by | Present |", "|---|---|---|---|"]
for name, (producer, desc) in config.DATA_FILES.items():
    mark = "yes" if io.available(name) else "no"
    rows.append(f"| `{name}` | {desc} | `{producer}` | {mark} |")
st.markdown("\n".join(rows))

st.info(
    "This application reads only the aggregated products above. It never "
    "opens the raw BME estimates, the 0.1 degree downscaling tree, or the "
    "validation outputs.")

st.divider()
st.caption(config.CITATION)
st.caption(config.EMBARGO_NOTICE)
