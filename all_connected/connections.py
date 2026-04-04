"""
Name: Sofia Kobayashi
Date: 06/07/2023
Description: File that connects all 5 components & calls functions for them to 
    run the backend of Snap N Go.
"""
from run_logging import get_logger, log_step, get_root_logger, setup_error_logging

logger = get_logger(__name__)
logger.info("module loaded")
get_root_logger()
setup_error_logging()

import os
import helper_functions
helper_functions.load_env()
log_step(logger, "connections env loaded")

import matching_assignments
import task
import messenger
import bot
import task_parameters
import verification_integration

from datetime import datetime as dt, date
import time
import schedule
from threading import Timer

### ### Control Center ### ###
DB_NAME = helper_functions.get_env("DB_NAME", "")
# All cycle/schedule knobs live in task_parameters — use task_parameters.* below



class RepeatTimer(Timer):
    def __init__(self, func, seconds=10, minutes=0, hours=0):
        super().__init__(seconds + minutes*60 + hours*3600, func)

    def run(self):
        while not self.finished.wait(self.interval):
            if helper_functions.is_weekday_and_business_hours():
                self.function(*self.args, **self.kwargs)


def deliver_pending_task_notifications():
    """DM all users who have new not-assigned tasks; then mark those assignments pending."""
    log_step(logger, "deliver_pending_task_notifications enter")
    assign_dict = messenger.get_assignments(DB_NAME)
    if not assign_dict:
        log_step(logger, "deliver_pending_task_notifications exit nothing to send")
        return
    bot.send_tasks(assign_dict)
    messenger.update_assign_status("pending", 0, 0)
    print("- delivered task notifications", dt.now())


### ### Task Generation call ### ###
# Generate & insert task(s)
def task_call():
    """Takes & returns nothing. Container for task call timer."""
    log_step(logger, "task_call enter", num_tasks=task_parameters.NUM_TASKS_PER_CYCLE)
    task.generate_tasks(task_parameters.NUM_TASKS_PER_CYCLE, DB_NAME)
    matching_assignments.match_users_and_tasks(task_parameters.MATCHING_ALGO, DB_NAME)
    deliver_pending_task_notifications()
    print('- tasks generated, matched, and delivered', dt.now())


### ### Matching Algorithm & Assignments call ### ###
# Update expired tasks, matches unexpired & unassigned tasks to users, create those Assignments
def match_call():
    """Takes & returns nothing. Container for match call timer."""
    log_step(logger, "match_call enter")
    matching_assignments.match_users_and_tasks(task_parameters.MATCHING_ALGO, DB_NAME)
    deliver_pending_task_notifications()
    print("- tasks matched and delivered", dt.now())


### ### MESSENGER call ### ###
# Backup pass: deliver anything still not sent (edge cases between timers)
def messenger_bot_call():
    """Takes & returns nothing. Container for messenger timer."""
    log_step(logger, "messenger_bot_call enter")
    deliver_pending_task_notifications()
    print('- messenger send pass', dt.now())


### ### Gemini verification ### ###
def gemini_verification_call():
    """Process submissions that have images but no Gemini result yet."""
    log_step(logger, "gemini_verification_call enter")
    n = verification_integration.process_pending_gemini_verifications()
    if n:
        print("- gemini verification processed", n, dt.now())


def start_all_timers():
    log_step(logger, "start_all_timers enter")
    task_timer = RepeatTimer(task_call, task_parameters.TASK_CYCLE)
    match_timer = RepeatTimer(
        match_call,
        seconds=task_parameters.MATCHING_CYCLE,
        minutes=0,
        hours=0,
    )
    messenger_timer = RepeatTimer(
        messenger_bot_call,
        seconds=task_parameters.MESSENGER_BOT_CYCLE,
        minutes=0,
        hours=0,
    )
    gemini_timer = RepeatTimer(
        gemini_verification_call,
        seconds=task_parameters.GEMINI_VERIFICATION_CYCLE,
        minutes=0,
        hours=0,
    )
    task_timer.start()
    match_timer.start()
    messenger_timer.start()
    gemini_timer.start()
    print("STARTED ALL TIMERS", dt.now())
    if helper_functions.is_weekday_and_business_hours():
        verification_integration.process_pending_gemini_verifications()
    return task_timer, match_timer, messenger_timer, gemini_timer


def cancel_all_timers(task_timer, match_timer, messenger_timer, gemini_timer):
    print("CANCEL ALL TIMERS", dt.now())
    task_timer.cancel()
    match_timer.cancel()
    messenger_timer.cancel()
    gemini_timer.cancel()

def daily_cycle():
    log_step(logger, "daily_cycle enter")
    all_users = messenger.get_all_users_list()
    for user_id in all_users:
        if user_id not in task_parameters.admin_list:
            messenger.update_account_status(user_id, "active")
    task_timer, match_timer, messenger_timer, gemini_timer = start_all_timers()
    # Run time
    end_time = dt.combine(date.today(), task_parameters.END_HOURS)
    duration = (end_time - dt.now()).total_seconds()
    print(duration)
    time.sleep(duration + 2) # run till end_time
    # Check assignments and end daily summary
    bot.check_all_assignments()
    for user_id in all_users:
        if user_id not in ['USLACKBOT']:
            messenger.update_reliability(user_id)
    # End all cycles
    cancel_all_timers(task_timer, match_timer, messenger_timer, gemini_timer)

def short_cycle():
    log_step(logger, "short_cycle enter")
    all_users = messenger.get_all_users_list()
    for user_id in all_users:
        if user_id not in task_parameters.admin_list:
            messenger.update_account_status(user_id, "active")
    task_timer, match_timer, messenger_timer, gemini_timer = start_all_timers()
    # Run time
    end_time = dt.combine(date.today(), task_parameters.END_HOURS)
    duration = (end_time - dt.now()).total_seconds()
    print(duration)
    time.sleep(duration + 2) # run till end_time
    # Check assignments and end daily summary
    bot.check_all_assignments()
    # End all cycles
    cancel_all_timers(task_timer, match_timer, messenger_timer, gemini_timer)

if __name__ == "__main__":
    log_step(logger, "connections main schedule loop starting")
    start_hours_str = task_parameters.START_HOURS.strftime("%H:%M")

    schedule.every().monday.at(start_hours_str).do(short_cycle)
    schedule.every().tuesday.at(start_hours_str).do(short_cycle)
    schedule.every().wednesday.at(start_hours_str).do(short_cycle)
    schedule.every().thursday.at(start_hours_str).do(short_cycle)
    schedule.every().friday.at(start_hours_str).do(short_cycle)
    
    while True:
        schedule.run_pending()
        time.sleep(1)