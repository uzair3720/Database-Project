-- =====================================================================
-- Indexes
-- Rule we followed: every FK column gets an index. PostgreSQL does NOT
-- index FK columns automatically (unlike the PK side). Without these,
-- a JOIN or a cascading DELETE would do a sequential scan.
--
-- Note: UNIQUE constraints in PG already create an underlying btree
-- index, so users(email) and courses(join_code) technically already
-- have one. We still add the explicit ones the spec asks for; they are
-- harmless duplicates and make intent obvious to anyone reading.
-- =====================================================================

-- Foreign-key columns
CREATE INDEX IF NOT EXISTS idx_courses_instructor_id        ON courses(instructor_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_student_id       ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course_id        ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_assignments_course_id        ON assignments(course_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment_id    ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student_id       ON submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_course_id            ON quizzes(course_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz_id        ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student_id     ON quiz_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_announcements_course_id      ON announcements(course_id);
CREATE INDEX IF NOT EXISTS idx_announcements_instructor_id  ON announcements(instructor_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id             ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_submission_id       ON comments(submission_id);
CREATE INDEX IF NOT EXISTS idx_comments_announcement_id     ON comments(announcement_id);
CREATE INDEX IF NOT EXISTS idx_audit_submission_id          ON grade_audit_log(submission_id);
CREATE INDEX IF NOT EXISTS idx_audit_changed_by             ON grade_audit_log(changed_by);

-- Spec-required extras
CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role       ON users(role);
CREATE INDEX IF NOT EXISTS idx_courses_join     ON courses(join_code);
CREATE INDEX IF NOT EXISTS idx_assignments_due  ON assignments(due_date);
CREATE INDEX IF NOT EXISTS idx_submissions_at   ON submissions(submitted_at);
