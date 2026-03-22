"""
Global configurable parameters for Snap.
"""
from datetime import time
from pathlib import Path

import matching_assignments
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")

# -----------------------------------------------------------------------------
# Paths (task generation data files — relative to all_connected/)
# -----------------------------------------------------------------------------
ALL_CONNECTED_DIR = Path(__file__).resolve().parent
DATA_DIR = ALL_CONNECTED_DIR / "data"
TASK_LOCATION_FILE = str(DATA_DIR / "task_locations.json")
TASK_DESCRIPTION_FILE = str(DATA_DIR / "task_descriptions.json")

# -----------------------------------------------------------------------------
# Task cycle & schedule
# -----------------------------------------------------------------------------
# Workday window when timers / daily cycle run
START_HOURS = time(20, 27)  # e.g. 9 am — adjust as needed
END_HOURS = time(23, 59)  # e.g. 5 pm

# Seconds between task generation runs
TASK_CYCLE = 5 * 60

# Seconds between matching runs (should be > task gen so tasks exist before match)
MATCHING_CYCLE = TASK_CYCLE + 2

# Seconds between messenger sending assigned tasks to users
MESSENGER_BOT_CYCLE = 5 * 60 + 2

# -----------------------------------------------------------------------------
# Task content randomization
# -----------------------------------------------------------------------------
# Minutes — allowed time window length for a task
TASK_TIMEWINDOW = (1, 100)

# Points — compensation range per data-collection task (random uniform)
TASK_COMP = (2, 6)

# -----------------------------------------------------------------------------
# How many tasks to generate per cycle (derived after DB user count is known)
# -----------------------------------------------------------------------------
def get_num_users():
    """Total active users in DB — used to size NUM_TASKS_PER_CYCLE."""
    log_step(logger, "get_num_users enter")
    from messenger import get_total_users
    num_users = get_total_users()
    log_step(logger, "get_num_users exit", num_users=num_users)
    print("NUM_USERS: ", num_users)
    return num_users


num_total_users = get_num_users()
NUM_TASKS_PER_CYCLE = num_total_users  # one task per active user per cycle by default

# -----------------------------------------------------------------------------
# Start time mode for new tasks (task.random_datetime)
# -----------------------------------------------------------------------------
# "business_hours" — existing weekday/next-day logic
# "next_minutes" — start within the next few minutes (good for testing)
START_TIME_MODE = "next_minutes"
NEXT_MINUTES_START_WINDOW = 3

# -----------------------------------------------------------------------------
# Verification pipeline (Gemini + crowd verification tasks)
# -----------------------------------------------------------------------------
# Fraction of each cycle that are verification tasks (rest = data_collection)
VERIFICATION_RATIO = 0.4

# Compensation for completing a verification task
VERIFICATION_COMPENSATION = 0.25

# Stop creating new verification tasks for a submission after this many reviews
MAX_VERIFICATIONS_PER_SUBMISSION = 30

# Text shown for verification tasks in DB/Slack
VERIFICATION_TASK_DESCRIPTION = "Review if Gemini correctly verified this submission"

# Time window (minutes) stored on verification task rows — use upper bound of TASK_TIMEWINDOW
VERIFICATION_TIME_WINDOW_MINUTES = TASK_TIMEWINDOW[1]

# TEST ONLY!!!!!!!!!! SET TO FALSE FOR PRODUCTION!!!!!!!!!!!!!!!!!!
ALLOW_SELF_VERIFICATION_FOR_TESTING = False

# -----------------------------------------------------------------------------
# Gemini (verification_integration / gemini_verifier)
# -----------------------------------------------------------------------------
# Default model when GEMINI_MODEL env is not set (google-genai SDK)
GEMINI_MODEL_DEFAULT = "gemini-2.5-flash"

# -----------------------------------------------------------------------------
# Matching
# -----------------------------------------------------------------------------
MATCHING_ALGO = matching_assignments.algorithm_random
# MATCHING_ALGO = matching_assignments.algorithm_weighted

# -----------------------------------------------------------------------------
# Admins — Slack user IDs excluded from receiving tasks like regular users
# -----------------------------------------------------------------------------
admin_list = ["U063BR68ZEZ", "U05B24S3LR9"]
