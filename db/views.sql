-- =====================================================================
-- Views
-- We expose three views the application can read instead of writing the
-- same long join over and over. Each view's comment explains the report
-- it answers.
-- =====================================================================

-- student_grades_view ------------------------------------------------
-- One row per graded submission. Used on the student's "my grades"
-- screen. We pre-join users, courses, assignments and submissions so
-- the template just iterates this view.
CREATE OR REPLACE VIEW student_grades_view AS
SELECT
    s.student_id          AS student_id,
    u.name                AS student_name,
    c.course_id           AS course_id,
    c.course_name         AS course_name,
    a.assignment_id       AS assignment_id,
    a.title               AS assignment_title,
    s.grade               AS grade,
    a.max_marks           AS max_marks,
    s.feedback            AS feedback,
    s.submitted_at        AS submitted_at,
    s.graded_at           AS graded_at
FROM submissions s
JOIN users       u ON u.user_id      = s.student_id
JOIN assignments a ON a.assignment_id = s.assignment_id
JOIN courses     c ON c.course_id    = a.course_id;

-- course_enrollment_counts -------------------------------------------
-- For the instructor's course list -- shows how many students are in
-- each course. LEFT JOIN so empty courses still appear with a 0.
CREATE OR REPLACE VIEW course_enrollment_counts AS
SELECT
    c.course_id      AS course_id,
    c.course_name    AS course_name,
    u.name           AS instructor_name,
    COUNT(e.enrollment_id) AS enrolled_count
FROM courses c
JOIN users u  ON u.user_id = c.instructor_id
LEFT JOIN enrollments e ON e.course_id = c.course_id
GROUP BY c.course_id, c.course_name, u.name;

-- instructor_dashboard -----------------------------------------------
-- Top-of-dashboard summary numbers for an instructor: how many courses
-- they run, how many distinct students they teach, and how many
-- assignments they have created.
CREATE OR REPLACE VIEW instructor_dashboard AS
SELECT
    u.user_id  AS instructor_id,
    u.name     AS instructor_name,
    COUNT(DISTINCT c.course_id)              AS total_courses,
    COUNT(DISTINCT e.student_id)             AS total_students,
    COUNT(DISTINCT a.assignment_id)          AS total_assignments
FROM users u
LEFT JOIN courses     c ON c.instructor_id = u.user_id
LEFT JOIN enrollments e ON e.course_id     = c.course_id
LEFT JOIN assignments a ON a.course_id     = c.course_id
WHERE u.role = 'instructor'
GROUP BY u.user_id, u.name;
