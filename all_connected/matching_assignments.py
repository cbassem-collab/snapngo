"""
Name: Sofia Kobayashi
Date: 06/07/2023
Description: All functions & algorithms for the Matching Component & Assignment generation.
"""

import random
import pymysql
import helper_functions
from datetime import datetime

import os
helper_functions.load_env()
from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")

### ### SPECIFIC HELPER FUNCTIONS ### ###
def read_table(db, table_name):
    log_step(logger, "read_table enter", table_name=table_name)
    """
    * Helper function for match_users_and_tasks()*
    Takes (str) database name and (str) table name.
    Reads data from that table.
    Returns data as a dict w/ column names (keys) and list of column values (values)
    """
    # Create Dict cursor object & fetch all data in the table
    cursor = db.cursor(pymysql.cursors.DictCursor)
    if table_name == 'users':
        cursor.execute(f"SELECT * FROM {table_name} WHERE `status` = 'active';")
    else:
        cursor.execute(f"SELECT * FROM {table_name};")
    table_data = cursor.fetchall()
    
    # Returns {} if table is empty
    if not table_data: 
        return table_data 

    # Reorder data into: col_name (keys), list of values (values)
    table_dict = {k:[] for k in table_data[0].keys()}
    for row in table_data:
        for col_name in row:
            table_dict[col_name].append(row[col_name])

    return table_dict

def create_task_user_dict(assignment_data):
    """
    * Helper functions for matching algorithms * 
    Takes data from the 'assignments' table (dict).
    Creates a task-user dict, key: task_id, value: set of all user_ids who've 
        previously been assigned to it.
    Returns that dict.
    """
    # get [task_id, user_id] pairs
    task_user_list = list(zip(assignment_data['task_id'], assignment_data['user_id']))
    
    # map all user_ids (values) to task_id (key) 
    task_users_dict = {}
    for task_id, user_id in task_user_list:
        previously_assigned = task_users_dict.get(task_id, set()) # get any user_ids already stored
        previously_assigned.add(user_id)
        task_users_dict[task_id] = previously_assigned
    return task_users_dict


def insert_assignments(assignment_info, db):
    log_step(logger, "insert_assignments enter", count=len(assignment_info) if assignment_info else 0)
    """
     * Helper function for match_users_and_tasks() *
    Takes a list of assignments and database (obj).
    Inserts the assignments into the database given. 
    Returns nothing.
    """
    # Connect to database & create cursor obj
    cursor = db.cursor()

    for assignment in assignment_info:
        # Create & execute query
        query = f"INSERT INTO assignments(`task_id`, `user_id`, `status`) VALUES \
            ({assignment['task_id']}, '{assignment['user_id']}', 'not assigned');"
        cursor.execute(query)

        # Commit the changes to the database
        db.commit()
    log_step(logger, "insert_assignments exit")

def get_unassigned_tasks(db, task_type):
    log_step(logger, "get_unassigned_tasks enter", task_type=task_type)
    cursor = db.cursor()
    cursor.execute(
        """SELECT tasks.id
           FROM tasks
           LEFT JOIN assignments ON tasks.id = assignments.task_id
           WHERE tasks.expired = 0
             AND tasks.task_type = %s
             AND tasks.id NOT IN (SELECT task_id FROM assignments)""",
        (task_type,),
    )
    out = set([tasks[0] for tasks in cursor.fetchall()])
    log_step(logger, "get_unassigned_tasks exit", count=len(out))
    return out


def get_verification_task_submitters(db, task_ids):
    log_step(logger, "get_verification_task_submitters enter", task_ids_count=len(task_ids) if task_ids else 0)
    if not task_ids:
        return {}
    cursor = db.cursor()
    placeholders = ",".join(["%s"] * len(task_ids))
    cursor.execute(
        f"""SELECT tasks.id, assignments.user_id
            FROM tasks
            INNER JOIN assignments ON tasks.assignment_id = assignments.id
            WHERE tasks.id IN ({placeholders})""",
        tuple(task_ids),
    )
    m = {row[0]: row[1] for row in cursor.fetchall()}
    log_step(logger, "get_verification_task_submitters exit", mapped=len(m))
    return m


def match_verification_tasks(task_ids, user_data, db):
    log_step(logger, "match_verification_tasks enter", task_count=len(task_ids) if task_ids else 0)
    import task_parameters
    allow_self = getattr(task_parameters, "ALLOW_SELF_VERIFICATION_FOR_TESTING", False)
    submitter_map = get_verification_task_submitters(db, task_ids)
    matchings = []
    for task_id in task_ids:
        submitter = submitter_map.get(task_id)
        if allow_self:
            available = user_data["id"]
        else:
            available = [uid for uid in user_data["id"] if uid != submitter]
        if not available:
            available = user_data["id"]
        user_id = random.choice(list(available))
        matchings.append([task_id, user_id])
    log_step(logger, "match_verification_tasks exit", matchings=len(matchings))
    return matchings

def create_ab_groups(user_list):
    middle_index = int(len(user_list)/2)
    a_group = user_list[:middle_index]
    b_group = user_list[middle_index:]
    return a_group, b_group

### ### ALGORITHMS ### ###
def algorithm_random(assignment_data, task_data, user_data):
    """
    * One of many possible matching algorithms for match_users_and_tasks()*
    Takes a list of all user ids & a list of all unassigned task ids.
    Randomly matches a user (who has never been previously assigned to this task) to each task.
    Returns a list of those user-task matches, format: [[task_id, user_id], [...], ...]
    """
    # Assemble task-user dict, key: task_id (int), value: ids of all previously-assigned users (set)
    task_users_dict = {} if not assignment_data else create_task_user_dict(assignment_data)

    # For each task, select a new random user_id 
    matchings = []
    for task_id in task_data:
        # Subtract all previously-assigned users from overall user pool
        available_user_ids = set(user_data['id']) - task_users_dict.get(task_id, set())

        # Assign & note matching
        user_id = random.choice(list(available_user_ids))
        matchings.append([task_id, user_id])

    return matchings

def algorithm_weighted(assignment_data, task_data, user_data):
    """
    * One of many possible matching algorithms for match_users_and_tasks()*
    Takes a list of all user ids & a list of all unassigned task ids.
    Matches a user (who has never been previously assigned to this task) to each task weighted on their reliability scores.
    Returns a list of those user-task matches, format: [[task_id, user_id], [...], ...]
    """
    # Assemble task-user dict, key: task_id (int), value: ids of all previously-assigned users (set)
    task_users_dict = {} if not assignment_data else create_task_user_dict(assignment_data)
    reliability_dict = {user_data['id'][i]:float(user_data['reliability'][i]) for i in range(len(user_data['id']))}
    
    # Split users into a-b groups
    # active_list = [user for user in reliability_dict if reliability_dict[user]> 0.1]
    # a_active, b_active = create_ab_groups(active_list)
    # inactive_list = [user for user in reliability_dict if reliability_dict[user]== 0.1]
    # a_inactive, b_inactive = create_ab_groups(inactive_list)
    # a_group = a_active + a_inactive
    # b_group = b_active + b_inactive
    # print("A GROUP: ", a_group)
    # print("B GROUP: ", b_group)
    # For each task, select a new random user_id 
    user_list = [user for user in reliability_dict]
    a_group, b_group = create_ab_groups(user_list)

    matchings = []
    count = 0
    half_task = int(len(task_data)/2)
    for task_id in task_data:
        if count <= half_task:
            # Subtract all previously-assigned users from overall user pool
            available_user_ids = set(b_group) - task_users_dict.get(task_id, set())
            reliability_list = [int(reliability_dict[user]*100) for user in available_user_ids]

            # Assign & note matching
            user_id = random.choices(list(available_user_ids), reliability_list)[0]
        else:
            available_user_ids = set(a_group) - task_users_dict.get(task_id, set())

            # Assign & note matching
            user_id = random.choice(list(available_user_ids))
        matchings.append([task_id, user_id])
        count += 1
    return matchings


### ### OVERALL MATCHING & ASSIGNMENT GENERATION ### ###
def match_users_and_tasks(matching_algo, db_name):
    log_step(logger, "match_users_and_tasks enter", db_name=db_name)
    """
    Takes 'users' table data & 'tasks' table data, and a matching algorithm (function).
    Finds unexpired & unassigned tasks, matches users to those tasks, writes those
        Assignments to the 'assignments' table.
    Returns nothing.
    """
    # Open database connection
    db = helper_functions.connectDB(db_name)

    # read in assignment, task, and user data
    assignment_data = read_table(db, 'assignments')
    # task_data = read_table(db, 'tasks')
    user_data = read_table(db, 'users')

    # Updates task expiration status
    cursor = db.cursor()
    cursor.execute(f"UPDATE tasks SET expired = 1 WHERE start_time + INTERVAL time_window minute < now()")
    
    data_tasks = get_unassigned_tasks(db, "data_collection")
    verification_tasks = get_unassigned_tasks(db, "verification")
    log_step(logger, "match_users_and_tasks unassigned", data_collection=len(data_tasks), verification=len(verification_tasks))

    if user_data:
        if data_tasks:
            task_user_matchings = matching_algo(assignment_data, data_tasks, user_data)
            all_assignments = [{'task_id': task_id, 'user_id': user_id} for task_id, user_id in task_user_matchings]
            insert_assignments(all_assignments, db)

        if verification_tasks:
            verification_matchings = match_verification_tasks(verification_tasks, user_data, db)
            verification_assignments = [{'task_id': task_id, 'user_id': user_id} for task_id, user_id in verification_matchings]
            insert_assignments(verification_assignments, db)

    # Close database connection
    log_step(logger, "match_users_and_tasks exit")
    db.close()



if __name__ == '__main__':
    import task_parameters
    db_name = helper_functions.get_env("DB_NAME", "")
    match_users_and_tasks(task_parameters.MATCHING_ALGO, db_name)
