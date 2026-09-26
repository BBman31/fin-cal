import streamlit as st

from fincal import metrics, storage, ui
from fincal.mapping import UNMAPPED
from fincal.models import BUCKETS, Settings

settings = ui.load_settings()
log = ui.load_enriched(settings)

head, reload_col = st.columns([5, 1], vertical_alignment="bottom")
head.title("Spending Log")
if reload_col.button("Reload", icon="🔄", width="stretch"):
    st.cache_data.clear()
    st.rerun()
st.caption(f"Read from `{storage.log_path()}`. Edit that file in Excel; this view is read-only.")

if log.attrs.get("dropped_rows"):
    st.warning(
        f"{log.attrs['dropped_rows']} row(s) in the Excel file were skipped "
        "because the date or amount could not be read."
    )
if log.empty:
    st.info("No spending rows yet. Paste rows (Date · Item · Amount) into the Excel file.")
    st.stop()

# --- Unmapped items ---------------------------------------------------------------------------
unmapped = log[log["category"] == UNMAPPED]
no_bucket = log[(log["category"] != UNMAPPED) & (log["bucket"] == UNMAPPED)]
if not unmapped.empty:
    with st.expander(
        f"⚠️ {unmapped['item'].nunique()} unmapped item(s) · "
        f"{ui.money(unmapped['amount'].sum(), settings)}",
        expanded=True,
    ):
        st.caption(
            "Pick a category to create a mapping. Shorten the match text to cover variants, "
            "e.g. `MobilePay` instead of `MobilePay Anna`."
        )
        todo = (
            unmapped.groupby("item", as_index=False)
            .agg(rows=("amount", "size"), amount=("amount", "sum"), last=("date", "max"))
            .sort_values("amount", ascending=False, ignore_index=True)
        )
        todo.insert(1, "match", todo["item"])
        todo["category"] = None
        edited = st.data_editor(
            todo,
            column_config={
                "item": st.column_config.TextColumn("Item", disabled=True),
                "match": st.column_config.TextColumn("Match text"),
                "rows": st.column_config.NumberColumn("Rows", disabled=True),
                "amount": st.column_config.NumberColumn("Amount", format="%.0f", disabled=True),
                "last": st.column_config.DateColumn("Last seen", disabled=True),
                "category": st.column_config.SelectboxColumn(
                    "Category", options=sorted(settings.category_buckets, key=str.casefold)
                ),
            },
            hide_index=True,
            width="stretch",
            key="unmapped",
        )
        new = {
            str(r.match).strip(): r.category
            for r in edited.itertuples()
            if isinstance(r.category, str) and isinstance(r.match, str) and r.match.strip()
        }
        if st.button(
            f"Add {len(new)} mapping(s)",
            type="primary",
            disabled=not new or ui.read_only(),
            icon="🏷️",
        ):
            draft = Settings.from_dict(settings.to_dict())
            draft.item_categories.update(new)
            if ui.save(draft, "Mappings"):
                st.rerun()
if not no_bucket.empty:
    cats = ", ".join(sorted(no_bucket["category"].unique()))
    st.warning(f"Categories without a bucket: {cats}. Assign them on the Mappings page.")

# --- Filters ----------------------------------------------------------------------------------
all_months = metrics.months(log)
f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
months = f1.multiselect(
    "Month", all_months[::-1], default=all_months[-1:], placeholder="All months"
)
buckets = f2.multiselect("Bucket", [*BUCKETS, UNMAPPED], placeholder="All buckets")
categories = f3.multiselect(
    "Category", sorted(log["category"].unique(), key=str.casefold), placeholder="All categories"
)
search = f4.text_input("Search item / comment", placeholder="e.g. Netto")

view = log
if months:
    view = view[view["month"].isin(months)]
if buckets:
    view = view[view["bucket"].isin(buckets)]
if categories:
    view = view[view["category"].isin(categories)]
if search:
    text = view["item"] + " " + view["comment"].fillna("")
    view = view[text.str.contains(search, case=False, regex=False)]

m1, m2, m3 = st.columns(3)
m1.metric("Rows", f"{len(view):,}".replace(",", " "))
m2.metric("Total", ui.money(view["amount"].sum(), settings))
m3.metric("Average", ui.money(view["amount"].mean() if len(view) else None, settings))

st.dataframe(
    view.assign(override=view["category_override"].notna())[
        ["date", "item", "amount", "category", "bucket", "override", "comment"]
    ].sort_values("date", ascending=False),
    column_config={
        "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
        "item": "Item",
        "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        "category": "Category",
        "bucket": "Bucket",
        "override": st.column_config.CheckboxColumn(
            "Manual", help="Category typed in the Excel file instead of coming from Mappings"
        ),
        "comment": "Comment",
    },
    hide_index=True,
    width="stretch",
    height=600,
)

csv = view.drop(columns=["mapped"]).to_csv(index=False).encode()
st.download_button("Download filtered rows (CSV)", csv, "spending.csv", "text/csv", icon="⬇️")
