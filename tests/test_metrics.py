import pandas as pd
import pytest

from fincal import metrics
from fincal.mapping import UNMAPPED
from fincal.models import FixedCost, FlexCategory, OpenClose, Settings
from fincal.spending import clean_log, enrich

SETTINGS = Settings(
    income=20000,  # Fixed 11000, Future 4000, Flexible 5000
    fixed_costs=[FixedCost("Rent", 8000), FixedCost("Insurance", 500)],
    flexible_categories=[FlexCategory("Clothes", 60), FlexCategory("Travel", 40)],
    item_categories={
        "Landlord": "Rent",
        "Netto": "Food",
        "Boozt": "Clothes",
        "DSB": "Travel",
        "Nordnet": "Investment",
        "Notino": "Perfume",
    },
    category_buckets={
        "Rent": "Fixed",
        "Food": "Fixed",
        "Clothes": "Flexible",
        "Travel": "Flexible",
        "Perfume": "Flexible",
        "Investment": "Future",
    },
    open_close=[OpenClose("2026-01", 10000, 13000), OpenClose("2026-02", 13000, None)],
)

ROWS = [
    ("2026-01-01", "Landlord", 8000),
    ("2026-01-03", "Netto", 400),
    ("2026-01-10", "Netto", 600),
    ("2026-01-12", "Boozt", 1200),
    ("2026-01-15", "DSB", 300),
    ("2026-01-20", "Notino", 250),
    ("2026-01-25", "Nordnet", 4000),
    ("2026-01-28", "Mystery shop", 150),
    ("2026-02-02", "Netto", 500),
]


@pytest.fixture
def log():
    raw = pd.DataFrame(ROWS, columns=["Date", "Item", "Amount"])
    return enrich(clean_log(raw), SETTINGS)


def test_months(log):
    assert metrics.months(log) == ["2026-01", "2026-02"]


def test_month_summary(log):
    s = metrics.month_summary(log, SETTINGS, "2026-01")
    assert s.spent == 14900
    assert s.spent_by_bucket == {
        "Fixed": 9000,
        "Future": 4000,
        "Flexible": 1750,
        UNMAPPED: 150,
    }
    assert s.saved == 3000
    assert s.savings_rate == pytest.approx(0.15)
    assert (s.unmapped_count, s.unmapped_amount) == (1, 150)
    assert s.transactions == 8

    feb = metrics.month_summary(log, SETTINGS, "2026-02")
    assert feb.saved is None and feb.savings_rate is None


def test_budget_vs_actual(log):
    df = metrics.budget_vs_actual(log, SETTINGS, "2026-01").set_index("bucket")
    assert df.loc["Fixed", "budget"] == 11000
    assert df.loc["Fixed", "actual"] == 9000
    assert df.loc["Fixed", "remaining"] == 2000
    assert df.loc["Flexible", "used"] == pytest.approx(1750 / 5000)
    assert df.loc["Future", "actual"] == 4000


def test_flexible_vs_budget(log):
    df = metrics.flexible_vs_budget(log, SETTINGS, "2026-01").set_index("category")
    assert df.loc["Clothes", ["budget", "actual"]].tolist() == [3000, 1200]
    assert df.loc["Travel", ["budget", "actual"]].tolist() == [2000, 300]
    # spent but not budgeted
    assert df.loc["Perfume", ["budget", "actual"]].tolist() == [0, 250]
    assert pd.isna(df.loc["Perfume", "used"])


def test_fixed_vs_planned(log):
    df = metrics.fixed_vs_planned(log, SETTINGS, "2026-01").set_index("category")
    assert df.loc["Rent", ["budget", "actual"]].tolist() == [8000, 8000]
    assert df.loc["Insurance", ["budget", "actual"]].tolist() == [500, 0]
    assert df.loc["Food", ["budget", "actual"]].tolist() == [0, 1000]


def test_monthly_by_bucket(log):
    df = metrics.monthly_by_bucket(log)
    feb = df[df["month"] == "2026-02"].set_index("bucket")["amount"]
    assert feb.to_dict() == {"Fixed": 500, "Flexible": 0, "Future": 0, UNMAPPED: 0}
    assert df["amount"].sum() == 15400


def test_savings_series():
    df = metrics.savings_series(SETTINGS)
    assert df["remaining"].tolist()[0] == 3000
    assert pd.isna(df["remaining"].tolist()[1])
    assert df["cumulative"].tolist()[0] == 3000


def test_top(log):
    df = metrics.top(log, "2026-01", by="item", n=2)
    assert df["item"].tolist() == ["Landlord", "Nordnet"]
    netto = metrics.top(log, "2026-01").set_index("item").loc["Netto"]
    assert (netto["amount"], netto["count"]) == (1000, 2)
