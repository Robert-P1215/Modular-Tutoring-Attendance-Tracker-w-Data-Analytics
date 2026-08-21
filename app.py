import streamlit as st
from connect import run_query

st.title("Hello")

tutors = run_query("SELECT * FROM tutors")

st.write(tutors)

tutorTimes = []
for item in tutors:
    for time in item['ttimes']:
        tutorTimes.append((item['tfname'], time))

selected_tutor = st.selectbox(
    "Select",
    tutorTimes,
    format_func=lambda tutor: f"{tutor[0]} : {tutor[1]}",
    accept_new_options=False
)
