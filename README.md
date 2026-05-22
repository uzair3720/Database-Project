# Learning Management Portal (LMP)

**Group Number:** 15
**Course:** Database Systems — FAST National University of Computer and Emerging Sciences

A Google Classroom-style web app where instructors create courses, post
assignments / quizzes / announcements, and students join courses with a
code, submit work, and view grades.

## Group Members

| Name | Roll Number | Contribution |
|------|-------------|--------------|
| Abdullah Kamal | 23P-0668 | Database schema & constraints, indexes, connection layer, authentication |
| Taha Rizwan | 23P-0037 | Database views & triggers, courses, enrollments, announcements, comments |
| Muhammad Uzair | 23P-0620 | Stored functions & migrations, assignments, submissions, quizzes, dashboard, UI |

**GitHub Repository:** https://github.com/uzair3720/database-Project

## Tech stack

- Python 3.12 + Flask 3
- PostgreSQL 16
- psycopg2-binary (raw SQL, no ORM)
- Jinja2 templates + Tailwind CSS (CDN) + Geist / Inter fonts + Material Symbols
- bcrypt for password hashing
- Local filesystem `uploads/` for file storage

## Features

- Email + password auth with bcrypt, "remember me" (30-day permanent session)
- Forgot-password / reset-password (reset link printed to Flask console if SMTP isn't configured)
- Instructor & student dashboards
- Courses with auto-generated 6-char join codes and optional human course codes
- Assignments with file attachments and due dates
- Submissions: students upload, instructors grade in a `SET LOCAL`-tracked transaction
- Quizzes: offline scoring by instructor
- Announcements (instructor-only posting) + class comments + delete-own-comment
- Per-course gradebook (instructor) and per-student grades view
- Calendar derived from assignment due dates
- Global search across courses, assignments, announcements
- Notifications fired by triggers on new assignment / grade / announcement
- Light + dark theme (persisted in localStorage)
- File downloads scoped to course membership / submission ownership
- Full CRUD: edit & delete for courses, assignments, quizzes, announcements

## Setup on Linux (Ubuntu / Debian)

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip \
                    postgresql-16 postgresql-client-16 libpq-dev
```

### 2. Create the database and a role

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE lmp_user WITH LOGIN PASSWORD 'lmp_pass';
CREATE DATABASE lmp_db OWNER lmp_user;
GRANT ALL PRIVILEGES ON DATABASE lmp_db TO lmp_user;
SQL
```

### 3. Apply the schema and DB objects (order matters)

```bash
cd lmp_project
psql -U lmp_user -d lmp_db -h localhost -f schema.sql
psql -U lmp_user -d lmp_db -h localhost -f db/indexes.sql
psql -U lmp_user -d lmp_db -h localhost -f db/views.sql
psql -U lmp_user -d lmp_db -h localhost -f db/triggers.sql
psql -U lmp_user -d lmp_db -h localhost -f db/procedures.sql
psql -U lmp_user -d lmp_db -h localhost -f db/migrations.sql
```
password = lmp_pass
`db/migrations.sql` is idempotent — re-running it is safe and required
when pulling new changes that add tables, columns, or triggers.

### 4. Create a virtual environment and install Python deps

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure environment

```bash
cp .env.example .env
# Edit .env: FLASK_SECRET_KEY, DB credentials.
```

Optional — to actually send password-reset emails (otherwise the reset
URL prints to the Flask console, which is enough for the viva):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=<gmail app password>
SMTP_FROM=you@gmail.com
```

### 6. Run

```bash
mkdir -p uploads/assignments uploads/submissions
flask --app app.py run --debug --port 5000
```

Open http://localhost:5000 and sign up as an instructor or student.

## How to test the full flow

1. Sign up as an instructor (e.g. `prof@fast.edu.pk`).
2. Sign up as a student in a second browser (e.g. `s1@fast.edu.pk`).
3. Instructor creates a course (optional course code, e.g. `CS2001`) — note the 6-character join code.
4. Student clicks "Join Course", pastes the code.
5. Instructor creates an assignment.
6. Student submits a file.
7. Instructor opens the assignment, sees the submission, grades it.
8. Student sees the grade and feedback on the course page and the Grades tab.
9. Try "Forgot password" — the reset link appears in the Flask console.
10. Open the bell icon — notifications appear on new assignment / grade.

## Team
- Abdullah Kamal (23P-0668) — schema & constraints, indexes, connection layer,auth
- Taha Rizwan (23P-0037) — views & triggers, courses, announcements, comments
- Muhammad Uzair (23P-0620) — stored functions & migrations, assignments,quizzes, dashboard, UI

