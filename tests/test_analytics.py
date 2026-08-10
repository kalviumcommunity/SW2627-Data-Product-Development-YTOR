import os
import tempfile
import pytest
import pandas as pd
from src.trust_model import compute_seller_trust_score
from src.analytics import get_seller_summary_metrics, compute_historical_trust_trend, get_behavior_correlation_matrix
from src.generator import generate_dataset

def test_trust_score_bounds_and_tiering():
    # Test perfect seller
    res_perfect = compute_seller_trust_score(
        total_orders=100, misleading_returns=0, late_orders=0, cancelled_orders=0,
        total_reviews=50, negative_reviews=0, avg_support_days=1.0
    )
    assert res_perfect["trust_score"] == 100.0
    assert res_perfect["risk_tier"] == "Low Risk"
    
    # Test heavily flawed seller
    res_bad = compute_seller_trust_score(
        total_orders=100, misleading_returns=20, late_orders=30, cancelled_orders=25,
        total_reviews=40, negative_reviews=35, avg_support_days=10.0
    )
    assert res_bad["trust_score"] < 50.0
    assert res_bad["risk_tier"] == "Critical Risk"
    assert 0.0 <= res_bad["trust_score"] <= 100.0

@pytest.fixture
def populated_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "analytics_test.db")
    generate_dataset(db_path=db_path, num_days=60, seed=42)
    yield db_path

def test_get_seller_summary_metrics(populated_db):
    df_summary = get_seller_summary_metrics(db_path=populated_db, days_window=60)
    assert not df_summary.empty
    assert "trust_score" in df_summary.columns
    assert "risk_tier" in df_summary.columns
    assert "misleading_return_pct" in df_summary.columns
    
    # Verify risk tiers classification
    tiers = set(df_summary["risk_tier"])
    assert len(tiers) > 1  # Should have a mix of risk tiers

def test_historical_trust_trend(populated_db):
    df_trend = compute_historical_trust_trend(db_path=populated_db)
    assert not df_trend.empty
    assert "month" in df_trend.columns
    assert "trust_score" in df_trend.columns

def test_correlation_matrix(populated_db):
    df_summary = get_seller_summary_metrics(db_path=populated_db, days_window=60)
    corr = get_behavior_correlation_matrix(df_summary)
    assert not corr.empty
    assert "trust_score" in corr.columns
