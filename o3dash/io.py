"""Cached loaders. Every loader tolerates a missing file and returns None."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from . import config


@st.cache_data(show_spinner=False)
def _read_csv(name: str) -> pd.DataFrame | None:
    path = config.resolve(name)
    if path is None:
        return None
    # Region labels contain commas ("Asia, Central"), so they are quoted in the
    # MATLAB output -- always parse with a real CSV reader, never by splitting.
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def _read_parquet(name: str) -> pd.DataFrame | None:
    path = config.resolve(name)
    if path is None:
        return None
    return pd.read_parquet(path)


def available(name: str) -> bool:
    return config.resolve(name) is not None


def missing_files(names) -> list[str]:
    return [n for n in names if not available(n)]


def require(page: str) -> bool:
    """Render a guidance banner and return False when a page cannot load."""
    needed = config.PAGE_REQUIREMENTS.get(page, [])
    missing = missing_files(needed)
    if not missing:
        return True
    st.warning(f"**{page}** needs data that has not been exported yet.")
    for name in missing:
        producer, desc = config.DATA_FILES.get(name, ("unknown", ""))
        st.markdown(f"- `{name}` — {desc}  \n  produced by `{producer}`")
    st.caption(
        "Run `dashboard/matlab_export/exportForDashboard.m` in MATLAB, then "
        "`python scripts/sync_data.py`, to populate `dashboard/data/`."
    )
    return False


# ---------------------------------------------------------------- series ----
def regional_series(weighting: str = "area") -> pd.DataFrame | None:
    """Long-format regional series: RegionSet, Region, Metric, Weighting, Year, Value."""
    if weighting == "pop":
        df = _read_csv("popweighted_annual.csv")
        if df is None:
            df = _read_csv("regional_series.csv")
    else:
        df = _read_csv("regional_series.csv")
    if df is None:
        return None
    if "Weighting" in df.columns:
        df = df[df["Weighting"] == weighting]
    return df.copy()


def seasonal_series() -> pd.DataFrame | None:
    return _read_csv("seasonal_means_trends.csv")


def regional_trends() -> pd.DataFrame | None:
    return _read_csv("regional_trends.csv")


def ols_trends() -> pd.DataFrame | None:
    return _read_csv("trend_ols_regional.csv")


def twoperiod_trends() -> pd.DataFrame | None:
    return _read_csv("trend_twoperiod_regional.csv")


def peak_month() -> pd.DataFrame | None:
    return _read_csv("peak_month_trend.csv")


# --------------------------------------------------------------- country ----
def country_trends() -> pd.DataFrame | None:
    return _read_csv("country_trends.csv")


def country_series() -> pd.DataFrame | None:
    return _read_csv("country_series.csv")


# -------------------------------------------------------------- exposure ----
def exposure_by_threshold() -> pd.DataFrame | None:
    return _read_csv("exposure_by_threshold.csv")


def exposure_trends() -> pd.DataFrame | None:
    return _read_csv("exposure_trends.csv")


def published_trends() -> pd.DataFrame | None:
    return _read_csv("ref_published_trends.csv")


# ------------------------------------------------------------------ grid ----
def grid_annual() -> pd.DataFrame | None:
    """Per-cell annual metrics: lon, lat, Year, AnnualMean, OSDMA8, ..."""
    return _read_parquet("grid_annual.parquet")


@st.cache_data(show_spinner=False)
def grid_year(year: int, metric: str) -> pd.DataFrame | None:
    df = grid_annual()
    if df is None or metric not in df.columns:
        return None
    out = df.loc[df["Year"] == year, ["lon", "lat", metric]].dropna()
    return out.rename(columns={metric: "value"})


@st.cache_data(show_spinner="Fitting per-cell trends...")
def cell_trends(metric: str, lo: int, hi: int,
                method: str = "theil-sen") -> pd.DataFrame | None:
    """Per-cell slope (ppb/decade) and p-value over [lo, hi].

    Cached because this is ~18k independent fits -- several seconds cold, and
    both the Overview hero map and the Maps trend view want the same answer.
    Values are in ppb; convert for display at the call site.
    """
    from . import timeseries  # local import keeps the module import graph flat

    df = grid_annual()
    if df is None or metric not in df.columns:
        return None
    sel = df[df["Year"].between(lo, hi)]
    cells = sel.pivot_table(index=["lon", "lat"], columns="Year", values=metric)
    if cells.empty:
        return None

    years = np.asarray(cells.columns, dtype=float)
    fit = timeseries.ols_ar1 if method == "ols-ar1" else timeseries.theil_sen
    values = cells.to_numpy(dtype=float)
    index = cells.index.to_frame(index=False)

    slopes = np.empty(len(values))
    pvals = np.empty(len(values))
    for i in range(len(values)):
        tr = fit(years, values[i])
        slopes[i] = tr.slope_per_decade
        pvals[i] = tr.p_value

    out = index.copy()
    out["slope"] = slopes
    out["p"] = pvals
    return out.dropna(subset=["slope"])


# ----------------------------------------------------------------- utils ----
def region_options(df: pd.DataFrame, region_set: str) -> list[str]:
    if df is None or "RegionSet" not in df.columns:
        return []
    sub = df[df["RegionSet"] == region_set]
    return sorted(sub["Region"].dropna().unique().tolist())


def region_sets(df: pd.DataFrame) -> list[str]:
    if df is None or "RegionSet" not in df.columns:
        return []
    order = ["Global", "areacode", "GBD", "WHO"]
    found = df["RegionSet"].dropna().unique().tolist()
    return [r for r in order if r in found] + [r for r in found if r not in order]
