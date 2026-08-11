import pandas as pd
import pytest

from src.type_enforcement import (
    enforce_datetime_column,
    enforce_currency_to_float,
    enforce_int_to_bool,
    enforce_types,
)


def test_enforce_datetime_success_and_failure():
    df = pd.DataFrame({"ts": ["2025-01-15", "2024-12-31", "bad-date", None]})
    # use coercion so we can inspect partial conversion
    report = enforce_datetime_column(df, "ts", fmt="%Y-%m-%d", errors="coerce", fail_on_error=False)
    assert report["status"] == "partial"
    assert report["converted_count"] == 2
    # Now insist on raising for bad values
    with pytest.raises(ValueError):
        enforce_datetime_column(pd.DataFrame({"ts": ["2025-01-15", "bad"]}), "ts", fmt="%Y-%m-%d", errors="coerce", fail_on_error=True)


def test_enforce_currency_to_float():
    df = pd.DataFrame({"price": ["$1,000.50", "€200,00", "300", "bad"]})
    report = enforce_currency_to_float(df, "price", currency_symbols=["$", "€"], thousands_sep=",", decimal=".", fail_on_error=False)
    # Expect partial because 'bad' cannot be converted
    assert report["status"] == "partial"
    assert df["price"].dtype.name in ("float64", "Float64")


def test_enforce_int_to_bool():
    df = pd.DataFrame({"flag": [1, 0, "yes", "no", "unknown"]})
    report = enforce_int_to_bool(df, "flag", fail_on_error=False)
    # unknown maps to <NA>
    assert report["status"] == "partial"
    assert df["flag"].dtype.name == "boolean"


def test_enforce_types_dispatcher():
    df = pd.DataFrame({
        "d": ["2025-01-01", "2025-01-02"],
        "amt": ["$10", "$20"],
        "f": [1, 0],
    })
    spec = {
        "d": {"type": "datetime", "format": "%Y-%m-%d", "errors": "raise"},
        "amt": {"type": "currency", "symbols": ["$"]},
        "f": {"type": "bool"},
    }
    reports = enforce_types(df, spec, fail_on_error=False)
    assert reports["d"]["status"] == "success"
    assert reports["amt"]["status"] == "success"
    assert reports["f"]["status"] == "success"
