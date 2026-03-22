from typing import Optional

import helper_functions
import task_parameters
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")


def get_verification_context(assignment_id: int):
    log_step(logger, "get_verification_context enter", assignment_id=assignment_id)
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT a.img, a.gemini_decision, a.gemini_explanation, t.description
               FROM assignments a
               INNER JOIN tasks t ON a.task_id = t.id
               WHERE a.id = %s""",
            (assignment_id,),
        )
        row = cur.fetchone()
        if not row:
            log_step(logger, "get_verification_context exit no_row", assignment_id=assignment_id)
            return None
        image_path, gemini_decision, gemini_explanation, task_description = row
        log_step(logger, "get_verification_context exit ok", assignment_id=assignment_id)
        return {
            "image_path": image_path,
            "gemini_decision": gemini_decision,
            "gemini_explanation": gemini_explanation,
            "task_description": task_description,
        }
    finally:
        conn.close()


def build_verification_blocks(assignment_id: int, feedback_task_id: int, image_url: Optional[str] = None):
    log_step(logger, "build_verification_blocks enter", assignment_id=assignment_id, feedback_task_id=feedback_task_id)
    context = get_verification_context(assignment_id)
    if not context:
        log_step(logger, "build_verification_blocks exit empty")
        return []

    decision_text = "MATCH" if context["gemini_decision"] else "NO MATCH"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Verification Task #{feedback_task_id}*\n*Original Task:* {context['task_description']}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Gemini Decision:* {decision_text}\n*Reason:* {context['gemini_explanation']}",
            },
        },
    ]

    if image_url:
        blocks.append(
            {
                "type": "image",
                "image_url": image_url,
                "alt_text": "Submitted image",
            }
        )
    else:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "_See the image above._"}],
            }
        )

    # Note: Input blocks are NOT allowed in chat messages (invalid_blocks). Use modal for comment if needed.
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Agree"},
                    "style": "primary",
                    "action_id": "verify_agree",
                    "value": f"{assignment_id}:{feedback_task_id}:agree",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Disagree"},
                    "style": "danger",
                    "action_id": "verify_disagree",
                    "value": f"{assignment_id}:{feedback_task_id}:disagree",
                },
            ],
        }
    )
    log_step(logger, "build_verification_blocks exit", blocks=len(blocks))
    return blocks


def update_verified_count(assignment_id: int):
    log_step(logger, "update_verified_count enter", assignment_id=assignment_id)
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE assignments SET verified_count = verified_count + 1 WHERE id = %s",
            (assignment_id,),
        )
        conn.commit()
        log_step(logger, "update_verified_count exit", assignment_id=assignment_id)
    finally:
        conn.close()


def process_feedback_response(user_id: str, feedback_task_id: int, agrees: bool, comment: Optional[str]):
    log_step(logger, "process_feedback_response enter", user_id=user_id, feedback_task_id=feedback_task_id, agrees=agrees)
    db_name = helper_functions.get_env("DB_NAME", "")
    conn = helper_functions.connectDB(db_name)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT tasks.assignment_id, assignments.gemini_decision
               FROM tasks
               INNER JOIN assignments ON tasks.assignment_id = assignments.id
               WHERE tasks.id = %s""",
            (feedback_task_id,),
        )
        row = cur.fetchone()
        if not row:
            log_step(logger, "process_feedback_response exit no_row")
            return
        assignment_id, gemini_decision = row
        cur.execute(
            """INSERT INTO user_feedback
               (assignment_id, user_id, feedback_task_id, gemini_decision, user_agrees, user_comment)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (assignment_id, user_id, feedback_task_id, gemini_decision, int(agrees), comment),
        )
        conn.commit()
    finally:
        conn.close()
    update_verified_count(assignment_id)
    import messenger
    messenger.add_account_compensation(user_id, task_parameters.VERIFICATION_COMPENSATION)
    log_step(
        logger,
        "process_feedback_response exit ok",
        assignment_id=assignment_id,
        compensation=task_parameters.VERIFICATION_COMPENSATION,
    )
