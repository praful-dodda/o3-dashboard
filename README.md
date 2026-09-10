# Surface Ozone Dashboard (1990–2022)

Streamlit dashboard over the BME-fused global monthly MDA8 ozone product:
maps, regional and country time series, and population exposure.

> **Pre-publication.** The paper is not out. This app is deployed from a
> **private** repository to a Streamlit Community Cloud app with a **viewer
> allowlist**. Panels export as images; the underlying data are not
> downloadable from the app, and there are no CSV export buttons anywhere.

---

## Quick start

```bash
conda create -n o3dash python=3.11 -y
conda activate o3dash
pip install -r requirements.txt

streamlit run app.py
```

Without the export step the app still starts — each page shows exactly which
product it is waiting for and which script writes it.

## Tests

```bash
python -m pytest tests -q     # 26 passed
```

Verified 2026-08-31 on Python 3.14.6 / pandas 3.0.3 / streamlit 1.58.0 /
plotly 6.7.0 / kaleido 1.4.0: 26 unit tests, all seven pages rendered through
`streamlit.testing.v1.AppTest` with no exceptions, and a PNG export produced
through `export.panel`'s kaleido path.

The exported products were reconciled against the MATLAB CSVs they sit beside:

| Check | Result |
|-------|--------|
| Python Theil-Sen vs `regional_trends.csv` (global, area-weighted) | 0.780 ppb/decade, p = 0.00069 — identical to 5 dp |
| `grid_annual.parquet` area-weighted global mean vs `regional_series.csv` | 0.000 ppb difference in 1990 and 2022 |
| `country_series.csv` trailing-decade mean vs `country_trends.csv` | max abs. difference 0.0000 over 218 countries |

The middle row is the one worth rerunning after any change to the export: it is
the only thing that catches `exportForDashboard` having composed a *different*
cube from the one the CSVs came from.

MATLAB-side self-tests:

```matlab
exportCountrySeries('--selftest')
exportGridFields('--selftest')
```

`exportCountrySeries`'s self-test asserts agreement with
`regionalCountrySummary.m` — the trailing-10-year mean of the series it writes
equals `MeanAnnual_recent` in `country_trends.csv`. If those two ever diverge,
the country pages are showing two different things.

---

## Layout

```
o3-dashboard/                 # this repo IS the Streamlit Cloud app root
├── app.py                    # entry point, data-status panel
├── pages/
│   ├── 1_Overview.py         # headline tiles + hero line and trend map
│   ├── 2_Maps.py             # level / anomaly / trend / two-year compare
│   ├── 3_Time_Series.py      # regions, decomposition, season shape, facets
│   ├── 4_Country_Metrics.py  # choropleths, rankings, profile cards, compare
│   ├── 5_Exposure.py         # population above WHO thresholds
│   └── 6_About.py            # coverage, methods in brief, caveats
├── o3dash/
│   ├── config.py             # paths, the data contract, constants
│   ├── io.py                 # cached loaders; every one tolerates a missing file
│   ├── ui.py                 # access gate, page setup, stat-tile rows
│   ├── theme.py              # palette, units, plotly template
│   ├── plots.py              # figure factories (all charts come from here)
│   ├── timeseries.py         # Theil–Sen, OLS+AR(1), anomalies, rolling trend
│   └── export.py             # poster-quality PNG panel download
├── matlab_export/
│   ├── exportForDashboard.m  # driver — run this one
│   ├── exportCountrySeries.m # NEW product: per-country annual series
│   └── exportGridFields.m    # NEW product: per-cell annual metrics
├── scripts/sync_data.py
└── tests/test_o3dash.py
```

## Data contract

The app reads **only** small aggregated products. It never opens the raw BME
estimates, the 9.2 GB `8postprocess/downscaleG5NR/` tree, `0cache/`, `1data/`,
or `7validation/`.

| File | Source |
|---|---|
| `regional_series.csv`, `popweighted_annual.csv`, `seasonal_means_trends.csv` | `annualSeasonalSeries.m` |
| `regional_trends.csv`, `trend_ols_regional.csv`, `trend_twoperiod_regional.csv` | `annualSeasonalSeries.m` |
| `peak_month_trend.csv` | `peakMonthAnalysis.m` |
| `country_trends.csv` | `regionalCountrySummary.m` |
| `exposure_by_threshold.csv`, `exposure_trends.csv` | `exposureMetrics.m` |
| **`country_series.csv`** | **`matlab_export/exportCountrySeries.m`** (new) |
| **`grid_annual.parquet`** | **`matlab_export/exportGridFields.m`** (new) |

The last two did not exist before this dashboard. `country_trends.csv` carries
only a recent-decade snapshot and a slope per country — no year axis — so the
country profile cards had nothing to plot until `exportCountrySeries.m` was
added.

`data/` **is** committed (~10 MB, `grid_annual.parquet` 7.4 MB). Streamlit Community
Cloud serves only what is in the repository, so the app's inputs have to be tracked —
which is exactly why this repo is **private**. Set `O3DASH_DATA_DIR` to read them from
somewhere else during development.

### Refreshing the data from the analysis repo

This repo holds only the app and its inputs. The products are generated in the
`gO3_II_mo` analysis repo, which is where MATLAB and the 200 GB of raw data live:

```matlab
% in gO3_II_mo, at the repository root
>> addpath(genpath('.')); exportForDashboard
```

That writes `gO3_II_mo/dashboard/data/`. Copy the result over and commit it:

```bash
cp /path/to/gO3_II_mo/dashboard/data/* data/
python scripts/sync_data.py --source /path/to/gO3_II_mo/8postprocess --dry-run  # check
git add data && git commit -m "Refresh exported products"
```

`matlab_export/*.m` is mirrored here so the export code travels with the app; the
copies in `gO3_II_mo/dashboard/matlab_export/` are the ones that actually run.

---

## Deployment (private repo + viewer allowlist)

1. This repository is **private** on GitHub. Keep it that way — it carries the
   unpublished product, not just the code that draws it.
2. On [share.streamlit.io](https://share.streamlit.io), create an app pointing
   at `app.py` on the default branch. Streamlit Cloud reads private repos once
   you grant the GitHub OAuth scope.
3. In **Settings → Sharing**, set the app to *specific viewers* and add each
   co-author's Google account. This is the real access control.
4. Optionally add a second gate in **Settings → Secrets**:
   ```toml
   app_password = "..."
   ```
   With no `app_password` set, the app relies on the allowlist alone.

Every page calls `ui.guard()` rather than gating only `app.py`, because
Streamlit pages are reachable directly by URL.

### Repo size

Streamlit Cloud clones the whole repository and runs it in ~1 GB of RAM. That is
the reason the app lives in its own repo rather than in `gO3_II_mo`: this tree is
~10 MB, all of it data the app actually reads. Nothing that is not read at runtime
belongs here.

---

## Design rules the code enforces

Charts follow one visual system so panels compose side by side in a figure.

- **One y-axis, ever.** Two measures on different scales become two panels.
- **Sequential = one hue** (blue, light→dark) for magnitude;
  **diverging = blue↔red with a neutral grey midpoint** for trends and
  anomalies. Never a rainbow, never a hue at the midpoint.
- **Colour follows the entity, not its rank.** `theme.stable_colors()` maps
  regions to fixed slots, so filtering a region out never repaints the others.
  There is a test for this.
- **Legend whenever ≥2 series** (a single series is named by the title);
  ≤4 series are also direct-labelled, so identity never rests on colour alone.
- **Nominal categories get one colour**, never a value ramp — bar length
  already encodes the value.
- **Fixed colour scales across compared panels**, so an A/B difference is a
  difference in the data.
- Categorical hues are the `dataviz` reference palette, used unchanged; its
  documented validation (worst adjacent CVD ΔE 9.1 on the light surface) is
  what this app relies on. **Re-run
  `dataviz/scripts/validate_palette.js` if you change any hex value.**
  Forms that put every pair on screen at once (scatter, categorical
  choropleth) are capped at `theme.CATEGORICAL_ALLPAIRS` — the first three
  slots.

## Export policy

`o3dash/export.py` is the only export path: a poster-quality PNG with the
citation and embargo line stamped into the footer. This is deliberate — it
publishes the picture, not the data. If you add a `st.download_button` for a
dataframe, you have broken the embargo policy.

---

## Known limitations

- **Monthly STL decomposition is stubbed.** `timeseries.decompose()` is
  implemented and tested-ready, but the current export is annual, so the
  Time Series page shows a rolling 15-year Sen slope instead. Add a
  `region_monthly.csv` export to switch it on.
- **Maps are markers, not a raster.** One square per grid cell — honest about
  the native 1° resolution, but not pretty at high zoom. A COG/tile layer is
  the upgrade path.
- **0.5° and 0.1° products are not served interactively.** They are far too
  large for Community Cloud's memory limit; produce static panels in MATLAB
  for the regions that need them.
- **Trend maps recompute per request.** ~18k cells × 33 years is a few seconds
  uncached. If it becomes annoying, precompute slopes into `grid_annual` or
  read the existing `8postprocess/maps/trend_sen_*.nc`.
