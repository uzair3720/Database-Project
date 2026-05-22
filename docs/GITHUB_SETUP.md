# GitHub Setup — get the project online with every member contributing

> Goal: a single repo where the **Contributors** tab and each member's
> profile graph show real commits — and where **each member owns a piece
> of the database** so everyone can answer DB questions in the viva.
>
> We do this by having **each teammate push only their own files**, in sequence.

Members, GitHub usernames, and the files each one owns:

| Member | GitHub | Owns these files |
|---|---|---|
| **Uzair** (`uzair3720`) | functions, migrations, UI, assignments, quizzes | `db/procedures.sql`, `db/migrations.sql`, `app.py`, `templates/base.html`, `templates/_partials/`, `templates/assignments/`, `templates/quizzes/`, `templates/submissions/`, `templates/dashboard.html`, `templates/calendar/`, `templates/notifications/`, `templates/profile/`, `templates/search/`, `routes/assignments.py`, `routes/submissions.py`, `routes/quizzes.py`, `routes/calendar.py`, `routes/notifications.py`, `routes/profile.py`, `routes/search.py`, `routes/__init__.py`, plus shared: `requirements.txt`, `.gitignore`, `.env.example`, `README.md`, `docs/`, `static/`, `frontend/` |
| **Taha** (`taha1903`) | views, triggers, courses, announcements | `db/views.sql`, `db/triggers.sql`, `routes/courses.py`, `routes/announcements.py`, `routes/comments.py`, `templates/courses/`, `templates/announcements/` |
| **Abdullah** (`abdullah-kam`) | schema, indexes, connection, auth | `schema.sql`, `db/indexes.sql`, `db.py`, `config.py`, `auth_helpers.py`, `routes/auth.py`, `templates/auth/` |

> **DB ownership for the viva:** Abdullah = schema + constraints + indexes;
> Taha = views + triggers; Uzair = stored functions + migrations. Each
> person should read that section of `docs/DATABASE_GUIDE.pdf` closely.

---

## STEP 0 — One-time: make sure git knows who you are

Each person runs this **on their own laptop**, with the **email tied to their GitHub account** (this is what lights up the profile graph):

```bash
git config --global user.name  "<Your Name>"
git config --global user.email "<your-github-email>"
```

---

## STEP 1 — Uzair: create the repo and push first

### 1a. Create the empty repo on github.com
1. Go to https://github.com/new
2. Repository name: **`database-Project`**
3. Visibility: **Private** is fine (add the instructor later if required), or Public.
4. **Do NOT** tick "Add a README" / .gitignore / license — keep it empty.
5. Click **Create repository**. Your URL will be `https://github.com/uzair3720/database-Project.git`

### 1b. Initialise locally and push only Uzair's files
```bash
cd /home/uzair/Desktop/lmp_project
git init -b main
git remote add origin https://github.com/uzair3720/database-Project.git

# stage ONLY Uzair's files + shared scaffolding
git add db/procedures.sql db/migrations.sql \
        app.py routes/__init__.py routes/assignments.py routes/submissions.py \
        routes/quizzes.py routes/calendar.py routes/notifications.py \
        routes/profile.py routes/search.py \
        templates/base.html templates/dashboard.html \
        templates/_partials/ templates/assignments/ templates/quizzes/ \
        templates/submissions/ templates/calendar/ templates/notifications/ \
        templates/profile/ templates/search/ \
        requirements.txt .gitignore .env.example README.md docs/ static/ frontend/

git commit -m "Add stored functions, migrations, Flask app shell, dashboard, assignments, quizzes, UI"
git push -u origin main
```

### 1c. Add the teammates as collaborators
1. On GitHub: repo → **Settings** → **Collaborators** → **Add people**
2. Add **`taha1903`** and **`abdullah-kam`**.
3. They accept the email invite (or visit the repo link).

---

## STEP 2 — Taha: push views, triggers, courses, announcements, comments

Taha needs the actual file contents. Easiest: **Uzair sends Taha a zip of the
project folder** (without `venv/`, `.env`, `uploads/`). Then:

```bash
# 1. Clone the repo Uzair created
git clone https://github.com/uzair3720/database-Project.git
cd database-Project

# 2. Copy Taha's files in from the unzipped project Uzair shared
#    (adjust ../lmp_project to wherever Taha unzipped it)
cp ../lmp_project/db/views.sql             db/
cp ../lmp_project/db/triggers.sql          db/
cp ../lmp_project/routes/courses.py        routes/
cp ../lmp_project/routes/announcements.py  routes/
cp ../lmp_project/routes/comments.py       routes/
cp -r ../lmp_project/templates/courses        templates/
cp -r ../lmp_project/templates/announcements  templates/

# 3. Stage ONLY Taha's files, commit as Taha, push
git add db/views.sql db/triggers.sql \
        routes/courses.py routes/announcements.py routes/comments.py \
        templates/courses/ templates/announcements/
git commit -m "Add database views and triggers, courses, enrollments, announcements and comments"
git pull --rebase    # in case the branch moved
git push
```

---

## STEP 3 — Abdullah: push schema, indexes, connection layer, auth

Same idea — Abdullah clones, copies his files in, commits, pushes:

```bash
git clone https://github.com/uzair3720/database-Project.git
cd database-Project

cp ../lmp_project/schema.sql       .
cp ../lmp_project/db.py            .
cp ../lmp_project/config.py        .
cp ../lmp_project/auth_helpers.py  .
cp ../lmp_project/db/indexes.sql   db/
cp ../lmp_project/routes/auth.py   routes/
cp -r ../lmp_project/templates/auth templates/

git add schema.sql db.py config.py auth_helpers.py db/indexes.sql \
        routes/auth.py templates/auth/
git commit -m "Add PostgreSQL schema and constraints, indexes, connection layer and authentication"
git pull --rebase
git push
```

> If a push is rejected with `Updates were rejected`, run
> `git pull --rebase` then `git push` again.

---

## STEP 4 — Verify (do this before the demo)

1. Repo → **Insights** → **Contributors**: all three names should appear.
2. Repo file list should show the **complete** project.
3. **Confirm `.env` is NOT in the repo** (it's git-ignored — your DB
   password must never be uploaded). Only `.env.example` should be there.

## STEP 5 — Each person clones fresh and runs it once

So everyone can demo independently:
```bash
git clone https://github.com/uzair3720/database-Project.git
cd database-Project
cp .env.example .env        # then edit DB credentials
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# create DB + run all .sql files (see README STEP 2 & 3), then:
flask --app app.py run --debug --port 5000
```

---

### Notes
- Order matters only so pushes don't conflict: **Uzair → Taha → Abdullah**.
- If anyone gets `Updates were rejected`, run `git pull --rebase` then `git push`.
- Want more commits per person? Each can make a second small commit (e.g.
  improving comments in their own files) — every commit is real and counts.
