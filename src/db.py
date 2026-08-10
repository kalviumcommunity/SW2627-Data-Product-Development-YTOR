import os
import sqlite3
from typing import Optional
import pandas as pd

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ytor.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "schema.sql")

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection object with row factory set."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH, schema_path: str = SCHEMA_PATH) -> None:
    """Initializes the database schema."""
    conn = get_connection(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

def query_to_df(query: str, params: Optional[tuple] = None, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Executes a SQL query and returns the results as a pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
    finally:
        conn.close()
    return df

def execute_script(script: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Executes a raw SQL script."""
    conn = get_connection(db_path)
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()
