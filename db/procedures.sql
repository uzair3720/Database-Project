-- =====================================================================
-- Functions
-- Two server-side functions the application calls. We keep them in
-- the database so the logic stays close to the data -- and so the viva
-- can see real PL/pgSQL.
-- =====================================================================


-- fn_enroll_student ---------------------------------------------------
-- Inputs: a student's user_id and a course's join_code (the 6-char
-- string the instructor shared).
-- Returns: the new enrollment_id.
-- Validates the student exists, has role='student', the join code
-- maps to a real course, and the pair is not already enrolled. Every
-- failure mode raises a clear EXCEPTION the Flask layer can show to
-- the user.
CREATE OR REPLACE FUNCTION fn_enroll_student(
    p_student_id INT,
    p_join_code  VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_role           VARCHAR(20);
    v_course_id      INT;
    v_existing       INT;
    v_enrollment_id  INT;
BEGIN
    -- 1. Does the user exist and is the role correct?
    SELECT role INTO v_role FROM users WHERE user_id = p_student_id;
    IF v_role IS NULL THEN
        RAISE EXCEPTION 'User % does not exist', p_student_id;
    END IF;
    IF v_role <> 'student' THEN
        RAISE EXCEPTION 'Only students can enrol in a course (user % is %)',
            p_student_id, v_role;
    END IF;

    -- 2. Does the join code map to a real course?
    SELECT course_id INTO v_course_id
    FROM courses WHERE join_code = p_join_code;
    IF v_course_id IS NULL THEN
        RAISE EXCEPTION 'Invalid join code: %', p_join_code;
    END IF;

    -- 3. Already enrolled?
    SELECT enrollment_id INTO v_existing
    FROM enrollments
    WHERE student_id = p_student_id AND course_id = v_course_id;
    IF v_existing IS NOT NULL THEN
        RAISE EXCEPTION 'You are already enrolled in this course';
    END IF;

    -- 4. Insert and return the new id.
    INSERT INTO enrollments (student_id, course_id)
    VALUES (p_student_id, v_course_id)
    RETURNING enrollment_id INTO v_enrollment_id;

    RETURN v_enrollment_id;
END;
$$ LANGUAGE plpgsql;


-- fn_course_average_grade --------------------------------------------
-- Returns the average grade across every graded submission in one
-- course. NULL grades (ungraded yet) are excluded by AVG by default.
-- If there are no graded submissions at all, AVG returns NULL and we
-- return NULL too -- the caller decides how to display that.
CREATE OR REPLACE FUNCTION fn_course_average_grade(p_course_id INT)
RETURNS NUMERIC AS $$
DECLARE
    v_avg NUMERIC;
BEGIN
    SELECT AVG(s.grade)::NUMERIC(6,2) INTO v_avg
    FROM submissions s
    JOIN assignments a ON a.assignment_id = s.assignment_id
    WHERE a.course_id = p_course_id
      AND s.grade IS NOT NULL;
    RETURN v_avg;
END;
$$ LANGUAGE plpgsql;
