"""
NEED CONSTANT MONITOR OF THIS FILE FOR CHANGES
Feb 2026 Gemini is on Google Gen AI SDK (google-genai).
See: https://ai.google.dev/gemini-api/docs/migrate
Docs: https://googleapis.github.io/python-genai/
"""
import re
from pathlib import Path

from google import genai
from google.genai import types

import helper_functions
import task_parameters
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")

PROMPT_TEMPLATE = """You are verifying if a photo matches a task description.

TASK DESCRIPTION: {task_description}

Analyze the provided photo and determine if it matches the task description.

You MUST respond in this exact format:
DECISION: [0 or 1]
REASON: [your explanation]

Rules:
- DECISION must be exactly "0" (does not match) or "1" (matches)
- REASON can be any length, be specific about what matches or doesn't match
- Do not add any other text, formatting, or explanations
- Do not repeat the decision in the reason
"""


def _get_client():
    """Client picks up GOOGLE_API_KEY or GEMINI_API_KEY from env."""
    helper_functions.load_env()
    api_key = helper_functions.get_env("GOOGLE_API_KEY") or helper_functions.get_env("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is not set. Check your .env file.")
    return genai.Client(api_key=api_key)


def _image_mime(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suf == ".png":
        return "image/png"
    if suf == ".webp":
        return "image/webp"
    return "image/jpeg"


def parse_gemini_response(raw_response: str):
    match = re.search(r"DECISION:\s*([01])\s*REASON:\s*(.+)\s*\Z", raw_response, re.S)
    if not match:
        raise ValueError(f"Unexpected Gemini response format: {raw_response!r}")
    decision = match.group(1) == "1"
    reason = match.group(2).strip()
    return decision, reason


def verify_submission(image_path: str, task_description: str):
    log_step(logger, "verify_submission enter", image_path=image_path)
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Submission image not found: {image_path}")

    model_name = helper_functions.get_env("GEMINI_MODEL", task_parameters.GEMINI_MODEL_DEFAULT)
    log_step(logger, "gemini model", model_name=model_name)

    prompt = PROMPT_TEMPLATE.format(task_description=task_description)
    mime = _image_mime(image_file)
    with open(image_file, "rb") as f:
        image_bytes = f.read()

    client = _get_client()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
            ],
        )
    except Exception as e:
        log_step(logger, "verify_submission api error", error=str(e))
        raise

    raw_text = (response.text or "").strip()
    if not raw_text and getattr(response, "candidates", None):
        parts = []
        for c in response.candidates:
            if c.content and c.content.parts:
                for p in c.content.parts:
                    if getattr(p, "text", None):
                        parts.append(p.text)
        raw_text = "\n".join(parts).strip()

    if not raw_text:
        raise ValueError("Gemini returned empty response")

    return parse_gemini_response(raw_text)


def is_verified(assignment_id: int) -> bool:
    conn = helper_functions.connectDB(helper_functions.get_env("DB_NAME", ""))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT verified_at FROM assignments WHERE id = %s",
            (assignment_id,),
        )
        row = cur.fetchone()
        return bool(row and row[0])
    finally:
        conn.close()
