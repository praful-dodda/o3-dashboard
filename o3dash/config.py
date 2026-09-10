"""Paths, constants and the data contract for the dashboard.

Every file the app reads is listed in DATA_FILES. Nothing else is touched at
runtime -- in particular the app never opens .mat files, the 9.2 GB
downscaleG5NR tree, or anything under 7validation/.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_DIR.parent

# ppb -> ug/m3 conversion. Matches runPostprocess.m default d.ugPerPpb = 2.0,
# so exposure thresholds line up with the published tables.
UG_PER_PPB = 2.0

BASELINE_PERIOD = (1990, 2010)  # climatology window for anomaly views
FULL_PERIOD = (1990, 2022)

# Deployment reads dashboard/data/. Local development falls back to the
# MATLAB output tree so you can iterate without running the sync step.
_FALLBACKS = [
    APP_DIR / "data",
    REPO_ROOT / "8postprocess" / "csv",
    REPO_ROOT / "8postprocess",  # ref_published_trends.csv lives here, not in csv/
]


def data_dir() -> Path:
    override = os.environ.get("O3DASH_DATA_DIR")
    if override:
        return Path(override)
    return APP_DIR / "data"


def resolve(name: str) -> Path | None:
    """First existing location of ``name``, or None."""
    override = os.environ.get("O3DASH_DATA_DIR")
    roots = [Path(override)] if override else _FALLBACKS
    for root in roots:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


# name -> (produced_by, human description)
DATA_FILES = {
    "regional_series.csv": ("annualSeasonalSeries.m", "Area-weighted regional annual series"),
    "popweighted_annual.csv": ("annualSeasonalSeries.m", "Population-weighted regional annual series"),
    "seasonal_means_trends.csv": ("annualSeasonalSeries.m", "Seasonal (DJF/MAM/JJA/SON) regional series"),
    "regional_trends.csv": ("annualSeasonalSeries.m", "Theil-Sen regional trends"),
    "trend_ols_regional.csv": ("annualSeasonalSeries.m", "OLS regional trends with AR(1) correction"),
    "trend_twoperiod_regional.csv": ("annualSeasonalSeries.m", "Early vs late period trend split"),
    "peak_month_trend.csv": ("peakMonthAnalysis.m", "Peak-month timing and season length"),
    "country_trends.csv": ("regionalCountrySummary.m", "Per-country recent means and trends"),
    "country_series.csv": ("matlab_export/exportCountrySeries.m", "Per-country annual series"),
    "exposure_by_threshold.csv": ("exposureMetrics.m", "Population above WHO thresholds by year"),
    "exposure_trends.csv": ("exposureMetrics.m", "Trend in exposed population fraction"),
    "grid_annual.parquet": ("matlab_export/exportGridFields.m", "Per-cell annual metrics for maps"),
    "ref_published_trends.csv": ("manual", "Published trend estimates for comparison"),
}

# Files without which a page cannot render at all.
PAGE_REQUIREMENTS = {
    "Overview": ["regional_series.csv", "regional_trends.csv"],
    "Maps": ["grid_annual.parquet"],
    "Time Series": ["regional_series.csv"],
    "Country Metrics": ["country_trends.csv"],
    "Exposure": ["exposure_by_threshold.csv"],
}

METRIC_LABELS = {
    "AnnualMean": "Annual mean MDA8",
    "OSDMA8": "Ozone-season MDA8 (OSDMA8)",
    "DJF": "Winter (DJF)",
    "MAM": "Spring (MAM)",
    "JJA": "Summer (JJA)",
    "SON": "Autumn (SON)",
    "SeasonAmp": "Seasonal amplitude",
}

WEIGHTING_LABELS = {"area": "Area-weighted", "pop": "Population-weighted"}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Shown on every page and stamped into every exported panel.
EMBARGO_NOTICE = (
    "Pre-publication material. Figures may be shared as infographics; "
    "underlying data are not for redistribution."
)
CITATION = "Dodda et al., global surface MDA8 ozone by BME data fusion, 1990-2022 (in preparation)."
