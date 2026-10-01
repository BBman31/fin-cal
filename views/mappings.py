import pandas as pd
import streamlit as st

from fincal import ui
from fincal.mapping import Lookup, normalize
from fincal.models import BUCKETS, Settings

settings = ui.load_settings()
log = ui.load_enriched(settings)

st.title("Mappings")
st.caption(
    "An item in the spending log gets its category from the first table (exact match, "
    "otherwise the longest key contained in the item text, case-insensitive). "
    "The category then decides the budget bucket."
)

draft = Settings.from_dict(settings.to_dict())


def pairs(df: pd.DataFrame, key: str, value: str) -> list[tuple[str, str]]:
    return [
        (str(k).strip(), str(v).strip())
        for k, v in zip(df[key], df[value], strict=True)
        if isinstance(k, str) and k.strip() and isinstance(v, str) and v.strip()
    ]


def warn_conflicts(lookup: Lookup, name: str) -> None:
    for key, values in lookup.conflicts.items():
        st.warning(
            f"{name} '{key}' is listed more than once with {sorted(values)}; first one wins."
        )


left, right = st.columns([2, 3], gap="large")

with left:
    st.subheader("Category → Bucket")
    spent = log.groupby("category")["amount"].agg(["size", "sum"])
    cat_df = pd.DataFrame(
        {
            "category": list(settings.category_buckets),
            "bucket": list(settings.category_buckets.values()),
        }
    )
    cat_df["rows"] = cat_df["category"].map(spent["size"]).fillna(0).astype(int)
    cat_edit = st.data_editor(
        cat_df,
        column_config={
            "category": st.column_config.TextColumn("Category", required=True),
            "bucket": st.column_config.SelectboxColumn("Bucket", options=BUCKETS, required=True),
            "rows": st.column_config.NumberColumn("Log rows", disabled=True),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        height=560,
        key="categories",
    )
    cat_pairs = pairs(cat_edit, "category", "bucket")
    cat_lookup = Lookup.from_pairs(cat_pairs)
    warn_conflicts(cat_lookup, "Category")
    draft.category_buckets = {}
    for k, v in cat_pairs:
        draft.category_buckets.setdefault(k, v)

with right:
    st.subheader("Item → Category")
    items = Lookup.from_dict(settings.item_categories)
    hits = log["item"].map(items.match).value_counts()
    item_df = pd.DataFrame(
        {
            "item": list(settings.item_categories),
            "category": list(settings.item_categories.values()),
        }
    )
    item_df["rows"] = item_df["item"].map(lambda i: int(hits.get(normalize(i), 0)))
    category_options = sorted(draft.category_buckets, key=str.casefold)
    item_edit = st.data_editor(
        item_df,
        column_config={
            "item": st.column_config.TextColumn("Item (text to match)", required=True),
            "category": st.column_config.SelectboxColumn(
                "Category",
                options=category_options,
                required=True,
                help="Add new categories in the Category → Bucket table first.",
            ),
            "rows": st.column_config.NumberColumn("Log rows", disabled=True),
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        height=560,
        key="items",
    )
    item_pairs = pairs(item_edit, "item", "category")
    warn_conflicts(Lookup.from_pairs(item_pairs), "Item")
    draft.item_categories = {}
    for k, v in item_pairs:
        draft.item_categories.setdefault(k, v)

missing = sorted(
    {v for v in draft.item_categories.values() if normalize(v) not in cat_lookup.exact}
)
if missing:
    st.warning(f"These categories have no bucket yet: {', '.join(missing)}")

st.divider()
errors = draft.validate()
for e in errors:
    st.error(e)
changed = draft != settings
if st.button(
    "Save mappings",
    type="primary",
    disabled=bool(errors) or not changed or ui.read_only(),
    icon="💾",
) and ui.save(draft, "Mappings"):
    st.rerun()
if changed and not errors:
    st.caption("Unsaved changes")
