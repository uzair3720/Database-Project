"""
db.py
A single helper, get_db_connection(), used by every route that touches
the database. We open a fresh psycopg2 connection per request and the
route closes it in a try/finally. This is the simplest pattern; we are
not using pools or Flask's g object on purpose -- it keeps the data
access code easy to read in the viva.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

import config


def get_db_connection():
    """
    Open and return a new psycopg2 connection.

    We pass cursor_factory=RealDictCursor at connect time so every
    cursor we create later returns rows as plain Python dicts. That
    lets templates and route code do row['name'] instead of row[1],
    which is much easier to read.
    """
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )
    return conn
