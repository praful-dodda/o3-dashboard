"""Figure factories. Every chart in the app comes from here so the visual
language stays consistent and each panel is export-ready."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme
from .config import MONTH_NAMES

LINE_WIDTH = 2
MARKER_SIZE = 8


# ------------------------------------------------------------ stat tile ----
def stat_tile(label: str, value: str, sub: str = "", tone: str | None = None) -> str:
    """A hero number. Used instead of a one-bar chart -- the number IS the chart."""
    accent = theme.STATUS.get(tone, theme.TEXT_PRIMARY) if tone else theme.TEXT_PRIMARY
    return f"""
    <div style="background:{theme.SURFACE_ALT};border-radius:10px;padding:14px 16px;
                height:100%;border:1px solid {theme.GRID};">
      <div style="font-size:12px;letter-spacing:.02em;color:{theme.TEXT_SECONDARY};
                  text-transform:uppercase;">{label}</div>
      <div style="font-size:30px;font-weight:650;line-height:1.15;margin-top:4px;
                  color:{accent};">{value}</div>
      <div style="font-size:12px;color:{theme.TEXT_MUTED};margin-top:2px;">{sub}</div>
    </div>"""


# ---------------------------------------------------------- line charts ----
def line_series(df: pd.DataFrame, x: str, y: str, color: str | None = None,
                title: str = "", y_title: str = "", colors: dict | None = None,
                direct_label: bool = True) -> go.Figure:
    """Multi-series line. Legend whenever >=2 series; a single series gets none
    (the title names it). Up to 4 series are also direct-labelled, so identity
    is never carried by colour alone."""
    fig = go.Figure()
    if color is None:
        groups = [(None, df)]
    else:
        groups = list(df.groupby(color, sort=True))
    colors = colors or theme.stable_colors([str(k) for k, _ in groups if k is not None])

    n = len(groups)
    label_them = direct_label and 2 <= n <= 4
    for key, sub in groups:
        sub = sub.sort_values(x)
        name = str(key) if key is not None else y
        col = colors.get(name, theme.CATEGORICAL[0]) if key is not None else theme.CATEGORICAL[0]
        fig.add_trace(go.Scatter(
            x=sub[x], y=sub[y], mode="lines", name=name,
            line=dict(color=col, width=LINE_WIDTH),
            hovertemplate="%{y:.2f}<extra>" + name + "</extra>",
        ))
        if label_them and len(sub):
            last = sub.iloc[-1]
            fig.add_annotation(x=last[x], y=last[y], text="  " + name,
                               showarrow=False, xanchor="left",
                               font=dict(color=theme.TEXT_SECONDARY, size=11))
    fig.update_layout(
        title=title, yaxis_title=y_title, xaxis_title="",
        showlegend=n >= 2,
        margin=dict(r=110 if label_them else 24),
    )
    fig.update_xaxes(showspikes=True, spikemode="across", spikethickness=1,
                     spikecolor=theme.GRID, spikedash="solid")
    return fig


def band_line(df: pd.DataFrame, x: str, y: str, lo: str, hi: str,
              title: str = "", y_title: str = "", name: str = "") -> go.Figure:
    """One series with an uncertainty / context band."""
    fig = go.Figure()
    col = theme.CATEGORICAL[0]
    fig.add_trace(go.Scatter(
        x=pd.concat([df[x], df[x][::-1]]),
        y=pd.concat([df[hi], df[lo][::-1]]),
        fill="toself", fillcolor="rgba(42,120,214,0.14)",
        line=dict(width=0), hoverinfo="skip", showlegend=False, name="range"))
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines", name=name or y,
                            line=dict(color=col, width=LINE_WIDTH),
                            hovertemplate="%{y:.2f}<extra></extra>"))
    fig.update_layout(title=title, yaxis_title=y_title, showlegend=False)
    return fig


def small_multiples(df: pd.DataFrame, x: str, y: str, facet: str,
                    n_cols: int = 4, y_title: str = "",
                    title: str = "") -> go.Figure:
    """One panel per facet, shared y range. Each panel holds a single series, so
    the all-pairs colour cap does not apply -- every panel uses slot 1."""
    keys = sorted(df[facet].dropna().unique().tolist())
    n_rows = int(np.ceil(len(keys) / n_cols)) if keys else 1
    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=keys,
                        shared_yaxes=True, shared_xaxes=True,
                        vertical_spacing=0.09, horizontal_spacing=0.03)
    for i, key in enumerate(keys):
        r, c = i // n_cols + 1, i % n_cols + 1
        sub = df[df[facet] == key].sort_values(x)
        fig.add_trace(go.Scatter(
            x=sub[x], y=sub[y], mode="lines", showlegend=False,
            line=dict(color=theme.CATEGORICAL[0], width=LINE_WIDTH),
            hovertemplate="%{x}: %{y:.2f}<extra>" + str(key) + "</extra>"),
            row=r, col=c)
    fig.update_layout(title=title, height=210 * n_rows, hovermode="closest")
    fig.update_annotations(font=dict(size=12, color=theme.TEXT_SECONDARY))
    fig.update_yaxes(title_text="")
    fig.update_yaxes(title_text=y_title, row=1, col=1)
    return fig


# -------------------------------------------------------------- heatmap ----
def month_year_heatmap(pivot: pd.DataFrame, title: str = "",
                       unit: str = "ppb", diverging: bool = False) -> go.Figure:
    """Year (x) by calendar month (y). Makes season lengthening visible."""
    if diverging:
        lim = float(np.nanmax(np.abs(pivot.values))) or 1.0
        scale, zmin, zmax = theme.DIVERGING, -lim, lim
    else:
        scale, zmin, zmax = theme.SEQUENTIAL, None, None
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns,
        y=[MONTH_NAMES[m - 1] for m in pivot.index],
        colorscale=scale, zmin=zmin, zmax=zmax,
        colorbar=dict(title=unit, thickness=12, outlinewidth=0, len=0.85),
        hovertemplate="%{x} %{y}: %{z:.2f}<extra></extra>",
        xgap=1, ygap=1))
    fig.update_layout(title=title, hovermode="closest")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False)
    return fig


# ---------------------------------------------------------------- maps -----
def grid_map(df: pd.DataFrame, value_col: str = "value", title: str = "",
             unit: str = "ppb", diverging: bool = False,
             zrange: tuple | None = None, marker_size: float = 3.2) -> go.Figure:
    """Gridded field on a geographic projection.

    One marker per grid cell -- honest about the native resolution rather than
    interpolating for looks. A true raster layer is a later upgrade.
    """
    if diverging:
        lim = zrange[1] if zrange else (float(np.nanmax(np.abs(df[value_col]))) or 1.0)
        scale, cmin, cmax = theme.DIVERGING, -lim, lim
    else:
        scale = theme.SEQUENTIAL
        cmin, cmax = zrange if zrange else (None, None)
    fig = go.Figure(go.Scattergeo(
        lon=df["lon"], lat=df["lat"], mode="markers",
        marker=dict(size=marker_size, color=df[value_col], colorscale=scale,
                    cmin=cmin, cmax=cmax, symbol="square", line=dict(width=0),
                    colorbar=dict(title=unit, thickness=12, outlinewidth=0, len=0.8)),
        hovertemplate="%{lat:.1f}, %{lon:.1f}<br>%{marker.color:.2f}<extra></extra>"))
    fig.update_geos(
        projection_type="robinson", showcoastlines=True,
        coastlinecolor=theme.TEXT_MUTED, coastlinewidth=0.5,
        showcountries=True, countrycolor=theme.GRID, countrywidth=0.4,
        showland=True, landcolor="#FAFAF8", showocean=True,
        oceancolor=theme.SURFACE, showframe=False, lataxis_range=[-60, 85])
    fig.update_layout(title=title, margin=dict(l=8, r=8, t=48, b=8), height=520)
    return fig


def choropleth(df: pd.DataFrame, iso_col: str, value_col: str, title: str = "",
               unit: str = "", diverging: bool = False,
               hover_name: str | None = None) -> go.Figure:
    if diverging:
        lim = float(np.nanmax(np.abs(df[value_col]))) or 1.0
        scale, zmin, zmax = theme.DIVERGING, -lim, lim
    else:
        scale, zmin, zmax = theme.SEQUENTIAL, None, None
    text = df[hover_name] if hover_name else df[iso_col]
    fig = go.Figure(go.Choropleth(
        locations=df[iso_col], z=df[value_col], locationmode="ISO-3",
        colorscale=scale, zmin=zmin, zmax=zmax, text=text,
        marker_line_color=theme.SURFACE, marker_line_width=0.4,
        colorbar=dict(title=unit, thickness=12, outlinewidth=0, len=0.8),
        hovertemplate="%{text}<br>%{z:.2f}<extra></extra>"))
    fig.update_geos(projection_type="robinson", showframe=False,
                    showcoastlines=False, showland=True, landcolor="#FAFAF8",
                    lataxis_range=[-60, 85])
    fig.update_layout(title=title, margin=dict(l=8, r=8, t=48, b=8), height=520)
    return fig


# ------------------------------------------------------------- rankings ----
def ranked_bar(df: pd.DataFrame, label_col: str, value_col: str, title: str = "",
               x_title: str = "", highlight: str | None = None) -> go.Figure:
    """Nominal categories -> ONE colour for every bar (never a value ramp).
    A single entity may be highlighted; the rest recede."""
    d = df.copy()
    base = theme.CATEGORICAL[0]
    if highlight is not None and highlight in set(d[label_col]):
        colors = [base if v == highlight else "#C6D6EA" for v in d[label_col]]
    else:
        colors = base
    fig = go.Figure(go.Bar(
        x=d[value_col], y=d[label_col], orientation="h", marker_color=colors,
        marker_line_width=0,
        hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
    fig.update_layout(title=title, xaxis_title=x_title,
                      height=max(320, 22 * len(d)), hovermode="closest",
                      bargap=0.35)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=theme.GRID)
    return fig


def dumbbell(df: pd.DataFrame, label_col: str, first_col: str, second_col: str,
             first_name: str, second_name: str, title: str = "",
             x_title: str = "") -> go.Figure:
    """Early vs late period comparison -- two states of one entity."""
    d = df.copy()
    fig = go.Figure()
    for _, row in d.iterrows():
        fig.add_trace(go.Scatter(
            x=[row[first_col], row[second_col]], y=[row[label_col]] * 2,
            mode="lines", line=dict(color=theme.GRID, width=2),
            showlegend=False, hoverinfo="skip"))
    for col, name, c in ((first_col, first_name, theme.CATEGORICAL[0]),
                         (second_col, second_name, theme.CATEGORICAL[1])):
        fig.add_trace(go.Scatter(
            x=d[col], y=d[label_col], mode="markers", name=name,
            marker=dict(color=c, size=MARKER_SIZE + 2,
                        line=dict(color=theme.SURFACE, width=2)),
            hovertemplate="%{y}<br>" + name + ": %{x:.2f}<extra></extra>"))
    fig.add_vline(x=0, line_width=1, line_color=theme.TEXT_MUTED)
    fig.update_layout(title=title, xaxis_title=x_title, hovermode="closest",
                      height=max(340, 24 * len(d)))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig
