import helper_functions
import task_parameters
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")


def select_submissions_for_verification(count: int):
    log_step(logger, "select_submissions_for_verification enter", count=count)
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT a.id
               FROM assignments a
               LEFT JOIN tasks t ON t.assignment_id = a.id AND t.task_type = 'verification'
               WHERE a.img IS NOT NULL
                 AND a.gemini_decision IS NOT NULL
               GROUP BY a.id
               HAVING COUNT(t.id) < %s
               ORDER BY COUNT(t.id) ASC, MAX(a.verified_at) DESC
               LIMIT %s""",
            (task_parameters.MAX_VERIFICATIONS_PER_SUBMISSION, count),
        )
        rows = cur.fetchall()
        ids = [row[0] for row in rows]
        log_step(logger, "select_submissions_for_verification exit", count=len(ids))
        return ids
    finally:
        conn.close()


def create_verification_tasks(assignment_ids):
    log_step(logger, "create_verification_tasks enter", count=len(assignment_ids) if assignment_ids else 0)
    if not assignment_ids:
        return
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        for assignment_id in assignment_ids:
            cur.execute(
                """INSERT INTO tasks
                   (`location`, `description`, task_type, assignment_id, start_time, time_window, compensation, expired)
                   VALUES (NULL, %s, 'verification', %s, NOW(), %s, %s, 0)""",
                (
                    task_parameters.VERIFICATION_TASK_DESCRIPTION,
                    assignment_id,
                    task_parameters.VERIFICATION_TIME_WINDOW_MINUTES,
                    task_parameters.VERIFICATION_COMPENSATION,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_verification_task_for_user(user_id: str, count: int = 1):
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT assignments.task_id
               FROM assignments
               INNER JOIN tasks ON assignments.task_id = tasks.id
               WHERE assignments.user_id = %s
                 AND assignments.status = 'pending'
                 AND tasks.task_type = 'verification'
                 AND tasks.expired = 0
               LIMIT %s""",
            (user_id, count),
        )
        rows = cur.fetchall()
        out = [row[0] for row in rows]
        log_step(logger, "get_verification_task_for_user exit", found=len(out))
        return out
    finally:
        conn.close()
