import altair as alt
import pandas as pd
import streamlit as st
from connect import run_query, get_connection

CHART_HUE = "#2a78d6"

RESET_CONFIRMATION_PHRASE = "RESET"


@st.dialog("Confirm Deletion")
def confirm_delete(description, delete_query, delete_params, key_suffix):
    st.warning(f"This will permanently delete {description}. This action cannot be undone.")
    st.write("Are you sure you want to delete this entry?")
    yes_col, cancel_col = st.columns([3, 1])
    with yes_col:
        if st.button("Yes, delete", key=f"confirm_delete_yes_{key_suffix}", type="primary"):
            run_query(delete_query, delete_params)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key=f"confirm_delete_cancel_{key_suffix}", width='stretch'):
            st.rerun()


# Order matters: children before parents, so FK constraints don't block deletion.
RESET_TABLE_ORDER = ["session", "registration", "tutors", "students", "courses"]
RESET_TABLE_LABELS = {
    "session": "Sessions",
    "registration": "Registrations",
    "tutors": "Tutors",
    "students": "Students",
    "courses": "Courses",
}
# Deleting a parent requires its dependent child rows to go too, or the FK constraint blocks it.
RESET_TABLE_DEPENDENTS = {
    "tutors": ["session"],
    "students": ["session", "registration"],
    "courses": ["registration"],
}


def expand_reset_selection(tables):
    expanded = set(tables)
    for table in tables:
        expanded.update(RESET_TABLE_DEPENDENTS.get(table, []))
    return [t for t in RESET_TABLE_ORDER if t in expanded]


def reset_selected_data(tables):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for table in RESET_TABLE_ORDER:
                if table in tables:
                    cur.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()


@st.dialog("Confirm Data Reset")
def confirm_reset_data(tables):
    expanded_tables = expand_reset_selection(tables)
    extra_tables = [t for t in expanded_tables if t not in tables]

    selected_labels = ", ".join(RESET_TABLE_LABELS[t] for t in expanded_tables)
    st.warning(
        f"This will permanently delete ALL data from: {selected_labels}. This action cannot be undone."
    )
    if extra_tables:
        extra_labels = ", ".join(RESET_TABLE_LABELS[t] for t in extra_tables)
        st.info(
            f"{extra_labels} will also be deleted since they reference the data you selected."
        )
    st.write("Are you absolutely sure you want to reset this data?")
    yes_col, cancel_col = st.columns([3, 1])
    with yes_col:
        if st.button("Yes, reset selected data", key="confirm_reset_yes", type="primary"):
            reset_selected_data(expanded_tables)
            st.session_state.pop("session_results", None)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key="confirm_reset_cancel", width='stretch'):
            st.rerun()


st.markdown(
    """
    <style>
    div.st-key-save_tutor button, div.st-key-save_prof button, div.st-key-save_course button {
        background-color: #F5D547;
        border-color: #F5D547;
        color: #1a1a1a;
    }
    div.st-key-save_tutor button:hover, div.st-key-save_prof button:hover, div.st-key-save_course button:hover {
        background-color: #E0C13F;
        border-color: #E0C13F;
        color: #1a1a1a;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Admin")
st.warning('''**This page is [prohibited for use](#) by students. Only administrators (Professors, Tutors) may use these features.**\n
Please return to the homepage to sign in.\n
**이 페이지는 학생 사용이 [금지되어 있습니다.](#) 관리자(교수, 튜터)만 이 기능을 사용할 수 있습니다.**\n
로그인하려면 홈페이지로 돌아가세요.''')

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

    if submitted:
        if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()

# --- Everything below this line is only reachable after a successful login ---
st.success("Logged in as admin.")

with st.sidebar:
    if st.button("Sign Out", key="admin_sign_out", type="primary", width='stretch'):
        st.session_state.admin_authenticated = False
        st.rerun()

col1, col2, col3, col4, col5, col6 = st.tabs(
    ["Session Records", "Manage Courses", "Manage Tutors", "Manage Professors", "Summary", "Reset Data"]
)

with col1:
    st.header("Session Records")

    session_mode = st.radio(
        "Show",
        ["All Sessions", "Filter by Tutor", "Filter by Course"],
        key="session_mode",
        horizontal=True,
    )

    session_tutor_filter = None
    session_course_filter = None

    if session_mode == "Filter by Tutor":
        session_tutors = run_query("SELECT tpid, tfname, tlname FROM tutors ORDER BY tlname, tfname")
        session_tutor_filter = st.selectbox(
            "Tutor",
            session_tutors,
            format_func=lambda t: f"{t['tfname']} {t['tlname']} ({t['tpid']})",
            key="session_tutor_filter",
        )
    elif session_mode == "Filter by Course":
        session_courses = run_query("SELECT ccode FROM courses ORDER BY ccode")
        session_course_filter = st.selectbox(
            "Course",
            session_courses,
            format_func=lambda c: c["ccode"],
            help="Filters to students registered in this course",
            key="session_course_filter",
        )

    if st.button("Get Sessions", type="primary"):
        conditions = []
        params = []

        if session_mode == "Filter by Tutor" and session_tutor_filter:
            conditions.append("s.tpid = %s")
            params.append(session_tutor_filter["tpid"])
        elif session_mode == "Filter by Course" and session_course_filter:
            conditions.append("EXISTS (SELECT 1 FROM registration r WHERE r.spid = s.spid AND r.ccode = %s)")
            params.append(session_course_filter["ccode"])

        query = """
            SELECT
                s.date,
                s.tpid,
                t.tfname AS tutor_first_name,
                t.tlname AS tutor_last_name,
                s.spid,
                st.sfname AS student_first_name,
                st.slname AS student_last_name,
                s.validated
            FROM session s
            LEFT JOIN tutors t ON s.tpid = t.tpid
            LEFT JOIN students st ON s.spid = st.spid
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY s.date DESC, t.tlname, st.slname"

        st.session_state.session_results = run_query(query, tuple(params) if params else None)

    if "session_results" in st.session_state:
        session_results = st.session_state.session_results
        st.write(f"{len(session_results)} session record(s) found.")

        if session_results:
            session_df = pd.DataFrame(session_results)
            st.dataframe(session_df, width='stretch')
            st.download_button(
                "Download CSV",
                data=session_df.to_csv(index=False),
                file_name="sessions.csv",
                mime="text/csv",
            )

            sessions_by_date = session_df.groupby("date").size().reset_index(name="session_count")
            date_chart = alt.Chart(sessions_by_date).mark_line(color=CHART_HUE, strokeWidth=2, point=alt.OverlayMarkDef(color=CHART_HUE, size=60)).encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("session_count:Q", title="Sessions"),
                tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("session_count:Q", title="Sessions")],
            ).properties(title="Sessions Over Time", height=280)
            st.altair_chart(date_chart, width='stretch')

with col2:
    st.header("Add/Modify Courses")
    course_action = st.radio("Action", ["Add", "Modify"], key="course_action", horizontal=True)

    course_professors = run_query("SELECT pfname, plname FROM professors ORDER BY plname, pfname")
    prof_options = [None] + course_professors

    def format_prof_option(p):
        return "No Professor Assigned" if p is None else f"{p['pfname']} {p['plname']}"

    if course_action == "Add":
        new_course_code = st.text_input("Course Code", help="Enter the course code (e.g., 'CS101')", key="add_course_code")
        new_course_level = st.text_input("Level", help="e.g., Undergraduate, Graduate", key="add_course_level")
        new_course_prof = st.selectbox("Assigned Professor", prof_options, format_func=format_prof_option, key="add_course_prof")

        if st.button("Add Course"):
            if not new_course_code or not new_course_level:
                st.error("Please fill in the course code and level.")
            else:
                query = "INSERT INTO courses (ccode, level, plname) VALUES (%s, %s, %s)"
                params = (new_course_code, new_course_level, new_course_prof["plname"] if new_course_prof else None)
                run_query(query, params)
                st.success(f"Course {new_course_code} added successfully.")
    else:
        existing_courses = run_query("SELECT ccode, level, plname FROM courses ORDER BY ccode")

        if not existing_courses:
            st.info("There are no courses to modify.")
        else:
            selected_course = st.selectbox(
                "Course",
                existing_courses,
                format_func=lambda c: f"{c['ccode']} ({c['level']})",
                key="modify_course_select",
            )

            edit_course_code = st.text_input("Course Code", value=selected_course["ccode"], key=f"edit_course_code_{selected_course['ccode']}")
            edit_course_level = st.text_input("Level", value=selected_course["level"], key=f"edit_course_level_{selected_course['ccode']}")

            current_prof_index = next(
                (i for i, p in enumerate(prof_options) if p is not None and p["plname"] == selected_course["plname"]),
                0,
            )
            edit_course_prof = st.selectbox(
                "Assigned Professor",
                prof_options,
                format_func=format_prof_option,
                index=current_prof_index,
                key=f"edit_course_prof_{selected_course['ccode']}",
            )

            save_col, delete_col = st.columns([4, 1])
            with save_col:
                if st.button("Save Changes", key="save_course", type="primary"):
                    if not edit_course_code or not edit_course_level:
                        st.error("Please fill in the course code and level.")
                    else:
                        query = "UPDATE courses SET ccode = %s, level = %s, plname = %s WHERE ccode = %s"
                        run_query(query, (
                            edit_course_code,
                            edit_course_level,
                            edit_course_prof["plname"] if edit_course_prof else None,
                            selected_course["ccode"],
                        ))
                        st.success(f"Course {edit_course_code} updated successfully.")
                        st.rerun()
            with delete_col:
                if st.button("Delete Course", key="delete_course", type="primary", width='stretch'):
                    confirm_delete(
                        f"course {selected_course['ccode']}",
                        "DELETE FROM courses WHERE ccode = %s",
                        (selected_course["ccode"],),
                        f"course_{selected_course['ccode']}",
                    )

with col3:
    st.header("Add/Modify Tutors")
    tutor_action = st.radio("Action", ["Add", "Modify"], key="tutor_action", horizontal=True)

    if tutor_action == "Add":
        add_tutor_pid = st.text_input("Tutor PID", max_chars=7, help="Enter the 7-digit PID of the tutor", key="add_tutor_pid")
        add_tutor_fname = st.text_input("First Name", key="add_tutor_fname")
        add_tutor_lname = st.text_input("Last Name", key="add_tutor_lname")
        add_tutor_availability = st.text_area(
            "Availability",
            help="Comma-separated list (e.g., 'Monday 12pm-2pm, Wednesday 10am-2pm')",
            key="add_tutor_availability",
        )

        if st.button("Add Tutor"):
            if not add_tutor_pid or not add_tutor_fname or not add_tutor_lname:
                st.error("Please fill in PID, first name, and last name.")
            elif len(add_tutor_pid) != 7 or not add_tutor_pid.isdigit():
                st.error("PID must be numeric and 7 digits long.")
            else:
                availability_list = [slot.strip() for slot in add_tutor_availability.split(",") if slot.strip()]
                query = "INSERT INTO tutors (tpid, tfname, tlname, ttimes) VALUES (%s, %s, %s, %s)"
                params = (add_tutor_pid, add_tutor_fname, add_tutor_lname, availability_list)
                run_query(query, params)
                st.success(f"Tutor {add_tutor_fname} {add_tutor_lname} added successfully.")
    else:
        existing_tutors = run_query("SELECT tpid, tfname, tlname, ttimes FROM tutors ORDER BY tlname, tfname")

        if not existing_tutors:
            st.info("There are no tutors to modify.")
        else:
            selected_tutor = st.selectbox(
                "Tutor",
                existing_tutors,
                format_func=lambda t: f"{t['tfname']} {t['tlname']} ({t['tpid']})",
                key="modify_tutor_select",
            )

            edit_tutor_pid = st.text_input("Tutor PID", value=selected_tutor["tpid"], max_chars=7, key=f"edit_tutor_pid_{selected_tutor['tpid']}")
            edit_tutor_fname = st.text_input("First Name", value=selected_tutor["tfname"], key=f"edit_tutor_fname_{selected_tutor['tpid']}")
            edit_tutor_lname = st.text_input("Last Name", value=selected_tutor["tlname"], key=f"edit_tutor_lname_{selected_tutor['tpid']}")
            edit_tutor_availability = st.text_area(
                "Availability",
                value=", ".join(selected_tutor["ttimes"] or []),
                help="Comma-separated list (e.g., 'Monday 12pm-2pm, Wednesday 10am-2pm')",
                key=f"edit_tutor_availability_{selected_tutor['tpid']}",
            )

            save_col, delete_col = st.columns([4, 1])
            with save_col:
                if st.button("Save Changes", key="save_tutor", type="primary"):
                    if not edit_tutor_pid or not edit_tutor_fname or not edit_tutor_lname:
                        st.error("Please fill in PID, first name, and last name.")
                    elif len(edit_tutor_pid) != 7 or not edit_tutor_pid.isdigit():
                        st.error("PID must be numeric and 7 digits long.")
                    else:
                        availability_list = [slot.strip() for slot in edit_tutor_availability.split(",") if slot.strip()]
                        query = "UPDATE tutors SET tpid = %s, tfname = %s, tlname = %s, ttimes = %s WHERE tpid = %s"
                        run_query(query, (edit_tutor_pid, edit_tutor_fname, edit_tutor_lname, availability_list, selected_tutor["tpid"]))
                        st.success(f"Tutor {edit_tutor_fname} {edit_tutor_lname} updated successfully.")
                        st.rerun()
            with delete_col:
                if st.button("Delete Tutor", key="delete_tutor", type="primary", width='stretch'):
                    confirm_delete(
                        f"{selected_tutor['tfname']} {selected_tutor['tlname']} ({selected_tutor['tpid']})",
                        "DELETE FROM tutors WHERE tpid = %s",
                        (selected_tutor["tpid"],),
                        f"tutor_{selected_tutor['tpid']}",
                    )

with col4:
    st.header("Add/Modify Professors")
    prof_action = st.radio("Action", ["Add", "Modify"], key="prof_action", horizontal=True)

    if prof_action == "Add":
        add_prof_fname = st.text_input("First Name", key="add_prof_fname")
        add_prof_lname = st.text_input("Last Name", key="add_prof_lname")

        if st.button("Add Professor"):
            if not add_prof_fname or not add_prof_lname:
                st.error("Please fill in both fields.")
            else:
                query = "INSERT INTO professors (pfname, plname) VALUES (%s, %s)"
                params = (add_prof_fname, add_prof_lname)
                run_query(query, params)
                st.success(f"Professor {add_prof_fname} {add_prof_lname} added successfully.")
    else:
        existing_profs = run_query("SELECT pfname, plname FROM professors ORDER BY plname, pfname")

        if not existing_profs:
            st.info("There are no professors to modify.")
        else:
            selected_prof = st.selectbox(
                "Professor",
                existing_profs,
                format_func=lambda p: f"{p['pfname']} {p['plname']}",
                key="modify_prof_select",
            )

            edit_prof_fname = st.text_input("First Name", value=selected_prof["pfname"], key=f"edit_prof_fname_{selected_prof['plname']}")
            edit_prof_lname = st.text_input("Last Name", value=selected_prof["plname"], key=f"edit_prof_lname_{selected_prof['plname']}")

            save_col, delete_col = st.columns([4, 1])
            with save_col:
                if st.button("Save Changes", key="save_prof", type="primary"):
                    if not edit_prof_fname or not edit_prof_lname:
                        st.error("Please fill in both fields.")
                    else:
                        query = "UPDATE professors SET pfname = %s, plname = %s WHERE plname = %s"
                        run_query(query, (edit_prof_fname, edit_prof_lname, selected_prof["plname"]))
                        st.success(f"Professor {edit_prof_fname} {edit_prof_lname} updated successfully.")
                        st.rerun()
            with delete_col:
                if st.button("Delete Professor", key="delete_prof", type="primary", width='stretch'):
                    confirm_delete(
                        f"{selected_prof['pfname']} {selected_prof['plname']}",
                        "DELETE FROM professors WHERE plname = %s",
                        (selected_prof["plname"],),
                        f"prof_{selected_prof['plname']}",
                    )

with col5:
    st.header("Summary")

    summary_totals = run_query("SELECT COUNT(*) AS total, COUNT(DISTINCT spid) AS students, COUNT(DISTINCT tpid) AS tutors FROM session")[0]
    summary_validated = run_query("SELECT COUNT(*) AS validated FROM session WHERE validated = TRUE")[0]["validated"]

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("Total Sessions", summary_totals["total"])
    kpi_col2.metric("Students Attended", summary_totals["students"])
    kpi_col3.metric("Tutors Active", summary_totals["tutors"])
    kpi_col4.metric("Validated Sessions", summary_validated)

    if summary_totals["total"] == 0:
        st.info("There are no sessions recorded yet.")
    else:
        student_attendance = run_query("""
            SELECT st.sfname, st.slname, COUNT(*) AS session_count
            FROM session s
            JOIN students st ON s.spid = st.spid
            GROUP BY st.sfname, st.slname
            ORDER BY session_count DESC
        """)
        student_df = pd.DataFrame(student_attendance)
        student_df["student"] = student_df["sfname"] + " " + student_df["slname"]

        st.subheader("Sessions Attended per Student")
        student_chart = alt.Chart(student_df).mark_bar(color=CHART_HUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("student:N", title=None, sort="-y"),
            y=alt.Y("session_count:Q", title="Sessions Attended"),
            tooltip=[alt.Tooltip("student:N", title="Student"), alt.Tooltip("session_count:Q", title="Sessions")],
        ).properties(height=300)
        st.altair_chart(student_chart, width='stretch')

        tutor_summary = run_query("""
            SELECT t.tfname, t.tlname, COUNT(DISTINCT s.spid) AS students_assisted, COUNT(*) AS total_sessions
            FROM session s
            JOIN tutors t ON s.tpid = t.tpid
            GROUP BY t.tfname, t.tlname
            ORDER BY students_assisted DESC
        """)
        tutor_df = pd.DataFrame(tutor_summary)
        tutor_df["tutor"] = tutor_df["tfname"] + " " + tutor_df["tlname"]

        st.subheader("Students Assisted per Tutor")
        tutor_chart = alt.Chart(tutor_df).mark_bar(color=CHART_HUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("tutor:N", title=None, sort="-y"),
            y=alt.Y("students_assisted:Q", title="Students Assisted"),
            tooltip=[
                alt.Tooltip("tutor:N", title="Tutor"),
                alt.Tooltip("students_assisted:Q", title="Students Assisted"),
                alt.Tooltip("total_sessions:Q", title="Total Sessions"),
            ],
        ).properties(height=300)
        st.altair_chart(tutor_chart, width='stretch')
        st.dataframe(tutor_df[["tutor", "students_assisted", "total_sessions"]], width='stretch', hide_index=True)

        course_summary = run_query("""
            SELECT c.ccode, COUNT(DISTINCT s.spid) AS students_assisted, COUNT(*) AS total_sessions
            FROM courses c
            JOIN registration r ON r.ccode = c.ccode
            JOIN session s ON s.spid = r.spid
            GROUP BY c.ccode
            ORDER BY students_assisted DESC
        """)

        if course_summary:
            course_df = pd.DataFrame(course_summary)

            st.subheader("Students Assisted per Course")
            course_chart = alt.Chart(course_df).mark_bar(color=CHART_HUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X("ccode:N", title=None, sort="-y"),
                y=alt.Y("students_assisted:Q", title="Students Assisted"),
                tooltip=[
                    alt.Tooltip("ccode:N", title="Course"),
                    alt.Tooltip("students_assisted:Q", title="Students Assisted"),
                    alt.Tooltip("total_sessions:Q", title="Total Sessions"),
                ],
            ).properties(height=300)
            st.altair_chart(course_chart, width='stretch')

with col6:
    st.header("Reset Data")
    st.warning(
        "Select the data you want to wipe below. Professor data can never be reset here. "
        "This action cannot be undone."
    )

    reset_counts = run_query("""
        SELECT
            (SELECT COUNT(*) FROM tutors) AS tutors,
            (SELECT COUNT(*) FROM students) AS students,
            (SELECT COUNT(*) FROM courses) AS courses,
            (SELECT COUNT(*) FROM session) AS sessions,
            (SELECT COUNT(*) FROM registration) AS registrations
    """)[0]

    count_col1, count_col2, count_col3, count_col4, count_col5 = st.columns(5)
    count_col1.metric("Tutors", reset_counts["tutors"])
    count_col2.metric("Students", reset_counts["students"])
    count_col3.metric("Courses", reset_counts["courses"])
    count_col4.metric("Sessions", reset_counts["sessions"])
    count_col5.metric("Registrations", reset_counts["registrations"])

    reset_tables_selected = st.multiselect(
        "Data to delete",
        options=RESET_TABLE_ORDER,
        format_func=lambda t: RESET_TABLE_LABELS[t],
        key="reset_tables_selected",
    )

    reset_confirmation_text = st.text_input(
        f'Type "{RESET_CONFIRMATION_PHRASE}" to enable the button below',
        key="reset_confirmation_text",
    )

    if st.button(
        "Reset Selected Data",
        key="reset_all_data_button",
        type="primary",
        disabled=not reset_tables_selected or reset_confirmation_text != RESET_CONFIRMATION_PHRASE,
    ):
        confirm_reset_data(reset_tables_selected)