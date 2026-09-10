# Global Surface Ozone Dashboard (1990–2022)

### ▶ **[Open the dashboard →](https://global-ozone-dashboard.streamlit.app/)**

Thirty-three years of global surface ozone, mapped and summarised: where it is
high, where it is rising, and how many people breathe it. No install, no
download — everything below happens in the browser.

> **Work in preparation.** Dodda et al., *global surface MDA8 ozone by BME data
> fusion, 1990–2022*. Figures may be shared as infographics; the underlying
> fields are not for redistribution or reuse in other analyses ahead of
> publication. Every panel exports as a stamped PNG carrying this line.

---

## What you are looking at

Monthly **MDA8** — the maximum daily 8-hour average ozone concentration, the
metric air-quality standards are written in — estimated for every 1° land cell
on Earth, every month from 1990 to 2022.

The fields come from **Bayesian Maximum Entropy** fusion. TOAR-II ground
stations enter as hard data. RAMP-corrected chemical transport models and
satellite products enter as soft data, each carrying its own uncertainty. The
result is gap-free: it has values over the Sahara and the Andes, where no
monitor has ever stood, and it tells you how much to trust them.

That last part matters more than it sounds. A station network answers "what did
we measure?" This answers "what was the ozone?" — including everywhere nobody
was measuring.

---

## How to read each page

**Overview** — start here. Headline numbers for the full record, one global
trend line, one trend map. If you read nothing else, read this page.

**Maps** — one year at a time, four ways of looking:
- *Level* — the field itself. Where ozone is high.
- *Anomaly* — that year against the 1990–2010 baseline. Where a year was
  unusual.
- *Trend* — the slope at every cell, blue falling, red rising. Tick **"grey out
  cells where p ≥ 0.05"** to hide the cells where the slope is not
  distinguishable from noise. Do that before you read a pattern into it. The
  **Estimator** switch here recomputes the map with OLS + AR(1) instead of
  Theil–Sen; if the pattern survives both, believe it.
- *Compare* — two years side by side. **Both panels share one colour scale**, so
  a visible difference is a real difference, not a rescaled one.

**Time Series** — regional curves, with a **rolling 15-year trend** underneath.
The rolling view is the honest one: it shows that a slope depends on the window
you choose, and that some regions changed direction mid-record. A single number
for 1990–2022 can hide a reversal.

**Country Metrics** — choropleths, rankings, and per-country profile cards.
Each card shows the **cell count** — a country covered by one or two 1° cells is
a point estimate wearing a national flag, and small countries are exactly where
this is worst. Check that number before quoting a national value.

**Exposure** — population above WHO thresholds, by year. This is the
population-weighted view, and it is where the atmosphere and the health story
come apart.

**About** — the methods, the metrics table, and the caveats, in the app itself.

### The one distinction that changes everything

**Area-weighted or population-weighted?** Overview shows both curves together,
Time Series has the switch in the sidebar, and Country Metrics and Exposure are
population-weighted throughout.

- **Area-weighted** describes *the atmosphere* — every square kilometre counts
  the same.
- **Population-weighted** describes *exposure* — a cell counts for as many
  people as live in it.

They give different answers, and the gap between them is itself a finding: air
quality where people actually are is not the global average. Know which one you
are reading — the Overview page puts the two side by side precisely so the gap
is the first thing you see.

Units toggle between **ppb** and **µg m⁻³** (at 2.0 µg m⁻³ per ppb) in the
sidebar.

---

## The metrics

| Metric | What it means |
|---|---|
| Annual mean | Mean of the twelve monthly MDA8 values |
| OSDMA8 | Highest 6-month running mean — the ozone season |
| DJF / MAM / JJA / SON | Calendar-season means |
| Seasonal amplitude | Highest minus lowest seasonal mean |
| Peak month | Calendar month of the annual maximum |

Trends are **Theil–Sen** slopes with **Mann–Kendall** significance — rank-based,
so a single freak year cannot swing them. The trend map also offers OLS with an
AR(1) correction, which accounts for one year resembling the last.

---

## What this cannot tell you

- **1990 is the weakest year in the record.** There is no 1989 TOAR-II file, so
  the 1990 estimation window is built from the months that exist.
- **Station density is not uniform.** Europe, North America and East Asia are
  well constrained. Much of Africa, South America and central Asia leans on the
  soft data — the uncertainty maps show exactly where.
- **Trends depend on the window.** Slopes over 1990–2022 and over sub-periods
  can differ in sign. That is a property of the atmosphere, not a defect; the
  rolling-trend view exists to keep it visible.
- **Downscaled products add detail, not information.** The finer fields
  redistribute the coarse estimate using a modelled spatial pattern. They do not
  resolve a highway or a power plant.
- **Per-configuration skill numbers are not here.** How each fusion setup scored
  in cross-validation belongs to the manuscript.

---

## Citation

> Dodda et al., global surface MDA8 ozone by BME data fusion, 1990–2022 (in
> preparation).

Please cite the paper rather than this URL, and get in touch before building on
the fields themselves.

---

## Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Everything the app reads is in `data/` (~10 MB of aggregated CSV and Parquet).
The fields are generated in MATLAB in the separate analysis repository;
`matlab_export/` holds the export scripts that produce them, and
`scripts/sync_data.py` refreshes `data/` from a post-processing tree. Tests:
`python -m pytest tests -q`.
