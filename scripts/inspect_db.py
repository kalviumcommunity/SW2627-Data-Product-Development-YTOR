import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'ytor.db')
print('DB path:', DB_PATH)
print('Exists:', os.path.exists(DB_PATH))
if os.path.exists(DB_PATH):
    print('Size (bytes):', os.path.getsize(DB_PATH))

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name").fetchall()
    if not rows:
        print('No tables or views found in sqlite_master')
    for name, objtype in rows:
        print(f"- {name} ({objtype})")
        try:
            cnt = cur.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
            print(f"  rows: {cnt}")
        except Exception as e:
            print(f"  rows: ERROR ({e})")
    conn.close()
except Exception as e:
    print('ERROR connecting to DB:', e)
    sys.exit(1)
