"""
Name: Sofia Kobayashi, based on work from Amy Fung & Cynthia Wang
Date: 06/07/2023
Description: All functions for the Task Generation Component.
"""
import random
import json
import time as _time
import helper_functions
import task_parameters
import verification_task_manager
from datetime import datetime, timedelta, time, date
import pandas as pd 

import json
import os
import time as _time
helper_functions.load_env()
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")

### ### TASK PARAMETERS (all in task_parameters.py) ### ###
DB_NAME = helper_functions.get_env("DB_NAME", "")

### ### HELPER FUNCTIONS ### ###
def random_datetime(n):
    """
    * Helper function for create_task() *
    Takes number of random dates to generate.
    Generates a random datetime with the limit specified below.
    Returns a random datetime.
    """    
    # Get start times
    now = datetime.now()

    if task_parameters.START_TIME_MODE == "next_minutes":
        end = now + timedelta(minutes=task_parameters.NEXT_MINUTES_START_WINDOW)
        dates = pd.date_range(now, end, freq="1min").to_series()
        date_sample = [str(date) for date in dates.sample(n, replace=True).to_list()]
        return date_sample

    # If today's a weekend or after hours on friday -> start = next monday at start_hours
    weekday = now.strftime("%A").lower()
    if weekday in {'saturday', 'sunday'} or (weekday == 'friday' and now.time() > task_parameters.END_HOURS):
        date = datetime.now() + timedelta(days=-now.date().weekday(), weeks=1) # next monday
        start = datetime.combine(date, task_parameters.START_HOURS)   
    # If weekday, but before 10am -> start = today at start_hours
    elif now.time() < task_parameters.START_HOURS:
        start = datetime.combine(now.date(), task_parameters.START_HOURS)
    # If weekday, during hours -> start time = now
    elif task_parameters.START_HOURS < now.time() < task_parameters.END_HOURS:
        start = now
    # If weekday (except friday), after hours -> start time = next day at start_hours
    else:
        start = datetime.combine((now + timedelta(hours=24)), task_parameters.START_HOURS)
    
    # Get end time
    next_hour = time((now.hour+2),00)
    end = datetime.combine(start.date(), next_hour) + timedelta(hours=1)

    # Generate & choose n random dates
    dates = pd.date_range(start, end, freq='1min').to_series()
    date_sample = [str(date) for date in dates.sample(n, replace=True).to_list()]
    #print(date_sample)
    return date_sample


def create_task(locations, all_descriptions):
    log_step(logger, "create_task enter")
    """
     * Helper function for generate_tasks() *
    Takes a list of task locations.
    Generates a task object - random: location, window, compensation, expired set 
        to FALSE, all other features to be determined & added later.
    Returns a task object.
    """
    # Generate a random location, time window (seconds), and compensation (cents)
    location = random.choice(locations)
    compensation = round(random.uniform(task_parameters.TASK_COMP[0], task_parameters.TASK_COMP[1]), 2)
    window = random.randint(task_parameters.TASK_TIMEWINDOW[0], task_parameters.TASK_TIMEWINDOW[1])  # in minutes
    
    print(window)
    return {'location': location,
            'time_window': window,
            'compensation': compensation,
            'expired': False,
            'description': f'At {location} in the Science Center, {random.choice(all_descriptions)}',
            'task_type': 'data_collection',
            'assignment_id': None}


def insert_tasks(db, tasks_list, start_times):
    log_step(logger, "insert_tasks enter", tasks=len(tasks_list) if tasks_list else 0)
    """
     * Helper function for generate_tasks() *
    Takes a list of tasks and database (obj).
    Inserts the tasks into the database given. 
    Returns nothing.
    """
    # Connect to database & a cursor object
    cursor = db.cursor()
    cursor.execute(f"SHOW COLUMNS FROM tasks FROM {DB_NAME}")
    columns = cursor.fetchall()
    #print("insert", start_times)
    for i, task in enumerate(tasks_list):
        #print("start time type:", type(start_times[i]))
        # Create & execute query
        assignment_id = "NULL" if task.get("assignment_id") is None else task["assignment_id"]
        query = (
            "INSERT INTO tasks (`location`, time_window, compensation, expired, `description`, "
            "start_time, task_type, assignment_id) "
            f"VALUES ('{task['location']}', {task['time_window']}, {task['compensation']}, "
            f"{task['expired']}, '{task['description']}', '{start_times[i]}', "
            f"'{task.get('task_type', 'data_collection')}', {assignment_id})"
        )
        
        cursor.execute(query)

        # Commit the changes to the database
        db.commit()
    log_step(logger, "insert_tasks exit")




### ### OVERALL TASK GENERATION ### ###
def generate_tasks(num_tasks, db_name):
    log_step(logger, "generate_tasks enter", num_tasks=num_tasks, db_name=db_name)
    """
    Takes number of tasks to be generated.
    Creates those tasks & inserts them into the Tasks database.
    Returns nothing.
    """
    # Open database connection
    db = helper_functions.connectDB(db_name)
    # Get list of possible locations
    with open(task_parameters.TASK_LOCATION_FILE, 'r') as infile:
        locations_list = json.load(infile)

    # Get list of possible task descriptions
    with open(task_parameters.TASK_DESCRIPTION_FILE, 'r') as infile:
        all_descriptions = json.load(infile)

    # Use round so 1 * 0.5 = 1 (not 0); ensure at least 1 verification slot when generating tasks
    verification_count = max(1, int(round(num_tasks * task_parameters.VERIFICATION_RATIO)))
    data_collection_count = max(num_tasks - verification_count, 0)

    # Generate data-collection tasks
    all_tasks = [create_task(locations_list, all_descriptions) for _ in range(data_collection_count)]
    start_times = random_datetime(data_collection_count) if data_collection_count else []
    if all_tasks:
        insert_tasks(db, all_tasks, start_times)

    # Generate verification tasks (fallback to data collection if none qualify)
    if verification_count > 0:
        generated = generate_verification_tasks(verification_count, db)
        if generated < verification_count:
            fallback_count = verification_count - generated
            fallback_tasks = [create_task(locations_list, all_descriptions) for _ in range(fallback_count)]
            fallback_times = random_datetime(fallback_count)
            insert_tasks(db, fallback_tasks, fallback_times)

    # Close database connection
    db.close()
    log_step(logger, "generate_tasks exit")


def generate_verification_tasks(num_tasks, db):
    log_step(logger, "generate_verification_tasks enter", num_tasks=num_tasks)
    """
    Generate verification tasks and insert into Tasks.
    Returns the number of verification tasks created.
    """
    assignment_ids = verification_task_manager.select_submissions_for_verification(num_tasks)
    if not assignment_ids:
        log_step(logger, "generate_verification_tasks exit none")
        return 0
    verification_task_manager.create_verification_tasks(assignment_ids)
    log_step(logger, "generate_verification_tasks exit", created=len(assignment_ids))
    return len(assignment_ids)


if __name__ == '__main__':
    generate_tasks(3, DB_NAME)
    
