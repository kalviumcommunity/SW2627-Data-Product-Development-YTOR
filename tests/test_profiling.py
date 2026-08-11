import json
from pathlib import Path

import pandas as pd

from src.profiling import (
    profile_nulls_and_duplicates,
    profile_numerical,
    profile_categorical,
    identify_issues,
    generate_profile_report,
)


def make_sample_df():
    return pd.DataFrame(
        {
            "id": [1, 1, 2, 3],
            "email": [None, "a@x.com", None, "b@x.com"],
            "revenue": [100.0, -5.0, 200.0, None],
            "category": ["A", "A", "B", "B"],
        }
    )


def test_nulls_and_duplicates():
    df = make_sample_df()
    profile = profile_nulls_and_duplicates(df)
    assert profile["per_column"]["email"]["null_count"] == 2
    # No exact duplicate rows in this sample
    assert profile["exact_duplicates"] == 0
    # But `id` column has a repeated value (id=1 appears twice)
    assert int(df.duplicated(subset=["id"]).sum()) == 1


def test_numerical_profile():
    df = make_sample_df()
    num = profile_numerical(df)
    assert "revenue" in num
    assert num["revenue"]["min"] == -5.0


def test_categorical_profile():
    df = make_sample_df()
    cats = profile_categorical(df, top_n=2)
    assert "category" in cats
    assert cats["category"]["distinct"] == 2


def test_identify_issues_and_report(tmp_path: Path):
    df = make_sample_df()
    issues = identify_issues(df, null_threshold=40.0, dup_threshold=10.0)
    # email has 50% nulls -> flagged
    assert any(i.get("type") == "High nulls" and i.get("column") == "email" for i in issues["issues"]) 

    # negative revenue present -> flagged
    assert any(i.get("type") == "Negative values" and i.get("column") == "revenue" for i in issues["issues"]) 

    report_path = tmp_path / "profile_report.json"
    report = generate_profile_report(df, name="sample", output_path=report_path)
    assert report_path.exists()
    with open(report_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["name"] == "sample"
