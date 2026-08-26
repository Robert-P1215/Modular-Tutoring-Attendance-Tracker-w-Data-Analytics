import streamlit as st
from connect import run_query

zoomLink=run_query("SELECT * FROM zoom")[0]["zlink"]

pages = [
    st.Page("app_pages/home.py", title="Home Page"),
    st.Page("app_pages/admin.py", title="Admin Page")
]

pg = st.navigation(pages)
pg.run()