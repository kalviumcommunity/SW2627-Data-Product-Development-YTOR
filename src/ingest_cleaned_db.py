import os
import sys

# Ensure src module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.db import load_cleaned_data_to_db, DEFAULT_DB_PATH, CLEANED_DIR

def main():
    print(f"Loading cleaned datasets from '{CLEANED_DIR}' into SQLite DB '{DEFAULT_DB_PATH}'...")
    summary = load_cleaned_data_to_db(db_path=DEFAULT_DB_PATH, cleaned_dir=CLEANED_DIR)
    
    print("\nDatabase Ingestion Complete! Loaded Tables:")
    print("=" * 50)
    for table_name, row_count in summary.items():
        print(f" - Table '{table_name:25s}': {row_count:,} rows")
    print("=" * 50)

if __name__ == "__main__":
    main()
