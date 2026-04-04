"""
terminal command to get into SQL:
source .bash_profile
mysql -u root -p
to get slack running:
ngrok http 5000 (in one terminal)
run this file in another terminal
(both of these things need to happen in order to run)
"""
import helper_functions
from datetime import datetime

import os
helper_functions.load_env()
import json
import time as _time
from pathlib import Path

from run_logging import get_logger, log_step

logger = get_logger(__name__)
logger.info("module loaded")

### ### CONSTANTS ### ###
DB_NAME = helper_functions.get_env("DB_NAME", "")


def add_users(user_store):
    log_step(logger, "add_users enter", keys=len(user_store) if user_store else 0)
    '''
    Gets teh database connection. Returns nothing.
    Add users to the database based on the current list of users in the the workplace 
    '''
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    # user_store = get_all_users_info()
    query = '''INSERT IGNORE INTO users (name, id) VALUES (%s, %s)'''
    for key in user_store:
        not_bot = user_store[key]['is_bot'] == False
        not_slackbot = (key != 'USLACKBOT')
        deleted = user_store[key]['deleted']
        if not_bot and not_slackbot and (not deleted):
            name = user_store[key]['name']
            cur.execute(query, (name, key))
            conn.commit()
    conn.close()
    log_step(logger, "add_users exit")

def get_total_users():
    log_step(logger, "get_total_users enter")
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = "SELECT COUNT(id) FROM users WHERE `status` = 'active'"
    cur.execute(query)
    total_users = cur.fetchone()[0]
    log_step(logger, "get_total_users exit", total_users=total_users)
    return int(total_users)

def get_active_users_list():
    log_step(logger, "get_active_users_list enter")
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = "SELECT id FROM users WHERE `status` = 'active'"
    cur.execute(query)
    active_users_list = cur.fetchall()
    active_users = [user[0] for user in active_users_list]
    log_step(logger, "get_active_users_list exit", count=len(active_users))
    return active_users

def get_all_users_list():
    log_step(logger, "get_all_users_list enter")
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = "SELECT id FROM users"
    cur.execute(query)
    all_users_list = cur.fetchall()
    all_users = [user[0] for user in all_users_list]
    log_step(logger, "get_all_users_list exit", count=len(all_users))
    return all_users

def get_account_info(user_id):
    log_step(logger, "get_account_info enter", user_id=user_id)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f"SELECT compensation FROM users WHERE id = '{user_id}'"
    cur.execute(query)
    row = cur.fetchone()
    if not row:
        conn.close()
        log_step(logger, "get_account_info exit no user", user_id=user_id)
        return 0.0, []
    compensation = row[0]
    cur.execute("SHOW COLUMNS FROM assignments")
    columns = [r[0] for r in cur.fetchall()]
    if "checked" in columns:
        query = f"SELECT task_id FROM assignments WHERE user_id = '{user_id}' AND checked = 1 AND submission_time IS NOT NULL"
    else:
        query = f"SELECT task_id FROM assignments WHERE user_id = '{user_id}' AND submission_time IS NOT NULL"
    cur.execute(query)
    tasks = [task[0] for task in cur.fetchall()]
    conn.close()
    log_step(logger, "get_account_info exit", task_count=len(tasks))
    return compensation, tasks

def update_account_status(user_id, status):
    log_step(logger, "update_account_status enter", user_id=user_id, status=status)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET `status` = '{status}' WHERE id = '{user_id}'")
    conn.commit()
    conn.close
    log_step(logger, "update_account_status exit")

def add_account_compensation(user_id, compensation):
    log_step(logger, "add_account_compensation enter", user_id=user_id, compensation=compensation)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"UPDATE users SET `compensation` = compensation + {compensation} WHERE id = '{user_id}'")
    conn.commit()
    conn.close
    log_step(logger, "add_account_compensation exit")

def update_tasks_expired():
    log_step(logger, "update_tasks_expired enter")
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET `expired` = 1 WHERE (start_time + INTERVAL time_window MINUTE) < NOW()")
    conn.commit()
    conn.close
    log_step(logger, "update_tasks_expired exit")

def get_task_list(user_id, task_id):
    log_step(logger, "get_task_list enter", user_id=user_id, task_id=task_id)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''SELECT assignments.task_id, assignments.user_id, 
                tasks.location, tasks.description, tasks.start_time, tasks.time_window, 
                tasks.compensation, tasks.task_type, tasks.assignment_id
                FROM assignments INNER JOIN tasks ON assignments.task_id = tasks.id
                WHERE (assignments.task_id = {task_id} AND assignments.user_id = '{user_id}')'''
    cur.execute(query)
    assignment = cur.fetchone()
    conn.close()
    assert assignment, f"Assignment #{task_id} could not be found in database!"
    log_step(logger, "get_task_list exit ok")
    return assignment


def get_assignments(db_name):
    log_step(logger, "get_assignments enter", db_name=db_name)
    '''
    Get all the assignments with status 'not assigned' together with each task's details. 
    Create a dictionary with keys being user ids and values being a list of tasks (with
    details) that user is assigned
    Return the dictionary
    '''
    update_tasks_expired()
    conn = helper_functions.connectDB(db_name)
    cur = conn.cursor()
    query = '''SELECT assignments.task_id, assignments.user_id, 
                tasks.location, tasks.description, tasks.start_time, tasks.time_window, 
                tasks.compensation, tasks.task_type, tasks.assignment_id
                FROM assignments INNER JOIN tasks ON assignments.task_id = tasks.id
                WHERE (assignments.`status` = 'not assigned' AND tasks.expired != 1)'''
    cur.execute(query)
    assignments = cur.fetchall()
    conn.close()
    assignments_dict = {}
    for assignment in assignments:
        uid = assignment[1]
        if uid in assignments_dict:
            (assignments_dict[uid]).append(assignment)
        else:
            assignments_dict[uid] = [assignment]
    log_step(logger, "get_assignments exit", users=len(assignments_dict), total_assignments=len(assignments))
    return assignments_dict

def get_assign_status(task, user):
    log_step(logger, "get_assign_status enter", task=task, user=user)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''SELECT status FROM assignments
                WHERE task_id = {task} AND user_id = '{user}'
    '''
    cur.execute(query)
    status = cur.fetchone()[0]
    log_step(logger, "get_assign_status exit", status=status)
    return status


def mark_assignment_pending_for_user(task_id, user_id):
    """Set one assignment to pending after a targeted DM (e.g. on-demand `task` command)."""
    log_step(logger, "mark_assignment_pending_for_user enter", task_id=task_id, user_id=user_id)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """UPDATE assignments SET `status` = 'pending', recommend_time = NOW()
           WHERE task_id = %s AND user_id = %s""",
        (task_id, user_id),
    )
    conn.commit()
    conn.close()
    log_step(logger, "mark_assignment_pending_for_user exit")


def update_assign_status(status, task_id, user_id):
    log_step(logger, "update_assign_status enter", status=status, task_id=task_id, user_id=user_id)
    '''
    Takes database name, the new status of the assignment, the task id and 
        the user id. 
    Updates the database accordingly.  
        If new status is pending (only when called in ), then ignore task id and user id, update all
        
    Helper function to update assignment status,
    '''
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    if status == "pending":
        query = '''UPDATE assignments INNER JOIN tasks 
                ON assignments.task_id = tasks.id
                SET assignments.`status` = 'pending', recommend_time = NOW()
                WHERE (assignments.`status` = 'not assigned' AND tasks.expired != 1)
        '''
        cur.execute(query)
    elif status == "accepted" or status == "rejected":
        cur.execute(f"UPDATE assignments SET `status` = '{status}' WHERE task_id={task_id} AND user_id='{user_id}'")
    conn.commit()
    conn.close
    log_step(logger, "update_assign_status exit", status=status)

def get_accepted_tasks(user_id) -> list:
    log_step(logger, "get_accepted_tasks enter", user_id=user_id)
    """
    Takes a user id (int)
    Finds that user's assignment data.
    
    """
    update_tasks_expired()
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''SELECT DISTINCT assignments.task_id
                FROM assignments INNER JOIN tasks 
                ON assignments.task_id = tasks.id
                WHERE (assignments.user_id = '{user_id}') AND (assignments.`status` = 'accepted') AND (tasks.expired != 1) AND (img IS NULL)'''
    cur.execute(query)

    task_list = [int(task_id[0]) for task_id in cur.fetchall()]
    conn.close()
    log_step(logger, "get_accepted_tasks exit", count=len(task_list))
    return task_list

def get_pending_tasks(user_id) -> list:
    log_step(logger, "get_pending_tasks enter", user_id=user_id)
    """
    Takes a user id (int)
    Finds that user's assignment data.
    
    """
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    # query = f'''SELECT task_id FROM assignments 
    #             WHERE user_id = '{user_id}' AND `status` = 'pending'
    #         '''
    query = f'''SELECT DISTINCT assignments.task_id 
                FROM assignments INNER JOIN tasks
                ON assignments.task_id = tasks.id
                WHERE assignments.user_id = '{user_id}' AND assignments.`status` = 'pending' AND tasks.expired = 0
            '''
    cur.execute(query)
    task_list = [item[0] for item in cur.fetchall()]
    conn.close()
    log_step(logger, "get_pending_tasks exit", count=len(task_list))
    return task_list

def check_time_window(task_id):
    log_step(logger, "check_time_window enter", task_id=task_id)
    update_tasks_expired()
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    
    try:
        payload = {
            "sessionId": "15a5f2",
            "runId": "run1",
            "hypothesisId": "H9",
            "location": "messenger.py:check_time_window",
            "message": "check_time_window query",
            "data": {"task_id": task_id},
            "timestamp": int(_time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload) + "\n")
    except Exception:
        pass
    # endregion
    cur.execute("SELECT expired, (start_time<NOW()) FROM tasks WHERE id = %s", (task_id,))
    timing = cur.fetchone()
    if timing is None:
        log_step(logger, "check_time_window exit no_task", task_id=task_id)
        conn.close()
        return "not started"
    expired = timing[0]
    started = timing[1]
    conn.close()
    if expired == 1:
        log_step(logger, "check_time_window exit", result="expired")
        return "expired"
    elif started == 0:
        log_step(logger, "check_time_window exit", result="not started")
        return "not started"
    log_step(logger, "check_time_window exit", result="open")
    return "open"

def submit_task(user_id, task_id, path):
    log_step(logger, "submit_task enter", user_id=user_id, task_id=task_id, path_len=len(path) if path else 0)
    update_tasks_expired()
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT expired, (start_time<NOW()) FROM tasks WHERE id = {task_id}")
    timing = cur.fetchone()
    if timing is None:
        log_step(logger, "submit_task rejected no_task", task_id=task_id)
        conn.close()
        return {"ok": False}
    expired = timing[0]
    started = timing[1]
    if expired == 0 and started == 1:
        cur.execute(
            "SELECT submission_time FROM assignments WHERE user_id = %s AND task_id = %s",
            (user_id, task_id),
        )
        prior = cur.fetchone()
        already_submitted = prior and prior[0] is not None

        query = '''UPDATE assignments 
                    INNER JOIN users ON assignments.user_id = users.id
                    INNER JOIN tasks ON assignments.task_id = tasks.id
                SET assignments.img = %s, 
                    assignments.`submission_time` = NOW()
                WHERE (assignments.user_id = %s 
                    AND assignments.task_id = %s)
                '''
        cur.execute(query, (path, user_id, task_id))
        conn.commit()
        comp_amount = 0.0
        if not already_submitted:
            cur.execute("SELECT compensation FROM tasks WHERE id = %s", (task_id,))
            comp_row = cur.fetchone()
            comp_amount = float(comp_row[0]) if comp_row and comp_row[0] is not None else 0.0
        if comp_amount > 0 and not already_submitted:
            cur.execute(
                "UPDATE users SET compensation = compensation + %s WHERE id = %s",
                (comp_amount, user_id),
            )
            conn.commit()
            log_step(
                logger,
                "submit_task immediate compensation",
                user_id=user_id,
                task_id=task_id,
                amount=comp_amount,
            )
        conn.close()
        update_reliability(user_id)
        log_step(
            logger,
            "submit_task exit success",
            compensation_paid=comp_amount,
            already_submitted=already_submitted,
        )
        return {"ok": True, "compensation": comp_amount, "already_submitted": already_submitted}
    else:
        log_step(logger, "submit_task exit rejected", expired=expired, started=started)
        return {"ok": False}


def delete_submission(user_id, task_id):
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''UPDATE assignments
            SET img = NULL, submission_time = NULL
            WHERE user_id = {user_id} AND task_id = {task_id}
            '''
    cur.execute(query)
    conn.commit()
    conn.close()
    return
    
def check_all_assignments():
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''UPDATE assignments 
                INNER JOIN users ON assignments.user_id = users.id
                INNER JOIN tasks ON assignments.task_id = tasks.id
            SET users.compensation = users.compensation+ tasks.compensation,
                assignments.checked = 1
            WHERE (assignments.checked = 0 AND submission_time IS NOT NULL)
            '''
    cur.execute(query)
    conn.commit()
    conn.close()
    return

def update_reliability(user_id):
    log_step(logger, "update_reliability enter", user_id=user_id)
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''SELECT COUNT(status)
                FROM assignments
                WHERE status = 'accepted' and user_id = '{user_id}' and DATE(recommend_time) >= CURDATE() -1
            '''
    cur.execute(query)
    accepted = cur.fetchone()[0]
    if accepted == 0:
        new_reliability = 0.1
    else:
        query = f'''SELECT COUNT(img)
                    FROM assignments
                    WHERE img IS NOT NULL and user_id = '{user_id}' and DATE(recommend_time) >= CURDATE() -1
                '''
        cur.execute(query)
        submissions = cur.fetchone()[0]
        if submissions == 0:
            new_reliability = 0.1
        else:
            new_reliability = round(submissions/accepted, 2)
    cur.execute(
        "SELECT reliability FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        log_step(logger, "update_reliability skip no user", user_id=user_id)
        conn.close()
        return
    old_reliability = float(row[0]) if row[0] is not None else 0.5
    new_reliability = float(new_reliability)
    reliability = old_reliability * 0.3 + new_reliability * 0.7
    print(user_id, reliability)
    cur.execute(
        "UPDATE users SET reliability = %s WHERE id = %s",
        (reliability, user_id),
    )
    conn.commit()
    conn.close()
    log_step(logger, "update_reliability exit", user_id=user_id, reliability=reliability)
    return

        
def update_reliability_old(user_id):
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    query = f'''SELECT COUNT(status)
                FROM assignments
                WHERE status = 'accepted' and user_id = '{user_id}'
            '''
    cur.execute(query)
    accepted = cur.fetchone()[0]
    if accepted == 0:
        reliability = 0.1
    else:
        query = f'''SELECT COUNT(img)
                    FROM assignments
                    WHERE img IS NOT NULL and user_id = '{user_id}'
                '''
        cur.execute(query)
        submissions = cur.fetchone()[0]
        if submissions == 0:
            reliability = 0.1
        else:
            reliability = round(submissions/accepted, 2)
    print(user_id, reliability)
    query = f'''UPDATE users 
            SET reliability = {reliability}
            WHERE id = '{user_id}'
            '''
    cur.execute(query)
    conn.commit()
    conn.close()
    return

if __name__ == "__main__":
    pass

