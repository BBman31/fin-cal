import streamlit as st

from fincal import ui

st.set_page_config(page_title="fin-cal", page_icon="💰", layout="wide")

pages = [
    st.Page("views/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("views/spending_log.py", title="Spending Log", icon="🧾"),
    st.Page("views/budget_setup.py", title="Budget Setup", icon="⚙️"),
    st.Page("views/mappings.py", title="Mappings", icon="🏷️"),
    st.Page("views/open_close.py", title="Open / Close", icon="🏦"),
]

ui.sidebar()
st.navigation(pages).run()
