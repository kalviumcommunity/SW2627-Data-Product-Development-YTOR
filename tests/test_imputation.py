import pandas as pd
from src.imputation import apply_imputation, analyze_missing_before


def make_df():
    return pd.DataFrame(
        {
            "customer_id": [1, 2, None, 4, 5],
            "amount": [100.0, None, 200.0, None, 500.0],
            "segment": ["A", "A", None, "B", "B"],
            "price": [10, None, 12, None, 15],
            "notes": [None, None, None, None, None],
        }
    )


def test_analyze_missing_before():
    df = make_df()
    summary = analyze_missing_before(df)
    assert summary["rows"] == 5
    assert summary["per_column"]["customer_id"]["null_count"] == 1


def test_apply_imputation_strategies():
    df = make_df()
    spec = {
        "customer_id": {"strategy": "drop", "reason": "identifier required"},
        "amount": {"strategy": "median", "reason": "median preserves distribution"},
        "segment": {"strategy": "mode", "reason": "most common segment"},
        "price": {"strategy": "ffill", "reason": "time series"},
        "notes": {"strategy": "fill_value", "value": "MISSING", "reason": "placeholder"},
    }

    res = apply_imputation(df, spec)
    new_df = res["df"]
    report = res["report"]

    # customer_id drop: originally 5 rows -> one missing -> 4 rows
    assert report["before"]["rows"] == 5
    assert report["after"]["rows"] == 4

    # amount median filled
    assert new_df["amount"].isna().sum() == 0

    # segment mode filled
    assert new_df["segment"].isna().sum() == 0

    # price ffill - first may still be NaN if leading NA
    assert new_df["price"].isna().sum() <= 1

    # notes filled with MISSING
    assert (new_df["notes"] == "MISSING").all()
