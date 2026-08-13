import os
import tempfile
import pytest
import pandas as pd
from src.db import init_db, get_connection, query_to_df, load_cleaned_data_to_db, DEFAULT_DB_PATH
from src.generator import generate_dataset

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ytor.db")
    init_db(db_path)
    yield db_path

def test_db_schema_initialization(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view');")
    objects = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    expected = ["sellers", "products", "orders", "returns", "reviews", "seller_trust_snapshots"]
    for obj in expected:
        assert obj in objects

def test_load_cleaned_data_to_db(temp_db):
    summary = load_cleaned_data_to_db(db_path=temp_db)
    assert "orders" in summary
    assert "sellers" in summary
    assert summary["orders"] > 0
    
    df_sellers = query_to_df("SELECT * FROM sellers", db_path=temp_db)
    assert not df_sellers.empty

def test_generator_and_query_df(temp_db):
    generate_dataset(db_path=temp_db, num_days=30, seed=123)
    
    df_sellers = query_to_df("SELECT * FROM sellers", db_path=temp_db)
    assert not df_sellers.empty
    assert len(df_sellers) > 10
    
    df_orders = query_to_df("SELECT * FROM orders", db_path=temp_db)
    assert not df_orders.empty
    assert "order_id" in df_orders.columns

def test_query_to_df_bindings(temp_db):
    generate_dataset(db_path=temp_db, num_days=10, seed=42)
    # Test query without params passing db_path as keyword arg
    df = query_to_df("SELECT * FROM sellers LIMIT 100", db_path=temp_db)
    assert not df.empty
    
    # Test query with params passing db_path as keyword arg
    first_seller_id = df["seller_id"].iloc[0]
    df_param = query_to_df("SELECT * FROM sellers WHERE seller_id = ?", params=(first_seller_id,), db_path=temp_db)
    assert len(df_param) == 1


