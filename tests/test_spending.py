from datetime import date

import pandas as pd

from fincal.mapping import UNMAPPED
from fincal.models import Settings
from fincal.spending import clean_log, enrich, load_log

SETTINGS = Settings(
    item_categories={"Netto": "Food", "Boozt": "Clothes"},
    category_buckets={"Food": "Fixed", "Clothes": "Flexible", "Travel": "Flexible"},
)


def write_log(path, rows, columns=("Date", "Item", "Amount")):
    pd.DataFrame(rows, columns=list(columns)).to_excel(path, sheet_name="Spending log", index=False)


def test_missing_file_gives_empty_log(tmp_path):
    df = load_log(tmp_path / "none.xlsx")
    assert df.empty
    assert df.attrs["dropped_rows"] == 0


def test_load_cleans_and_sorts(tmp_path):
    path = tmp_path / "log.xlsx"
    write_log(
        path,
        [
            [date(2026, 2, 3), " Netto Vejle ", 120.5],
            [None, None, None],  # blank row, ignored silently
            [date(2026, 1, 5), "Boozt", 300],
            [None, "No date", 10],  # dropped
            [date(2026, 1, 9), "Bad amount", "abc"],  # dropped
        ],
    )
    df = load_log(path)
    assert list(df["item"]) == ["Boozt", "Netto Vejle"]
    assert list(df["amount"]) == [300, 120.5]
    assert df.attrs["dropped_rows"] == 2


def test_legacy_columns_and_override(tmp_path):
    path = tmp_path / "log.xlsx"
    write_log(
        path,
        [
            [date(2026, 1, 1), "Fixed", "Food", "Netto", 50],
            [date(2026, 1, 2), "Flexible", "Travel", "Netto", 70],
        ],
        columns=("Date", "Budget Bucket", "Category", "Item", "Amount"),
    )
    df = enrich(load_log(path), SETTINGS)
    assert list(df["category"]) == ["Food", "Travel"]
    assert list(df["bucket"]) == ["Fixed", "Flexible"]


def test_enrich(tmp_path):
    path = tmp_path / "log.xlsx"
    write_log(
        path,
        [
            [date(2026, 1, 31), "NETTO 123", 100],
            [date(2026, 2, 1), "Random shop", 40],
        ],
    )
    df = enrich(load_log(path), SETTINGS)
    assert list(df["month"]) == ["2026-01", "2026-02"]
    assert list(df["category"]) == ["Food", UNMAPPED]
    assert list(df["bucket"]) == ["Fixed", UNMAPPED]
    assert list(df["mapped"]) == [True, False]


def test_text_dates_iso_and_day_first():
    raw = pd.DataFrame(
        [("2026-01-03", "a", 1), ("03.02.2026", "b", 1), ("13/02/2026", "c", 1)],
        columns=["Date", "Item", "Amount"],
    )
    assert clean_log(raw)["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-03",
        "2026-02-03",
        "2026-02-13",
    ]
