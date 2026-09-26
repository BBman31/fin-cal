# fin-cal

Local Streamlit dashboard for a monthly budget that started life as an Excel sheet
(`Financial_calculations_template.xlsx`).

- **Spending log** stays in Excel (`data/spending_log.xlsx`): paste rows `Date | Item | Amount`.
- **Everything else** (income, budget weights, fixed costs, mappings, open/close balances)
  is edited in the app and stored in `data/settings.yaml`.
- `data/` is gitignored; without it the app falls back to fake data in `examples/`.

## Run

```bash
uv sync
uv run streamlit run app.py
```

## Test

```bash
uv run pytest
uv run ruff check .
```

## Task tracking

Issues live in beads: `bd ready` shows the next task.
