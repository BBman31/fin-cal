from datetime import date

import openpyxl
import pytest

from fincal import storage
from fincal.importer import read_log, read_settings
from fincal.spending import enrich, load_log
from scripts.import_template import main

TEMPLATE = storage.PROJECT_ROOT / "Financial_calculations_template.xlsx"


@pytest.fixture
def workbook(tmp_path):
    """Template copy with income, open/close and a few log rows filled in."""
    wb = openpyxl.load_workbook(TEMPLATE)
    wb["Overview"]["B1"] = 30000
    wb["OpenClose"]["B3"], wb["OpenClose"]["C3"] = 1000, 2500
    log = wb["Spending log"]
    rows = [
        (date(2025, 7, 2), "Fixed", "Food", "Netto Billund", 120),
        (date(2025, 7, 3), "Flexible", "Travel", "Netto", 80),  # manual re-categorization
        (date(2025, 7, 4), None, None, "Unknown shop", 50),
    ]
    for r, values in enumerate(rows, start=2):
        for c, v in enumerate(values, start=1):
            log.cell(r, c, v)
    path = tmp_path / "book.xlsx"
    wb.save(path)
    return path


def test_template_settings():
    s, warnings = read_settings(TEMPLATE)
    assert s.bucket_weights == {"Fixed": 55, "Future": 20, "Flexible": 25}
    assert [(c.category, c.weight) for c in s.flexible_categories] == [
        ("Clothing", 30),
        ("Self-development", 25),
        ("Social / Experiences", 25),
        ("Misc", 20),
    ]
    assert len(s.fixed_costs) == 8
    assert s.fixed_costs[0].category == "Rent"
    assert s.fixed_costs[1].comment.startswith("I do not know")
    assert len(s.item_categories) == 22
    assert s.item_categories["LEGO Store BLL"] == "LEGO"
    assert len(s.category_buckets) == 14  # 15 rows, "Home" listed twice
    assert s.category_buckets["Investment"] == "Future"
    assert [o.month for o in s.open_close][:2] == ["2025-07", "2025-08"]
    assert len(s.open_close) == 18
    assert s.validate() == []
    assert warnings == []


def test_log_keeps_only_differing_categories(workbook):
    s, _ = read_settings(workbook)
    log = read_log(workbook, s)
    assert log["Item"].tolist() == ["Netto Billund", "Netto", "Unknown shop"]
    assert log["Category"].tolist() == [None, "Travel", None]


def test_cli_end_to_end(workbook, tmp_path):
    out = tmp_path / "data"
    assert main([str(workbook), "--out", str(out)]) == 0
    s = storage.load_settings(out / "settings.yaml")
    assert s.income == 30000
    assert s.open_close[0].remaining == 1500
    df = enrich(load_log(out / "spending_log.xlsx"), s)
    assert df["category"].tolist() == ["Food", "Travel", "Unmapped"]
    assert df["bucket"].tolist() == ["Fixed", "Flexible", "Unmapped"]

    assert main([str(workbook), "--out", str(out)]) == 1  # no overwrite without --force
    assert main([str(workbook), "--out", str(out), "--force"]) == 0
