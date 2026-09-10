"""Shared visual language.

Palette values are the dataviz reference palette, used unchanged so the
documented validation still applies (worst adjacent CVD dE 9.1 on the light
surface). The app pins base="light" in .streamlit/config.toml, so the chart
surface is known and the light column is the one in play.

Rules enforced here rather than per-chart:
  * sequential magnitude  -> one hue, light to dark (blue ramp)
  * polarity (trends, anomalies) -> blue<->red with a NEUTRAL GRAY midpoint
  * categorical identity  -> fixed slot order, never cycled, never re-ranked
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from .config import UG_PER_PPB

# ------------------------------------------------------------- surfaces ----
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F4F6F8"
TEXT_PRIMARY = "#0B0B0B"
TEXT_SECONDARY = "#52514E"
TEXT_MUTED = "#8A8A85"
GRID = "#E6E6E2"

# --------------------------------------------------- categorical (light) ----
# Fixed order. Assign by entity, never by rank; a 9th series folds to "Other".
CATEGORICAL = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]
# Forms that put every pair on screen at once (scatter, bubble, choropleth
# with categorical fill) are capped at the first three slots -- past three the
# all-pairs floors fail. Line charts use the adjacent pairlist and may use all 8.
CATEGORICAL_ALLPAIRS = CATEGORICAL[:3]

# --------------------------------------------------------- sequential ------
# One hue, light -> dark. Full 100-700 range for continuous magnitude.
SEQUENTIAL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
# Ordinal (discrete ordered marks) must clear 2:1 on the light surface:
# start no lighter than step 250.
SEQUENTIAL_ORDINAL = SEQUENTIAL[3:]

# ---------------------------------------------------------- diverging ------
# blue <-> red, neutral gray midpoint. Never a hue at the midpoint.
DIVERGING_NEUTRAL = "#f0efec"
DIVERGING = [
    [0.0, "#0d366b"], [0.15, "#256abf"], [0.32, "#86b6ef"],
    [0.5, DIVERGING_NEUTRAL],
    [0.68, "#f0a3a2"], [0.85, "#e34948"], [1.0, "#8f2120"],
]

STATUS = {  # reserved -- never reused as "series N"
    "good": "#1baf7a",
    "warning": "#eda100",
    "serious": "#eb6834",
    "critical": "#e34948",
}

TEMPLATE_NAME = "o3dash"


def register_template() -> None:
    """Recessive grid and axes, thin marks, no chart junk."""
    if TEMPLATE_NAME in pio.templates:
        return
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif",
                  size=13, color=TEXT_PRIMARY),
        title=dict(font=dict(size=16, color=TEXT_PRIMARY), x=0, xanchor="left"),
        colorway=CATEGORICAL,
        margin=dict(l=56, r=24, t=56, b=48),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=GRID,
                   ticks="outside", tickcolor=GRID,
                   tickfont=dict(color=TEXT_SECONDARY), automargin=True),
        yaxis=dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
                   linecolor=GRID, ticks="outside", tickcolor=GRID,
                   tickfont=dict(color=TEXT_SECONDARY), automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(color=TEXT_SECONDARY),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=GRID,
                        font=dict(color=TEXT_PRIMARY, size=12)),
    )
    pio.templates[TEMPLATE_NAME] = tmpl
    pio.templates.default = TEMPLATE_NAME


# --------------------------------------------------------------- units -----
class Units:
    """Display units. Stored data is always ppb."""

    def __init__(self, name: str = "ppb"):
        self.name = name

    @property
    def factor(self) -> float:
        return 1.0 if self.name == "ppb" else UG_PER_PPB

    @property
    def label(self) -> str:
        return "ppb" if self.name == "ppb" else "\u00b5g m\u207b\u00b3"

    def convert(self, values):
        return values * self.factor

    def axis(self, what: str = "MDA8 ozone") -> str:
        return f"{what} ({self.label})"


def unit_picker(key: str = "units") -> Units:
    """Sidebar unit toggle, shared across pages via session state."""
    choice = st.sidebar.radio(
        "Units", ["ppb", "ug/m3"], key=key, horizontal=True,
        format_func=lambda v: "ppb" if v == "ppb" else "\u00b5g m\u207b\u00b3",
        help=f"Converted at {UG_PER_PPB} \u00b5g m\u207b\u00b3 per ppb, "
             "matching the value used in the analysis.",
    )
    return Units(choice)


def series_color(index: int) -> str:
    """Slot colour by position. Callers pass a STABLE per-entity index."""
    return CATEGORICAL[index % len(CATEGORICAL)]


def stable_colors(entities: list[str]) -> dict[str, str]:
    """Map entities to fixed slots so filtering never repaints survivors."""
    ordered = sorted(entities)
    return {e: CATEGORICAL[i % len(CATEGORICAL)] for i, e in enumerate(ordered)}
