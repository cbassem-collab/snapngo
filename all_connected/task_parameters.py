"""
Global configurable parameters for Snap.
"""
import random
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
START_HOURS = time(9, 0)
END_HOURS = time(21, 0)

# Seconds between task generation runs (larger = fewer batches per day)
TASK_CYCLE = 120 * 60

# Seconds between matching runs (should be > task gen so tasks exist before match)
MATCHING_CYCLE = TASK_CYCLE + 2

# Seconds between messenger sending assigned tasks to users (keep aligned with TASK_CYCLE)
MESSENGER_BOT_CYCLE = TASK_CYCLE + 2

# Connector: pending Gemini verification (independent of TASK_CYCLE so API runs often enough)
GEMINI_VERIFICATION_CYCLE = 60
# Max data-collection submissions to run Gemini on per connector tick
GEMINI_VERIFICATION_BATCH = 10

# -----------------------------------------------------------------------------
# Task content randomization
# -----------------------------------------------------------------------------
# Minutes — random time window for each data-collection task (min, max).
# Wider windows = users have longer to complete before the task expires.
TASK_TIMEWINDOW = (60, 120)

# Data-collection compensation (dollars in DB / shown to users).
# Mixture model: most tasks pay "small"; a minority pay "large". Long-run mean ≈ TASK_COMP_MEAN_TARGET.
TASK_COMP_MEAN_TARGET = 0.80
TASK_COMP_SMALL_RANGE = (0.5, 1.0)  # typical tasks (wide-ish but modest)
TASK_COMP_LARGE_RANGE = (1.50, 3.00)  # occasional bonus tasks
# P(large); tuned so E[pay] ≈ TASK_COMP_MEAN_TARGET (≈0.95×0.525 + 0.05×3.25 ≈ 0.80)
TASK_COMP_LARGE_FRACTION = 0.05


def sample_data_collection_compensation() -> float:
    """
    Random compensation for one data-collection task (dollars).
    Mostly draws from TASK_COMP_SMALL_RANGE; with probability TASK_COMP_LARGE_FRACTION
    draws from TASK_COMP_LARGE_RANGE (occasional high-value tasks).
    """
    if random.random() < TASK_COMP_LARGE_FRACTION:
        lo, hi = TASK_COMP_LARGE_RANGE
    else:
        lo, hi = TASK_COMP_SMALL_RANGE
    return round(random.uniform(lo, hi), 2)

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
# "business_hours" — weekday + START_HOURS/END_HOURS (use in production)
# "next_minutes" — start within the next few minutes (testing only; ignores business hours)
START_TIME_MODE = "business_hours"
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

# Time window (minutes) for verification tasks — need not match data-collection max
VERIFICATION_TIME_WINDOW_MINUTES = 120

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
