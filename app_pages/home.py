import streamlit as st
import datetime
import base64
from connect import run_query
# from app import zoomLink


st.title("Tutoring Session Attendance")

st.session_state.admin_authenticated = False

tutors = run_query("SELECT * FROM tutors")

from datetime import datetime

tutor_schedule = []

for item in tutors:
    for time in item['ttimes']:
        day, time_range = time.split(' ', 1)
        start, end = time_range.split('-', 1)

        start_time = datetime.strptime(start, "%I%p")
        end_time = datetime.strptime(end, "%I%p")

        tutor_schedule.append({
            "tpid": item["tpid"],
            "tfname": item["tfname"],
            "tlname": item["tlname"],
            "day": day,
            "start": start_time,
            "end": end_time,
        })

days = {}

for rec in tutor_schedule:
    days.setdefault(rec["day"], []).append((rec["start"], rec["end"]))


# Merge overlapping/adjacent times
merged = {}

for day, times in days.items():

    # Sort by starting time
    times.sort(key=lambda x: x[0])

    merged_times = []

    for start, end in times:

        if not merged_times:
            merged_times.append([start, end])

        else:
            previous_start, previous_end = merged_times[-1]

            # If this time starts when the previous one ends,
            # or overlaps with it, merge them
            if start <= previous_end:
                merged_times[-1][1] = max(previous_end, end)
            else:
                merged_times.append([start, end])

    merged[day] = merged_times


# Find the tutor whose schedule covers right now, if any.
# Slots are mutually exclusive but may be back-to-back (one ends when the
# next starts) - use an exclusive end so the later tutor wins at the boundary.
now = datetime.now()
current_day = now.strftime("%A")
current_time = now.time()

active_tutor = None
for rec in tutor_schedule:
    if rec["day"] == current_day and rec["start"].time() <= current_time < rec["end"].time():
        active_tutor = rec

is_session_active = active_tutor is not None

availableCourses = run_query('''SELECT * FROM courses''')
result = []

for day, times in merged.items():
    for start, end in times:
        start_string = start.strftime("%I%p").lstrip("0").lower()
        end_string = end.strftime("%I%p").lstrip("0").lower()

        result.append(f"{day} {start_string}-{end_string}")


# Sort days Monday → Sunday
day_order = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

result.sort(key=lambda x: day_order[x.split(" ")[0]])


hours = "\n".join(f"- {time}" for time in result)

st.markdown(f"""
Welcome to the Tutoring Session Attendance App for Korean! We offer Korean tutoring both in-person at SIPA 1 240 as well as through zoom. This semester, our current hours are:

{hours}

Please sign in with your PID to record your attendance or register as a first-time student if you have not done so before.
""")

# with open("assets/zoom.png", "rb") as f:
#     zoom_image_b64 = base64.b64encode(f.read()).decode()
#
# st.sidebar.markdown(
#     f"""
#     <div style="text-align: center;">
#         <a href="{zoomLink}" target="_blank">
#             <img src="data:image/png;base64,{zoom_image_b64}" width="100">
#         </a>
#         <div style="font-size: 0.8rem; color: rgba(49, 51, 63, 0.6);">
#             Click to join the zoom session!
#         </div>
#     </div>
#     """,
#     unsafe_allow_html=True,
# )

tab1, tab2 = st.tabs(["Attendance Form", "First Time Student Registeration"])

with tab1:
    st.header("Attendance Form")
    if is_session_active:
        st.write(f"Tutor on duty: {active_tutor['tfname']} {active_tutor['tlname']}")
        st.write("Please fill out the form below to record your attendance for the tutoring session.")
        attForm = st.form("Attendance Form", clear_on_submit=True)
    else:
        st.warning("There is no tutoring session currently in progress. Attendance can only be recorded during active tutoring hours.")
        attForm = None

with tab2:
    st.header("First Time Student Registeration")
    st.write("Please fill out the form below to register as a first time student.")
    regForm = st.form("Registeration Form", clear_on_submit=True)

if attForm:
    with attForm:
        student_PID = st.text_input("Student PID", max_chars=7, help="Enter your 7-digit PID")


        submit_button = st.form_submit_button("Submit Attendance")

        if submit_button:
            if not student_PID:
                st.error("Please enter your PID.")
            elif len(student_PID) != 7 or not student_PID.isdigit():
                st.error("PID must be numeric and 7 digits long.")
            elif not run_query("SELECT * FROM students WHERE spid = %s", (student_PID,)):
                st.error("PID not found. Please register as a first-time student.")
            else:

                date = datetime.today().strftime("%Y-%m-%d")

                # Insert attendance record into the database
                query = """
                    INSERT INTO session (date, tpid, spid, validated)
                    VALUES (%s, %s, %s, %s)
                """
                params = (
                    date,
                    active_tutor["tpid"],
                    student_PID,
                    False  # validated
                )
                run_query(query, params)
                st.success("Attendance recorded successfully!")

with regForm:
    student_first_name = st.text_input("Student First Name", help="Enter your first name")
    student_last_name = st.text_input("Student Last Name", help="Enter your last name")
    student_PID = st.text_input("Student PID", max_chars=7, help="Enter your 7-digit PID")

    enrolled_courses = st.multiselect(
        "Enrolled Courses",
        options=availableCourses,
        format_func=lambda c: f"{c['ccode']} - {c['level']} - Professor {c['plname']}",
    )

    submit_button = st.form_submit_button("Register Student")

    if submit_button:
        if not student_first_name or not student_last_name or not student_PID:
            st.error("Please fill in all fields.")
        elif len(student_PID) != 7 or not student_PID.isdigit():
            st.error("PID must be numeric and 7 digits long.")
        else:
            # Insert new student record into the database
            query_student = """
                INSERT INTO students (spid, sfname, slname)
                VALUES (%s, %s, %s)
            """
            params_student = (
                student_PID,
                student_first_name,
                student_last_name
            )
            run_query(query_student, params_student)

            query_registration = """
                INSERT INTO registration (spid, ccode)
                VALUES (%s, %s)
            """
            for course in enrolled_courses:
                run_query(query_registration, (student_PID, course["ccode"]))

            st.success("Student registered successfully!")