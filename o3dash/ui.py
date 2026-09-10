"""Per-page boilerplate: access gate, theme registration, standing notices.

Access control is primarily platform-level (private GitHub repo + a Streamlit
Community Cloud viewer allowlist). The password below is an optional second
gate; it is only enforced when ``app_password`` is present in st.secrets.
Every page calls ``setup()`` because Streamlit pages are directly reachable by
URL -- gating only app.py would leave them open.
"""
from __future__ import annotations

import hmac

import streamlit as st

from . import theme
from .config import EMBARGO_NOTICE


def _password_ok() -> bool:
    try:
        expected = st.secrets.get("app_password")
    except Exception:
        expected = None
    if not expected:
        return True  # no password configured -> rely on the viewer allowlist
    if st.session_state.get("_auth_ok"):
        return True

    st.title("Global Surface Ozone, 1990-2022")
    st.caption("Pre-publication. Access is restricted.")
    entered = st.text_input("Access code", type="password")
    if entered:
        if hmac.compare_digest(entered, str(expected)):
            st.session_state["_auth_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect access code.")
    return False


def setup(page_title: str, icon: str = "O3", wide: bool = True) -> bool:
    """Configure the page. Returns False when the caller should stop()."""
    st.set_page_config(
        page_title=f"{page_title} | Surface Ozone 1990-2022",
        layout="wide" if wide else "centered",
        initial_sidebar_state="expanded",
    )
    theme.register_template()
    if not _password_ok():
        return False
    return True


def guard(page_title: str) -> None:
    """setup() plus st.stop() on failure -- the common case."""
    if not setup(page_title):
        st.stop()


def embargo_note() -> None:
    st.sidebar.divider()
    st.sidebar.caption(EMBARGO_NOTICE)


def page_header(title: str, lede: str = "") -> None:
    st.title(title)
    if lede:
        st.markdown(
            f"<p style='color:{theme.TEXT_SECONDARY};font-size:15px;"
            f"max-width:70ch;margin-top:-8px;'>{lede}</p>",
            unsafe_allow_html=True)


def tiles(items: list[tuple]) -> None:
    """Render a row of stat tiles: [(label, value, sub[, tone]), ...]."""
    from .plots import stat_tile
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, sub = item[0], item[1], item[2]
        tone = item[3] if len(item) > 3 else None
        col.markdown(stat_tile(label, value, sub, tone), unsafe_allow_html=True)
