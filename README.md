# Tutoring Session Attendance

A Streamlit app for tracking tutoring session attendance. Students sign in with
their PID during active tutoring hours or register as first-time students; an
admin page manages tutors, professors, courses, and session records.

## Pages

- **Home Page** (`app_pages/home.py`) — shows current tutor hours, lets a student
  record attendance during an active session, or register as a new student.
  The sidebar also shows a clickable Zoom icon linking to the current
  session's Zoom link.
- **Admin Page** (`app_pages/admin.py`) — password-protected. Tabs:
  - **Session Records** — view all sessions, or filter by tutor / course; export to CSV.
  - **Manage Courses** — add, edit, or delete courses.
  - **Manage Tutors** — add, edit, or delete tutors and their availability.
  - **Manage Professors** — add, edit, or delete professors.
  - **Summary** — attendance counts per student, students assisted per tutor, and
    students assisted per course, with charts.
  - **Reset Data** — wipes all tutors, students, courses, sessions, and
    registrations (professors are kept). Requires typing a confirmation phrase
    plus a second confirmation dialog.
  - **Misc. Settings** — update the Zoom link shown on the Home Page.

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
| `zoom`         | `zlink` — single-row table holding the current semester's Zoom link |

## Notes for maintainers

- Page files must not live in a folder named `pages/` — that name
  triggers Streamlit's legacy auto-multipage mode, which conflicts with
  the explicit `st.navigation()` setup in `app.py` and can cause pages to
  execute twice. Keep them under `app_pages/` (or any non-magic folder
  name).
- Page files must fetch their own data directly (e.g. via `run_query`)
  rather than importing values from `app.py`. Streamlit executes page
  scripts into a bare module that is never registered in `sys.modules` as
  `app`, so a page-level `from app import ...` triggers a real, first-time
  import of `app.py` — which re-runs `st.navigation(...).run()` and
  recursively re-executes the current page a second time. This previously
  caused "multiple identical forms" errors on the first page load of a
  fresh process.

`registration.ccode` is `varchar(20)` (widened from its original `varchar(10)`,
which was too short for real course codes like `KOR1113  U01`).
