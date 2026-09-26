"""Pure pandas calculations over the enriched spending log.

All functions take the output of ``fincal.spending.enrich`` and never mutate it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fincal.mapping import UNMAPPED, normalize
from fincal.models import BUCKETS, Settings


def months(log: pd.DataFrame) -> list[str]:
    return sorted(log["month"].dropna().unique().tolist())


def for_month(log: pd.DataFrame, month: str) -> pd.DataFrame:
    return log[log["month"] == month]


@dataclass
class MonthSummary:
    month: str
    income: float
    spent: float
    spent_by_bucket: dict[str, float]
    saved: float | None  # close - open from Open/Close, if recorded
    savings_rate: float | None
    unmapped_count: int
    unmapped_amount: float
    transactions: int


def month_summary(log: pd.DataFrame, settings: Settings, month: str) -> MonthSummary:
    rows = for_month(log, month)
    by_bucket = rows.groupby("bucket")["amount"].sum()
    oc = next((o for o in settings.open_close if o.month == month), None)
    saved = oc.remaining if oc else None
    unmapped = rows[~rows["mapped"]]
    return MonthSummary(
        month=month,
        income=settings.income,
        spent=float(rows["amount"].sum()),
        spent_by_bucket={b: float(by_bucket.get(b, 0.0)) for b in (*BUCKETS, UNMAPPED)},
        saved=saved,
        savings_rate=saved / settings.income if saved is not None and settings.income else None,
        unmapped_count=len(unmapped),
        unmapped_amount=float(unmapped["amount"].sum()),
        transactions=len(rows),
    )


def budget_vs_actual(log: pd.DataFrame, settings: Settings, month: str) -> pd.DataFrame:
    """One row per bucket: budget, actual, remaining, used (actual / budget)."""
    actual = for_month(log, month).groupby("bucket")["amount"].sum()
    df = pd.DataFrame(
        {
            "bucket": list(BUCKETS),
            "budget": [settings.bucket_budget(b) for b in BUCKETS],
            "actual": [float(actual.get(b, 0.0)) for b in BUCKETS],
        }
    )
    return _finish(df)


def _plan_vs_actual(actual: pd.Series, plan: dict[str, float], label: str) -> pd.DataFrame:
    """Outer-join planned amounts and actual spend on normalized category names.

    Categories that are only planned get actual 0; categories that are only spent get budget 0.
    """
    rows: dict[str, dict] = {}
    for category, amount in plan.items():
        rows.setdefault(normalize(category), {label: category, "budget": 0.0, "actual": 0.0})
        rows[normalize(category)]["budget"] += amount
    for category, amount in actual.items():
        key = normalize(category)
        rows.setdefault(key, {label: category, "budget": 0.0, "actual": 0.0})
        rows[key]["actual"] += float(amount)
    df = pd.DataFrame(list(rows.values()), columns=[label, "budget", "actual"])
    return _finish(df).sort_values(["budget", "actual"], ascending=False, ignore_index=True)


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    df["remaining"] = df["budget"] - df["actual"]
    df["used"] = (df["actual"] / df["budget"]).where(df["budget"] > 0)
    return df


def flexible_vs_budget(log: pd.DataFrame, settings: Settings, month: str) -> pd.DataFrame:
    rows = for_month(log, month)
    actual = rows[rows["bucket"] == "Flexible"].groupby("category")["amount"].sum()
    return _plan_vs_actual(actual, settings.flexible_budgets(), "category")


def fixed_vs_planned(log: pd.DataFrame, settings: Settings, month: str) -> pd.DataFrame:
    rows = for_month(log, month)
    actual = rows[rows["bucket"] == "Fixed"].groupby("category")["amount"].sum()
    plan: dict[str, float] = {}
    for c in settings.fixed_costs:
        plan[c.category] = plan.get(c.category, 0.0) + c.amount
    return _plan_vs_actual(actual, plan, "category")


def monthly_by_bucket(log: pd.DataFrame) -> pd.DataFrame:
    """Long format: month, bucket, amount (every month x bucket present, zeros filled)."""
    if log.empty:
        return pd.DataFrame(columns=["month", "bucket", "amount"])
    buckets = list(BUCKETS) + ([UNMAPPED] if (log["bucket"] == UNMAPPED).any() else [])
    pivot = log.pivot_table(
        index="month", columns="bucket", values="amount", aggfunc="sum", fill_value=0.0
    ).reindex(columns=buckets, fill_value=0.0)
    return (
        pivot.reset_index()
        .melt(id_vars="month", var_name="bucket", value_name="amount")
        .sort_values(["month", "bucket"], ignore_index=True)
    )


def savings_series(settings: Settings) -> pd.DataFrame:
    """Open/Close per month with remaining (close - open) and cumulative saved."""
    df = pd.DataFrame(
        [
            {"month": o.month, "open": o.open, "close": o.close, "remaining": o.remaining}
            for o in settings.open_close
        ],
        columns=["month", "open", "close", "remaining"],
    )
    df = df.sort_values("month", ignore_index=True)
    df["remaining"] = pd.to_numeric(df["remaining"])
    df["cumulative"] = df["remaining"].fillna(0).cumsum().where(df["remaining"].notna())
    return df


def top(log: pd.DataFrame, month: str, by: str = "item", n: int = 10) -> pd.DataFrame:
    rows = for_month(log, month)
    return (
        rows.groupby(by, as_index=False)
        .agg(amount=("amount", "sum"), count=("amount", "size"))
        .sort_values("amount", ascending=False, ignore_index=True)
        .head(n)
    )
