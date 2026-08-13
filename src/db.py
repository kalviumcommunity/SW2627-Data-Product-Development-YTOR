import os
import sqlite3
from typing import Optional
import pandas as pd

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ytor.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "schema.sql")
CLEANED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cleaned")

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection object with row factory set."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH, schema_path: str = SCHEMA_PATH) -> None:
    """Initializes the database schema."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT type FROM sqlite_master WHERE name='returns'")
    row = cur.fetchone()
    if row:
        cur.execute(f"DROP {row[0].upper()} IF EXISTS returns")
        conn.commit()
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    conn.close()

def load_cleaned_data_to_db(db_path: str = DEFAULT_DB_PATH, cleaned_dir: str = CLEANED_DIR) -> dict:
    """Imports all cleaned CSV files from data/cleaned/ into SQLite tables."""
    conn = get_connection(db_path)
    
    if not os.path.exists(cleaned_dir):
        conn.close()
        raise FileNotFoundError(f"Cleaned directory not found: {cleaned_dir}")
        
    loaded_summary = {}
    csv_files = [f for f in os.listdir(cleaned_dir) if f.endswith("_cleaned.csv")]
    
    for filename in sorted(csv_files):
        table_name = filename.replace("_cleaned.csv", "")
        file_path = os.path.join(cleaned_dir, filename)
        
        # Read CSV and load to SQLite
        df = pd.read_csv(file_path, low_memory=False)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        loaded_summary[table_name] = len(df)
        
    conn.commit()
    
    # Re-apply schema script to ensure views (returns) and indexes are created
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        cur = conn.cursor()
        cur.execute("SELECT type FROM sqlite_master WHERE name='returns'")
        row = cur.fetchone()
        if row:
            obj_type = row[0]
            cur.execute(f"DROP {obj_type.upper()} IF EXISTS returns")
        conn.executescript(schema_sql)
        conn.commit()
        
    conn.close()
    return loaded_summary

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

