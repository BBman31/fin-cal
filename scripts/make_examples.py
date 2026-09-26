"""Regenerate the fake data in examples/ (deterministic).

Usage:
    uv run python scripts/make_examples.py
"""

from __future__ import annotations

import random
from datetime import date

import pandas as pd

from fincal import storage
from fincal.importer import write_log
from fincal.models import FixedCost, FlexCategory, OpenClose, Settings

MONTHS = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]

SETTINGS = Settings(
    currency="DKK",
    income=32000,
    bucket_weights={"Fixed": 55, "Future": 20, "Flexible": 25},
    fixed_costs=[
        FixedCost("Flat rent", 9500, "Flat rent price"),
        FixedCost("Food", 4000, "Groceries + canteen"),
        FixedCost("Insurance", 450, "Tryg"),
        FixedCost("Health", 300, "Pharmacy, Matas"),
        FixedCost("Charity", 200, "Monthly donation"),
    ],
    flexible_categories=[
        FlexCategory("Clothes", 25),
        FlexCategory("Travel", 20),
        FlexCategory("Free Time", 20),
        FlexCategory("Home", 15),
        FlexCategory("LEGO", 10),
        FlexCategory("Other", 10),
    ],
    item_categories={
        "Red Barnet": "Charity",
        "ABC Lavpris": "Food",
        "LEGO store": "LEGO",
        "Netto": "Food",
        "Lidl": "Food",
        "Super Brugsen": "Food",
        "Fotex": "Food",
        "Compass Group": "Food",
        "Flat rent price": "Flat rent",
        "DSB": "Travel",
        "Jysk": "Home",
        "Notino": "Perfume",
        "Nordnet": "Investment",
        "Tryg": "Insurance",
        "Boozt": "Clothes",
        "Matas": "Health",
        "Cinema": "Free Time",
    },
    category_buckets={
        "Food": "Fixed",
        "Flat rent": "Fixed",
        "Charity": "Fixed",
        "Insurance": "Fixed",
        "Health": "Fixed",
        "Clothes": "Flexible",
        "LEGO": "Flexible",
        "Travel": "Flexible",
        "Free Time": "Flexible",
        "Home": "Flexible",
        "Perfume": "Flexible",
        "Other": "Flexible",
        "Investment": "Future",
    },
)

# (item, day range, amount range, probability per month)
RECURRING = [
    ("Flat rent price", (1, 1), (9500, 9500), 1.0),
    ("Tryg", (3, 3), (450, 450), 1.0),
    ("Red Barnet", (5, 5), (200, 200), 1.0),
    ("Nordnet", (26, 27), (5000, 6500), 1.0),
]
OCCASIONAL = [
    ("Netto Billund", (1, 28), (60, 450), 6),
    ("Lidl", (1, 28), (80, 400), 4),
    ("Super Brugsen", (1, 28), (40, 250), 3),
    ("Fotex Vejle", (1, 28), (100, 600), 2),
    ("Compass Group", (1, 28), (45, 75), 8),
    ("Boozt", (1, 28), (300, 1400), 1),
    ("DSB", (1, 28), (120, 700), 2),
    ("Cinema Vejle", (1, 28), (110, 260), 1),
    ("Jysk", (1, 28), (150, 900), 1),
    ("LEGO store", (1, 28), (200, 1200), 1),
    ("Notino", (1, 28), (250, 700), 0.4),
    ("Matas", (1, 28), (80, 350), 1),
    ("MobilePay Anna", (1, 28), (100, 400), 0.5),  # stays unmapped on purpose
    ("Kiosk", (1, 28), (20, 80), 0.7),  # stays unmapped on purpose
]


def generate(seed: int = 7) -> tuple[Settings, pd.DataFrame]:
    rng = random.Random(seed)
    rows = []
    for month in MONTHS:
        year, mon = map(int, month.split("-"))
        for item, days, amounts, p in RECURRING:
            if rng.random() <= p:
                rows.append(
                    (date(year, mon, rng.randint(*days)), item, rng.randint(*amounts), None)
                )
        for item, days, amounts, times in OCCASIONAL:
            n = int(times) + (1 if rng.random() < times % 1 else 0)
            n = max(0, n + rng.choice([-1, 0, 0, 1])) if times >= 1 else n
            for _ in range(n):
                rows.append(
                    (date(year, mon, rng.randint(*days)), item, rng.randint(*amounts), None)
                )
    # a manual re-categorization, as the user would type it in the Category column
    rows.append((date(2026, 7, 14), "Netto", 350, "Free Time"))
    log = pd.DataFrame(rows, columns=["Date", "Item", "Amount", "Category"])
    log = log.sort_values("Date", kind="stable", ignore_index=True)
    log["Comment"] = None
    log.loc[log["Category"].notna(), "Comment"] = "BBQ party supplies"

    settings = Settings.from_dict(SETTINGS.to_dict())
    balance = 25000.0
    for month in MONTHS:
        spent = float(
            log[pd.to_datetime(log["Date"]).dt.strftime("%Y-%m") == month]["Amount"].sum()
        )
        close = round(balance + settings.income - spent + rng.randint(-1500, 1500), 2)
        settings.open_close.append(OpenClose(month, balance, close))
        balance = close
    settings.open_close.append(OpenClose("2026-09", balance, None))
    return settings, log


def main() -> None:
    settings, log = generate()
    storage.save_settings(settings, storage.settings_path(storage.EXAMPLES_DIR))
    write_log(log, storage.log_path(storage.EXAMPLES_DIR))
    print(f"Wrote examples/: {len(log)} log rows, {len(settings.open_close)} open/close months")


if __name__ == "__main__":
    main()
