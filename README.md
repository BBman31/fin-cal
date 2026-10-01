# fin-cal

Local Streamlit dashboard for a monthly budget that started life as an Excel sheet
(`Financial_calculations_template.xlsx`).

- **Spending log** stays in Excel (`data/spending_log.xlsx`): paste rows `Date | Item | Amount`.
  Category and bucket are derived from the mappings. Type a value in the optional
  `Category` column only to override the mapping for that one row.
- **Everything else** (income, budget weights, fixed costs, flexible split, mappings,
  open/close balances) is edited in the app and stored in `data/settings.yaml`.
- `data/` is git-ignored and never leaves the machine. Without it, the app shows the fake
  data in `examples/` read-only.

## Run

```bash
uv sync
uv run streamlit run app.py        # http://localhost:8501 (bound to localhost only)
```

## First-time setup

Either use the sidebar (**Use my own data** → import your workbook, or start blank from the
template), or from the command line:

```bash
uv run python scripts/import_template.py path/to/your_workbook.xlsx   # --force to overwrite
```

The importer reads Overview, Fixed, Flexible Budget, OpenClose, Spending log and Mapping
tables. It keeps a log row's Category only when it differs from what the mapping would give.

## Monthly workflow

1. **Open spending log in Excel** (sidebar), paste the new rows, save.
2. The **Spending Log** page flags unmapped items. Pick a category to add a mapping.
3. On **Open / Close**, click **Start <month>** and fill in the balances.
4. Check the **Dashboard**.

Tip: name the Fixed-cost and Flexible-split categories exactly like the mapping categories
(e.g. `Flat rent`, `Clothes`), so planned and actual amounts line up on the dashboard.

## Develop

```bash
uv run pytest
uv run ruff check . && uv run ruff format .
uv run python scripts/make_examples.py    # regenerate examples/
FINCAL_DATA_DIR=/some/dir uv run streamlit run app.py   # point at another data folder
```

Layout: `app.py` (navigation) · `views/` (pages) · `fincal/` (models, storage, mapping,
spending log, metrics, charts, importer; pure and tested) · `scripts/` · `tests/`.

Issues are tracked in beads: `bd ready` shows the next task.
