import pandas as pd
import streamlit as st

from fincal import ui
from fincal.models import OpenClose, Settings

settings = ui.load_settings()
st.title("Open / Close")
st.caption(
    "Main account balance at the start (Open) and end (Close) of each month. "
    "Remaining = Close − Open is what you saved that month."
)

rows = sorted(settings.open_close, key=lambda o: o.month)
df = pd.DataFrame(
    {
        "month": pd.to_datetime([o.month for o in rows], format="%Y-%m"),
        "open": [o.open for o in rows],
        "close": [o.close for o in rows],
    },
    columns=["month", "open", "close"],
)
df["open"] = df["open"].astype(float)
df["close"] = df["close"].astype(float)
df["remaining"] = df["close"] - df["open"]

edited = st.data_editor(
    df,
    column_config={
        "month": st.column_config.DateColumn("Month", format="MMM YYYY", required=True),
        "open": st.column_config.NumberColumn("Open", format="%.2f"),
        "close": st.column_config.NumberColumn("Close", format="%.2f"),
        "remaining": st.column_config.NumberColumn(
            "Remaining", format="%.2f", disabled=True, help="Recalculated on save"
        ),
    },
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key="open_close",
)


def num(value) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


draft = Settings.from_dict(settings.to_dict())
draft.open_close = sorted(
    (
        OpenClose(pd.Timestamp(r.month).strftime("%Y-%m"), num(r.open), num(r.close))
        for r in edited.itertuples()
        if r.month is not None and not pd.isna(r.month)
    ),
    key=lambda o: o.month,
)

errors = draft.validate()
for e in errors:
    st.error(e)
changed = draft != settings
disabled = bool(errors) or ui.read_only()

c1, c2, _ = st.columns([1, 2, 3])
if c1.button("Save", type="primary", disabled=disabled or not changed, icon="💾") and ui.save(
    draft, "Open/Close"
):
    st.rerun()

if draft.open_close:
    last = draft.open_close[-1]
    next_month = (pd.Period(last.month, "M") + 1).strftime("%Y-%m")
    label = f"Start {pd.Period(next_month, 'M').strftime('%b %Y')}"
    help_text = "Adds the next month with Open = last month's Close."
else:
    next_month = pd.Timestamp.today().strftime("%Y-%m")
    label, help_text = "Start this month", None
    last = None
if c2.button(label, disabled=disabled, help=help_text, icon="➕"):
    draft.open_close.append(OpenClose(next_month, last.close if last else None, None))
    if ui.save(draft, "Open/Close"):
        st.rerun()
if changed and not errors:
    st.caption("Unsaved changes")
