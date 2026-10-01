import pandas as pd
import streamlit as st

from fincal import ui
from fincal.models import BUCKETS, FixedCost, FlexCategory, Settings

settings = ui.load_settings()
st.title("Budget Setup")
st.caption(
    "Your rough monthly plan. It doesn't need to be exact; it's the yardstick for the dashboard."
)

draft = Settings.from_dict(settings.to_dict())

c1, c2 = st.columns([3, 1])
draft.income = c1.number_input(
    "Net monthly income", min_value=0.0, value=float(settings.income), step=500.0, format="%.0f"
)
draft.currency = c2.text_input("Currency", value=settings.currency, max_chars=5)

# --- Bucket split -----------------------------------------------------------------------------
st.subheader("Budget split")
weights = st.data_editor(
    pd.DataFrame(
        {"bucket": list(BUCKETS), "weight": [settings.bucket_weights.get(b, 0.0) for b in BUCKETS]}
    ),
    column_config={
        "bucket": st.column_config.TextColumn("Bucket", disabled=True),
        "weight": st.column_config.NumberColumn(
            "Weight (%)", min_value=0, max_value=100, step=1, format="%.0f"
        ),
    },
    hide_index=True,
    width="stretch",
    key="weights",
)
draft.bucket_weights = {r.bucket: float(r.weight or 0) for r in weights.itertuples()}
cols = st.columns(len(BUCKETS))
for col, bucket in zip(cols, BUCKETS, strict=True):
    col.metric(bucket, ui.money(draft.bucket_budget(bucket), draft))

# --- Fixed costs ------------------------------------------------------------------------------
st.subheader("Fixed costs")
st.caption(
    "Planned monthly amounts. Name categories the same as in Mappings to compare with actuals."
)
fixed = st.data_editor(
    pd.DataFrame(
        [vars(c) for c in settings.fixed_costs], columns=["category", "amount", "comment"]
    ),
    column_config={
        "category": st.column_config.TextColumn("Category", required=True),
        "amount": st.column_config.NumberColumn("Monthly cost", min_value=0, format="%.0f"),
        "comment": st.column_config.TextColumn("Comment", width="large"),
    },
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key="fixed",
)
draft.fixed_costs = [
    FixedCost(
        str(r.category).strip(), float(r.amount or 0), "" if pd.isna(r.comment) else r.comment
    )
    for r in fixed.itertuples()
    if isinstance(r.category, str) and r.category.strip()
]
planned, budget = draft.fixed_planned_total(), draft.bucket_budget("Fixed")
st.caption(
    f"Total planned **{ui.money(planned, draft)}** of {ui.money(budget, draft)} Fixed budget "
    f"→ remaining **{ui.money(budget - planned, draft)}**"
)

# --- Flexible categories ----------------------------------------------------------------------
st.subheader("Flexible budget split")
flex = st.data_editor(
    pd.DataFrame([vars(c) for c in settings.flexible_categories], columns=["category", "weight"]),
    column_config={
        "category": st.column_config.TextColumn("Category", required=True),
        "weight": st.column_config.NumberColumn(
            "Weight (%)", min_value=0, max_value=100, step=1, format="%.0f"
        ),
    },
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    key="flex",
)
draft.flexible_categories = [
    FlexCategory(str(r.category).strip(), float(r.weight or 0))
    for r in flex.itertuples()
    if isinstance(r.category, str) and r.category.strip()
]
if draft.flexible_categories:
    budgets = draft.flexible_budgets()
    st.caption(" · ".join(f"{k}: **{ui.money(v, draft)}**" for k, v in budgets.items()))

# --- Save -------------------------------------------------------------------------------------
st.divider()
errors = draft.validate()
for e in errors:
    st.error(e)
changed = draft != settings
if st.button(
    "Save", type="primary", disabled=bool(errors) or not changed or ui.read_only(), icon="💾"
) and ui.save(draft, "Budget"):
    st.rerun()
if changed and not errors:
    st.caption("Unsaved changes")
