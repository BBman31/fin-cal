import streamlit as st

from fincal import ui

st.set_page_config(page_title="fin-cal", page_icon="💰", layout="wide")

pages = [
    st.Page("pages/budget_setup.py", title="Budget Setup", icon="⚙️"),
    st.Page("pages/mappings.py", title="Mappings", icon="🏷️"),
    st.Page("pages/open_close.py", title="Open / Close", icon="🏦"),
]

ui.sidebar()
st.navigation(pages).run()
