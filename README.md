# Tutoring Session Attendance

A Streamlit app for tracking tutoring session attendance. Students sign in with
their PID during active tutoring hours or register as first-time students; an
admin page manages tutors, professors, courses, and session records.

## Pages

- **Home Page** (`pages/home.py`) — shows current tutor hours, lets a student
  record attendance during an active session, or register as a new student.
- **Admin Page** (`pages/admin.py`) — password-protected. Tabs:
  - **Session Records** — view all sessions, or filter by tutor / course; export to CSV.
  - **Manage Courses** — add, edit, or delete courses.
  - **Manage Tutors** — add, edit, or delete tutors and their availability.
  - **Manage Professors** — add, edit, or delete professors.
  - **Summary** — attendance counts per student, students assisted per tutor, and
    students assisted per course, with charts.
  - **Reset Data** — wipes all tutors, students, courses, sessions, and
    registrations (professors are kept). Requires typing a confirmation phrase
    plus a second confirmation dialog.

Signing out (via the sidebar) or navigating to the Home Page clears the admin
session.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```

2. Create `.streamlit/secrets.toml` (gitignored — never commit this file):

   ```toml
   DATABASE_URL = "postgresql://<user>:<password>@<host>/<database>?sslmode=require"

   [admin]
   username = "your-admin-username"
   password = "your-admin-password"
   ```

3. Run the app:

   ```
   streamlit run app.py
   ```

## Deploying (Streamlit Community Cloud)

Set the same keys from `secrets.toml` in the app's **Settings > Secrets** on
[share.streamlit.io](https://share.streamlit.io) — the local `secrets.toml`
file is never uploaded (it's gitignored), so secrets must be entered there
directly.

## Database schema

PostgreSQL, referenced via `connect.py`:

| Table          | Key columns                                          |
|----------------|-------------------------------------------------------|
| `students`     | `spid` (PK), `sfname`, `slname`                       |
| `tutors`       | `tpid` (PK), `tfname`, `tlname`, `ttimes` (array)     |
| `professors`   | `plname` (PK), `pfname`                               |
| `courses`      | `ccode` (PK), `level`, `plname` (FK → `professors`)   |
| `registration` | `spid` (FK → `students`), `ccode` (FK → `courses`)    |
| `session`      | `date`, `tpid` (FK → `tutors`), `spid` (FK → `students`), `validated` — PK on `(date, tpid, spid)` |

`registration.ccode` is `varchar(20)` (widened from its original `varchar(10)`,
which was too short for real course codes like `KOR1113  U01`).
