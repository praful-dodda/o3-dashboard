"""Panel export.

The only export the app offers is a rendered image. Underlying values are not
downloadable while the paper is unpublished -- see EMBARGO_NOTICE.
"""
from __future__ import annotations

import io
import re

import plotly.graph_objects as go
import streamlit as st

from . import theme
from .config import CITATION, EMBARGO_NOTICE


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s or "panel"


def stamp(fig: go.Figure, caption: str = "") -> go.Figure:
    """Add the attribution / embargo footer used on exported panels."""
    out = go.Figure(fig)
    footer = caption or CITATION
    out.add_annotation(
        text=f"<span style='font-size:10px'>{footer}</span>",
        xref="paper", yref="paper", x=0, y=-0.14, showarrow=False,
        xanchor="left", yanchor="top",
        font=dict(size=10, color=theme.TEXT_MUTED))
    out.update_layout(margin=dict(b=out.layout.margin.b or 48))
    return out


def panel(fig: go.Figure, name: str, caption: str = "",
          width: int = 1600, height: int | None = None, scale: int = 2,
          key: str | None = None) -> None:
    """Render a figure plus a poster-quality PNG download button.

    Falls back to the chart alone with an explanatory caption when kaleido is
    not installed, rather than breaking the page.
    """
    st.plotly_chart(fig, width="stretch",
                    config={"displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                    key=key)
    if caption:
        st.caption(caption)

    try:
        img = stamp(fig, caption).to_image(
            format="png", width=width,
            height=height or int(fig.layout.height or 600), scale=scale)
    except Exception as exc:  # kaleido missing or render failure
        st.caption(f"PNG export unavailable ({type(exc).__name__}). "
                   "Install `kaleido` to enable poster-quality download.")
        return

    st.download_button(
        "Download panel (PNG)", data=io.BytesIO(img),
        file_name=f"{_slug(name)}.png", mime="image/png",
        key=f"dl_{key or _slug(name)}", help=EMBARGO_NOTICE)
