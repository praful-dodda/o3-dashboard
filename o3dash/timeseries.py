"""Time-series analysis helpers.

Trends here are computed on the fly for whatever slice the user selected. The
published regional numbers still come from the MATLAB CSVs (trendSenMK /
trend_ols_regional.csv) -- these functions are for interactive exploration and
should agree with them, not replace them.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Trend:
    slope_per_decade: float
    intercept: float
    p_value: float
    n: int
    method: str

    @property
    def significant(self) -> bool:
        return np.isfinite(self.p_value) and self.p_value < 0.05

    def label(self, unit: str = "ppb") -> str:
        if not np.isfinite(self.slope_per_decade):
            return "trend unavailable"
        stars = "" if self.significant else " (n.s.)"
        return f"{self.slope_per_decade:+.2f} {unit}/decade{stars}"

    def fit_line(self, years: np.ndarray) -> np.ndarray:
        return self.intercept + self.slope_per_decade / 10.0 * years


def _clean(years, values):
    y = np.asarray(years, dtype=float)
    v = np.asarray(values, dtype=float)
    ok = np.isfinite(y) & np.isfinite(v)
    return y[ok], v[ok]


def theil_sen(years, values) -> Trend:
    """Theil-Sen slope with a Mann-Kendall p-value (normal approximation with
    tie correction). Mirrors trendSenMK.m."""
    y, v = _clean(years, values)
    n = len(y)
    if n < 4:
        return Trend(np.nan, np.nan, np.nan, n, "theil-sen")

    slopes = []
    for i in range(n - 1):
        dy = y[i + 1:] - y[i]
        dv = v[i + 1:] - v[i]
        nz = dy != 0
        slopes.append(dv[nz] / dy[nz])
    slope = float(np.median(np.concatenate(slopes)))
    intercept = float(np.median(v - slope * y))

    # Mann-Kendall S
    s = 0.0
    for i in range(n - 1):
        s += np.sum(np.sign(v[i + 1:] - v[i]))
    _, counts = np.unique(v, return_counts=True)
    tie = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    if var_s <= 0:
        p = np.nan
    else:
        z = (s - np.sign(s)) / np.sqrt(var_s)
        from scipy.stats import norm
        p = float(2 * (1 - norm.cdf(abs(z))))
    return Trend(slope * 10.0, intercept, p, n, "theil-sen")


def ols_ar1(years, values) -> Trend:
    """OLS slope with an AR(1) correction to the standard error, matching the
    effective-sample-size approach behind trend_ols_regional.csv (phi, nStar)."""
    y, v = _clean(years, values)
    n = len(y)
    if n < 4:
        return Trend(np.nan, np.nan, np.nan, n, "ols-ar1")

    x = y - y.mean()
    slope = float(np.sum(x * (v - v.mean())) / np.sum(x ** 2))
    intercept = float(v.mean() - slope * y.mean())

    resid = v - (intercept + slope * y)
    if n > 2 and np.std(resid) > 0:
        phi = float(np.corrcoef(resid[:-1], resid[1:])[0, 1])
    else:
        phi = 0.0
    phi = min(max(phi, 0.0), 0.99)
    n_star = n * (1 - phi) / (1 + phi)

    dof = max(n_star - 2, 1.0)
    se = float(np.sqrt(np.sum(resid ** 2) / dof / np.sum(x ** 2)))
    from scipy.stats import t as tdist
    p = float(2 * (1 - tdist.cdf(abs(slope / se), dof))) if se > 0 else np.nan
    return Trend(slope * 10.0, intercept, p, n, "ols-ar1")


def climatology(df: pd.DataFrame, value_col: str, year_col: str = "Year",
                baseline: tuple = (1990, 2010)) -> float:
    m = df[year_col].between(*baseline)
    ref = df.loc[m, value_col]
    return float(ref.mean()) if len(ref) else float(df[value_col].mean())


def anomalies(df: pd.DataFrame, value_col: str, year_col: str = "Year",
              baseline: tuple = (1990, 2010)) -> pd.Series:
    return df[value_col] - climatology(df, value_col, year_col, baseline)


def decompose(series: pd.Series, period: int = 12, robust: bool = True):
    """STL decomposition. ``series`` must be indexed by time and regularly
    spaced. Returns None when statsmodels is unavailable or the series is too
    short (STL needs at least two full cycles)."""
    if series.dropna().shape[0] < 2 * period:
        return None
    try:
        from statsmodels.tsa.seasonal import STL
    except ImportError:
        return None
    filled = series.interpolate(limit_direction="both")
    return STL(filled, period=period, robust=robust).fit()


def rolling_trend(df: pd.DataFrame, year_col: str, value_col: str,
                  window: int = 15) -> pd.DataFrame:
    """Sen slope in a sliding window -- shows when a trend changed sign without
    committing to a formal changepoint model."""
    d = df.sort_values(year_col)
    years = d[year_col].to_numpy(float)
    vals = d[value_col].to_numpy(float)
    out = []
    for i in range(len(d) - window + 1):
        sl = slice(i, i + window)
        tr = theil_sen(years[sl], vals[sl])
        out.append({"CentreYear": float(np.mean(years[sl])),
                    "SlopePerDecade": tr.slope_per_decade,
                    "pValue": tr.p_value})
    return pd.DataFrame(out)


def to_month_year_pivot(df: pd.DataFrame, year_col: str = "Year",
                        month_col: str = "Month",
                        value_col: str = "Value") -> pd.DataFrame:
    """Month (rows, 1-12) by year (columns) for the heatmap view."""
    p = df.pivot_table(index=month_col, columns=year_col, values=value_col,
                       aggfunc="mean")
    return p.reindex(range(1, 13))


def season_from_month(month: int) -> str:
    return {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
            6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON",
            11: "SON"}[int(month)]
