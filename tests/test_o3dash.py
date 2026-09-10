"""Unit tests for the dashboard helpers.

    cd dashboard && python -m pytest tests -q

These cover the analysis helpers and the figure factories. They deliberately do
not need any real data -- the fixtures are synthetic so the suite runs before
the MATLAB export step.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from o3dash import plots, theme, timeseries  # noqa: E402
from o3dash.config import UG_PER_PPB  # noqa: E402


# ------------------------------------------------------------- fixtures ----
@pytest.fixture
def linear_series():
    years = np.arange(1990, 2023)
    values = 30.0 + 0.08 * (years - 1990)  # +0.8 ppb/decade, exactly
    return years, values


@pytest.fixture
def region_frame():
    years = np.arange(1990, 2023)
    rows = []
    for i, region in enumerate(["CONUS", "Europe", "EastAsia"]):
        for y in years:
            rows.append({"Region": region, "Year": y,
                         "Value": 30 + i * 3 + 0.05 * (y - 1990)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- trends ----
def test_theil_sen_recovers_known_slope(linear_series):
    years, values = linear_series
    tr = timeseries.theil_sen(years, values)
    assert tr.slope_per_decade == pytest.approx(0.8, abs=1e-9)
    assert tr.significant


def test_ols_recovers_known_slope(linear_series):
    years, values = linear_series
    tr = timeseries.ols_ar1(years, values)
    assert tr.slope_per_decade == pytest.approx(0.8, abs=1e-9)


def test_theil_sen_is_robust_to_an_outlier(linear_series):
    years, values = linear_series
    spiked = values.copy()
    spiked[5] += 40.0
    sen = timeseries.theil_sen(years, spiked)
    ols = timeseries.ols_ar1(years, spiked)
    assert abs(sen.slope_per_decade - 0.8) < abs(ols.slope_per_decade - 0.8)


def test_flat_series_is_not_significant():
    years = np.arange(1990, 2023)
    rng = np.random.default_rng(0)
    tr = timeseries.theil_sen(years, 30 + rng.normal(0, 0.01, years.size))
    assert not tr.significant


def test_short_series_returns_nan():
    tr = timeseries.theil_sen([2000, 2001], [10, 11])
    assert np.isnan(tr.slope_per_decade)
    assert not tr.significant


def test_nan_values_are_dropped(linear_series):
    years, values = linear_series
    holed = values.copy()
    holed[3] = np.nan
    tr = timeseries.theil_sen(years, holed)
    assert tr.slope_per_decade == pytest.approx(0.8, abs=1e-9)
    assert tr.n == len(years) - 1


def test_fit_line_passes_through_the_data(linear_series):
    years, values = linear_series
    tr = timeseries.theil_sen(years, values)
    assert np.allclose(tr.fit_line(years.astype(float)), values, atol=1e-8)


def test_rolling_trend_window(linear_series):
    years, values = linear_series
    df = pd.DataFrame({"Year": years, "Value": values})
    roll = timeseries.rolling_trend(df, "Year", "Value", window=15)
    assert len(roll) == len(years) - 15 + 1
    assert np.allclose(roll["SlopePerDecade"], 0.8, atol=1e-8)


def test_anomalies_are_centred_on_the_baseline(linear_series):
    years, values = linear_series
    df = pd.DataFrame({"Year": years, "Value": values})
    anom = timeseries.anomalies(df, "Value", baseline=(1990, 2010))
    base = anom[df["Year"].between(1990, 2010)]
    assert base.mean() == pytest.approx(0.0, abs=1e-9)


def test_month_year_pivot_has_all_twelve_months():
    df = pd.DataFrame({"Year": [2000] * 6, "Month": range(1, 7),
                       "Value": range(6)})
    p = timeseries.to_month_year_pivot(df)
    assert list(p.index) == list(range(1, 13))
    assert p.loc[7:].isna().all().all()


# ----------------------------------------------------------------- units ----
def test_unit_conversion_matches_the_analysis():
    u = theme.Units("ug/m3")
    assert u.factor == UG_PER_PPB
    assert u.convert(np.array([30.0]))[0] == pytest.approx(60.0)
    assert theme.Units("ppb").factor == 1.0


# ------------------------------------------------------------- palette ------
def test_colours_follow_the_entity_not_the_filter(region_frame):
    """Removing a region must not repaint the survivors."""
    all_regions = sorted(region_frame["Region"].unique())
    full = theme.stable_colors(all_regions)
    subset = theme.stable_colors(all_regions)  # same entity list -> same map
    assert full == subset

    fig_all = plots.line_series(region_frame, "Year", "Value", color="Region",
                                colors=full)
    filtered = region_frame[region_frame["Region"] != "CONUS"]
    fig_sub = plots.line_series(filtered, "Year", "Value", color="Region",
                                colors=full)
    colour_of = {t.name: t.line.color for t in fig_sub.data}
    for name, colour in colour_of.items():
        original = next(t.line.color for t in fig_all.data if t.name == name)
        assert colour == original


def test_categorical_palette_is_not_cycled_within_eight():
    assert len(set(theme.CATEGORICAL)) == 8


def test_allpairs_palette_is_capped_at_three():
    assert len(theme.CATEGORICAL_ALLPAIRS) == 3


def test_diverging_midpoint_is_neutral():
    mid = [c for pos, c in theme.DIVERGING if pos == 0.5]
    assert mid == [theme.DIVERGING_NEUTRAL]


# ------------------------------------------------------------- figures ------
def test_single_series_has_no_legend(region_frame):
    one = region_frame[region_frame["Region"] == "Europe"]
    fig = plots.line_series(one, "Year", "Value")
    assert fig.layout.showlegend is False


def test_multi_series_always_has_a_legend(region_frame):
    fig = plots.line_series(region_frame, "Year", "Value", color="Region")
    assert fig.layout.showlegend is True


def test_few_series_are_also_direct_labelled(region_frame):
    fig = plots.line_series(region_frame, "Year", "Value", color="Region")
    assert len(fig.layout.annotations) == 3


def test_many_series_drop_direct_labels():
    rows = []
    for i in range(6):
        for y in range(1990, 2000):
            rows.append({"Region": f"R{i}", "Year": y, "Value": y - 1990 + i})
    fig = plots.line_series(pd.DataFrame(rows), "Year", "Value", color="Region")
    assert len(fig.layout.annotations) == 0
    assert fig.layout.showlegend is True


def test_ranked_bar_uses_one_colour_for_nominal_categories():
    df = pd.DataFrame({"Country": list("ABCD"), "Value": [4, 3, 2, 1]})
    fig = plots.ranked_bar(df, "Country", "Value")
    assert fig.data[0].marker.color == theme.CATEGORICAL[0]


def test_ranked_bar_highlight_recedes_the_rest():
    df = pd.DataFrame({"Country": list("ABCD"), "Value": [4, 3, 2, 1]})
    fig = plots.ranked_bar(df, "Country", "Value", highlight="B")
    colours = list(fig.data[0].marker.color)
    assert colours.count(theme.CATEGORICAL[0]) == 1


def test_grid_map_builds_and_is_diverging_when_asked():
    df = pd.DataFrame({"lon": [0, 10, 20], "lat": [0, 5, 10],
                       "value": [-1.0, 0.0, 2.0]})
    fig = plots.grid_map(df, "value", diverging=True)
    assert fig.data[0].marker.cmin == -2.0
    assert fig.data[0].marker.cmax == 2.0


def test_heatmap_orders_months():
    df = pd.DataFrame({"Year": [2000] * 12, "Month": range(1, 13),
                       "Value": range(12)})
    fig = plots.month_year_heatmap(timeseries.to_month_year_pivot(df))
    assert list(fig.data[0].y)[:3] == ["Jan", "Feb", "Mar"]


def test_small_multiples_one_panel_per_region(region_frame):
    fig = plots.small_multiples(region_frame, "Year", "Value", "Region")
    assert len(fig.data) == 3
    assert all(t.line.color == theme.CATEGORICAL[0] for t in fig.data)


def test_stat_tile_renders_the_value():
    html = plots.stat_tile("Label", "31.4 ppb", "sub")
    assert "31.4 ppb" in html and "Label" in html


def test_no_figure_uses_two_y_axes(region_frame):
    fig = plots.line_series(region_frame, "Year", "Value", color="Region")
    assert not any(k.startswith("yaxis2") for k in fig.layout)
