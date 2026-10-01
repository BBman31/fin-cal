import pandas as pd
import streamlit as st

from fincal import charts, metrics, ui
from fincal.mapping import UNMAPPED

settings = ui.load_settings()
log = ui.load_enriched(settings)
t = charts.theme(st.context.theme.type == "dark")
cur = settings.currency
PLOT = {"displayModeBar": False}

all_months = metrics.months(log)
head, picker = st.columns([4, 1], vertical_alignment="bottom")
head.title("Dashboard")
if not all_months:
    st.info(
        "No spending yet. Open the spending log from the sidebar and paste rows "
        "(Date · Item · Amount), then come back here."
    )
    st.stop()

month = picker.selectbox(
    "Month",
    all_months[::-1],
    format_func=lambda m: pd.Period(m, "M").strftime("%B %Y"),
    label_visibility="collapsed",
)
idx = all_months.index(month)
prev = all_months[idx - 1] if idx > 0 else None

summary = metrics.month_summary(log, settings, month)
prev_summary = metrics.month_summary(log, settings, prev) if prev else None


def delta(now: float | None, before: float | None) -> str | None:
    if now is None or before is None:
        return None
    return f"{now - before:+,.0f}".replace(",", " ")


def num(value: float | None) -> str:
    return "–" if value is None else f"{value:,.0f}".replace(",", " ")


vs_prev = f"vs {pd.Period(prev, 'M').strftime('%b')}" if prev else None

# --- KPI tiles ---------------------------------------------------------------------------------
consumption = summary.spent - summary.spent_by_bucket["Future"]
budget_ex_future = settings.bucket_budget("Fixed") + settings.bucket_budget("Flexible")
st.caption(f"Amounts in {cur}")
k = st.columns(5)
k[0].metric(
    "Spent",
    num(summary.spent),
    spent_delta := delta(summary.spent, prev_summary.spent if prev_summary else None),
    delta_color="inverse",
    delta_description=vs_prev if spent_delta else None,
    help="All rows in the spending log for this month, including Future (investing/saving).",
    border=True,
)
k[1].metric(
    "Left to spend",
    num(budget_ex_future - consumption),
    help="Fixed + Flexible budget minus what was spent in Fixed, Flexible and Unmapped.",
    border=True,
)
k[2].metric(
    "Into Future",
    num(summary.spent_by_bucket["Future"]),
    f"target {num(settings.bucket_budget('Future'))}",
    delta_color="off",
    delta_arrow="off",
    border=True,
)
k[3].metric(
    "Saved",
    num(summary.saved),
    saved_delta := delta(summary.saved, prev_summary.saved if prev_summary else None),
    delta_description=vs_prev if saved_delta else None,
    help="Close − Open of the main account, from the Open / Close page.",
    border=True,
)
k[4].metric(
    "Unmapped rows",
    summary.unmapped_count,
    f"{num(summary.unmapped_amount)} {cur}" if summary.unmapped_count else None,
    delta_color="off",
    delta_arrow="off",
    help="Rows without a category or bucket. Fix them on the Spending Log page.",
    border=True,
)
if summary.unmapped_count:
    st.page_link("views/spending_log.py", label="Map the unmapped items →", icon="🏷️")


def data_view(df: pd.DataFrame, key: str) -> None:
    with st.expander("Show data", icon="📋"):
        st.dataframe(df, hide_index=True, width="stretch", key=key)


# --- Budget vs actual ---------------------------------------------------------------------------
left, right = st.columns(2, gap="large")
with left:
    st.subheader("Budget vs. actual")
    st.caption("Pale track = budget, bar = spent. Red ▲ = over budget.")
    bva = metrics.budget_vs_actual(log, settings, month)
    st.plotly_chart(charts.plan_vs_actual(bva, "bucket", t, cur), config=PLOT, key="bva")
    data_view(bva, "bva_data")
with right:
    st.subheader("Where it went")
    st.caption("Top categories this month, colored by bucket.")
    cats = metrics.top(log, month, by="category", n=8)
    bucket_of = log.drop_duplicates("category").set_index("category")["bucket"]
    fig = charts.top_bars(cats, "category", t, cur, color=t.buckets["Fixed"])
    fig.update_traces(
        marker_color=[
            t.buckets.get(bucket_of.get(c, UNMAPPED), t.muted) for c in cats["category"][::-1]
        ]
    )
    st.plotly_chart(fig, config=PLOT, key="cats")
    data_view(cats, "cats_data")

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Flexible categories")
    flex = metrics.flexible_vs_budget(log, settings, month)
    if flex.empty:
        st.caption("No flexible budget split or spending yet.")
    else:
        st.plotly_chart(
            charts.plan_vs_actual(flex, "category", t, cur, color=t.buckets["Flexible"]),
            config=PLOT,
            key="flex",
        )
        data_view(flex, "flex_data")
with right:
    st.subheader("Fixed: planned vs. actual")
    fixed = metrics.fixed_vs_planned(log, settings, month)
    if fixed.empty:
        st.caption("No fixed costs planned or spent yet.")
    else:
        st.plotly_chart(
            charts.plan_vs_actual(fixed, "category", t, cur, color=t.buckets["Fixed"]),
            config=PLOT,
            key="fixed",
        )
        data_view(fixed, "fixed_data")

# --- Trends -------------------------------------------------------------------------------------
st.subheader("Monthly spending by bucket")
trend = metrics.monthly_by_bucket(log)
st.plotly_chart(
    charts.monthly_trend(trend, t, cur, settings.income, selected=month), config=PLOT, key="trend"
)
data_view(
    trend.pivot_table(index="month", columns="bucket", values="amount").reset_index(),
    "trend_data",
)

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Saved per month")
    sav = metrics.savings_series(settings)
    if sav["remaining"].notna().any():
        total = sav["remaining"].sum()
        st.caption(
            f"Close − Open of the main account. Total so far: **{ui.money(total, settings)}**"
        )
        st.plotly_chart(charts.savings(sav, t, cur, selected=month), config=PLOT, key="savings")
        data_view(sav, "savings_data")
    else:
        st.caption("Add Open and Close balances on the Open / Close page.")
with right:
    st.subheader("Top items")
    items = metrics.top(log, month, by="item", n=8)
    st.plotly_chart(charts.top_bars(items, "item", t, cur, color=t.muted), config=PLOT, key="items")
    data_view(items, "items_data")
