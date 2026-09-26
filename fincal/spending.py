"""Read the spending log Excel and enrich it with category / bucket / month."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fincal.mapping import UNMAPPED, Lookup, normalize
from fincal.models import Settings

SHEET_NAME = "Spending log"
COLUMNS = ["date", "item", "amount", "category_override", "comment"]
_ALIASES = {
    "date": "date",
    "item": "item",
    "amount": "amount",
    "category": "category_override",
    "category override": "category_override",
    "comment": "comment",
}


def empty_log() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype="object") for c in COLUMNS})
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    df.attrs["dropped_rows"] = 0
    return df


def load_log(path: Path) -> pd.DataFrame:
    """Load the log. Blank rows are ignored; rows missing a date or amount are dropped
    and counted in ``df.attrs["dropped_rows"]``."""
    if not path.exists():
        return empty_log()
    with pd.ExcelFile(path) as xls:
        sheet = SHEET_NAME if SHEET_NAME in xls.sheet_names else xls.sheet_names[0]
        raw = pd.read_excel(xls, sheet_name=sheet)
    return clean_log(raw)


def clean_log(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=lambda c: _ALIASES.get(normalize(c), None))
    df = df.loc[:, [c for c in df.columns if c is not None]]
    df = df.loc[:, ~df.columns.duplicated()]
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS].dropna(how="all")

    df["date"] = _parse_dates(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").astype(float)
    valid = df["date"].notna() & df["amount"].notna()
    dropped = int((~valid).sum())
    df = df[valid].copy()

    df["item"] = df["item"].fillna("").astype(str).str.strip()
    for col in ("category_override", "comment"):
        df[col] = df[col].map(_clean_text).astype(object)
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    df.attrs["dropped_rows"] = dropped
    return df


def _clean_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value).strip() or None


def _parse_dates(values: pd.Series) -> pd.Series:
    """Excel dates arrive as datetimes; text dates may be ISO or day-first (03.01.2026)."""
    parsed = pd.to_datetime(values, errors="coerce", format="ISO8601")
    missing = parsed.isna() & values.notna()
    if missing.any():
        parsed[missing] = pd.to_datetime(
            values[missing].astype(str), errors="coerce", dayfirst=True, format="mixed"
        )
    return parsed


def enrich(log: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Add ``category``, ``bucket``, ``month`` (YYYY-MM) and ``mapped`` columns."""
    items = Lookup.from_dict(settings.item_categories)
    categories = Lookup.from_dict(settings.category_buckets)
    df = log.copy()
    resolved = df["item"].map(lambda i: items.get(i) or UNMAPPED)
    df["category"] = df["category_override"].where(df["category_override"].notna(), resolved)
    df["bucket"] = df["category"].map(lambda c: categories.get(c, substring=False) or UNMAPPED)
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["mapped"] = (df["category"] != UNMAPPED) & (df["bucket"] != UNMAPPED)
    df.attrs = dict(log.attrs)
    return df
