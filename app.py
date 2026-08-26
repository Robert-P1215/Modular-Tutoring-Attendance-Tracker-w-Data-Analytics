import streamlit as st

pages = [
    st.Page("app_pages/home.py", title="Home Page"),
    st.Page("app_pages/admin.py", title="Admin Page")
]

pg = st.navigation(pages)
pg.run()