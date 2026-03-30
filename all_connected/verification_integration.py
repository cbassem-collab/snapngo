from typing import Optional

import helper_functions
import task_parameters
from gemini_verifier import verify_submission, is_verified
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")


def handle_submission_verification(user_id: str, task_id: int, image_path: str) -> None:
    log_step(logger, "handle_submission_verification enter", user_id=user_id, task_id=task_id)
    helper_functions.load_env()
    db_name = helper_functions.get_env("DB_NAME", "")
    if not db_name:
        raise RuntimeError("DB_NAME is not set. Check your .env file.")

    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT assignments.id, tasks.description
               FROM assignments
               INNER JOIN tasks ON assignments.task_id = tasks.id
               WHERE assignments.user_id = %s AND assignments.task_id = %s
               ORDER BY assignments.id DESC
               LIMIT 1""",
            (user_id, task_id),
        )
        row = cur.fetchone()
        if not row:
            print(f"[verification] No assignment found for user {user_id} task {task_id}")
            return
        assignment_id, task_description = row
        if is_verified(assignment_id):
            return

        decision, reason = verify_submission(image_path, task_description)
        cur.execute(
            """UPDATE assignments
               SET gemini_decision = %s,
                   gemini_explanation = %s,
                   verified_at = NOW()
               WHERE id = %s""",
            (int(decision), reason, assignment_id),
        )
        conn.commit()
        log_step(
            logger,
            "gemini verification stored",
            assignment_id=assignment_id,
            task_id=task_id,
            user_id=user_id,
            gemini_match=bool(decision),
            reason_len=len(reason) if reason else 0,
        )
    finally:
        conn.close()


def process_pending_gemini_verifications(limit: Optional[int] = None) -> int:
    """
    Connector-driven entry point: find data-collection submissions with an image but no
    Gemini result yet, and run verification for each (same logic as handle_submission_verification).

    Messenger only writes img to the DB; connections calls this on a timer.
    Returns how many assignments were processed successfully.
    """
    if limit is None:
        limit = task_parameters.GEMINI_VERIFICATION_BATCH

    log_step(logger, "process_pending_gemini_verifications enter", limit=limit)
    db_name = helper_functions.get_env("DB_NAME", "")
    if not db_name:
        return 0

    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT a.user_id, a.task_id, a.img
               FROM assignments a
               INNER JOIN tasks t ON a.task_id = t.id
               WHERE a.img IS NOT NULL
                 AND a.verified_at IS NULL
                 AND t.task_type = 'data_collection'
               ORDER BY a.submission_time ASC
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    done = 0
    for user_id, task_id, img in rows:
        try:
            handle_submission_verification(user_id, task_id, img)
            done += 1
        except Exception as exc:
            log_step(
                logger,
                "process_pending_gemini_verifications row failed",
                user_id=user_id,
                task_id=task_id,
                error=str(exc),
            )
    log_step(logger, "process_pending_gemini_verifications exit", processed=done)
    return done
