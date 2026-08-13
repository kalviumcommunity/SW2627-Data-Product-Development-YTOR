import os
import sys

# Ensure project root is on sys.path so `src` imports work when run from scripts/
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import DEFAULT_DB_PATH, init_db, load_cleaned_data_to_db, query_to_df

need_load = False

if not os.path.exists(DEFAULT_DB_PATH):
    need_load = True
else:
    try:
        query_to_df("SELECT 1 FROM orders_enriched LIMIT 1", db_path=DEFAULT_DB_PATH)
    except Exception as e:
        print('orders_enriched missing or query failed:', e)
        need_load = True

if need_load:
    print('Initializing schema and loading cleaned CSVs into DB...')
    init_db(db_path=DEFAULT_DB_PATH)
    summary = load_cleaned_data_to_db(db_path=DEFAULT_DB_PATH)
    print('Loaded tables:', summary)
else:
    print('DB appears complete. No action taken.')
