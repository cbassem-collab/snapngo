"""
Name: Sofia Kobayashi
Date: 06/07/2023
Description: General helper functions & environment set up for the overall Snap N Go connections.
"""
from run_logging import get_logger, log_step
from task_parameters import START_HOURS, END_HOURS

logger = get_logger(__name__)
logger.info("module loaded")

import os
from pathlib import Path
from dotenv import load_dotenv


def load_env():
    log_step(logger, "load_env enter")
    repo_root = Path(__file__).resolve().parent.parent
    env_path = repo_root / '.env'
    load_dotenv(dotenv_path=env_path)
    log_step(logger, "load_env exit", env_path=str(env_path))
    return env_path


def get_env(name, default=None):
    log_step(logger, "get_env", name=name, has_default=default is not None)
    if name not in os.environ:
        load_env()
    return os.environ.get(name, default)

import json
import sys
import time as _time
import pymysql
from flask import Flask


from datetime import datetime, time

def connectDB(dbName):
    log_step(logger, "connectDB enter", dbName_set=bool(dbName))
    """
     * General Helper Function * 
    Takes a database name (str).
    Returns a connection object to that database. This connection should eventually
        be closed with .close()
    """
    sql_pass = get_env("SQL_PASS")
    if not sql_pass:
        raise RuntimeError("SQL_PASS is not set. Check your .env file.")
    if not dbName:
        raise RuntimeError("DB_NAME is not set. Check your .env file.")
    # Connect to the database
    db = pymysql.connect(
        host='localhost',
        user='root', 
        password=sql_pass, 
        db=dbName
    )
    log_step(logger, "connectDB exit ok")
    return db


# code to open text file and read into a matrix
def read_file(fname):
    log_step(logger, "read_file enter", fname=fname)
    with open(fname, "r") as file:
        # Read the first line that contains the number of vertices
        numVertices = int(file.readline().strip())

        # Create a dictionary to store each vertex and its corresponding location description
        vertices = {}
        for _ in range(numVertices):
            line = file.readline().strip().split(",")
            vertices[line[0]] = line[1]

        # Create an empty matrix
        matrix = [[-1 for _ in range(numVertices)] for _ in range(numVertices)]

        # Next, read the edges and build the graph
        for line in file:
            # edge is a list of 3 values representing a pair of adjacent vertices and their distance
            edge = line.strip().split(",")
            v1, v2, distance = int(edge[0]), int(edge[1]), float(edge[2])

            # Update the matrix with the distance between v1 and v2
            matrix[v1-1][v2-1] = distance
            matrix[v2-1][v1-1] = distance

        # Return the matrix and the dictionary of vertices
        log_step(logger, "read_file exit", numVertices=numVertices)
        return matrix, vertices

def is_weekday_and_business_hours() -> bool:
    now = datetime.now()
    if now.strftime("%A").lower() in {"saturday", "sunday"}:
        return False
    t = now.time()
    return START_HOURS <= t <= END_HOURS

if __name__ == '__main__':
    pass

