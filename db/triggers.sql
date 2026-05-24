-- =====================================================================
-- Triggers
-- We rely on triggers for three things:
--   (1) keep updated_at honest on UPDATE,
--   (2) write an audit row every time a grade is created or changed,
--   (3) refuse a submission row from a student who is not enrolled.
-- Every trigger has its function defined first, then the trigger that
-- binds the function to a table.
-- =====================================================================


-- ---------------------------------------------------------------------
-- (1) Generic updated_at function
-- Re-used by five tables. Sets NEW.updated_at to NOW() before UPDATE.
-- This way the application never has to remember to bump the column.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at        ON users;
DROP TRIGGER IF EXISTS trg_courses_updated_at      ON courses;
DROP TRIGGER IF EXISTS trg_assignments_updated_at  ON assignments;
DROP TRIGGER IF EXISTS trg_submissions_updated_at  ON submissions;
DROP TRIGGER IF EXISTS trg_quizzes_updated_at      ON quizzes;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_courses_updated_at
    BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_assignments_updated_at
    BEFORE UPDATE ON assignments
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER trg_quizzes_updated_at
    BEFORE UPDATE ON quizzes
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ---------------------------------------------------------------------
-- (2) Grade audit log
-- Fires AFTER INSERT OR UPDATE on submissions whenever the grade column
-- becomes non-null or changes value. We read the application's user id
-- out of a session GUC called "app.current_user_id" that the Flask code
-- sets with SET LOCAL inside the grading transaction. If the GUC is
-- absent (e.g. a manual psql update), changed_by is just NULL.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_log_grade_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_changed_by INT;
    v_guc        TEXT;
BEGIN
    -- current_setting(name, true) returns NULL instead of erroring if
    -- the setting is undefined. Empty string also means "not set".
    v_guc := current_setting('app.current_user_id', true);
    IF v_guc IS NULL OR v_guc = '' THEN
        v_changed_by := NULL;
    ELSE
        v_changed_by := v_guc::INT;
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF NEW.grade IS NOT NULL THEN
            INSERT INTO grade_audit_log (submission_id, old_grade, new_grade, changed_by)
            VALUES (NEW.submission_id, NULL, NEW.grade, v_changed_by);
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- IS DISTINCT FROM treats two NULLs as equal -- so we don't log
        -- a row when nothing actually changed.
        IF NEW.grade IS DISTINCT FROM OLD.grade THEN
            INSERT INTO grade_audit_log (submission_id, old_grade, new_grade, changed_by)
            VALUES (NEW.submission_id, OLD.grade, NEW.grade, v_changed_by);
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_grade_changes ON submissions;
CREATE TRIGGER trg_log_grade_changes
    AFTER INSERT OR UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION fn_log_grade_changes();


-- ---------------------------------------------------------------------
-- (3) Enforce enrolment at submission time
-- BEFORE INSERT on submissions. Walks back through the assignment to
-- find its course, then checks the student has a matching row in
-- enrollments. If not, raise an exception so the INSERT fails.
-- The application also checks this, but a DB-level guard means even a
-- direct psql INSERT cannot break the rule.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_enforce_enrollment_for_submission()
RETURNS TRIGGER AS $$
DECLARE
    v_course_id INT;
    v_count     INT;
BEGIN
    SELECT course_id INTO v_course_id
    FROM assignments
    WHERE assignment_id = NEW.assignment_id;

    IF v_course_id IS NULL THEN
        RAISE EXCEPTION 'Assignment % does not exist', NEW.assignment_id;
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM enrollments
    WHERE student_id = NEW.student_id
      AND course_id  = v_course_id;

    IF v_count = 0 THEN
        RAISE EXCEPTION
            'Student % is not enrolled in course % -- cannot submit',
            NEW.student_id, v_course_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enforce_enrollment_for_submission ON submissions;
CREATE TRIGGER trg_enforce_enrollment_for_submission
    BEFORE INSERT ON submissions
    FOR EACH ROW EXECUTE FUNCTION fn_enforce_enrollment_for_submission();
