-- =====================================================================
-- Incremental migrations layered on top of schema.sql.
-- Safe to re-run: every statement is IF NOT EXISTS / OR REPLACE / guarded.
--
-- Apply once after the original schema:
--   psql -U lmp_user -d lmp_db -h localhost -f db/migrations.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. courses.course_code (e.g. "CS2001") -- shown on course-card badge.
-- ---------------------------------------------------------------------
ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS course_code VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_courses_course_code ON courses(course_code);


-- ---------------------------------------------------------------------
-- 2. notifications
-- A minimal feed: one row per (recipient_user, event). Populated by
-- triggers below. Read state is per-row.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id  SERIAL PRIMARY KEY,
    user_id          INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    kind             VARCHAR(30) NOT NULL,     -- 'assignment' | 'grade' | 'announcement'
    message          TEXT NOT NULL,
    link             VARCHAR(500),             -- relative URL the bell item points at
    is_read          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id   ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read   ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created   ON notifications(created_at DESC);


-- ---------------------------------------------------------------------
-- 3. password_reset_tokens
-- One-time tokens that expire. The /auth/forgot route inserts one and
-- prints (or emails) the reset URL; /auth/reset/<token> consumes it.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token        VARCHAR(64) PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    expires_at   TIMESTAMP NOT NULL,
    used_at      TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id);


-- ---------------------------------------------------------------------
-- 4. Notification triggers
-- ---------------------------------------------------------------------

-- 4a. New assignment -> notify every enrolled student.
CREATE OR REPLACE FUNCTION fn_notify_on_new_assignment()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notifications (user_id, kind, message, link)
    SELECT
        e.student_id,
        'assignment',
        'New assignment: ' || NEW.title,
        '/assignments/' || NEW.assignment_id
    FROM enrollments e
    WHERE e.course_id = NEW.course_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_on_new_assignment ON assignments;
CREATE TRIGGER trg_notify_on_new_assignment
    AFTER INSERT ON assignments
    FOR EACH ROW EXECUTE FUNCTION fn_notify_on_new_assignment();


-- 4b. New announcement -> notify every enrolled student.
CREATE OR REPLACE FUNCTION fn_notify_on_new_announcement()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO notifications (user_id, kind, message, link)
    SELECT
        e.student_id,
        'announcement',
        'New post: ' || NEW.title,
        '/announcements/' || NEW.announcement_id
    FROM enrollments e
    WHERE e.course_id = NEW.course_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_on_new_announcement ON announcements;
CREATE TRIGGER trg_notify_on_new_announcement
    AFTER INSERT ON announcements
    FOR EACH ROW EXECUTE FUNCTION fn_notify_on_new_announcement();


-- 4c. Grade set / changed -> notify the student whose submission it is.
-- We fire on the same conditions as the audit trigger (grade IS DISTINCT
-- FROM old grade) so re-saves with the same number don't spam.
CREATE OR REPLACE FUNCTION fn_notify_on_grade()
RETURNS TRIGGER AS $$
DECLARE
    v_msg TEXT;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.grade IS NOT DISTINCT FROM OLD.grade THEN
        RETURN NEW;
    END IF;
    IF NEW.grade IS NULL THEN
        RETURN NEW;
    END IF;

    v_msg := 'Your submission was graded: ' || NEW.grade::TEXT;
    INSERT INTO notifications (user_id, kind, message, link)
    VALUES (
        NEW.student_id,
        'grade',
        v_msg,
        '/assignments/' || NEW.assignment_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notify_on_grade ON submissions;
CREATE TRIGGER trg_notify_on_grade
    AFTER INSERT OR UPDATE OF grade ON submissions
    FOR EACH ROW EXECUTE FUNCTION fn_notify_on_grade();
