-- =====================================================================
-- LMP schema (PostgreSQL 16)
-- All tables in dependency order so a clean run from top to bottom works.
-- We use SERIAL for primary keys, and explicit FK ON DELETE CASCADE so
-- cleaning up a course or user does not leave orphan rows.
-- =====================================================================

-- We drop in reverse dependency order so re-running the file works.
DROP TABLE IF EXISTS grade_audit_log CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS announcements CASCADE;
DROP TABLE IF EXISTS quiz_attempts CASCADE;
DROP TABLE IF EXISTS quizzes CASCADE;
DROP TABLE IF EXISTS submissions CASCADE;
DROP TABLE IF EXISTS assignments CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. users -------------------------------------------------------------
-- Single users table for both students and instructors. We split by the
-- role column rather than separate tables; it keeps FK relationships
-- simple (one user_id everywhere).
CREATE TABLE users (
    user_id        SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(255) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(20)  NOT NULL CHECK (role IN ('student', 'instructor')),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. courses -----------------------------------------------------------
-- A course is owned by exactly one instructor. join_code is the 6-char
-- string a student types to enrol -- UNIQUE so no two courses collide.
CREATE TABLE courses (
    course_id           SERIAL PRIMARY KEY,
    course_name         VARCHAR(150) NOT NULL,
    course_description  TEXT,
    join_code           VARCHAR(10) UNIQUE NOT NULL,
    instructor_id       INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. enrollments -------------------------------------------------------
-- The bridge table between students and courses. UNIQUE (student, course)
-- prevents the same student joining the same course twice.
CREATE TABLE enrollments (
    enrollment_id  SERIAL PRIMARY KEY,
    student_id     INT NOT NULL REFERENCES users(user_id)   ON DELETE CASCADE,
    course_id      INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    enrolled_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, course_id)
);

-- 4. assignments -------------------------------------------------------
-- attachment_path is the instructor's brief (PDF etc), optional.
-- max_marks lets each assignment have its own scale, even though the DB
-- check on submissions.grade is 0..100.
CREATE TABLE assignments (
    assignment_id    SERIAL PRIMARY KEY,
    course_id        INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title            VARCHAR(200) NOT NULL,
    description      TEXT,
    attachment_path  VARCHAR(500),
    due_date         TIMESTAMP,
    max_marks        INT NOT NULL DEFAULT 100,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. submissions -------------------------------------------------------
-- One row per (assignment, student) -- enforced by the UNIQUE pair. A
-- second upload by the same student updates the existing row (handled
-- in application code as a re-submission).
CREATE TABLE submissions (
    submission_id  SERIAL PRIMARY KEY,
    assignment_id  INT NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
    student_id     INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    file_path      VARCHAR(500) NOT NULL,
    submitted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    grade          INT CHECK (grade IS NULL OR (grade >= 0 AND grade <= 100)),
    feedback       TEXT,
    graded_at      TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assignment_id, student_id)
);

-- 6. quizzes -----------------------------------------------------------
-- Simple model: quiz happens offline (in class or on paper) and the
-- instructor enters each student's score later. So we only store the
-- meta-data here, no questions.
CREATE TABLE quizzes (
    quiz_id      SERIAL PRIMARY KEY,
    course_id    INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    total_marks  INT NOT NULL DEFAULT 100,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. quiz_attempts -----------------------------------------------------
-- One score per (quiz, student). Score is nullable because the row is
-- not created until the instructor enters a value.
CREATE TABLE quiz_attempts (
    attempt_id    SERIAL PRIMARY KEY,
    quiz_id       INT NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    student_id    INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    score         INT CHECK (score IS NULL OR score >= 0),
    attempted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (quiz_id, student_id)
);

-- 8. announcements -----------------------------------------------------
CREATE TABLE announcements (
    announcement_id  SERIAL PRIMARY KEY,
    course_id        INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    instructor_id    INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title            VARCHAR(200) NOT NULL,
    content          TEXT NOT NULL,
    posted_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. comments (polymorphic) -------------------------------------------
-- A comment attaches to EITHER a submission OR an announcement, never
-- both and never neither. The CHECK at the bottom enforces that.
CREATE TABLE comments (
    comment_id       SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    submission_id    INT REFERENCES submissions(submission_id) ON DELETE CASCADE,
    announcement_id  INT REFERENCES announcements(announcement_id) ON DELETE CASCADE,
    content          TEXT NOT NULL,
    posted_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (submission_id IS NOT NULL AND announcement_id IS NULL) OR
        (submission_id IS NULL AND announcement_id IS NOT NULL)
    )
);

-- 10. grade_audit_log -------------------------------------------------
-- Filled by trigger every time a grade is set or changed. Useful for
-- the viva: "Prove no one secretly edited the grade after submission."
CREATE TABLE grade_audit_log (
    log_id         SERIAL PRIMARY KEY,
    submission_id  INT NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    old_grade      INT,
    new_grade      INT,
    changed_by     INT REFERENCES users(user_id),
    changed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
