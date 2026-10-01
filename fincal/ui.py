"""Shared Streamlit helpers: data loading, saving, sidebar and formatting."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from fincal import storage
from fincal.importer import read_log, read_settings, write_log
from fincal.models import Settings
from fincal.spending import enrich, load_log

TEMPLATE = storage.PROJECT_ROOT / "Financial_calculations_template.xlsx"


def read_only() -> bool:
    """Example data is a playground shipped with the repo; never write to it."""
    return storage.is_example_data()


def load_settings() -> Settings:
    return storage.load_settings()


@st.cache_data(show_spinner=False)
def _load_log(path: str, mtime: float) -> pd.DataFrame:
    return load_log(Path(path))


def load_enriched(settings: Settings) -> pd.DataFrame:
    """Enriched log, re-read automatically whenever the Excel file changes on disk."""
    path = storage.log_path()
    mtime = path.stat().st_mtime if path.exists() else 0.0
    return enrich(_load_log(str(path), mtime), settings)


def save(settings: Settings, what: str = "Settings") -> bool:
    if read_only():
        st.warning("You're viewing example data. Set up your own data in the sidebar first.")
        return False
    try:
        storage.save_settings(settings)
    except storage.SettingsError as e:
        st.error(f"Not saved: {e}")
        return False
    st.toast(f"{what} saved", icon="✅")
    return True


def money(value: float | None, settings: Settings | None = None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "–"
    currency = settings.currency if settings else "DKK"
    return f"{value:,.{decimals}f} {currency}".replace(",", " ")


def open_in_default_app(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def _bootstrap(workbook: Path) -> None:
    settings, warnings = read_settings(workbook)
    target = storage.PROJECT_ROOT / "data"
    storage.save_settings(settings, storage.settings_path(target))
    log_file = storage.log_path(target)
    if not log_file.exists():
        write_log(read_log(workbook, settings), log_file)
    for w in warnings:
        st.warning(w)


def sidebar() -> None:
    with st.sidebar:
        if read_only():
            st.info("Showing **example data**. Nothing you edit here is saved.", icon="🧪")
            with st.expander("Use my own data", expanded=False):
                st.caption(
                    "Creates `data/settings.yaml` and `data/spending_log.xlsx` "
                    "(git-ignored, stays on this machine)."
                )
                upload = st.file_uploader("Import my existing workbook", type=["xlsx"])
                if upload and st.button("Import workbook", type="primary"):
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / "upload.xlsx"
                        path.write_bytes(upload.getvalue())
                        _bootstrap(path)
                    st.rerun()
                if st.button("Start blank from template"):
                    _bootstrap(TEMPLATE)
                    st.rerun()
        else:
            log_file = storage.log_path()
            st.caption(f"Data: `{storage.data_dir()}`")
            if st.button("Open spending log in Excel", icon="📄", width="stretch"):
                open_in_default_app(log_file)
            st.caption("Paste rows (Date · Item · Amount), save, and the app picks them up.")
