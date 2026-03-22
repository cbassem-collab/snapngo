"""
Name: Helen Mao
Date: 06/26/2023
Description: Maintenance file for Snap N Go. Can be used to apply immediate
        fix while the bot and connections file are running.
"""
import helper_functions
import matching_assignments
import task
import messenger
import bot

import time


import os
helper_functions.load_env()
from run_logging import get_logger, log_step, setup_error_logging

logger = get_logger(__name__)
setup_error_logging()
logger.info("module loaded")

import json
import requests
import copy
import pandas as pd
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler

from datetime import datetime, timedelta, time, date
#import schedule


### ### Control Center ### ###
DB_NAME = helper_functions.get_env("DB_NAME", "")

def add_new_users():
    user_store = bot.get_all_users_info()
    messenger.add_users(user_store)

def delete_invalid_submissions(user_id, task_id, assignment_id):
    message = []
    bot.send_messages(user_id, message, "invalid submission")
    return

def broadcast(block = None, text = None):
    active_users = messenger.get_active_users_list()
    for user_id in active_users:
        bot.send_messages(user_id, block = None, text = None)

def test_update_reliability(user_id):
    conn = helper_functions.connectDB(DB_NAME)
    cur = conn.cursor()
    date = datetime.today().strftime('%Y/%m/%d')
    print(date)
    query = f'''SELECT task_id
                FROM assignments
                WHERE (user_id = '{user_id}') and DATE(recommend_time) >= CURDATE() -1
            '''
    cur.execute(query)
    accepted = cur.fetchall()
    print(accepted)

def print_gemini_submission_summary(limit=20):
    """
    Print recent assignments that have an image — shows Gemini decision if present.
    Use when debugging verification without opening SQL.
    """
    conn = helper_functions.connectDB(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, user_id, task_id, submission_time,
                      gemini_decision, verified_at, verified_count,
                      LEFT(gemini_explanation, 80) AS reason_preview
               FROM assignments
               WHERE submission_time IS NOT NULL
               ORDER BY submission_time DESC
               LIMIT %s""",
            (limit,),
        )
        rows = cur.fetchall()
        for r in rows:
            print(r)
        log_step(logger, "maintenance print_gemini_summary", rows=len(rows))
    finally:
        conn.close()


def export_assignments_with_gemini(csv_file):
    """Export assignments with submission + Gemini columns for analysis."""
    conn = helper_functions.connectDB(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, task_id, user_id, submission_time,
                      gemini_decision, verified_at, verified_count, gemini_explanation
               FROM assignments
               WHERE submission_time IS NOT NULL"""
        )
        rows = cur.fetchall()
        df = pd.DataFrame(
            rows,
            columns=[
                "id", "task_id", "user_id", "submission_time",
                "gemini_decision", "verified_at", "verified_count", "gemini_explanation",
            ],
        )
        df.to_csv(csv_file, index=False)
        print(f"Exported {len(df)} rows to {csv_file}")
        log_step(logger, "maintenance export_assignments_with_gemini", path=csv_file, rows=len(df))
    finally:
        conn.close()


def export_table_to_csv(table_name, csv_file):
    # Connect to MySQL database
    conn = helper_functions.connectDB(DB_NAME)

    try:
        # Execute SQL query to fetch data from table
        with conn.cursor() as cursor:
            sql = f'SELECT * FROM {table_name}'
            cursor.execute(sql)
            result = cursor.fetchall()

        # Convert result to DataFrame
        df = pd.DataFrame(result)

        # Save DataFrame to CSV file with column names
        df.to_csv(csv_file, index=False)

        print(f"Table '{table_name}' exported to '{csv_file}' successfully.")

    finally:
        # Close database connection
        conn.close()



if __name__ == "__main__":
    add_new_users()
    # bot.send_messages('U080N4WDXK2', block = None, text = 'Hello world')
    export_table_to_csv('users', '../users.csv')
    export_table_to_csv('assignments', '../assignments.csv')
    export_table_to_csv('tasks', '../tasks.csv')
    export_table_to_csv('user_feedback', '../user_feedback.csv')
    print_gemini_submission_summary()
    print("DONE")